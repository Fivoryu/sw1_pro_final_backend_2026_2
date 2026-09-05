from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenant"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), server_default=text("'activo'"))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )


class Invitacion(Base):
    __tablename__ = "invitacion"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), nullable=False)
    token_unico: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    consumido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CheckoutIntent(Base):
    __tablename__ = "checkout_intencion"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plan.id"), nullable=False)
    nombre_empresa: Mapped[str] = mapped_column(String(120), nullable=False)
    correo_admin: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Plan(Base):
    __tablename__ = "plan"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    precio_bob: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_agents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cuota_almacenamiento_gb: Mapped[int] = mapped_column(Integer, nullable=False)
    cuota_inmuebles: Mapped[int] = mapped_column(Integer, nullable=False)
    cuota_reconstrucciones_mes: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Suscripcion(Base):
    __tablename__ = "suscripcion"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), nullable=False)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("plan.id"), nullable=False)
    estado: Mapped[str] = mapped_column(String(50), nullable=False)
    trial_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    periodo_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    periodo_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TenantAdministrator(Base):
    __tablename__ = "tenant_administrator"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "usuario_global_id",
            name="uq_tenant_administrator_tenant_usuario",
        ),
        UniqueConstraint(
            "invitacion_id", name="uq_tenant_administrator_invitacion"
        ),
        Index("ix_tenant_administrator_usuario_activo", "usuario_global_id", "activo"),
        Index("ix_tenant_administrator_tenant_activo", "tenant_id", "activo"),
    )
    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenant.id", name="fk_tenant_administrator_tenant"), nullable=False
    )
    usuario_global_id: Mapped[UUID] = mapped_column(
        ForeignKey("usuario_global.id", name="fk_tenant_administrator_usuario_global"),
        nullable=False,
    )
    invitacion_id: Mapped[UUID] = mapped_column(
        ForeignKey("invitacion.id", name="fk_tenant_administrator_invitacion"), nullable=False
    )
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    desactivado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EventoFacturacion(Base):
    __tablename__ = "evento_facturacion"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    suscripcion_id: Mapped[UUID] = mapped_column(ForeignKey("suscripcion.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_firmado: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    checkout_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("checkout_intencion.id"), nullable=True
    )
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resultado_periodo_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resultado_periodo_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
