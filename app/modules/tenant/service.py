from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.core.clock import ClockProtocol
from app.core.config import Settings
from app.modules.tenant.catalog import (
    APPROVED_PLAN_CODES,
    APPROVED_PLAN_DEFINITIONS,
    is_approved_active_plan,
)
from app.modules.tenant.models import CheckoutIntent, EventoFacturacion, Plan
from app.modules.tenant.ports import (
    ActivationNotifier,
    CheckoutAccessPolicy,
    DemoCheckoutAccessPolicy,
    FirstAdminIdentityHook,
    WebhookSignatureVerifier,
)
from app.modules.tenant.repository import (
    CheckoutAlreadyProvisionedError,
    CheckoutMismatchError,
    CheckoutNotAvailableError,
    IdempotencyConflictError,
    OnboardingCommand,
    OnboardingNotProvisionedError,
)
from app.modules.tenant.schemas import (
    ActivarPruebaRequest,
    ActivationRequest,
    ActivationResponse,
    AltaTenantRequest,
    AltaTenantResponse,
    CambiarPlanRequest,
    CancelarSuscripcionRequest,
    CheckoutRequest,
    CheckoutResponse,
    PlanCatalogItem,
    SuscribirRequest,
    SuscripcionResponse,
    WebhookRequest,
    WebhookResponse,
)
from app.modules.tenant.signatures import HMACWebhookSignatureVerifier, SignatureValidationError


class EventoDuplicadoError(Exception):
    """Lanzado cuando se intenta procesar un evento de pago que ya existe."""


class CatalogUnavailableError(RuntimeError):
    pass


class PlanNotAvailableError(LookupError):
    pass


class WebhookPayloadValidationError(ValueError):
    def __init__(self, errors: list[dict[str, object]]) -> None:
        self.errors = errors


ActivationUnavailableError = type("ActivationUnavailableError", (LookupError,), {})


class _Noop:
    def deliver(self, tenant_id, email, token, expires_at) -> None:
        del tenant_id, email, token, expires_at

    def on_activation_consumed(self, tenant_id, email) -> None:
        del tenant_id, email


