---
title: Errors
section_id: 08-errors
api_version: v2
---

# Errors

The Qorvex Pay API uses conventional HTTP status codes to show whether a request succeeded. Codes in the 2xx range mean success, codes in the 4xx range mean that the request was invalid or not allowed in the current state, and codes in the 5xx range mean that something went wrong on the platform. This section lists every error the API returns and every reason a card payment can be declined.

Card declines are not API errors. A declined payment is a successfully created payment object with `status: declined` and a `decline_code`; the request that created it returns HTTP 201. Decline codes are listed at the end of this section.

## HTTP status codes

| Status | Meaning |
|---|---|
| 200 OK | The request succeeded |
| 201 Created | A new object was created; the response contains it |
| 400 Bad Request | The request is malformed or a parameter is missing or invalid |
| 401 Unauthorized | No valid API key was provided |
| 403 Forbidden | The API key is valid but not allowed to perform this request |
| 404 Not Found | The object or endpoint does not exist in this environment |
| 409 Conflict | The request conflicts with the current state of an object |
| 422 Unprocessable Entity | The request is well formed but breaks a business rule |
| 429 Too Many Requests | The rate limit was exceeded |
| 500 Internal Server Error | An unexpected error on the platform |
| 503 Service Unavailable | A downstream system, such as a card scheme, is temporarily unavailable |

## The error object

Every 4xx and 5xx response has a JSON body with a single `error` object. The object always contains the error `type`, a machine-readable `code`, and a human-readable `message`. When the error relates to a specific request parameter, `param` contains the parameter name using dot notation for nested fields; otherwise it is `null`.

```json
{
  "error": {
    "type": "invalid_request",
    "code": "currency_not_supported",
    "message": "The currency 'CZK' is not supported for card payments.",
    "param": "currency",
    "trace_id": "tr_8c41f0e2a7b94d3e9f15a6c2d8b07e31"
  }
}
```

Build your error handling on `type` and `code`. Messages are written for developers, may change at any time without notice, and must not be parsed or shown to customers as-is.

Error messages are always in English. The API ignores the `Accept-Language` header, so there is no way to request localised messages; translate error codes into your own customer-facing texts instead.

When you contact support about a failed request, include the complete error object from the response together with the endpoint and the time of the request. Support can find the request in the platform logs from this information.

## Error types

| Type | Typical HTTP status | Meaning |
|---|---|---|
| `invalid_request` | 400, 422 | The request is invalid or breaks a business rule; fix it before retrying |
| `authentication` | 401 | The API key is missing or invalid |
| `permission` | 403 | The API key cannot perform this request |
| `not_found` | 404 | The object does not exist |
| `conflict` | 409, 422 | The object is not in a state that allows the operation, or an idempotency token clashes |
| `rate_limit` | 429 | Too many requests |
| `api` | 500, 503 | A problem on the platform side |

## API error codes

| Code | HTTP | Type | Safe to retry | Description |
|---|---|---|---|---|
| `parameter_missing` | 400 | `invalid_request` | No | A required parameter or header is missing; `param` names it |
| `parameter_invalid` | 400 | `invalid_request` | No | A parameter has the wrong type or format, is unknown, or a card token has expired or was already used |
| `amount_below_minimum` | 400 | `invalid_request` | No | The amount is below the minimum for the currency |
| `amount_above_maximum` | 400 | `invalid_request` | No | The amount is above the maximum for the currency or your account |
| `amount_precision_invalid` | 400 | `invalid_request` | No | The amount does not respect the precision rules of the currency |
| `currency_not_supported` | 400 | `invalid_request` | No | The currency is not supported |
| `api_key_invalid` | 401 | `authentication` | No | The API key is missing, malformed, revoked or from the other environment |
| `key_not_permitted` | 403 | `permission` | No | The key is read-only, is a publishable key, or the request came from an address outside the IP allowlist |
| `resource_not_found` | 404 | `not_found` | No | No object with this ID exists in this environment |
| `payment_not_capturable` | 409 | `conflict` | No | Only payments in status `authorized` can be captured |
| `payment_not_releasable` | 409 | `conflict` | No | Only payments in status `authorized` can be released |
| `duplicate_merchant_ref` | 409 | `conflict` | No | Another payment with the same `merchant_ref` exists and was not declined; use a new reference or retrieve the existing payment |
| `payment_not_refundable` | 409 | `conflict` | No | Only payments in status `captured` can be refunded |
| `idempotency_in_progress` | 409 | `conflict` | Yes | A request with the same idempotency token is still being processed |
| `idempotency_token_reused` | 422 | `conflict` | No | The idempotency token was already used with a different body or endpoint |
| `refund_window_closed` | 422 | `invalid_request` | No | The refund window for this payment has closed |
| `refund_amount_invalid` | 422 | `invalid_request` | No | The refund amount exceeds the remaining amount or is not allowed for the currency |
| `request_throttled` | 429 | `rate_limit` | Yes | Too many requests; wait as described in Rate limits and retry |
| `internal_error` | 500 | `api` | Yes | Unexpected platform error |
| `upstream_unavailable` | 503 | `api` | Yes | A card scheme or issuer connection is temporarily unavailable |

