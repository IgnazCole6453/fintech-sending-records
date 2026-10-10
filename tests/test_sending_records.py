from src.sending_records import PaymentEvent, decide_notification, verify_domain


def test_large_valid_payment_is_sent():
    decision = decide_notification(PaymentEvent("pay_42", 12500, "member@example.org"))
    assert decision.send is True
    assert decision.reason == "payment accepted"


def test_invalid_recipient_is_held_for_audit():
    decision = decide_notification(PaymentEvent("pay_43", 12500, "redacted"))
    assert decision.send is False
    assert decision.reason == "recipient is not deliverable"


class RecordingClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, payload):
        self.calls.append((method, path, payload))
        return {"data": {"verified": True}}


def test_verify_domain_calls_only_verification_capability():
    client = RecordingClient()

    result = verify_domain(client, "pay.example")

    assert result == {"verified": True}
    assert client.calls == [("POST", "/email/domain/verify", {"domain": "pay.example"})]


def test_verify_domain_accepts_optional_idempotency_key():
    client = RecordingClient()

    verify_domain(client, "pay.example", "verify-pay-example")

    assert client.calls == [(
        "POST",
        "/email/domain/verify",
        {"domain": "pay.example", "idempotency_key": "verify-pay-example"},
    )]
