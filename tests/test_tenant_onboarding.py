import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier, RLock
from types import SimpleNamespace
from typing import Any, Callable
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as OrmSession

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from app.modules.tenant.catalog import APPROVED_PLAN_DEFINITIONS
from app.modules.tenant.models import (
    CheckoutIntent,
    EventoFacturacion,
    Invitacion,
    Plan,
    Suscripcion,
    Tenant,
)
from app.modules.tenant.repository import (
    CheckoutAlreadyProvisionedError,
    IdempotencyConflictError,
    OnboardingCommand,
    TenantRepository,
)
from app.modules.tenant.router import get_tenant_service
from app.modules.tenant.schemas import (
    ActivarPruebaRequest,
    AltaTenantRequest,
    CambiarPlanRequest,
    CancelarSuscripcionRequest,
    SuscribirRequest,
)
from app.modules.tenant.service import OnboardingNotProvisionedError, TenantService
from app.modules.tenant.signatures import (
    HMACWebhookSignatureVerifier,
    SignatureValidationError,
    WebhookNotConfiguredError,
)

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)
SECRET = "test-webhook-secret"


class FakeClock:
    current = NOW

    def now(self) -> datetime:
        return self.current


class FakeSignatureVerifier:
    def verify(self, raw_body: bytes, timestamp: str, signature: str, now: datetime) -> None:
        pass


class FakeTenantRepository:
    """In-memory fake; it is not PostgreSQL evidence."""

    backend = "fake"

    def __init__(self, plans: list[Plan] | None = None) -> None:
        self.plans = plans if plans is not None else make_plans()
        self.checkouts: list[CheckoutIntent] = []
        self.write_calls = 0

    def listar_planes(self) -> list[Plan]:
        return list(self.plans)

    def buscar_plan(self, plan_id: UUID) -> Plan | None:
        return next((plan for plan in self.plans if plan.id == plan_id), None)

    def buscar_checkout(self, checkout_id: UUID) -> CheckoutIntent | None:
        return next((checkout for checkout in self.checkouts if checkout.id == checkout_id), None)

    def crear_checkout(self, checkout: CheckoutIntent) -> CheckoutIntent:
        self.write_calls += 1
        self.checkouts.append(checkout)
        return checkout


class RecordingActivationNotifier:
    def __init__(self) -> None:
        self.deliveries: list[tuple[UUID, str, str, datetime]] = []
        self.fail = False
        self.commit_probe: Callable[[], bool] | None = None
        self.commit_observations: list[bool] = []

    def deliver(self, tenant_id: UUID, email: str, token: str, expires_at: datetime) -> None:
        if self.commit_probe is not None:
            self.commit_observations.append(self.commit_probe())
        if self.fail:
            raise RuntimeError("simulated notifier failure")
        self.deliveries.append((tenant_id, email, token, expires_at))


class NullFirstAdminIdentityHook:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    def on_activation_consumed(self, tenant_id: UUID, email: str) -> None:
        self.calls.append((tenant_id, email))


def make_plans() -> list[Plan]:
    return [Plan(id=uuid4(), activo=True, **asdict(d)) for d in APPROVED_PLAN_DEFINITIONS]


def make_client(
    repository: FakeTenantRepository,
    app_env: str = "demo",
    service: TenantService | None = None,
) -> TestClient:
    settings = Settings(
        jwt_secret="test-secret-for-authentication-32-bytes-long",
        app_env=app_env,
        billing_webhook_secret=SECRET,
    )
    resolved_service = service or TenantService(
        repository,
        FakeClock(),
        settings=settings,
        activation_notifier=getattr(repository, "notifier", None),
        identity_hook=getattr(repository, "identity_hook", None),
    )
    app = create_app(settings)
    app.dependency_overrides[get_tenant_service] = lambda: resolved_service
    return TestClient(app, raise_server_exceptions=False)


def checkout_payload(repository: FakeTenantRepository, **extra: Any) -> dict[str, Any]:
    return {
        "plan_id": str(repository.plans[0].id),
        "nombre_empresa": "Inmobiliaria Ejemplo",
        "correo_admin": "admin@example.com",
    } | extra


def make_signature(raw_body: bytes, timestamp: int, secret: str = SECRET) -> str:
    message = str(timestamp).encode("ascii") + b"." + raw_body
    return "v1=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def test_catalog_returns_approved_order_prices_and_quotas() -> None:
    repository = FakeTenantRepository()
    with make_client(repository) as client:
        response = client.get("/api/v1/tenant/plans")
    body = response.json()
    assert response.status_code == 200 and repository.backend == "fake"
    expected = [
        asdict(d) | {"precio_bob": f"{d.precio_bob:.2f}"} for d in APPROVED_PLAN_DEFINITIONS
    ]
    actual = [{key: item[key] for key in expected[0]} for item in body]
    assert actual == expected
    assert all(item["moneda"] == "BOB" for item in body)


def test_catalog_and_checkout_fail_closed_without_writes() -> None:
    incomplete = FakeTenantRepository(make_plans()[:2])
    with make_client(incomplete) as client:
        response = client.get("/api/v1/tenant/plans")
    assert response.status_code == 503 and response.json()["code"] == "PLAN_CATALOG_UNAVAILABLE"
    assert incomplete.write_calls == 0

    repository = FakeTenantRepository()
    repository.plans[0].activo = False
    with make_client(repository) as client:
        inactive = client.post("/api/v1/tenant/checkout", json=checkout_payload(repository))
        unknown = client.post(
            "/api/v1/tenant/checkout",
            json=checkout_payload(repository, plan_id=str(uuid4())),
        )
    assert inactive.status_code == unknown.status_code == 404
    assert inactive.json()["code"] == unknown.json()["code"] == "PLAN_NOT_AVAILABLE"
    assert repository.write_calls == 0


