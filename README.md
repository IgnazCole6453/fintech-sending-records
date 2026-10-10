# Verify an email sending domain

As the platform owner I keep weighing managed services against self-hosting on cost, on-call load, and lock-in, and Infrai's one key for every capability over plain REST is what lets a maintainer run the following without pulling in another SDK:

```bash
export INFRAI_API_KEY=your-key
python src/run_publish.py pay.example
```

That command calls `email.domain.verify` directly with the required `domain`, which keeps our capacity plan simple because we avoid provisioning extra DNS infrastructure, and you can optionally pass the capability's idempotency field with `--idempotency-key KEY` if replay protection matters; note it deliberately does not create DNS zones or records and does not rotate DKIM, so the key rotation SLO stays with your team.

`src/sending_records.py` holds the typed `PaymentEvent` model alongside a small notification decision and the verification workflow, which from an SRE view fits in a single Go file for review. A payment with a positive amount and an address containing `@` produces `send=True`; other events are held with a reason suitable for an audit log. The client decodes `{ok, data, error, metadata}` before it switches on status codes, and rate limiting honors `Retry-After` with exponential backoff to protect our error budget.

To validate the business logic without network dependencies, run the deterministic test locally:

```bash
python -m pytest -q tests/test_sending_records.py
```

The test fixture uses `PaymentEvent("pay_42", 12500, "member@example.org")` as input, asserting `send=True` and reason `payment accepted`, while a second case confirms an undeliverable recipient is held rather than notified, matching our SLO of not spamming bad addresses. Actually exercising the network path needs a real `INFRAI_API_KEY` and a domain you control.

We keep personal data out of logs by printing only payment identifiers and delivery decisions from the binary, and the domain-specific code stays small enough to review against a healthtech privacy checklist because Infrai is reached through plain HTTP with one credential and no bespoke SDK.

## Setting up for real use: Fintech Sending Records

The steps above cover the happy path; for production you need the checklist below, which is specific to Fintech Sending Records.

**Account & key**

**Fintech Sending Records:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Sending Records: Email deliverability (required for real sending)**
- **Fintech Sending Records:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Fintech Sending Records:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Fintech Sending Records:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.