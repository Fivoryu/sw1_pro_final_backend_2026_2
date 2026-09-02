from __future__ import annotations
from datetime import datetime
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.modules.tenant.models import Tenant, Invitacion, Plan, Suscripcion, EventoFacturacion

class DuplicateEventError(Exception):
    """Lanzado cuando el evento de pago simulado ya existe en la base de datos."""

class TenantRepository:
    def __init__(self, session: Session):
        self.session = session

    # =======================================================
    # HU-004: Alta de inmobiliaria
    # =======================================================
    def evento_procesado(self, idempotency_key: str) -> bool:
        statement = select(EventoFacturacion).where(EventoFacturacion.idempotency_key == idempotency_key)
        return self.session.scalar(statement) is not None

    def buscar_plan(self, plan_id: UUID) -> Plan | None:
        statement = select(Plan).where(Plan.id == plan_id)
        return self.session.scalar(statement)

    def provisionar_alta(
        self,
        tenant: Tenant,
        invitacion: Invitacion,
        suscripcion: Suscripcion,
        evento: EventoFacturacion
    ) -> Tenant:
        self.session.add(tenant)
        self.session.add(invitacion)
        self.session.add(suscripcion)
        self.session.add(evento)
        try:
            self.session.flush()
            self.session.commit()
            self.session.refresh(tenant)
            return tenant
        except IntegrityError as error:
            self.session.rollback()
            raise DuplicateEventError("El evento de pago ya fue procesado o la clave de idempotencia está duplicada.") from error

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
            Suscripcion.estado == "canceled_read_only",
            Suscripcion.cancelado_en <= fecha_limite
        )
        return list(self.session.scalars(statement).all())