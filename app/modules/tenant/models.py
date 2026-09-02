from sqlalchemy import String, Boolean, ForeignKey, DateTime, Integer, Numeric, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from datetime import datetime
from uuid import UUID
from app.db.base import Base

class Tenant(Base):
    __tablename__ = "tenant"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), server_default=text("'activo'"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

class Invitacion(Base):
    __tablename__ = "invitacion"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenant.id"), nullable=False)
    correo: Mapped[str] = mapped_column(String(255), nullable=False)
    token_unico: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)

class Plan(Base):
    __tablename__ = "plan"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False)
    precio_bob: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
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
    trial_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    periodo_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class EventoFacturacion(Base):
    __tablename__ = "evento_facturacion"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    suscripcion_id: Mapped[UUID] = mapped_column(ForeignKey("suscripcion.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_firmado: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)