"""Optional Stripe PaymentIntent integration for event tickets."""

from typing import Any

from app.config import (
    STRIPE_ENABLED,
    STRIPE_PUBLISHABLE_KEY,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)

stripe_sdk: Any = None
try:
    import stripe as _stripe_module
    stripe_sdk = _stripe_module
except ImportError:  # pragma: no cover - exercised through configuration tests
    pass


class StripePaymentError(RuntimeError):
    """A configured Stripe request failed."""


class StripePaymentConfigurationError(StripePaymentError):
    """Stripe was requested without a complete local configuration."""


def _value(payload: Any, key: str, default: Any = None) -> Any:
    if isinstance(payload, dict):
        return payload.get(key, default)
    return getattr(payload, key, default)


class StripePaymentGateway:
    def __init__(self, enabled: bool = STRIPE_ENABLED,
                 secret_key: str = STRIPE_SECRET_KEY,
                 publishable_key: str = STRIPE_PUBLISHABLE_KEY,
                 webhook_secret: str = STRIPE_WEBHOOK_SECRET,
                 sdk: Any = None):
        self.enabled = enabled
        self.secret_key = secret_key
        self.publishable_key = publishable_key
        self.webhook_secret = webhook_secret
        self.sdk = stripe_sdk if sdk is None else sdk

    @property
    def ready(self) -> bool:
        return bool(self.enabled and self.secret_key and self.publishable_key and self.sdk)

    def create_payment_intent(self, amount_cents: int, currency: str,
                              metadata: dict[str, str],
                              idempotency_key: str) -> dict[str, Any]:
        if not self.ready:
            raise StripePaymentConfigurationError(
                "Stripe ticket payments are not configured"
            )
        try:
            self.sdk.api_key = self.secret_key
            intent = self.sdk.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                automatic_payment_methods={"enabled": True},
                metadata=metadata,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            raise StripePaymentError("Stripe PaymentIntent creation failed") from exc
        client_secret = _value(intent, "client_secret")
        if not client_secret:
            raise StripePaymentError("Stripe returned no client secret")
        return {
            "id": _value(intent, "id"),
            "client_secret": client_secret,
            "status": _value(intent, "status", "requires_payment_method"),
        }

    def construct_webhook_event(self, payload: bytes, signature: str | None) -> Any:
        if not self.enabled or not self.webhook_secret or not self.sdk:
            raise StripePaymentConfigurationError(
                "Stripe webhook verification is not configured"
            )
        if not signature:
            raise StripePaymentError("Missing Stripe webhook signature")
        try:
            return self.sdk.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
        except Exception as exc:
            raise StripePaymentError("Invalid Stripe webhook signature") from exc

    def health(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "ready": self.ready,
            "webhook_ready": bool(self.enabled and self.webhook_secret and self.sdk),
        }


stripe_gateway = StripePaymentGateway()