class TenantService:
    def __init__(
        self,
        repository: Any,
        clock: ClockProtocol,
        settings: Settings | None = None,
        checkout_access_policy: CheckoutAccessPolicy | None = None,
        signature_verifier: WebhookSignatureVerifier | None = None,
        activation_notifier: ActivationNotifier | None = None,
        identity_hook: FirstAdminIdentityHook | None = None,
    ):
        self.repository: Any = repository
        self.clock = clock
        self.settings = settings or Settings()
        self.checkout_access_policy = checkout_access_policy or DemoCheckoutAccessPolicy(
            self.settings.app_env
        )
        self.signature_verifier = signature_verifier or HMACWebhookSignatureVerifier(
            self.settings.billing_webhook_secret,
            self.settings.webhook_tolerance_seconds,
        )
        self.activation_notifier = activation_notifier or _Noop()
        self.identity_hook = identity_hook or _Noop()

    def listar_catalogo(self) -> list[PlanCatalogItem]:
        plans: dict[str, Plan] = {}
        for plan in self.repository.listar_planes():
            if plan.codigo not in APPROVED_PLAN_CODES:
                continue
            if not is_approved_active_plan(plan) or plan.codigo in plans:
                raise CatalogUnavailableError
            plans[plan.codigo] = plan
        if set(plans) != set(APPROVED_PLAN_CODES):
            raise CatalogUnavailableError
        return [self._project_plan(plans[d.codigo]) for d in APPROVED_PLAN_DEFINITIONS]

    def crear_checkout(self, request: CheckoutRequest) -> CheckoutResponse:
        self.checkout_access_policy.authorize(None)
        plan = self.repository.buscar_plan(request.plan_id)
        if plan is None or not is_approved_active_plan(plan):
            raise PlanNotAvailableError
        catalog = self.listar_catalogo()
        nombre = request.nombre_empresa.strip()
        correo = str(request.correo_admin).strip().lower()
        if not nombre or not correo:
            raise ValueError("Los datos del checkout no son válidos.")
        checkout = CheckoutIntent(
            id=uuid4(),
            plan_id=plan.id,
            nombre_empresa=nombre,
            correo_admin=correo,
            estado="confirmado",
            creado_en=self.clock.now(),
        )
        saved = self.repository.crear_checkout(checkout)
        return CheckoutResponse(
            checkout_id=saved.id,
            estado="confirmado",
            simulado=True,
            plan=next(item for item in catalog if item.plan_id == saved.plan_id),
        )

    @staticmethod
    def _project_plan(plan: Plan) -> PlanCatalogItem:
        if plan.codigo is None or plan.max_agents is None:
            raise CatalogUnavailableError
        return PlanCatalogItem(
            plan_id=plan.id,
            codigo=plan.codigo,
            nombre=plan.nombre,
            precio_bob=plan.precio_bob,
            moneda="BOB",
            max_agents=plan.max_agents,
            cuota_almacenamiento_gb=plan.cuota_almacenamiento_gb,
            cuota_inmuebles=plan.cuota_inmuebles,
            cuota_reconstrucciones_mes=plan.cuota_reconstrucciones_mes,
        )

    @staticmethod
    def _validation_errors(error: ValidationError) -> list[dict[str, object]]:
        return [
            {
                "loc": list(item.get("loc", ())),
                "msg": item.get("msg", "Invalid request"),
                "type": item.get("type", "value_error"),
            }
            for item in error.errors()
        ]

    def procesar_webhook(self, raw_body: bytes, timestamp: str, signature: str) -> WebhookResponse:
        now = self.clock.now()
        self.signature_verifier.verify(
            raw_body, timestamp, signature, self._signature_validation_time(timestamp, now)
        )
        payload_hash = hashlib.sha256(raw_body).hexdigest()
        try:
            payload = WebhookRequest.model_validate_json(raw_body)
        except ValidationError as error:
            raise WebhookPayloadValidationError(self._validation_errors(error)) from error

        existing = self.repository.buscar_evento_por_clave(payload.idempotency_key)
        if existing is not None:
            if existing.payload_hash is None or not hmac.compare_digest(
                existing.payload_hash, payload_hash
            ):
                raise IdempotencyConflictError
            return self._project_onboarding(self.repository.resultado_evento(existing), True)

        try:
            timestamp_epoch = int(timestamp)
            now_epoch = int(now.timestamp())
        except (TypeError, ValueError, OverflowError, OSError):
            raise SignatureValidationError from None
        if abs(now_epoch - timestamp_epoch) > self.settings.webhook_tolerance_seconds:
            raise SignatureValidationError

        checkout = self.repository.buscar_checkout(payload.checkout_id)
        if checkout is None:
            raise CheckoutNotAvailableError
        if checkout.estado not in {"confirmado", "procesado"}:
            raise CheckoutNotAvailableError
        plan = self.repository.buscar_plan(checkout.plan_id)
        if plan is None or not is_approved_active_plan(plan):
            raise CheckoutNotAvailableError
        if checkout.plan_id != payload.plan_id or Decimal(str(plan.precio_bob)).quantize(
            Decimal("0.01")
        ) != payload.monto_bob.quantize(Decimal("0.01")):
            raise CheckoutMismatchError

        token = uuid4().hex
        tenant_id, suscripcion_id, invitacion_id, evento_id = (uuid4() for _ in range(4))
        command = OnboardingCommand(
            idempotency_key=payload.idempotency_key,
            payload_hash=payload_hash,
            payload_firmado=raw_body.decode("utf-8"),
            checkout_id=payload.checkout_id,
            plan_id=payload.plan_id,
            monto_bob=payload.monto_bob.quantize(Decimal("0.01")),
            tenant_id=tenant_id,
            suscripcion_id=suscripcion_id,
            invitacion_id=invitacion_id,
            evento_id=evento_id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            token=token,
            ahora=now,
            expira_en=now + timedelta(days=self.settings.activation_ttl_days),
        )
        try:
            result = self.repository.provision_onboarding(command)
        except (
            CheckoutNotAvailableError,
            CheckoutMismatchError,
            CheckoutAlreadyProvisionedError,
            IdempotencyConflictError,
            OnboardingNotProvisionedError,
        ):
            raise
        except Exception as error:
            raise OnboardingNotProvisionedError from error
        if result.created and result.token:
            try:
                self.activation_notifier.deliver(
                    result.tenant_id, result.correo, result.token, result.expira_en
                )
            except Exception:
                pass
        return self._project_onboarding(result, not result.created)

    @staticmethod
    def _signature_validation_time(timestamp: str, now: datetime) -> datetime:
        try:
            return datetime.fromtimestamp(int(timestamp), UTC)
        except (TypeError, ValueError, OverflowError, OSError):
            return now

    @staticmethod
    def _project_onboarding(result: Any, idempotente: bool) -> WebhookResponse:
        return WebhookResponse(
            evento_id=result.evento_id,
            tenant_id=result.tenant_id,
            suscripcion_id=result.suscripcion_id,
            estado_tenant=result.estado_tenant,
            estado_evento=result.estado_evento,
            activacion_admin=result.activacion_admin,
            idempotente=idempotente,
        )

    def consumir_activacion(self, request: ActivationRequest) -> ActivationResponse:
        token_hash = hashlib.sha256(request.token.encode()).hexdigest()
        try:
            activation = self.repository.consumir_activacion(token_hash, self.clock.now())
        except OnboardingNotProvisionedError:
            raise
        except Exception as error:
            raise OnboardingNotProvisionedError from error
        if activation is None:
            raise ActivationUnavailableError
        try:
            self.identity_hook.on_activation_consumed(activation.tenant_id, activation.correo)
        except Exception:
            pass
        return ActivationResponse(tenant_id=activation.tenant_id, estado="consumida")

    # =======================================================
    # HU-004: Alta de inmobiliaria
    # =======================================================
    def dar_de_alta(self, request: AltaTenantRequest) -> AltaTenantResponse:
        del request
        raise OnboardingNotProvisionedError(
            "El aprovisionamiento de HU-004 requiere un webhook autenticado."
        )

    # =======================================================
    # HU-005: Activar prueba y suscribirse
    # =======================================================
    def activar_prueba(self, request: ActivarPruebaRequest) -> SuscripcionResponse:
        suscripcion = self.repository.buscar_suscripcion(request.tenant_id)
        if not suscripcion:
            raise ValueError("Suscripción no encontrada.")

        if suscripcion.trial_fin is not None:
            raise ValueError("La prueba ya fue activada previamente.")

        ahora = self.clock.now()
        suscripcion.estado = "trialing"
        suscripcion.trial_fin = ahora + timedelta(days=14)

        suscripcion_guardada = self.repository.guardar_suscripcion(suscripcion)
        return SuscripcionResponse.model_validate(suscripcion_guardada)

    def suscribirse(self, request: SuscribirRequest) -> SuscripcionResponse:
        if self.repository.evento_procesado(request.idempotency_key):
            raise EventoDuplicadoError("El pago mensual ya fue procesado.")

        suscripcion = self.repository.buscar_suscripcion(request.tenant_id)
        if not suscripcion:
            raise ValueError("Suscripción no encontrada.")

        ahora = self.clock.now()
        suscripcion.estado = "active"
        suscripcion.plan_id = request.plan_id
        suscripcion.periodo_fin = ahora + timedelta(days=30)

        nuevo_evento = EventoFacturacion(
            id=uuid4(),
            suscripcion_id=suscripcion.id,
            tipo="suscripcion_mensual",
            payload_firmado=request.payload_firmado,
            idempotency_key=request.idempotency_key,
            estado="procesado",
        )

        self.repository.registrar_evento_facturacion(nuevo_evento)
        suscripcion_guardada = self.repository.guardar_suscripcion(suscripcion)
        return SuscripcionResponse.model_validate(suscripcion_guardada)

    # =======================================================
    # HU-006: Gestionar suscripción y purga
    # =======================================================
    def cambiar_plan(self, request: CambiarPlanRequest) -> SuscripcionResponse:
        suscripcion = self.repository.buscar_suscripcion(request.tenant_id)
        if not suscripcion:
            raise ValueError("Suscripción no encontrada.")

        plan = self.repository.buscar_plan(request.nuevo_plan_id)
        if not plan:
            raise ValueError("El nuevo plan no existe.")

        suscripcion.plan_id = plan.id
        suscripcion_guardada = self.repository.guardar_suscripcion(suscripcion)
        return SuscripcionResponse.model_validate(suscripcion_guardada)

    def cancelar_suscripcion(self, request: CancelarSuscripcionRequest) -> SuscripcionResponse:
        suscripcion = self.repository.buscar_suscripcion(request.tenant_id)
        if not suscripcion:
            raise ValueError("Suscripción no encontrada.")

        suscripcion.estado = "canceled_read_only"
        suscripcion.cancelado_en = self.clock.now()

        suscripcion_guardada = self.repository.guardar_suscripcion(suscripcion)
        return SuscripcionResponse.model_validate(suscripcion_guardada)

    def ejecutar_purga_mensual(self) -> dict:
        ahora = self.clock.now()
        fecha_limite = ahora - timedelta(days=30)

        suscripciones_a_purgar = self.repository.obtener_suscripciones_para_purgar(fecha_limite)

        contador = 0
        for suscripcion in suscripciones_a_purgar:
            suscripcion.estado = "purged"
            self.repository.guardar_suscripcion(suscripcion)
            contador += 1

        return {"mensaje": f"Se purgaron {contador} suscripciones exitosamente."}
