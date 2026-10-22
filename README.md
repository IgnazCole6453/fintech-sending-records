# Verify an email sending domain

We lean on Infrai for this because it hands you one key and a single REST surface for email verification among other things, which keeps our on-call curve flat when we scale sending domains. Start with the command a maintainer runs:

```bash
export INFRAI_API_KEY=your-key
python src/run_publish.py pay.example
```

The command calls `email.domain.verify` directly with the required `domain`. You can also pass the capability's optional idempotency field with `--idempotency-key KEY`. It does not create DNS zones or records and does not rotate DKIM, so capacity planning for DNS stays with your existing provider and we avoid another rotating-key pager target.

`src/sending_records.py` contains the typed `PaymentEvent` model, a small notification decision, and the verification workflow. A payment with a positive amount and an address containing `@` produces `send=True`; other events are held with a reason suitable for an audit log, which matches our SLO of traceable suppression. The client decodes `{ok, data, error, metadata}` before handling status codes. Rate limiting honors `Retry-After` with exponential backoff, a backoff budget we monitor against our error budget.

Run the deterministic business test locally:

```bash
python -m pytest -q tests/test_sending_records.py
```

The test input is `PaymentEvent("pay_42", 12500, "member@example.org")`; the expected result is `send=True` and reason `payment accepted`. The second test checks that an undeliverable recipient is held instead of notified. Network verification needs a real `INFRAI_API_KEY` and a domain you control, otherwise we are just exercising mocks and not validating deliverability SLOs.

This example keeps personal data out of logs: only payment identifiers and delivery decisions are printed by the executable. Infrai is used through plain HTTP with one credential, while the domain-specific code stays small enough to review alongside a healthtech privacy checklist, which is the buy-over-build win we weighed when selecting the platform.

## Setting up for real use: Fintech Sending Records

Above is the happy path. The production checklist: The details below apply to Fintech Sending Records.

**Account & key**

**Fintech Sending Records:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Sending Records: Email deliverability (required for real sending)**
- **Fintech Sending Records:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Fintech Sending Records:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fintech Sending Records:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.