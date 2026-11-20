---
title: API v1 (legacy)
section_id: 12-api-v1-legacy
api_version: v1
---

# API v1 (legacy)

> **Deprecated.** API v1 is deprecated and will be switched off on 2027-03-31. New merchant accounts cannot use v1. Existing v1 integrations keep working until the switch-off date, but receive no new features. Plan your migration to API v2 now.

This section describes how API v1 works, so that you can maintain an existing integration and understand what changes when you migrate. Everything in this section applies to v1 only. For the current behaviour of any feature, see the corresponding v2 sections.

## Timeline

| Date | Milestone |
|---|---|
| 2025-04-01 | API v2 generally available |
| 2026-01-15 | API v1 deprecated; closed to new merchant accounts |
| 2026-10-01 | v1 requests start returning a `Qx-Deprecation` warning header |
| 2027-03-31 | API v1 switched off; all `/v1` requests return HTTP 410 Gone |

## Base URL and authentication

v1 endpoints live under `https://api.qorvex.example/v1`. The sandbox equivalent is `https://sandbox.qorvex.example/v1`.

v1 uses HTTP Basic authentication. The user name is your numeric merchant ID and the password is your v1 API secret, both shown in the Dashboard under **Developers → Legacy credentials**:

```bash
curl https://api.qorvex.example/v1/payment/status?order_id=ORD-1042 \
  -u "100482:v1sec_4Gm8Kq2Tz6Wb9Nx3"
```

v1 credentials do not work with API v2, and v2 keys do not work with v1. To migrate, create v2 keys as described in Authentication. Live v2 keys require the integration check even if you already process live payments through v1.

## Endpoints

| Method | v1 path | Purpose |
|---|---|---|
| `POST` | `/v1/payment/create` | Create a payment |
| `POST` | `/v1/payment/capture` | Capture a payment created with `auth_only=true` |
| `POST` | `/v1/payment/reverse` | Reverse an uncaptured authorization |
| `GET` | `/v1/payment/status` | Look up a payment by `order_id` |
| `POST` | `/v1/refund/create` | Refund a payment |
| `GET` | `/v1/refund/status` | Look up a refund |

v1 identifies payments by your `order_id` instead of a platform-generated ID. All v1 requests use form-encoded or JSON bodies; responses are JSON.

## Amounts

In v1, amounts are decimal strings in the major unit of the currency, with a full stop as the decimal separator:

```json
{
  "order_id": "ORD-1042",
  "amount": "12.50",
  "currency": "EUR",
  "card_token": "ctok_01JC8YV2B6N3K8Q4R7T1W5X9ZA",
  "description": "Order 1042"
}
```

The example above charges twelve euros and fifty cents. v1 accepts at most two decimal places for every currency and supports only UAH, EUR and USD.

API v2 represents amounts differently. When you migrate, every place where your code builds or parses an amount must change; see Amounts and currencies for the v2 format.

## Capture

In v1, payments are captured immediately by default: a successful `/v1/payment/create` request both authorizes and captures the amount. To authorize only and capture later, send `auth_only=true` in the create request, then call `/v1/payment/capture` with the same `order_id`.

| v1 parameter | Value | Effect |
|---|---|---|
| `auth_only` | `false` (default) | Authorize and capture in one step |
| `auth_only` | `true` | Authorize only; capture with `/v1/payment/capture` |

Capture behaviour in API v2 is described in Payments; review it before you migrate.

## Refunds

v1 refunds can be created within 30 days after the payment was captured. Partial refunds are supported for EUR and USD. v1 has no refund statuses: a refund is either accepted or rejected synchronously, and the actual return of funds is not reported back.

The refund window and the refund lifecycle are different in API v2; see Refunds.

## Callbacks (v1 webhooks)

v1 sends notifications, called callbacks, to a single `callback_url` configured in the Dashboard. There is one callback per payment status change.

Each callback carries an `X-Qorvex-Hash` header containing a lower-case hexadecimal MD5 hash of the raw request body concatenated with your v1 API secret. To verify a callback, compute the same MD5 hash and compare it with the header value.

```python
import hashlib


def verify_v1_callback(raw_body: bytes, header_value: str, api_secret: str) -> bool:
    expected = hashlib.md5(raw_body + api_secret.encode()).hexdigest()
    return expected == header_value
```

If your server does not respond with HTTP 200, the callback is retried 5 times at 10-minute intervals, then dropped. Failed callbacks are not stored, and there is no way to fetch them later.

The v1 hash offers no replay protection. API v2 webhooks use a different signature scheme, a different retry policy and an event envelope; see Webhooks.

## Statuses

| v1 status | Meaning | Closest v2 status |
|---|---|---|
| `new` | Payment created, waiting for the issuer | `pending` |
| `authorized` | Authorized, waiting for capture (only with `auth_only=true`) | `authorized` |
| `paid` | Captured | `captured` |
| `reversed` | Authorization reversed | `released` |
| `failed` | Declined or failed | `declined` |
| `refunded` | Refund accepted (full or partial) | No payment status; tracked with refund objects |

v1 does not support 3-D Secure challenges through the API. Payments that require a challenge are declined in v1 with the reason `3ds_required`.

## Errors

v1 errors are returned with HTTP 200 and a body of the form `{"result": "error", "error_code": 1203, "error_text": "..."}`. Numeric v1 error codes are listed in the legacy error catalogue available in the Dashboard. API v2 uses HTTP status codes and string error codes; see Errors. Before you switch traffic, map every numeric v1 code that your integration handles today to the corresponding v2 error or decline code, and log both during the transition so that support cases from either version can be traced.

## Running v1 and v2 side by side

During migration, both versions can be used with the same merchant account at the same time. They share the account, its settlement batches and its payouts, so money from v1 and v2 payments arrives in the same payouts. In settlement reports, v1 payments are listed with their `order_id` in the `merchant_ref` column.

Objects cannot cross versions, however. A payment created through v1 can only be captured, reversed, refunded and looked up through v1 endpoints, and a payment created through v2 only through v2 endpoints. Keep the v1 code paths for refunds in place until the last v1 payment can no longer be refunded.

## Migration checklist

1. Create v2 sandbox keys and build the v2 integration in parallel with the running v1 integration.
2. Replace `order_id` with `merchant_ref` and store the payment ID returned by v2.
3. Convert all amounts to the v2 format and test every currency you accept.
4. Decide on the capture behaviour you need and set it explicitly on every v2 payment.
5. Implement the v2 3-D Secure flow; it is mandatory for most cards issued in the EEA.
6. Register v2 webhook endpoints and implement the v2 signature verification. Remove the v1 callback URL only after v2 webhooks work.
7. Send idempotency tokens with every `POST` request; v1 had no equivalent mechanism.
8. Pass the integration check and request live v2 keys.
9. Switch traffic gradually, for example one sales channel at a time, and keep v1 running until all channels have moved.
10. Before 2027-03-31, remove all v1 calls and revoke the legacy credentials in the Dashboard.
