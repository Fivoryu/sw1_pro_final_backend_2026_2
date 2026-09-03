from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.tenant.catalog import is_approved_active_plan
from app.modules.tenant.models import (
    CheckoutIntent,
    EventoFacturacion,
    Invitacion,
    Plan,
    Suscripcion,
    Tenant,
)


class DuplicateEventError(Exception):
    """Lanzado cuando el evento de pago simulado ya existe en la base de datos."""


CheckoutNotAvailableError = type("CheckoutNotAvailableError", (Exception,), {})
CheckoutMismatchError = type("CheckoutMismatchError", (Exception,), {})
CheckoutAlreadyProvisionedError = type("CheckoutAlreadyProvisionedError", (Exception,), {})
IdempotencyConflictError = type("IdempotencyConflictError", (Exception,), {})
OnboardingNotProvisionedError = type("OnboardingNotProvisionedError", (Exception,), {})


@dataclass(frozen=True, slots=True)
class OnboardingCommand:
    idempotency_key: str
    payload_hash: str
    payload_firmado: str
    checkout_id: UUID
    plan_id: UUID
    monto_bob: Decimal
    tenant_id: UUID
    suscripcion_id: UUID
    invitacion_id: UUID
    evento_id: UUID
    token_hash: str
    token: str
    ahora: datetime
    expira_en: datetime