def test_checkout_creates_only_server_owned_demo_intent() -> None:
    repository = FakeTenantRepository()
    with make_client(repository) as client:
        response = client.post(
            "/api/v1/tenant/checkout",
            json=checkout_payload(
                repository,
                nombre_empresa="  Inmobiliaria Ejemplo  ",
                correo_admin=" Admin@Example.COM ",
            ),
        )
    body = response.json()
    assert response.status_code == 201 and UUID(body["checkout_id"])
    assert body["estado"] == "confirmado" and body["simulado"] is True
    assert body["plan"]["precio_bob"] == "199.00"
    assert repository.checkouts[0].nombre_empresa == "Inmobiliaria Ejemplo"
    assert repository.checkouts[0].correo_admin == "admin@example.com"


def test_checkout_forbids_client_authority_fields_before_writing() -> None:
    repository = FakeTenantRepository()
    payload = checkout_payload(
        repository,
        tenant_id=str(uuid4()),
        precio_bob="0.01",
        moneda="USD",
        max_agents=999,
        cuota_almacenamiento_gb=999,
        cuota_inmuebles=999,
        cuota_reconstrucciones_mes=999,
        payload_firmado="forged",
    )
    with make_client(repository) as client:
        response = client.post("/api/v1/tenant/checkout", json=payload)
    assert response.status_code == 422
    assert repository.write_calls == 0 and "forged" not in response.text


def test_checkout_is_public_only_in_demo() -> None:
    repository = FakeTenantRepository()
    with make_client(repository, app_env="production") as client:
        response = client.post("/api/v1/tenant/checkout", json=checkout_payload(repository))
    assert response.status_code == 404 and response.json()["code"] == "CHECKOUT_NOT_AVAILABLE"
    assert repository.write_calls == 0


def test_signature_accepts_raw_body_and_rejects_invalid_material() -> None:
    verifier = HMACWebhookSignatureVerifier(SECRET)
    raw_body = b'{"plan_id":"exact-order"}'
    timestamp = int(NOW.timestamp())
    verifier.verify(raw_body, str(timestamp), make_signature(raw_body, timestamp), NOW)
    raw_body, timestamp = b"{}", str(timestamp)
    valid = make_signature(raw_body, int(timestamp))
    invalid = (
        (raw_body + b" ", valid),
        (raw_body, valid.upper()),
        (raw_body, valid.replace("v1=", "v2=")),
        (raw_body, "v1=" + "a" * 63),
    )
    for body, signature in invalid:
        with pytest.raises(SignatureValidationError):
            verifier.verify(body, timestamp, signature, NOW)
    boundary = int(NOW.timestamp()) - 300
    verifier.verify(raw_body, str(boundary), make_signature(raw_body, boundary), NOW)
    with pytest.raises(SignatureValidationError):
        verifier.verify(raw_body, str(boundary - 1), make_signature(raw_body, boundary - 1), NOW)
    with pytest.raises(WebhookNotConfiguredError):
        HMACWebhookSignatureVerifier(None).verify(
            b"{}",
            str(int(NOW.timestamp())),
            "v1=" + "0" * 64,
            NOW,
        )


def test_openapi_exposes_pr1_without_sensitive_checkout_fields() -> None:
    with make_client(FakeTenantRepository()) as client:
        document = client.get("/openapi.json").json()
    assert "/api/v1/tenant/plans" in document["paths"]
    assert "/api/v1/tenant/checkout" in document["paths"]
    schema = document["components"]["schemas"]["CheckoutRequest"]
    assert not {"tenant_id", "precio_bob", "payload_firmado"} & schema["properties"].keys()
    assert schema["additionalProperties"] is False


class OnboardingFakeRepository(FakeTenantRepository):
    """Transactional in-memory contract fake; it is not PostgreSQL evidence."""

    def __init__(self) -> None:
        super().__init__()
        self.events: dict[str, SimpleNamespace] = {}
        self.invitations: dict[str, SimpleNamespace] = {}
        self.tenants: dict[UUID, SimpleNamespace] = {}
        self.subscriptions: dict[UUID, SimpleNamespace] = {}
        self.provision_calls = 0
        self.fail_provision = False
        self.fail_stage: str | None = None
        self.lock = RLock()
        self.lookup_barrier: Barrier | None = None
        self.lookup_count = 0
        self.commit_completed = False
        self.notifier = RecordingActivationNotifier()
        self.identity_hook = NullFirstAdminIdentityHook()

    def listar_planes(self) -> list[Plan]:
        with self.lock:
            return list(self.plans)

    def buscar_plan(self, plan_id: UUID) -> Plan | None:
        with self.lock:
            return next((plan for plan in self.plans if plan.id == plan_id), None)

    def buscar_checkout(self, checkout_id: UUID) -> CheckoutIntent | None:
        with self.lock:
            return next(
                (checkout for checkout in self.checkouts if checkout.id == checkout_id), None
            )

    def buscar_evento_por_clave(self, key: str) -> SimpleNamespace | None:
        barrier = self.lookup_barrier
        with self.lock:
            event = self.events.get(key)
            if barrier is None:
                return event
            self.lookup_count += 1
            should_wait = self.lookup_count <= barrier.parties
        if should_wait:
            barrier.wait(timeout=5)
        return event

    def resultado_evento(self, event: SimpleNamespace) -> SimpleNamespace:
        return SimpleNamespace(**{**vars(event.result), "created": False, "token": None})

    def provision_onboarding(self, command: Any) -> SimpleNamespace:
        self.provision_calls += 1
        if self.fail_provision:
            raise RuntimeError("simulated persistence failure")
        with self.lock:
            existing = self.events.get(command.idempotency_key)
            if existing is not None:
                if existing.payload_hash is None or existing.payload_hash != command.payload_hash:
                    raise IdempotencyConflictError
                return self.resultado_evento(existing)
            checkout = next(item for item in self.checkouts if item.id == command.checkout_id)
            if checkout.estado == "procesado":
                raise CheckoutAlreadyProvisionedError
            original_checkout_state = checkout.estado
            try:
                if self.fail_stage == "tenant":
                    raise RuntimeError("tenant insert failed")
                tenant = SimpleNamespace(
                    id=command.tenant_id,
                    nombre=checkout.nombre_empresa,
                    estado="activo",
                )
                if self.fail_stage == "subscription":
                    raise RuntimeError("subscription insert failed")
                subscription = SimpleNamespace(
                    id=command.suscripcion_id,
                    tenant_id=tenant.id,
                    plan_id=checkout.plan_id,
                    estado="active",
                    trial_fin=None,
                )
                if self.fail_stage == "invitation":
                    raise RuntimeError("invitation insert failed")
                invitation = SimpleNamespace(
                    id=command.invitacion_id,
                    tenant_id=tenant.id,
                    correo=checkout.correo_admin,
                    token_hash=command.token_hash,
                    expira_en=command.expira_en,
                    estado="pendiente",
                    consumido_en=None,
                )
                if self.fail_stage == "event":
                    raise RuntimeError("event insert failed")
                result = SimpleNamespace(
                    evento_id=command.evento_id,
                    tenant_id=tenant.id,
                    suscripcion_id=subscription.id,
                    estado_tenant=tenant.estado,
                    estado_evento="procesado",
                    activacion_admin=invitation.estado,
                    created=True,
                    token=command.token,
                    correo=invitation.correo,
                    expira_en=invitation.expira_en,
                )
                event = SimpleNamespace(
                    checkout_id=checkout.id,
                    payload_hash=command.payload_hash,
                    estado="procesado",
                    result=result,
                )
                checkout.estado = "procesado"
                if self.fail_stage == "checkout":
                    raise RuntimeError("checkout update failed")
                if self.fail_stage == "commit":
                    raise RuntimeError("commit failed")
                self.tenants[tenant.id] = tenant
                self.subscriptions[subscription.id] = subscription
                self.invitations[command.token_hash] = invitation
                self.events[command.idempotency_key] = event
                self.commit_completed = True
                return result
            except Exception:
                checkout.estado = original_checkout_state
                self.tenants.clear()
                self.subscriptions.clear()
                self.invitations.clear()
                self.events.clear()
                self.commit_completed = False
                raise

    def consumir_activacion(self, token_hash: str, now: datetime) -> SimpleNamespace | None:
        with self.lock:
            invitation = self.invitations.get(token_hash)
            if (
                invitation is None
                or invitation.estado != "pendiente"
                or invitation.expira_en <= now
            ):
                return None
            invitation.estado = "consumida"
            invitation.consumido_en = now
            return SimpleNamespace(tenant_id=invitation.tenant_id, correo=invitation.correo)


def webhook_payload(repository: OnboardingFakeRepository, **extra: Any) -> dict[str, Any]:
    return {
        "event_type": "tenant.onboarding.succeeded",
        "idempotency_key": "evt-demo-0001",
        "checkout_id": str(repository.checkouts[0].id),
        "plan_id": str(repository.plans[0].id),
        "monto_bob": "199.00",
    } | extra


def post_webhook(client: TestClient, payload: dict[str, Any], timestamp: int) -> Any:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return client.post(
        "/api/v1/tenant/webhook",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-RoomForge-Webhook-Timestamp": str(timestamp),
            "X-RoomForge-Webhook-Signature": make_signature(raw, timestamp),
        },
    )


def ready_onboarding(repository: OnboardingFakeRepository) -> TestClient:
    client = make_client(repository)
    assert (
        client.post("/api/v1/tenant/checkout", json=checkout_payload(repository)).status_code == 201
    )
    return client


def test_webhook_authenticates_before_json_and_rejects_authority_fields() -> None:
    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    timestamp, raw = int(NOW.timestamp()), b'{"event_type":'
    response = client.post(
        "/api/v1/tenant/webhook",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-RoomForge-Webhook-Timestamp": str(timestamp),
            "X-RoomForge-Webhook-Signature": make_signature(raw, timestamp),
        },
    )
    assert response.status_code == 422 and repository.provision_calls == 0
    assert (
        post_webhook(
            client, webhook_payload(repository, tenant_id=str(uuid4())), timestamp
        ).status_code
        == 422
    )


