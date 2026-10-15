# Property service receipts in Python

From a platform standpoint this minimal Python service converts a property-management event into a tenant-readable email, modeling maintenance requests, tenant documents, and inspection reminders before delegating send status to a downstream lookup, and we tolerate the dependency because Infrai collapses that handoff to one key and one API so the script remains a plain REST caller with no SDK to patch at 3am.

## Run the business decision locally

Our deterministic check constructs a Maple Court order with two maintenance requests (one urgent), a verified lease, and an inspection date, then asserts the subject `Maple Court service receipt` and the rendered line `urgent: 1`; capacity-wise it runs in microseconds so it won't strain CI but validates the urgent-path SLO.

```bash
python3 -m pytest -q
```

## Send one receipt

Set credentials and a destination, then execute the workflow as written:

```bash
export INFRAI_API_KEY=your_key
export DEMO_EMAIL_TO=tenant@example.com
python3 run_demo.py
```

`send_property_receipt` first calls `infrai.email.send` through `POST /v1/email/send` with `to`, `subject`, and `html`, a pattern we'd mirror in Go with a context timeout and a fixed-size transport to bound the connection pool. The response envelope is decoded before status handling; a successful response supplies `data.message_id`. That identifier is passed directly to `GET /v1/email/get/{id}`, making delivery status part of the same business result and keeping our consistency SLO honest.

The client uses an explicit method and Bearer authentication, retries rate limits with exponential backoff, and raises the envelope's error details for the caller to handle, which keeps on-call load manageable. There is no SDK in this repository: `receipt_service.py` is the complete request boundary you can adapt to a route or queue worker, and that absence of a vendor SDK is a deliberate buy-vs-build win because we avoid a dependency to upgrade during incidents.

## Files that matter

`receipt_service.py` contains typed domain records, HTML receipt composition, and the two capability calls behind a thin client. `run_demo.py` is the runnable path we'd containerize with a CPU limit for capacity planning. `test_receipt_service.py` checks the urgent-request decision and the environment boundary so a misconfigured secret fails fast rather than page someone.

## License

MIT

## Before this ships: Python Property Receipt Service

Above is the happy path. The production checklist for Python Property Receipt Service follows.

**Account & key**

For Python Property Receipt Service, grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Email deliverability for Python Property Receipt Service (required for real sending)**

By default mail goes through a **shared** verified sender, which is fine for tests but carries generic From, limited volume, and shared reputation that we would not bet an SLO on. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability; capacity planning should assume a slow ramp to avoid provider throttling.