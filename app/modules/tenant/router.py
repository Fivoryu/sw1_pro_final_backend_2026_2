from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.clock import ClockProtocol, SystemClock
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.modules.tenant.ports import CheckoutAccessDeniedError
from app.modules.tenant.repository import (
    CheckoutAlreadyProvisionedError,
    CheckoutMismatchError,
    CheckoutNotAvailableError,
    IdempotencyConflictError,
    OnboardingNotProvisionedError,
    TenantRepository,
)
from app.modules.tenant.schemas import (
    ActivarPruebaRequest,
    ActivationRequest,
    ActivationResponse,
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
from app.modules.tenant.service import (
    ActivationUnavailableError,
    CatalogUnavailableError,
    EventoDuplicadoError,
    PlanNotAvailableError,
    TenantService,
    WebhookPayloadValidationError,
)
from app.modules.tenant.signatures import SignatureValidationError, WebhookNotConfiguredError

router = APIRouter(prefix="/tenant", tags=["tenant"])


def get_clock() -> ClockProtocol:
    return SystemClock()


def get_tenant_repository(db: Session = Depends(get_db)) -> TenantRepository:
    return TenantRepository(db)


def get_tenant_service(
    repository: TenantRepository = Depends(get_tenant_repository),
    clock: ClockProtocol = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> TenantService:
    return TenantService(repository, clock, settings=settings)


_ERROR_DETAILS = {
    CheckoutAccessDeniedError: (404, "CHECKOUT_NOT_AVAILABLE", "El checkout no está disponible"),
    CatalogUnavailableError: (
        503,
        "PLAN_CATALOG_UNAVAILABLE",
        "El catálogo de planes no está disponible",
    ),
    PlanNotAvailableError: (404, "PLAN_NOT_AVAILABLE", "El plan no está disponible"),
    WebhookNotConfiguredError: (503, "WEBHOOK_NOT_CONFIGURED", "Webhook no disponible"),
    SignatureValidationError: (401, "WEBHOOK_UNAUTHORIZED", "Evento no autorizado"),
    CheckoutNotAvailableError: (409, "CHECKOUT_NOT_AVAILABLE", "El checkout no está disponible"),
    CheckoutMismatchError: (
        409,
        "CHECKOUT_MISMATCH",
        "Los datos del evento no coinciden con el checkout",
    ),
    IdempotencyConflictError: (
        409,
        "IDEMPOTENCY_CONFLICT",
        "La clave de idempotencia ya fue utilizada con otros datos",
    ),
    CheckoutAlreadyProvisionedError: (
        409,
        "CHECKOUT_ALREADY_PROVISIONED",
        "El checkout ya fue procesado",
    ),
    OnboardingNotProvisionedError: (
        500,
        "ONBOARDING_NOT_PROVISIONED",
        "No se pudo completar el alta",
    ),
    ActivationUnavailableError: (410, "ACTIVATION_UNAVAILABLE", "La activación no está disponible"),
}


def _error_response(error: Exception) -> JSONResponse:
    status_code, code, detail = _ERROR_DETAILS[type(error)]
    return JSONResponse(status_code=status_code, content={"code": code, "detail": detail})


@router.get("/plans", response_model=list[PlanCatalogItem])
def listar_planes(service: TenantService = Depends(get_tenant_service)):
    try:
        return service.listar_catalogo()
    except CatalogUnavailableError as error:
        return _error_response(error)


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
def crear_checkout(request: CheckoutRequest, service: TenantService = Depends(get_tenant_service)):
    try:
        return service.crear_checkout(request)
    except (CheckoutAccessDeniedError, CatalogUnavailableError, PlanNotAvailableError) as error:
        return _error_response(error)


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    status_code=201,
    responses={200: {"model": WebhookResponse}},
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": WebhookRequest.model_json_schema()}},
        }
    },
)
async def recibir_webhook(
    request: Request, service: TenantService = Depends(get_tenant_service)
) -> JSONResponse:
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        return JSONResponse(
            status_code=415,
            content={
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "detail": "El webhook requiere Content-Type application/json",
            },
        )
    timestamps = request.headers.getlist("X-RoomForge-Webhook-Timestamp")
    signatures = request.headers.getlist("X-RoomForge-Webhook-Signature")
    timestamp = timestamps[0] if len(timestamps) == 1 else ""
    signature = signatures[0] if len(signatures) == 1 else ""
    try:
        result = service.procesar_webhook(raw_body, timestamp, signature)
        return JSONResponse(
            status_code=200 if result.idempotente else 201,
            content=result.model_dump(mode="json"),
        )
    except WebhookPayloadValidationError as error:
        return JSONResponse(status_code=422, content={"detail": error.errors})
    except (
        WebhookNotConfiguredError,
        SignatureValidationError,
        CheckoutNotAvailableError,
        CheckoutMismatchError,
        IdempotencyConflictError,
        CheckoutAlreadyProvisionedError,
        OnboardingNotProvisionedError,
    ) as error:
        return _error_response(error)


@router.post("/activacion/consumir", response_model=ActivationResponse, status_code=200)
def consumir_activacion(
    request: ActivationRequest, service: TenantService = Depends(get_tenant_service)
) -> ActivationResponse | JSONResponse:
    try:
        return service.consumir_activacion(request)
    except (ActivationUnavailableError, OnboardingNotProvisionedError) as error:
        return _error_response(error)


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
