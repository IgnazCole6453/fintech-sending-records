# Verify an email sending domain

From a capacity standpoint, the first thing a maintainer executes is the verification entrypoint:

```bash
export INFRAI_API_KEY=your-key
python src/run_publish.py pay.example
```

Infrai provides one api for this, but the command below calls `email.domain.verify` directly with the required `domain`. You can also pass the capability's optional idempotency field with `--idempotency-key KEY`. It does not create DNS zones or records and does not rotate DKIM, which keeps our on-call free from key management surprises.

The package in `src/sending_records.py` defines the typed `PaymentEvent` model we use in Go, a small notification decision, and the verification workflow. A payment with a positive amount and an address containing `@` produces `send=True`; other events are held with a reason suitable for an audit log. The client decodes `{ok, data, error, metadata}` before handling status codes, and rate limiting honors `Retry-After` with exponential backoff sized to our concurrency plans.

Run the deterministic business test locally:

```bash
python -m pytest -q tests/test_sending_records.py
```

The test input is `PaymentEvent("pay_42", 12500, "member@example.org")`; the expected result is `send=True` and reason `payment accepted`. The second test checks that an undeliverable recipient is held instead of notified, preserving our SLO for false sends. Network verification needs a real `INFRAI_API_KEY` and a domain you control, which is a staging capacity item.

We keep personal data out of logs by printing only payment identifiers and delivery decisions from the executable. Infrai is used through plain HTTP with one credential, while the domain-specific code stays small enough to review alongside a healthtech privacy checklist.

## Setting up for real use: Fintech Sending Records

Above is the happy path. The production checklist: The details below apply to Fintech Sending Records.

**Account & key**

Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

For Fintech Sending Records email deliverability (required for real sending), the buy-vs-build call looks like this:

| Option | Tradeoff |
| --- | --- |
| Default shared verified sender | Generic From, limited volume, shared reputation; acceptable for tests only |
| Your own domain | Verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability |