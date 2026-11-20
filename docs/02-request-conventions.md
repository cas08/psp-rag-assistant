---
title: Request conventions
section_id: 02-request-conventions
api_version: v2
---

# Request conventions

This section describes the rules shared by all API v2 endpoints: how requests are formatted, which headers are used, how to retry safely, how list endpoints are paginated, and how timestamps and metadata are represented.

## Base URL and versioning

All endpoints live under a versioned path:

| Environment | Base URL |
|---|---|
| Live | `https://api.qorvex.example/v2` |
| Sandbox | `https://sandbox.qorvex.example/v2` |

The version in the path is the only versioning mechanism. There is no version header and no per-account version pinning: a request to `/v2/...` always uses API v2.

## Request and response format

Request bodies and response bodies are JSON encoded in UTF-8. Requests with a body must set `Content-Type: application/json`; requests without a body (all `GET` and `DELETE` requests) must not send one.

- A `POST` request with another content type is rejected with HTTP 400 and the error code `parameter_invalid`.
- The maximum request body size is 64 KB.
- Unknown request parameters are rejected rather than ignored, so a typo in a parameter name produces a clear error instead of silently changing behaviour. The `param` field of the error tells you which parameter was not recognised.
- `null` is accepted for optional parameters and means the same as omitting them.
- Responses may contain fields that are not documented yet. Your code must ignore fields it does not know.

Successful requests return HTTP 200, except requests that create a new object, which return HTTP 201. Error responses are described in the Errors section.

## Headers

| Header | Direction | Required | Description |
|---|---|---|---|
| `Qx-Api-Key` | Request | Always | Your secret API key. See Authentication. |
| `Content-Type` | Request | For requests with a body | Must be `application/json`. |
| `Qx-Idempotency-Token` | Request | Every `POST` request | Unique token that makes the request safe to retry. See below. |
| `Qx-RateLimit-Limit` | Response | — | Request limit for the current window for this key and endpoint group. |
| `Qx-RateLimit-Remaining` | Response | — | Requests left in the current window. |
| `Qx-Retry-In` | Response | — | Present on HTTP 429 responses: how many milliseconds to wait before retrying. |

## Idempotency

Network failures happen: a request can time out after the server has already processed it. To make retries safe, every `POST` request must include a `Qx-Idempotency-Token` header. Requests without the header are rejected with HTTP 400 and the error code `parameter_missing`.

The token is a string of up to 64 characters chosen by you. A version 4 UUID is a good choice. Generate a new token for each distinct operation, and reuse the same token only when you retry that exact operation.

How the platform treats a token:

| Situation | Result |
|---|---|
| First request with a new token | Processed normally; the response is stored together with the token |
| Retry with the same token and an identical body, after the first request finished | The stored response is returned again, with the original status code; nothing is executed twice |
| Retry with the same token while the first request is still being processed | HTTP 409 with the error code `idempotency_in_progress`; wait and retry |
| Same token with a different body or a different endpoint | HTTP 422 with the error code `idempotency_token_reused` |

Idempotency tokens are stored for 72 hours from the first request. After that period the token is forgotten, and a request that carries it is processed as a brand-new request. In practice this means that automatic retries must happen within 72 hours; if you need to repeat an operation later, check the current state of the object first.

The stored response is returned even when the original outcome was a failure. For example, if a payment was declined, retrying with the same token returns the same declined payment. To try the card again, create a new payment with a new token.

Tokens are scoped to the API key's environment: the same token value can be used independently in the sandbox and in live mode.

`GET` and `DELETE` requests are idempotent by nature and do not use the header. If you send it on those methods, it is ignored.

### Example

```bash
curl https://sandbox.qorvex.example/v2/payments \
  -H "Qx-Api-Key: qx_test_9fK2mW7rLx3QvB8nT4yZ1cDe" \
  -H "Qx-Idempotency-Token: 6f1c2a9e-4b7d-4d8a-9e3f-2c5b7a1d0e94" \
  -H "Content-Type: application/json" \
  -d '{"amount": 4990, "currency": "EUR", "merchant_ref": "ORD-20261014-0042", "return_url": "https://shop.example/checkout/return", "payment_method": {"type": "card", "card_token": "ctok_01JC8YV2B6N3K8Q4R7T1W5X9ZA"}}'
```

