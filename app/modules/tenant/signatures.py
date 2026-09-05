import hashlib
import hmac
import re
from datetime import UTC, datetime


class WebhookNotConfiguredError(RuntimeError):
    pass


class SignatureValidationError(ValueError):
    pass


class HMACWebhookSignatureVerifier:
    _TIMESTAMP_PATTERN = re.compile(r"[0-9]+")
    _SIGNATURE_PATTERN = re.compile(r"v1=[0-9a-f]{64}")

    def __init__(self, secret: str | None, tolerance_seconds: int = 300) -> None:
        self.secret = secret
        self.tolerance_seconds = tolerance_seconds

    def verify(self, raw_body: bytes, timestamp: str, signature: str, now: datetime) -> None:
        if not self.secret:
            raise WebhookNotConfiguredError
        if not self._TIMESTAMP_PATTERN.fullmatch(timestamp):
            raise SignatureValidationError
        if not self._SIGNATURE_PATTERN.fullmatch(signature):
            raise SignatureValidationError
        message = timestamp.encode("ascii") + b"." + raw_body
        expected = hmac.new(self.secret.encode(), message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature[3:]):
            raise SignatureValidationError
        if now.tzinfo is None:
            raise SignatureValidationError
        try:
            timestamp_epoch = int(timestamp)
            now_epoch = int(now.astimezone(UTC).timestamp())
        except (OverflowError, ValueError):
            raise SignatureValidationError from None
        if abs(now_epoch - timestamp_epoch) > self.tolerance_seconds:
            raise SignatureValidationError
