from __future__ import annotations
import hashlib
from datetime import timedelta
from uuid import uuid4, UUID

from app.core.clock import ClockProtocol
from app.modules.tenant.models import Tenant, Invitacion, Plan, Suscripcion, EventoFacturacion
from app.modules.tenant.repository import TenantRepository, DuplicateEventError
from app.modules.tenant.schemas import (
    AltaTenantRequest, 
    AltaTenantResponse, 
    ActivarPruebaRequest, 
    SuscribirRequest, 
    SuscripcionResponse,
    CambiarPlanRequest,
    CancelarSuscripcionRequest
)

class EventoDuplicadoError(Exception):
    """Lanzado cuando se intenta procesar un evento de pago que ya existe."""

class TenantService:
    def __init__(self, repository: TenantRepository, clock: ClockProtocol):
        self.repository = repository
        self.clock = clock

    # =======================================================
    # HU-004: Alta de inmobiliaria
    # =======================================================
    def dar_de_alta(self, request: AltaTenantRequest) -> AltaTenantResponse:
        if self.repository.evento_procesado(request.idempotency_key):
            raise EventoDuplicadoError("El tenant ya fue provisionado con este evento de pago.")

        plan = self.repository.buscar_plan(request.plan_id)
        if not plan:
            raise ValueError("El plan seleccionado no existe.")

        ahora = self.clock.now()

        nuevo_tenant = Tenant(
            id=uuid4(),
            nombre=request.nombre_empresa,
            estado="activo",
            creado_en=ahora
        )

        token_crudo = uuid4().hex
        token_hash = hashlib.sha256(token_crudo.encode()).hexdigest()
        
        nueva_invitacion = Invitacion(
            id=uuid4(),
            tenant_id=nuevo_tenant.id,
            correo=request.correo_admin,
            token_unico=token_hash,
            expira_en=ahora + timedelta(days=7),
            estado="pendiente"
        )

        nueva_suscripcion = Suscripcion(
            id=uuid4(),
            tenant_id=nuevo_tenant.id,
            plan_id=plan.id,
            estado="trialing",
            trial_fin=None,
            periodo_fin=None,
            cancelado_en=None
        )

        nuevo_evento = EventoFacturacion(
            id=uuid4(),
            suscripcion_id=nueva_suscripcion.id,
            tipo="checkout_alta",
            payload_firmado=request.payload_firmado,
            idempotency_key=request.idempotency_key,
            estado="procesado"
        )

        try:
            tenant_guardado = self.repository.provisionar_alta(
                tenant=nuevo_tenant,
                invitacion=nueva_invitacion,
                suscripcion=nueva_suscripcion,
                evento=nuevo_evento
            )
        except DuplicateEventError as e:
            raise EventoDuplicadoError(str(e)) from e

        return AltaTenantResponse(
            tenant_id=tenant_guardado.id,
            estado_tenant=tenant_guardado.estado,
            mensaje=f"Alta exitosa. Enlace único enviado a {request.correo_admin}"
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
            estado="procesado"
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