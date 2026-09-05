from datetime import datetime
from typing import Protocol
from uuid import UUID


class CheckoutAccessDeniedError(PermissionError):
    """Raised when public checkout is unavailable outside the demo environment."""


class CheckoutAccessPolicy(Protocol):
    def authorize(self, actor: object | None) -> None: ...


class DemoCheckoutAccessPolicy:
    def __init__(self, app_env: str) -> None:
        self.app_env = app_env

    def authorize(self, actor: object | None) -> None:
        del actor
        if self.app_env.lower() != "demo":
            raise CheckoutAccessDeniedError


class WebhookSignatureVerifier(Protocol):
    def verify(self, raw_body: bytes, timestamp: str, signature: str, now: datetime) -> None: ...


class ActivationNotifier(Protocol):
    def deliver(self, tenant_id: UUID, email: str, token: str, expires_at: datetime) -> None: ...


class FirstAdminIdentityHook(Protocol):
    def on_activation_consumed(self, tenant_id: UUID, email: str) -> None: ...