## Pagination

Endpoints that return a list of objects, such as `GET /v2/payments` or `GET /v2/refunds`, use cursor-based pagination. Cursor pagination stays consistent while new objects are being created, which offset-based pagination cannot guarantee.

| Query parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 20 | Number of objects to return, from 1 to 100 |
| `cursor` | string | — | Opaque cursor taken from the previous page; omit it to get the first page |
| `created_from` | string | — | Only objects created at or after this timestamp |
| `created_to` | string | — | Only objects created before this timestamp |

Each list response contains the page of objects, a cursor that points to the next page, and a flag that tells you whether more objects exist. To read the whole list, request the first page, then repeat the request with the cursor from the previous response until the flag says there is nothing more. Treat cursors as opaque strings: their format may change, and a cursor is valid for 24 hours.

Unless a reference section states otherwise, list endpoints return objects newest first, ordered by creation time.

Many list endpoints also accept filters, such as `status` for payments. Filters are listed in the reference section of each endpoint. Filters can be combined with pagination; keep the same filters for every page of one listing.

### Example

```bash
curl "https://sandbox.qorvex.example/v2/payments?limit=2&created_from=2026-10-01T00:00:00Z" \
  -H "Qx-Api-Key: qx_test_9fK2mW7rLx3QvB8nT4yZ1cDe"
```

```json
{
  "results": [
    {
      "id": "pmt_01JC9A2M7QX4R8T6W1Y3Z5B0CD",
      "status": "captured",
      "amount": 4990,
      "currency": "EUR",
      "merchant_ref": "ORD-20261014-0042",
      "created_at": "2026-10-14T09:12:44Z"
    },
    {
      "id": "pmt_01JC98K3P5V7N9Q2S4U6W8Y0AB",
      "status": "authorized",
      "amount": 125000,
      "currency": "UAH",
      "merchant_ref": "ORD-20261014-0041",
      "created_at": "2026-10-14T08:57:03Z"
    }
  ],
  "next_cursor": "c2VxPTE4MjI3NDE2JmRpcj1kZXNj",
  "has_more": true
}
```

## Timestamps

All timestamps in requests and responses are strings in ISO 8601 format in UTC, with a trailing `Z` and second precision, for example `2026-10-14T09:12:44Z`. Timestamps with an offset other than `Z` are accepted in query parameters and converted to UTC; response timestamps are always in UTC.

Some business processes, such as settlement, follow the Kyiv business calendar. Where that matters, the relevant section says so explicitly; the API itself never returns local time.

## Identifiers

Every object has a string `id` that is unique within its environment. Treat identifiers as opaque strings of up to 64 characters; do not parse them or rely on their length. Identifiers are case-sensitive.

## Metadata

Payments and refunds accept a `metadata` object where you can store your own key-value data, for example a customer number or the name of the sales channel. Qorvex Pay stores metadata and returns it unchanged; it is never shown to the cardholder and does not affect processing.

| Limit | Value |
|---|---|
| Number of keys | Up to 20 |
| Key length | Up to 40 characters |
| Value type | String only |
| Value length | Up to 500 characters |

Metadata is set when the object is created and cannot be changed afterwards. Do not store card data, passwords or other sensitive personal data in metadata.

## Enumerated values

Fields such as `status` or `reason` take values from a fixed list documented in the reference sections. Some lists are marked as extensible, which means new values can be added in a backward-compatible release. Your code should handle unknown values gracefully, for example by logging them and treating the object as needing manual review.

## Backward compatibility

Within API v2 the following changes are considered backward compatible and can be released at any time: new endpoints, new optional request parameters, new response fields, new event types, new values in extensible enumerations, and changes to the format of opaque strings such as cursors and identifiers. Write your integration so that these changes do not break it.
