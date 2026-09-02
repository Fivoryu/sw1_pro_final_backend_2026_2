from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.clock import ClockProtocol, SystemClock
from app.db.session import get_db
from app.modules.tenant.repository import TenantRepository
from app.modules.tenant.schemas import (
    AltaTenantRequest, 
    AltaTenantResponse,
    ActivarPruebaRequest,
    SuscribirRequest,
    SuscripcionResponse,
    CambiarPlanRequest,
    CancelarSuscripcionRequest
)
from app.modules.tenant.service import EventoDuplicadoError, TenantService

router = APIRouter(prefix="/tenant", tags=["tenant"])

def get_clock() -> ClockProtocol:
    return SystemClock()

def get_tenant_repository(db: Session = Depends(get_db)) -> TenantRepository:
    return TenantRepository(db)

def get_tenant_service(
    repository: TenantRepository = Depends(get_tenant_repository),
    clock: ClockProtocol = Depends(get_clock),
) -> TenantService:
    return TenantService(repository, clock)

# =======================================================
# HU-004: Alta de inmobiliaria
# =======================================================
@router.post(
    "/alta",
    response_model=AltaTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def registrar_tenant(
    request: AltaTenantRequest,
    service: TenantService = Depends(get_tenant_service),
) -> AltaTenantResponse:
    try:
        return service.dar_de_alta(request)
    except EventoDuplicadoError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

# =======================================================
# HU-005: Activar prueba y suscribirse
# =======================================================
@router.post(
    "/activar-prueba",
    response_model=SuscripcionResponse,
    status_code=status.HTTP_200_OK,
)
def activar_prueba(
    request: ActivarPruebaRequest,
    service: TenantService = Depends(get_tenant_service),
) -> SuscripcionResponse:
    try:
        return service.activar_prueba(request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

@router.post(
    "/suscribir",
    response_model=SuscripcionResponse,
    status_code=status.HTTP_200_OK,
)
def suscribir_mensual(
    request: SuscribirRequest,
    service: TenantService = Depends(get_tenant_service),
) -> SuscripcionResponse:
    try:
        return service.suscribirse(request)
    except EventoDuplicadoError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

# =======================================================
# HU-006: Gestionar suscripción y purga
# =======================================================
@router.post(
    "/cambiar-plan",
    response_model=SuscripcionResponse,
    status_code=status.HTTP_200_OK,
)
def cambiar_plan_suscripcion(
    request: CambiarPlanRequest,
    service: TenantService = Depends(get_tenant_service),
) -> SuscripcionResponse:
    try:
        return service.cambiar_plan(request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

@router.post(
    "/cancelar",
    response_model=SuscripcionResponse,
    status_code=status.HTTP_200_OK,
)
def cancelar_suscripcion(
    request: CancelarSuscripcionRequest,
    service: TenantService = Depends(get_tenant_service),
) -> SuscripcionResponse:
    try:
        return service.cancelar_suscripcion(request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

@router.post(
    "/ejecutar-purga",
    status_code=status.HTTP_200_OK,
)
def ejecutar_purga_mensual(
    service: TenantService = Depends(get_tenant_service),
) -> dict:
    return service.ejecutar_purga_mensual()