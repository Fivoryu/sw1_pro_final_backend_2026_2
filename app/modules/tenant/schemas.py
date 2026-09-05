from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator

# =======================================================
# HU-004: Alta de inmobiliaria (Tenant)
# =======================================================


class AltaTenantRequest(BaseModel):
    nombre_empresa: str = Field(..., max_length=120)
    correo_admin: str = Field(..., max_length=255)
    plan_id: UUID
    payload_firmado: str = Field(..., description="Payload crudo del simulador")
    idempotency_key: str = Field(
        ...,
        max_length=100,
        description="Clave única para evitar duplicados",
    )


class AltaTenantResponse(BaseModel):
    tenant_id: UUID
    estado_tenant: str
    mensaje: str


class PlanCatalogItem(BaseModel):
    plan_id: UUID
    codigo: str
    nombre: str
    precio_bob: Decimal
    moneda: Literal["BOB"]
    max_agents: int
    cuota_almacenamiento_gb: int
    cuota_inmuebles: int
    cuota_reconstrucciones_mes: int

    @field_serializer("precio_bob")
    def serialize_price(self, value: Decimal) -> str:
        return f"{value.quantize(Decimal('0.01')):.2f}"


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: UUID
    nombre_empresa: str = Field(..., min_length=1, max_length=120)
    correo_admin: EmailStr = Field(..., max_length=255)


class CheckoutResponse(BaseModel):
    checkout_id: UUID
    estado: Literal["confirmado"]
    simulado: bool
    plan: PlanCatalogItem


class WebhookRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: Literal["tenant.onboarding.succeeded"]
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    checkout_id: UUID
    plan_id: UUID
    monto_bob: Decimal

    @field_validator("monto_bob")
    @classmethod
    def validate_finite_amount(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("monto_bob debe ser finito")
        return value


class WebhookResponse(BaseModel):
    evento_id: UUID
    tenant_id: UUID
    suscripcion_id: UUID
    estado_tenant: Literal["activo"]
    estado_evento: Literal["procesado"]
    activacion_admin: Literal["pendiente"]
    idempotente: bool


class ActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(..., min_length=1, max_length=512)


class ActivationResponse(BaseModel):
    tenant_id: UUID
    estado: Literal["consumida"]


# =======================================================
# HU-005: Activar prueba y suscribirse
# =======================================================


class ActivarPruebaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
BootstrapRequest = ActivarPruebaRequest

class SuscribirRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: Literal["subscription.monthly.succeeded"]
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    subscription_id: UUID
    plan_id: UUID
    monto_bob: Decimal = Field(..., allow_inf_nan=False)

class SuscripcionProjection(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    subscription_id: UUID
    plan_id: UUID
    estado: str
    trial_inicio: datetime | None
    trial_fin: datetime | None
    periodo_inicio: datetime | None
    periodo_fin: datetime | None

class BootstrapResponse(BaseModel):
    tenant_id: UUID
    administrador_id: UUID
    activo: bool
    idempotente: bool

class SuscripcionConversionResponse(BaseModel):
    evento_id: UUID
    subscription_id: UUID
    estado: Literal["active"]
    periodo_inicio: datetime
    periodo_fin: datetime
    idempotente: bool


class SuscripcionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    plan_id: UUID
    estado: str
    trial_fin: datetime | None
    periodo_fin: datetime | None
    cancelado_en: datetime | None


# =======================================================
# HU-006: Gestionar suscripción
# =======================================================


class CambiarPlanRequest(BaseModel):
    tenant_id: UUID
    nuevo_plan_id: UUID


class CancelarSuscripcionRequest(BaseModel):
    tenant_id: UUID
