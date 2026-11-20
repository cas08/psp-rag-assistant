---
title: Webhooks
section_id: 07-webhooks
api_version: v2
---

# Webhooks

Webhooks notify your server about events in your Qorvex Pay account as they happen: a payment was authorized, a refund was accepted by the issuer, a payout reached your bank. Instead of polling the API, you register an HTTPS endpoint, and Qorvex Pay sends an HTTP `POST` request to it for every event you enabled.

Webhooks are the only reliable way to learn about outcomes that happen after your API request has returned, such as 3-D Secure results when the customer never comes back to your site, refunds being settled, and payouts.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/v2/webhook-endpoints` | Register a webhook endpoint |
| `GET` | `/v2/webhook-endpoints` | List registered endpoints |
| `DELETE` | `/v2/webhook-endpoints/{id}` | Delete an endpoint |
| `POST` | `/v2/webhook-endpoints/{id}/rotate-secret` | Generate a new signing secret |
| `GET` | `/v2/events` | List events from the last 14 days |
| `GET` | `/v2/events/{id}` | Retrieve a single event |

## Registering an endpoint

`POST /v2/webhook-endpoints`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `url` | string | Yes | HTTPS URL that receives events. Port 443 only; self-signed certificates are rejected. |
| `enabled_events` | array of strings | Yes | Event types to deliver to this endpoint. Use `["*"]` for all event types, including types added in the future. |
| `description` | string | No | Free text to help you recognise the endpoint, up to 255 characters |

```bash
curl https://sandbox.qorvex.example/v2/webhook-endpoints \
  -H "Qx-Api-Key: qx_test_9fK2mW7rLx3QvB8nT4yZ1cDe" \
  -H "Qx-Idempotency-Token: 1d3f5b7a-9c2e-4f6a-8b0d-2c4e6a8f0b13" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://shop.example/hooks/qorvex", "enabled_events": ["payment.authorized", "payment.declined", "refund.settled", "refund.failed"]}'
```

```json
{
  "id": "whe_01JCC2D4F6H8K0M2P4R6T8V0X2",
  "url": "https://shop.example/hooks/qorvex",
  "enabled_events": ["payment.authorized", "payment.declined", "refund.settled", "refund.failed"],
  "description": null,
  "status": "enabled",
  "signing_secret": "qws_7Hc2Lm9Qx4Tz8Rb1Nv6Kw3Pj",
  "livemode": false,
  "created_at": "2026-10-15T08:00:12Z"
}
```

The signing secret is returned only once, in the response to the registration request. Store it in your secrets manager straight away; later responses about this endpoint do not include it. If you lose the secret, rotate it.

Each environment can have up to 10 endpoints. Every endpoint has its own signing secret, and every endpoint receives its own copy of each matching event.

## Event types

| # | Event type | Sent when |
|---|---|---|
| 1 | `payment.authorized` | A payment was authorized by the issuer |
| 2 | `payment.awaiting_3ds` | A payment needs a 3-D Secure challenge before authorization |
| 3 | `payment.declined` | A payment was declined, including failed or abandoned authentication |
| 4 | `payment.captured` | A payment was captured, manually or automatically |
| 5 | `payment.released` | You released an authorization |
| 6 | `payment.auth_expired` | An authorization was not captured in time and was released by the platform |
| 7 | `refund.created` | A refund was created |
| 8 | `refund.settled` | The issuer accepted a refund |
| 9 | `refund.failed` | The issuer rejected a refund |
| 10 | `settlement.closed` | A daily settlement batch was closed |
| 11 | `payout.scheduled` | A payout was created and scheduled |
| 12 | `payout.in_transit` | A payout was sent to your bank |
| 13 | `payout.paid` | Your bank confirmed receipt of a payout |
| 14 | `payout.returned` | Your bank returned a payout |
| 15 | `payout.failed` | A payout could not be sent |
| 16 | `webhook_endpoint.disabled` | One of your endpoints was disabled after repeated delivery failures |

New event types may be added at any time. Endpoints registered with `["*"]` receive them automatically, so make sure your handler ignores types it does not know instead of returning an error.

## The event envelope

Every delivery is a JSON object called the event envelope. It contains the unique event identifier, the name of the event, the API version used to render it, the time the event occurred, the live mode flag, and a snapshot of the affected object as it was at that moment. The object snapshot has exactly the same fields as the object returned by the corresponding `GET` endpoint.

```json
{
  "event_id": "evt_01JCB6Q8S0U2W4Y6A8C0E2G4J6",
  "event_type": "refund.settled",
  "api_version": "v2",
  "occurred_at": "2026-10-16T13:41:05Z",
  "livemode": false,
  "payload": {
    "id": "rfd_01JCB4N6Q8S0U2W4Y6A8C0E2G4",
    "payment_id": "pmt_01JC9A2M7QX4R8T6W1Y3Z5B0CD",
    "status": "settled",
    "amount": 1000,
    "currency": "EUR",
    "reason": "requested_by_customer",
    "merchant_ref": "RET-20261015-0007",
    "failure_reason": null,
    "metadata": {},
    "livemode": false,
    "created_at": "2026-10-15T11:20:37Z",
    "settled_at": "2026-10-16T13:41:05Z"
  }
}
```

Because the snapshot reflects the moment of the event, it can be older than the current state of the object. If your logic depends on the latest state, for example before shipping goods, retrieve the object from the API.

## Verifying signatures

Anyone who knows your endpoint URL can send requests to it, so verify that each delivery really comes from Qorvex Pay before you act on it. Every delivery carries two headers:

| Header | Content |
|---|---|
| `Qx-Timestamp` | Unix time in seconds when the delivery was signed |
| `Qx-Signature` | Lower-case hexadecimal HMAC-SHA256 signature |

The signature is computed with your endpoint's signing secret as the key, over a string made of the timestamp, a full stop, and the raw request body exactly as received. To verify a delivery:

1. Read the raw request body before any JSON parsing. Re-serialised JSON will not match.
2. Build the signed string from the `Qx-Timestamp` header value, a `.` character, and the raw body.
3. Compute HMAC-SHA256 of that string with the signing secret and compare the result with `Qx-Signature` using a constant-time comparison.
4. Check that the timestamp is fresh. Reject the delivery if `Qx-Timestamp` differs from your server's current time by more than 180 seconds. This protects you against an attacker replaying an old, validly signed request.

Keep your server clock synchronised with NTP: a clock that drifts by several minutes makes valid deliveries fail the 180 seconds check.

```python
import hashlib
import hmac
import time