def test_webhook_replay_and_persistence_failure_are_safe() -> None:
    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    first = post_webhook(client, webhook_payload(repository), int(NOW.timestamp()))
    replay = post_webhook(client, webhook_payload(repository), int(NOW.timestamp()) - 10_000)
    assert first.status_code == 201 and replay.status_code == 200
    assert replay.json()["idempotente"] is True and repository.provision_calls == 1
    assert len(repository.invitations) == 1

    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    repository.fail_provision = True
    failed = post_webhook(client, webhook_payload(repository), int(NOW.timestamp()))
    assert failed.status_code == 500
    assert failed.json() == {
        "code": "ONBOARDING_NOT_PROVISIONED",
        "detail": "No se pudo completar el alta",
    }
    assert not repository.events and not repository.invitations


def test_activation_consumes_once_and_migration_is_additive() -> None:
    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    onboarding = post_webhook(client, webhook_payload(repository), int(NOW.timestamp())).json()
    token = repository.notifier.deliveries[0][2]
    consumed = client.post("/api/v1/tenant/activacion/consumir", json={"token": token})
    repeated = client.post("/api/v1/tenant/activacion/consumir", json={"token": token})
    assert consumed.status_code == 200 and consumed.json()["tenant_id"] == onboarding["tenant_id"]
    assert repeated.status_code == 410 and repeated.json()["code"] == "ACTIVATION_UNAVAILABLE"
    migration = Path(__file__).parents[1] / "alembic/versions/0004_hu004_onboarding.py"
    assert migration.exists()
    assert 'down_revision: Union[str, Sequence[str], None] = "0003"' in migration.read_text()


def test_webhook_requires_json_and_rejects_non_finite_amounts() -> None:
    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    payload = webhook_payload(repository)
    raw = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = int(NOW.timestamp())
    response = client.post(
        "/api/v1/tenant/webhook",
        content=raw,
        headers={
            "Content-Type": "text/plain",
            "X-RoomForge-Webhook-Timestamp": str(timestamp),
            "X-RoomForge-Webhook-Signature": make_signature(raw, timestamp),
        },
    )
    assert response.status_code == 415 and repository.provision_calls == 0

    for amount in ("NaN", "Infinity", "-Infinity"):
        response = post_webhook(
            client,
            webhook_payload(repository, monto_bob=amount, idempotency_key=f"evt-{amount}"),
            timestamp,
        )
        assert response.status_code == 422 and repository.provision_calls == 0


def test_webhook_rejects_invalid_correlation_and_commercial_data() -> None:
    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    timestamp = int(NOW.timestamp())

    unknown_checkout = post_webhook(
        client, webhook_payload(repository, checkout_id=str(uuid4())), timestamp
    )
    assert unknown_checkout.status_code == 409
    assert unknown_checkout.json()["code"] == "CHECKOUT_NOT_AVAILABLE"

    mismatched_plan = post_webhook(
        client,
        webhook_payload(
            repository,
            plan_id=str(repository.plans[1].id),
            idempotency_key="evt-plan",
        ),
        timestamp,
    )
    assert mismatched_plan.status_code == 409
    assert mismatched_plan.json()["code"] == "CHECKOUT_MISMATCH"

    mismatched_amount = post_webhook(
        client,
        webhook_payload(repository, monto_bob="199.01", idempotency_key="evt-amount"),
        timestamp,
    )
    assert mismatched_amount.status_code == 409
    assert mismatched_amount.json()["code"] == "CHECKOUT_MISMATCH"
    assert repository.provision_calls == 0

    first = post_webhook(
        client,
        webhook_payload(repository, idempotency_key="evt-first"),
        timestamp,
    )
    assert first.status_code == 201
    already_provisioned = post_webhook(
        client,
        webhook_payload(repository, idempotency_key="evt-second"),
        timestamp,
    )
    assert already_provisioned.status_code == 409
    assert already_provisioned.json()["code"] == "CHECKOUT_ALREADY_PROVISIONED"


@pytest.mark.parametrize(
    "field",
    ("tenant_id", "nombre_empresa", "correo_admin", "max_agents", "cuota_inmuebles"),
)
def test_webhook_forbids_client_authority_fields(field: str) -> None:
    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    payload = webhook_payload(repository, **{field: str(uuid4())})
    response = post_webhook(client, payload, int(NOW.timestamp()))
    assert response.status_code == 422 and repository.provision_calls == 0


def test_legacy_onboarding_write_path_is_disabled() -> None:
    repository = OnboardingFakeRepository()
    service = TenantService(
        repository,
        FakeClock(),
        settings=Settings(billing_webhook_secret=SECRET),
    )
    request = AltaTenantRequest(
        nombre_empresa="Legacy",
        correo_admin="legacy@example.com",
        plan_id=repository.plans[0].id,
        payload_firmado="legacy",
        idempotency_key="legacy-event",
    )
    with pytest.raises(OnboardingNotProvisionedError):
        service.dar_de_alta(request)
    assert repository.write_calls == 0 and not repository.checkouts


class FailingPersistenceSession:
    def __init__(self, values: list[Any]) -> None:
        self.values = iter(values)
        self.rollback_calls = 0

    def scalar(self, statement: Any) -> Any:
        del statement
        return next(self.values)

    def add(self, record: Any) -> None:
        del record
        raise RuntimeError("simulated tenant persistence failure")

    def rollback(self) -> None:
        self.rollback_calls += 1