def _money(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


class TenantRepository:
    def __init__(self, session: Session):
        self.session = session

    def _find(self, model: Any, condition: Any, lock: bool = False) -> Any:
        statement = select(model).where(condition)
        if lock:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        return self.session.scalar(statement)

    def listar_planes(self) -> list[Plan]:
        return list(self.session.scalars(select(Plan)).all())

    def crear_checkout(self, checkout: CheckoutIntent) -> CheckoutIntent:
        self.session.add(checkout)
        try:
            self.session.flush()
            self.session.commit()
            self.session.refresh(checkout)
            return checkout
        except IntegrityError:
            self.session.rollback()
            raise

    def buscar_evento_por_clave(self, key: str) -> EventoFacturacion | None:
        return self._find(EventoFacturacion, EventoFacturacion.idempotency_key == key)

    def buscar_checkout(self, checkout_id: UUID) -> CheckoutIntent | None:
        return self._find(CheckoutIntent, CheckoutIntent.id == checkout_id)

    def resultado_evento(self, evento: EventoFacturacion) -> Any:
        if evento.checkout_id is None or evento.payload_hash is None:
            raise IdempotencyConflictError
        row = self.session.execute(
            select(Suscripcion, Tenant, Invitacion)
            .join(Tenant, Tenant.id == Suscripcion.tenant_id)
            .join(Invitacion, Invitacion.tenant_id == Tenant.id)
            .where(Suscripcion.id == evento.suscripcion_id)
            .order_by(Invitacion.id)
        ).first()
        if row is None:
            raise OnboardingNotProvisionedError
        subscription, tenant, invitation = row
        return SimpleNamespace(
            evento_id=evento.id,
            tenant_id=tenant.id,
            suscripcion_id=subscription.id,
            estado_tenant=tenant.estado,
            estado_evento=evento.estado,
            # Replay projects the original onboarding result, not current activation state.
            activacion_admin="pendiente",
            created=False,
            token=None,
            correo=invitation.correo,
            expira_en=invitation.expira_en,
        )

    def _replay(self, evento: EventoFacturacion, payload_hash: str) -> Any:
        if evento.payload_hash is None or not hmac.compare_digest(
            evento.payload_hash, payload_hash
        ):
            raise IdempotencyConflictError
        return self.resultado_evento(evento)

    def _records(self, command: OnboardingCommand, checkout: CheckoutIntent) -> tuple[Any, ...]:
        tenant = Tenant(
            id=command.tenant_id,
            nombre=checkout.nombre_empresa,
            estado="activo",
            creado_en=command.ahora,
        )
        subscription = Suscripcion(
            id=command.suscripcion_id,
            tenant_id=tenant.id,
            plan_id=checkout.plan_id,
            estado="active",
            trial_fin=None,
            periodo_fin=None,
            cancelado_en=None,
        )
        invitation = Invitacion(
            id=command.invitacion_id,
            tenant_id=tenant.id,
            correo=checkout.correo_admin,
            token_unico=command.token_hash,
            expira_en=command.expira_en,
            estado="pendiente",
            consumido_en=None,
        )
        event = EventoFacturacion(
            id=command.evento_id,
            suscripcion_id=subscription.id,
            checkout_id=checkout.id,
            tipo="tenant.onboarding.succeeded",
            payload_firmado=command.payload_firmado,
            payload_hash=command.payload_hash,
            idempotency_key=command.idempotency_key,
            estado="procesado",
        )
        return tenant, subscription, invitation, event

    def provision_onboarding(self, command: OnboardingCommand) -> Any:
        return self._provision_onboarding(command)

    def _provision_onboarding(self, command: OnboardingCommand, retry: bool = False) -> Any:
        try:
            existing = self._find(
                EventoFacturacion,
                EventoFacturacion.idempotency_key == command.idempotency_key,
                lock=True,
            )
            if existing is not None:
                return self._replay(existing, command.payload_hash)
            checkout = self._find(
                CheckoutIntent, CheckoutIntent.id == command.checkout_id, lock=True
            )
            if checkout is None:
                raise CheckoutNotAvailableError
            if checkout.estado == "procesado":
                existing = self._find(
                    EventoFacturacion,
                    EventoFacturacion.idempotency_key == command.idempotency_key,
                    lock=True,
                )
                if existing is not None:
                    return self._replay(existing, command.payload_hash)
                raise CheckoutAlreadyProvisionedError
            if checkout.estado != "confirmado":
                raise CheckoutNotAvailableError
            plan = self._find(Plan, Plan.id == checkout.plan_id, lock=True)
            if plan is None or not is_approved_active_plan(plan):
                raise CheckoutNotAvailableError
            if checkout.plan_id != command.plan_id or _money(plan.precio_bob) != _money(
                command.monto_bob
            ):
                raise CheckoutMismatchError
            if self._find(
                EventoFacturacion, EventoFacturacion.checkout_id == checkout.id, lock=True
            ):
                raise CheckoutAlreadyProvisionedError
            tenant, subscription, invitation, event = self._records(command, checkout)
            self.session.add(tenant)
            self.session.flush()
            self.session.add(subscription)
            self.session.flush()
            self.session.add(invitation)
            self.session.add(event)
            checkout.estado = "procesado"
            self.session.flush()
            self.session.commit()
            return SimpleNamespace(
                evento_id=event.id,
                tenant_id=tenant.id,
                suscripcion_id=subscription.id,
                estado_tenant=tenant.estado,
                estado_evento=event.estado,
                activacion_admin=invitation.estado,
                created=True,
                token=command.token,
                correo=invitation.correo,
                expira_en=invitation.expira_en,
            )
        except (
            CheckoutNotAvailableError,
            CheckoutMismatchError,
            CheckoutAlreadyProvisionedError,
            IdempotencyConflictError,
        ):
            self.session.rollback()
            raise
        except IntegrityError as error:
            self.session.rollback()
            existing = self.buscar_evento_por_clave(command.idempotency_key)
            if existing is not None:
                return self._replay(existing, command.payload_hash)
            if self._find(EventoFacturacion, EventoFacturacion.checkout_id == command.checkout_id):
                raise CheckoutAlreadyProvisionedError from error
            if not retry:
                return self._provision_onboarding(command, retry=True)
            raise OnboardingNotProvisionedError from error
        except SQLAlchemyError as error:
            self.session.rollback()
            raise OnboardingNotProvisionedError from error
        except Exception as error:
            self.session.rollback()
            raise OnboardingNotProvisionedError from error

    def consumir_activacion(self, token_hash: str, now: datetime) -> Any:
        statement = (
            update(Invitacion)
            .where(
                Invitacion.token_unico == token_hash,
                Invitacion.estado == "pendiente",
                Invitacion.expira_en > now,
            )
            .values(estado="consumida", consumido_en=now)
            .returning(
                Invitacion.tenant_id,
                Invitacion.correo,
            )
        )
        try:
            row = self.session.execute(statement).first()
            self.session.commit()
            return None if row is None else SimpleNamespace(tenant_id=row[0], correo=row[1])
        except SQLAlchemyError as error:
            self.session.rollback()
            raise OnboardingNotProvisionedError from error

    # =======================================================
    # HU-004: Alta de inmobiliaria
    # =======================================================
    def evento_procesado(self, idempotency_key: str) -> bool:
        statement = select(EventoFacturacion).where(
            EventoFacturacion.idempotency_key == idempotency_key
        )
        return self.session.scalar(statement) is not None

    def buscar_plan(self, plan_id: UUID) -> Plan | None:
        statement = select(Plan).where(Plan.id == plan_id)
        return self.session.scalar(statement)

    def provisionar_alta(
        self,
        tenant: Tenant,
        invitacion: Invitacion,
        suscripcion: Suscripcion,
        evento: EventoFacturacion,
    ) -> Tenant:
        del tenant, invitacion, suscripcion, evento
        raise OnboardingNotProvisionedError(
            "El aprovisionamiento de HU-004 requiere un webhook autenticado."
        )

    # =======================================================
    # HU-005 & HU-006: Activar prueba, suscribirse y gestionar
    # =======================================================
    def buscar_suscripcion(self, tenant_id: UUID) -> Suscripcion | None:
        statement = select(Suscripcion).where(Suscripcion.tenant_id == tenant_id)
        return self.session.scalar(statement)

    def guardar_suscripcion(self, suscripcion: Suscripcion) -> Suscripcion:
        self.session.add(suscripcion)
        try:
            self.session.flush()
            self.session.commit()
            self.session.refresh(suscripcion)
            return suscripcion
        except IntegrityError:
            self.session.rollback()
            raise

    def registrar_evento_facturacion(self, evento: EventoFacturacion) -> EventoFacturacion:
        self.session.add(evento)
        try:
            self.session.flush()
            self.session.commit()
            self.session.refresh(evento)
            return evento
        except IntegrityError as error:
            self.session.rollback()
            raise DuplicateEventError("La clave de idempotencia ya existe.") from error

    # =======================================================
    # PURGA MENSUAL
    # =======================================================
    def obtener_suscripciones_para_purgar(self, fecha_limite: datetime) -> list[Suscripcion]:
        statement = select(Suscripcion).where(
            Suscripcion.estado == "canceled_read_only", Suscripcion.cancelado_en <= fecha_limite
        )
        return list(self.session.scalars(statement).all())