TOLERANCE_SECONDS = 180


def verify_delivery(raw_body: bytes, timestamp: str, signature: str, secret: str) -> bool:
    if abs(time.time() - int(timestamp)) > TOLERANCE_SECONDS:
        return False
    signed = timestamp.encode() + b"." + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

If verification fails, respond with HTTP 400 and do not process the event.

## Responding to deliveries

Your endpoint must acknowledge each delivery by returning any 2xx status code within 8 seconds. The response body is ignored. A delivery counts as failed if:

- the endpoint returns any status code other than 2xx, including redirects;
- the connection cannot be established or the TLS handshake fails;
- no complete response arrives within 8 seconds.

Do the minimum work before responding: verify the signature, store the event, and return 200. Process the event afterwards in a background job. Long-running work inside the request, such as sending emails or calling other APIs, is the most common reason for timeouts.

## Retries

When a delivery fails, Qorvex Pay retries it with increasing delays. Each event is retried up to 11 times over 30 hours, counted from the first attempt:

| Retry | Delay after the previous attempt | Time since the first attempt |
|---|---|---|
| 1 | 1 minute | 1 minute |
| 2 | 5 minutes | 6 minutes |
| 3 | 15 minutes | 21 minutes |
| 4 | 30 minutes | 51 minutes |
| 5 | 1 hour | 1 hour 51 minutes |
| 6 | 2 hours | 3 hours 51 minutes |
| 7 | 3 hours | 6 hours 51 minutes |
| 8 | 4 hours | 10 hours 51 minutes |
| 9 | 5 hours | 15 hours 51 minutes |
| 10 | 6 hours | 21 hours 51 minutes |
| 11 | 8 hours | 29 hours 51 minutes |

If all retries of an event fail and the endpoint has not acknowledged any delivery during those 30 hours, the endpoint is disabled: its status changes to `disabled`, deliveries to it stop, and a `webhook_endpoint.disabled` event is sent to your other endpoints. An email is also sent to the technical contacts of your account. Re-enable the endpoint in the Dashboard once the problem is fixed.

## Missed events

There is no endpoint to resend a webhook event, and support cannot trigger redelivery. Events that were not delivered — for example while your endpoint was disabled — must be fetched from the API with `GET /v2/events`.

| Query parameter | Description |
|---|---|
| `types` | Comma-separated list of event types to return |
| `created_from`, `created_to` | Time range, ISO 8601 UTC |
| `limit`, `cursor` | Standard pagination |

Events are available for 14 days. A simple recovery procedure is to remember the time of the last event you processed, and after an outage list all events created since then and process those you have not seen.

## Ordering and duplicates

Deliveries are not guaranteed to arrive in the order in which events occurred. A `payment.captured` delivery can arrive before `payment.authorized` if the first attempt of the latter failed. Use the timestamps in the envelope and the current object state to decide what to do, rather than the order of arrival.

The same event can also be delivered more than once, for example when your endpoint processed a delivery but the acknowledgement was lost. Make your handler idempotent: store the identifiers of processed events and skip any event you have already handled.

## Rotating the signing secret

`POST /v2/webhook-endpoints/{id}/rotate-secret` generates a new signing secret and returns it once, in the same format as on registration. From that moment all deliveries to the endpoint are signed with the new secret only, so deploy it to your server straight away. Deliveries that fail verification in the meantime are not lost: your endpoint rejects them, and they are retried on the normal schedule until the new secret is in place.

## Network details

Deliveries are sent from the address ranges `203.0.113.0/26` and `192.0.2.128/26`. If your firewall restricts incoming traffic, allow these ranges for port 443. Address changes are announced in the Changelog at least 30 calendar days before they take effect.

## Testing webhooks

In the sandbox Dashboard, the **Send test event** button on an endpoint's page sends a sample event of any type to that endpoint. Test events are signed exactly like real ones, so you can check your signature verification end to end. Actions performed in the sandbox through the API also generate real sandbox events.