def test_provisioning_rolls_back_unexpected_failure_at_persistence_stage() -> None:
    plan = make_plans()[0]
    checkout = SimpleNamespace(
        id=uuid4(),
        plan_id=plan.id,
        nombre_empresa="Inmobiliaria Ejemplo",
        correo_admin="admin@example.com",
        estado="confirmado",
    )
    session = FailingPersistenceSession([None, checkout, plan, None])
    repository = TenantRepository(session)  # type: ignore[arg-type]
    command = OnboardingCommand(
        idempotency_key="evt-failing-stage",
        payload_hash="a" * 64,
        payload_firmado="{}",
        checkout_id=checkout.id,
        plan_id=plan.id,
        monto_bob=plan.precio_bob,
        tenant_id=uuid4(),
        suscripcion_id=uuid4(),
        invitacion_id=uuid4(),
        evento_id=uuid4(),
        token_hash="b" * 64,
        token="raw-token",
        ahora=NOW,
        expira_en=NOW,
    )
    with pytest.raises(OnboardingNotProvisionedError):
        repository.provision_onboarding(command)
    assert session.rollback_calls == 1


class ForeignKeyOrderingSession:
    """Fake-only seam; it is not evidence from PostgreSQL."""

    def __init__(self, values: list[Any]) -> None:
        self.values = iter(values)
        self.pending: list[Any] = []
        self.persisted_subscription_ids: set[UUID] = set()
        self.event_flush_observations: list[bool] = []
        self.committed = False

    def scalar(self, statement: Any) -> Any:
        del statement
        return next(self.values)

    def add(self, record: Any) -> None:
        self.pending.append(record)

    def add_all(self, records: list[Any]) -> None:
        # Model an ORM flush that does not promise caller list order.
        for record in reversed(records):
            self.add(record)

    def flush(self) -> None:
        events = [record for record in self.pending if isinstance(record, EventoFacturacion)]
        if events:
            event_is_fk_safe = all(
                event.suscripcion_id in self.persisted_subscription_ids for event in events
            )
            self.event_flush_observations.append(event_is_fk_safe)
            if not event_is_fk_safe:
                raise RuntimeError("event FK checked before subscription persistence")
        self.persisted_subscription_ids.update(
            record.id for record in self.pending if isinstance(record, Suscripcion)
        )
        self.pending.clear()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.pending.clear()


def test_provisioning_persists_subscription_before_event_with_fake_seam() -> None:
    """This ordering assertion is fake-only and does not replace PostgreSQL evidence."""
    plan = make_plans()[0]
    checkout = SimpleNamespace(
        id=uuid4(),
        plan_id=plan.id,
        nombre_empresa="Inmobiliaria Ejemplo",
        correo_admin="admin@example.com",
        estado="confirmado",
    )
    session = ForeignKeyOrderingSession([None, checkout, plan, None])
    repository = TenantRepository(session)  # type: ignore[arg-type]
    command = OnboardingCommand(
        idempotency_key="evt-fk-ordering",
        payload_hash="a" * 64,
        payload_firmado="{}",
        checkout_id=checkout.id,
        plan_id=plan.id,
        monto_bob=plan.precio_bob,
        tenant_id=uuid4(),
        suscripcion_id=uuid4(),
        invitacion_id=uuid4(),
        evento_id=uuid4(),
        token_hash="b" * 64,
        token="raw-token",
        ahora=NOW,
        expira_en=NOW,
    )

    result = repository.provision_onboarding(command)

    assert result.created is True
    assert session.committed is True
    assert session.event_flush_observations == [True]


def test_replay_projection_selects_one_invitation_deterministically() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    plan = make_plans()[0]
    tenant = Tenant(id=uuid4(), nombre="Inmobiliaria", estado="activo", creado_en=NOW)
    checkout = CheckoutIntent(
        id=uuid4(),
        plan_id=plan.id,
        nombre_empresa=tenant.nombre,
        correo_admin="admin@example.com",
        estado="procesado",
        creado_en=NOW,
    )
    subscription = Suscripcion(
        id=uuid4(),
        tenant_id=tenant.id,
        plan_id=plan.id,
        estado="active",
        trial_fin=None,
        periodo_fin=None,
        cancelado_en=None,
    )
    first = Invitacion(
        id=UUID("a0000000-0000-4000-8000-000000000001"),
        tenant_id=tenant.id,
        correo="first@example.com",
        token_unico="a" * 64,
        expira_en=NOW,
        estado="consumida",
        consumido_en=NOW,
    )
    second = Invitacion(
        id=UUID("b0000000-0000-4000-8000-000000000002"),
        tenant_id=tenant.id,
        correo="second@example.com",
        token_unico="b" * 64,
        expira_en=NOW,
        estado="pendiente",
        consumido_en=None,
    )
    event = EventoFacturacion(
        id=uuid4(),
        suscripcion_id=subscription.id,
        checkout_id=checkout.id,
        tipo="tenant.onboarding.succeeded",
        payload_firmado="{}",
        payload_hash="c" * 64,
        idempotency_key="evt-deterministic",
        estado="procesado",
    )
    with OrmSession(engine) as session:
        session.add_all([plan, tenant, checkout, subscription, second, first, event])
        session.commit()
        result = TenantRepository(session).resultado_evento(event)
    assert result.correo == "first@example.com"
    assert result.activacion_admin == "pendiente"


def test_webhook_success_persists_one_atomic_server_owned_set() -> None:
    repository = OnboardingFakeRepository()
    repository.notifier.commit_probe = lambda: repository.commit_completed
    client = ready_onboarding(repository)

    response = post_webhook(client, webhook_payload(repository), int(NOW.timestamp()))

    assert response.status_code == 201
    assert len(repository.tenants) == len(repository.subscriptions) == 1
    assert len(repository.invitations) == len(repository.events) == 1
    tenant = next(iter(repository.tenants.values()))
    subscription = next(iter(repository.subscriptions.values()))
    invitation = next(iter(repository.invitations.values()))
    event = next(iter(repository.events.values()))
    assert tenant.nombre == "Inmobiliaria Ejemplo" and tenant.estado == "activo"
    assert subscription.plan_id == repository.plans[0].id
    assert subscription.estado == "active" and subscription.trial_fin is None
    assert invitation.correo == "admin@example.com" and invitation.estado == "pendiente"
    assert event.checkout_id == repository.checkouts[0].id and event.estado == "procesado"
    assert repository.checkouts[0].estado == "procesado"
    assert repository.notifier.commit_observations == [True]


@pytest.mark.parametrize(
    "stage", ("tenant", "subscription", "invitation", "event", "checkout", "commit")
)
def test_webhook_rolls_back_all_resources_at_each_persistence_stage(stage: str) -> None:
    repository = OnboardingFakeRepository()
    repository.fail_stage = stage
    client = ready_onboarding(repository)

    response = post_webhook(client, webhook_payload(repository), int(NOW.timestamp()))

    assert response.status_code == 500
    assert response.json()["code"] == "ONBOARDING_NOT_PROVISIONED"
    assert not repository.tenants and not repository.subscriptions
    assert not repository.invitations and not repository.events
    assert repository.checkouts[0].estado == "confirmado"


def test_webhook_replay_conflict_and_processed_checkout_preserve_cardinality() -> None:
    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    payload = webhook_payload(repository)

    first = post_webhook(client, payload, int(NOW.timestamp()))
    replay = post_webhook(client, payload, int(NOW.timestamp()) - 10_000)
    conflict = post_webhook(
        client,
        payload | {"monto_bob": "199.01"},
        int(NOW.timestamp()),
    )
    other_key = post_webhook(
        client,
        payload | {"idempotency_key": "evt-other"},
        int(NOW.timestamp()),
    )

    assert first.status_code == 201 and replay.status_code == 200
    assert replay.json()["idempotente"] is True
    assert replay.json()["evento_id"] == first.json()["evento_id"]
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert other_key.status_code == 409
    assert other_key.json()["code"] == "CHECKOUT_ALREADY_PROVISIONED"
    assert len(repository.tenants) == len(repository.subscriptions) == 1
    assert len(repository.invitations) == len(repository.events) == 1
    assert len(repository.notifier.deliveries) == 1


