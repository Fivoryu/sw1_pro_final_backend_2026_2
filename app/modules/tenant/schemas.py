from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime

# =======================================================
# HU-004: Alta de inmobiliaria (Tenant)
# =======================================================

class AltaTenantRequest(BaseModel):
    nombre_empresa: str = Field(..., max_length=120)
    correo_admin: str = Field(..., max_length=255)
    plan_id: UUID
    payload_firmado: str = Field(..., description="Payload crudo del simulador")
    idempotency_key: str = Field(..., max_length=100, description="Clave única para evitar duplicados")

class AltaTenantResponse(BaseModel):
    tenant_id: UUID
    estado_tenant: str
    mensaje: str

# =======================================================
# HU-005: Activar prueba y suscribirse
# =======================================================

class ActivarPruebaRequest(BaseModel):
    tenant_id: UUID

class SuscribirRequest(BaseModel):
    tenant_id: UUID
    plan_id: UUID
    payload_firmado: str
    idempotency_key: str = Field(..., max_length=100)

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