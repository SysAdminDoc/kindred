import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import database
from app.payments import (
    StripePaymentConfigurationError,
    StripePaymentGateway,
)


class FakePaymentIntents:
    calls = []

    @classmethod
    def create(cls, **kwargs):
        cls.calls.append(kwargs)
        return {
            "id": "pi_test_123",
            "client_secret": "pi_test_123_secret",
            "status": "requires_payment_method",
        }


class FakeWebhook:
    @staticmethod
    def construct_event(payload, signature, secret):
        return {
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": payload.decode()}},
            "signature": signature,
            "secret": secret,
        }


class FakeStripe:
    PaymentIntent = FakePaymentIntents
    Webhook = FakeWebhook
    api_key = None


class StripePaymentGatewayTests(unittest.TestCase):
    def setUp(self):
        FakePaymentIntents.calls = []

    def test_payment_intent_uses_idempotency_and_metadata(self):
        gateway = StripePaymentGateway(
            enabled=True,
            secret_key="sk_test",
            publishable_key="pk_test",
            webhook_secret="whsec_test",
            sdk=FakeStripe,
        )

        intent = gateway.create_payment_intent(
            2500, "usd", {"event_id": "event-1", "profile_id": "profile-1"},
            "event-rsvp:event-1:profile-1",
        )

        self.assertEqual(intent["id"], "pi_test_123")
        self.assertEqual(FakeStripe.api_key, "sk_test")
        self.assertEqual(
            FakePaymentIntents.calls[0]["idempotency_key"],
            "event-rsvp:event-1:profile-1",
        )
        self.assertEqual(
            FakePaymentIntents.calls[0]["metadata"]["event_id"], "event-1"
        )

    def test_webhook_is_verified_by_gateway(self):
        gateway = StripePaymentGateway(
            enabled=True,
            secret_key="sk_test",
            publishable_key="pk_test",
            webhook_secret="whsec_test",
            sdk=FakeStripe,
        )

        event = gateway.construct_webhook_event(b"pi_test_123", "sig_test")

        self.assertEqual(event["type"], "payment_intent.succeeded")
        self.assertEqual(event["signature"], "sig_test")

    def test_enabled_gateway_without_keys_fails_closed(self):
        gateway = StripePaymentGateway(enabled=True, sdk=FakeStripe)

        with self.assertRaises(StripePaymentConfigurationError):
            gateway.create_payment_intent(2500, "usd", {}, "idempotency-key")


class TicketedEventPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        old_conn = getattr(database._local, "conn", None)
        if old_conn is not None:
            old_conn.close()
        database._local.conn = None
        database.DB_PATH = Path(self.temp.name) / "kindred.db"
        database.init_db()
        for profile_id in ("host", "attendee"):
            database.save_profile({
                "id": profile_id,
                "name": profile_id.title(),
                "age": 30,
                "gender": "x",
                "seeking": "x",
            })

    def tearDown(self):
        conn = getattr(database._local, "conn", None)
        if conn is not None:
            conn.close()
        database._local.conn = None
        database.DB_PATH = self.old_db_path
        self.temp.cleanup()

    def test_ticketed_rsvp_waits_for_payment_then_counts_as_attendee(self):
        event_id = database.create_event(
            "Ticketed meetup", "Bring a friend", "host",
            event_date="2026-09-01", max_attendees=2,
            ticket_price_cents=2500, ticket_currency="usd",
        )
        database.rsvp_event(
            event_id, "attendee", "going", payment_status="pending",
            payment_intent_id="pi_test_123", amount_cents=2500,
            currency="usd", payment_expires_at="9999-12-31 23:59:59",
        )

        event = database.get_event(event_id)
        pending = database.get_event_rsvp(event_id, "attendee")
        self.assertEqual(event["ticket_price_cents"], 2500)
        self.assertEqual(pending["payment_status"], "pending")
        self.assertEqual(database.get_event_attendee_count(event_id), 2)

        self.assertTrue(database.update_event_rsvp_payment("pi_test_123", "paid"))
        paid = database.get_event_rsvp(event_id, "attendee")
        self.assertEqual(paid["payment_status"], "paid")
        self.assertIsNone(paid["payment_expires_at"])
        self.assertEqual(database.get_event_attendee_count(event_id), 2)

        public_rsvps = database.get_event_rsvps(event_id)
        self.assertTrue(all("payment_intent_id" not in rsvp for rsvp in public_rsvps))

    def test_rsvp_endpoint_returns_client_secret_without_calling_stripe_live(self):
        from app import main

        class FakeGateway:
            ready = True

            def create_payment_intent(self, amount_cents, currency, metadata, idempotency_key):
                self.request = {
                    "amount_cents": amount_cents,
                    "currency": currency,
                    "metadata": metadata,
                    "idempotency_key": idempotency_key,
                }
                return {
                    "id": "pi_route_test",
                    "client_secret": "pi_route_test_secret",
                    "status": "requires_payment_method",
                }

        gateway = FakeGateway()
        with patch.object(main, "STRIPE_ENABLED", True), \
             patch.object(main, "stripe_gateway", gateway):
            created = main.create_event_endpoint(
                main.EventCreate(
                    title="Paid route event",
                    ticket_price_cents=2500,
                    ticket_currency="usd",
                    max_attendees=2,
                ),
                {"profile_id": "host"},
            )
            response = main.rsvp_event_endpoint(
                created["id"], main.EventRSVP(status="going"),
                {"profile_id": "attendee"},
            )

        self.assertTrue(response["payment_required"])
        self.assertEqual(response["client_secret"], "pi_route_test_secret")
        self.assertEqual(gateway.request["amount_cents"], 2500)
        self.assertEqual(
            database.get_event_rsvp(created["id"], "attendee")["payment_status"],
            "pending",
        )


if __name__ == "__main__":
    unittest.main()