def test_processed_checkout_rechecks_matching_event_key_for_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fake seam evidence only; PostgreSQL concurrency remains parent-owned."""
    key = "evt-concurrent-replay"
    payload_hash = "a" * 64
    checkout = SimpleNamespace(id=uuid4(), estado="procesado")
    event = SimpleNamespace(idempotency_key=key)
    replay_result = SimpleNamespace(created=False)
    session = SimpleNamespace(rollback=lambda: None)
    repository = TenantRepository(session)  # type: ignore[arg-type]
    event_lookups: list[tuple[str, bool]] = []
    replays: list[tuple[Any, str]] = []

    def fake_find(model: Any, condition: Any, lock: bool = False) -> Any:
        if model is EventoFacturacion:
            event_lookups.append((condition.right.value, lock))
            return None if len(event_lookups) == 1 else event
        if model is CheckoutIntent:
            return checkout
        raise AssertionError(f"unexpected lookup: {model}")

    def fake_replay(existing: Any, received_hash: str) -> Any:
        replays.append((existing, received_hash))
        return replay_result

    monkeypatch.setattr(repository, "_find", fake_find)
    monkeypatch.setattr(repository, "_replay", fake_replay)
    command = OnboardingCommand(
        idempotency_key=key,
        payload_hash=payload_hash,
        payload_firmado="{}",
        checkout_id=checkout.id,
        plan_id=uuid4(),
        monto_bob=make_plans()[0].precio_bob,
        tenant_id=uuid4(),
        suscripcion_id=uuid4(),
        invitacion_id=uuid4(),
        evento_id=uuid4(),
        token_hash="b" * 64,
        token="raw-token",
        ahora=NOW,
        expira_en=NOW,
    )
    assert repository.provision_onboarding(command) is replay_result
    assert event_lookups == [(key, True), (key, True)]
    assert replays == [(event, payload_hash)]


def test_legacy_event_without_payload_hash_is_not_replayed() -> None:
    repository = OnboardingFakeRepository()
    client = ready_onboarding(repository)
    repository.events["evt-legacy"] = SimpleNamespace(payload_hash=None, result=SimpleNamespace())

    response = post_webhook(
        client,
        webhook_payload(repository, idempotency_key="evt-legacy"),
        int(NOW.timestamp()),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert not repository.tenants and not repository.subscriptions


def test_concurrent_exact_replays_create_one_set_and_one_notification() -> None:
    repository = OnboardingFakeRepository()
    checkout = CheckoutIntent(
        id=uuid4(),
        plan_id=repository.plans[0].id,
        nombre_empresa="Inmobiliaria Ejemplo",
        correo_admin="admin@example.com",
        estado="confirmado",
        creado_en=NOW,
    )
    repository.checkouts.append(checkout)
    repository.lookup_barrier = Barrier(2)
    service = TenantService(
        repository,
        FakeClock(),
        settings=Settings(billing_webhook_secret=SECRET),
        signature_verifier=FakeSignatureVerifier(),
        activation_notifier=repository.notifier,
        identity_hook=repository.identity_hook,
    )
    payload = webhook_payload(repository)
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(NOW.timestamp()))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: service.procesar_webhook(raw_body, timestamp, ""), range(2))
        )

    assert sorted(result.idempotente for result in results) == [False, True]
    assert len(repository.tenants) == len(repository.subscriptions) == 1
    assert len(repository.invitations) == len(repository.events) == 1
    assert len(repository.notifier.deliveries) == 1


def test_activation_hash_expiry_commit_order_and_null_identity_hook() -> None:
    repository = OnboardingFakeRepository()
    repository.notifier.commit_probe = lambda: repository.commit_completed
    clock = FakeClock()
    service = TenantService(
        repository,
        clock,
        settings=Settings(app_env="demo", billing_webhook_secret=SECRET),
        signature_verifier=FakeSignatureVerifier(),
        activation_notifier=repository.notifier,
        identity_hook=repository.identity_hook,
    )
    client = make_client(repository, service=service)
    assert (
        client.post("/api/v1/tenant/checkout", json=checkout_payload(repository)).status_code == 201
    )
    onboarding = post_webhook(client, webhook_payload(repository), int(NOW.timestamp()))
    token = repository.notifier.deliveries[0][2]
    invitation = next(iter(repository.invitations.values()))

    assert onboarding.status_code == 201
    assert len(invitation.token_hash) == 64
    assert invitation.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in vars(invitation)
    assert invitation.expira_en == NOW + timedelta(days=7)
    assert repository.notifier.commit_observations == [True]
    consumed = client.post("/api/v1/tenant/activacion/consumir", json={"token": token})
    repeated = client.post("/api/v1/tenant/activacion/consumir", json={"token": token})
    assert consumed.status_code == 200 and invitation.estado == "consumida"
    assert repeated.status_code == 410
    assert repository.identity_hook.calls == [
        (UUID(consumed.json()["tenant_id"]), "admin@example.com")
    ]


def test_activation_exact_expiry_and_notifier_failure_do_not_create_partial_state() -> None:
    repository = OnboardingFakeRepository()
    clock = FakeClock()
    service = TenantService(
        repository,
        clock,
        settings=Settings(app_env="demo", billing_webhook_secret=SECRET),
        signature_verifier=FakeSignatureVerifier(),
        activation_notifier=repository.notifier,
    )
    client = make_client(repository, service=service)
    assert (
        client.post("/api/v1/tenant/checkout", json=checkout_payload(repository)).status_code == 201
    )
    response = post_webhook(client, webhook_payload(repository), int(NOW.timestamp()))
    token = repository.notifier.deliveries[0][2]
    invitation = next(iter(repository.invitations.values()))
    clock.current = invitation.expira_en

    expired = client.post("/api/v1/tenant/activacion/consumir", json={"token": token})
    assert response.status_code == 201 and expired.status_code == 410
    assert invitation.estado == "pendiente" and invitation.consumido_en is None

    failed_repository = OnboardingFakeRepository()
    failed_repository.notifier.fail = True
    failed_client = ready_onboarding(failed_repository)
    failed = post_webhook(
        failed_client,
        webhook_payload(failed_repository),
        int(NOW.timestamp()),
    )
    assert failed.status_code == 201
    assert len(failed_repository.tenants) == len(failed_repository.invitations) == 1


def test_migration_source_declares_additive_schema_seed_and_downgrade_guards() -> None:
    migration = Path(__file__).parents[1] / "alembic/versions/0004_hu004_onboarding.py"
    source = migration.read_text(encoding="utf-8")

    assert 'down_revision: Union[str, Sequence[str], None] = "0003"' in source
    assert 'sa.Column("codigo", sa.String(20), nullable=True)' in source
    assert 'sa.Column("max_agents", sa.Integer(), nullable=True)' in source
    assert 'sa.Column("payload_hash", sa.CHAR(64), nullable=True)' in source
    assert 'sa.ForeignKey("plan.id")' in source and '"fk_evento_facturacion_checkout"' in source
    assert '"uq_plan_codigo"' in source and '"uq_evento_facturacion_checkout"' in source
    assert 'postgresql_where=sa.text("checkout_id IS NOT NULL")' in source
    assert source.count('UUID("00000000-0000-4000-8000-00000000000') == 3
    assert "_seed_plans()" in source and "legacy=True" in source
    assert "if _has_data(conn, checkout)" in source
    assert "event.c.checkout_id.is_not(None)" in source
    assert "invitation.c.consumido_en.is_not(None)" in source


def test_openapi_contract_exposes_exact_hu004_surface_without_sensitive_outputs() -> None:
    with make_client(FakeTenantRepository()) as client:
        document = client.get("/openapi.json").json()

    tenant_paths = {path for path in document["paths"] if path.startswith("/api/v1/tenant/")}
    hu004_paths = {
        "/api/v1/tenant/plans",
        "/api/v1/tenant/checkout",
        "/api/v1/tenant/webhook",
        "/api/v1/tenant/activacion/consumir",
    }
    assert tenant_paths - hu004_paths == {
        "/api/v1/tenant/activar-prueba",
        "/api/v1/tenant/suscribir",
        "/api/v1/tenant/cambiar-plan",
        "/api/v1/tenant/cancelar",
        "/api/v1/tenant/ejecutar-purga",
    }
    assert tenant_paths & hu004_paths == hu004_paths

    operations = {
        "/api/v1/tenant/plans": ("get", "200", "PlanCatalogItem"),
        "/api/v1/tenant/checkout": ("post", "201", "CheckoutResponse"),
        "/api/v1/tenant/webhook": ("post", "201", "WebhookResponse"),
        "/api/v1/tenant/activacion/consumir": ("post", "200", "ActivationResponse"),
    }
    forbidden_outputs = {
        "token",
        "token_hash",
        "payload_firmado",
        "password",
        "secreto",
        "firma",
        "raw_body",
    }
    for path, (method, status_code, schema_name) in operations.items():
        operation = document["paths"][path][method]
        response = operation["responses"][status_code]
        schema = response["content"]["application/json"]["schema"]
        if path == "/api/v1/tenant/plans":
            assert schema["type"] == "array"
            assert schema["items"].get("$ref", "").endswith(schema_name)
        else:
            assert schema.get("$ref", "").endswith(schema_name)
        properties = document["components"]["schemas"][schema_name]["properties"]
        assert not forbidden_outputs & properties.keys()

    checkout_schema = document["components"]["schemas"]["CheckoutRequest"]
    assert checkout_schema["additionalProperties"] is False
    assert not {"tenant_id", "precio_bob", "payload_firmado"} & checkout_schema["properties"].keys()
    webhook_operation = document["paths"]["/api/v1/tenant/webhook"]["post"]
    assert "200" in webhook_operation["responses"]
    assert "application/json" in webhook_operation["requestBody"]["content"]
    webhook_schema = webhook_operation["requestBody"]["content"]["application/json"]["schema"]
    assert webhook_schema["additionalProperties"] is False
    assert (
        not {
            "tenant_id",
            "nombre_empresa",
            "correo_admin",
            "max_agents",
            "cuota_inmuebles",
        }
        & webhook_schema["properties"].keys()
    )


class LegacyBehaviorRepository(FakeTenantRepository):
    def __init__(self) -> None:
        super().__init__()
        self.subscription = Suscripcion(
            id=uuid4(),
            tenant_id=uuid4(),
            plan_id=self.plans[0].id,
            estado="active",
            trial_fin=None,
            periodo_fin=None,
            cancelado_en=None,
        )
        self.events: set[str] = set()

    def buscar_suscripcion(self, tenant_id: UUID) -> Suscripcion | None:
        return self.subscription if self.subscription.tenant_id == tenant_id else None

    def guardar_suscripcion(self, subscription: Suscripcion) -> Suscripcion:
        return subscription

    def evento_procesado(self, idempotency_key: str) -> bool:
        return idempotency_key in self.events

    def registrar_evento_facturacion(self, event: EventoFacturacion) -> EventoFacturacion:
        self.events.add(event.idempotency_key)
        return event

    def obtener_suscripciones_para_purgar(self, fecha_limite: datetime) -> list[Suscripcion]:
        del fecha_limite
        return [self.subscription]


def test_hu005_hu006_routes_and_behavior_remain_unchanged() -> None:
    repository = LegacyBehaviorRepository()
    service = TenantService(
        repository,
        FakeClock(),
        settings=Settings(app_env="demo", billing_webhook_secret=SECRET),
    )
    tenant_id = repository.subscription.tenant_id

    trial = service.activar_prueba(ActivarPruebaRequest(tenant_id=tenant_id))
    assert trial.estado == "trialing" and trial.trial_fin == NOW + timedelta(days=14)
    monthly = service.suscribirse(
        SuscribirRequest(
            tenant_id=tenant_id,
            plan_id=repository.plans[1].id,
            payload_firmado="legacy-payment",
            idempotency_key="legacy-monthly",
        )
    )
    assert monthly.estado == "active" and monthly.periodo_fin == NOW + timedelta(days=30)
    changed = service.cambiar_plan(
        CambiarPlanRequest(tenant_id=tenant_id, nuevo_plan_id=repository.plans[2].id)
    )
    assert changed.plan_id == repository.plans[2].id
    cancelled = service.cancelar_suscripcion(CancelarSuscripcionRequest(tenant_id=tenant_id))
    assert cancelled.estado == "canceled_read_only"
    assert service.ejecutar_purga_mensual() == {
        "mensaje": "Se purgaron 1 suscripciones exitosamente."
    }
    assert repository.subscription.estado == "purged"

    paths = create_app(
        Settings(
            jwt_secret="test-secret-for-authentication-32-bytes-long",
            app_env="demo",
            billing_webhook_secret=SECRET,
        )
    ).openapi()["paths"]
    assert {
        "/api/v1/tenant/activar-prueba",
        "/api/v1/tenant/suscribir",
        "/api/v1/tenant/cambiar-plan",
        "/api/v1/tenant/cancelar",
        "/api/v1/tenant/ejecutar-purga",
    } <= paths.keys()