## Retrying failed requests

Retry only errors marked as safe to retry in the table above, and always reuse the original `Qx-Idempotency-Token` so that the operation is executed at most once.

Recommended policy:

1. For `request_throttled`, wait for the interval the API tells you to wait, then retry.
2. For `idempotency_in_progress`, wait one second and retry.
3. For `internal_error` and `upstream_unavailable`, retry with exponential backoff: 1, 2, 4, 8 and 16 seconds, with random jitter of up to 50%.
4. Give up after five attempts, log the full error object, and alert your team.

For network errors and timeouts where you received no response at all, retry with the same idempotency token. Because the token makes the request idempotent, a retry can never create a second payment or a second refund.

Never retry `invalid_request`, `authentication` or `permission` errors without changing the request: they will fail the same way every time.

## Decline codes

When a payment is declined, the payment object has `status: declined` and one of the following values in `decline_code`. The list is extensible; handle unknown values as `issuer_declined`.

| Decline code | Meaning | Suggested customer message |
|---|---|---|
| `issuer_declined` | The issuer declined the payment without giving a specific reason | "Your card was declined. Please contact your bank or use another card." |
| `card_balance_low` | The card does not have enough available funds or credit for this payment | "Your card has insufficient funds. Please use another card." |
| `card_expired` | The card has expired | "Your card has expired. Please use another card." |
| `cvc_mismatch` | The security code is incorrect | "The security code is incorrect. Please check it and try again." |
| `suspected_fraud` | The issuer or the Qorvex Pay risk engine suspects fraud | "Your card was declined. Please use another card." |
| `card_not_supported` | The card type or scheme is not accepted for this payment | "This card is not supported. Please use another card." |
| `limit_exceeded` | The payment exceeds a spending or frequency limit set by the issuer | "Your card limit was reached. Please contact your bank or use another card." |
| `authentication_failed` | The cardholder failed 3-D Secure authentication | "We could not verify your card. Please try again." |
| `authentication_timed_out` | The cardholder did not complete the 3-D Secure challenge before the session expired | "Verification was not completed in time. Please try again." |
| `issuer_unavailable` | The issuer could not be reached | "Your bank is not responding. Please try again in a few minutes." |

### Handling declines

- Do not tell the customer that a payment was declined for suspected fraud. Use the same neutral message as for `issuer_declined`.
- Do not retry a declined payment automatically. Repeated attempts on a declined card can trigger additional fraud controls at the issuer and make the card unusable for your shop.
- For `issuer_unavailable`, the customer can try again after a short pause; create a new payment with a new card token.
- For `authentication_failed` and `authentication_timed_out`, let the customer start the payment again; most of these declines are caused by a customer closing the bank page by mistake.

## Validation errors in detail

`parameter_missing` and `parameter_invalid` always set `param`. For nested parameters, `param` uses dot notation, for example `payment_method.card_token` or `customer.email`. For headers, `param` contains the header name, for example `Qx-Idempotency-Token`.

When a request has several problems, only the first one found is reported. Fix it and send the request again to see whether anything else needs attention.

## Errors and webhooks

Requests that fail with an API error do not create objects and do not produce webhook events. A declined payment, on the other hand, is an object: it produces a `payment.declined` event like any other status change.
