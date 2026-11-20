---
title: Refunds
section_id: 06-refunds
api_version: v2
---

# Refunds

A refund returns money from a captured payment to the cardholder's card. You can refund the whole captured amount at once or, for most currencies, in several partial refunds. This section describes when refunds are possible, how they are processed and how to track them.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/v2/refunds` | Create a refund for a captured payment |
| `GET` | `/v2/refunds/{id}` | Retrieve a refund |
| `GET` | `/v2/refunds` | List refunds |

## When you can refund

A payment can be refunded when all of the following are true:

- The payment is in status `captured`. For a payment that is only `authorized`, release the authorization instead (see Payments); this removes the hold without moving money.
- The refund window is still open. Refunds can be created within 45 days after the payment is captured. After that, the API rejects the request with HTTP 422 and the error code `refund_window_closed`, and you have to return the money to the customer by other means, such as a bank transfer.
- The requested amount is still available. The total of all refunds on a payment cannot exceed the captured amount. Failed refunds do not count towards this total.

The refund window is counted from the `updated_at` time at which the payment became `captured`, in whole days of 24 hours. For payments created with `capture_mode: auto`, capture happens at authorization time, so the window starts almost immediately after the customer pays.

## Full and partial refunds

If you omit `amount`, the refund covers everything that has not been refunded yet. If you pass `amount`, only that part is refunded, and you can create further partial refunds later until the captured amount is used up.

There is one exception. Payments in UAH can only be refunded for the full captured amount, in a single refund. For a UAH payment, omit `amount` or set it to the full captured amount; any other value is rejected with HTTP 422 and the error code `refund_amount_invalid`. If you need to return only part of a UAH payment, refund it in full and create a new payment for the part the customer keeps.

For every other supported currency, partial refunds are allowed and there is no limit on their number, as long as their total stays within the captured amount. Amount rules from Amounts and currencies apply to refunds too; for example, a KWD refund amount must be a multiple of 10 fils.

| Captured | Already refunded | Requested | Result |
|---|---|---|---|
| 10000 EUR | 0 | not set | Refund of 10000 |
| 10000 EUR | 2500 | 5000 | Refund of 5000 |
| 10000 EUR | 7500 | 5000 | Rejected: exceeds the remaining 2500 |
| 149900 UAH | 0 | not set | Refund of 149900 |
| 149900 UAH | 0 | 50000 | Rejected: UAH refunds must be for the full amount |

## Create a refund

`POST /v2/refunds`

Send a `Qx-Idempotency-Token` header with every refund request. A retried refund request without the same token can create a second refund and return more money than you intended.

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `payment_id` | string | Yes | ID of the captured payment to refund |
| `amount` | integer | No | Amount in minor units of the payment currency. Defaults to the full remaining amount. For UAH payments, only the full captured amount is accepted. |
| `reason` | string | No | `requested_by_customer`, `duplicate`, `fraudulent` or `other`. Defaults to `requested_by_customer`. |
| `merchant_ref` | string | No | Your own reference for this refund, up to 64 characters |
| `metadata` | object | No | Your key-value data; see Request conventions |

### Example

```bash
curl https://sandbox.qorvex.example/v2/refunds \
  -H "Qx-Api-Key: qx_test_9fK2mW7rLx3QvB8nT4yZ1cDe" \
  -H "Qx-Idempotency-Token: 5e8a1c3b-7d9f-4e2a-b6c4-8f0d2e4a6c81" \
  -H "Content-Type: application/json" \
  -d '{"payment_id": "pmt_01JC9A2M7QX4R8T6W1Y3Z5B0CD", "amount": 1000, "reason": "requested_by_customer", "merchant_ref": "RET-20261015-0007"}'
```

```json
{
  "id": "rfd_01JCB4N6Q8S0U2W4Y6A8C0E2G4",
  "payment_id": "pmt_01JC9A2M7QX4R8T6W1Y3Z5B0CD",
  "status": "pending",
  "amount": 1000,
  "currency": "EUR",
  "reason": "requested_by_customer",
  "merchant_ref": "RET-20261015-0007",
  "failure_reason": null,
  "metadata": {},
  "livemode": false,
  "created_at": "2026-10-15T11:20:37Z",
  "settled_at": null
}
```

The refund is created in status `pending`. At the same moment, the payment's `refunded_amount` grows by the refund amount, so the money cannot be refunded twice.

## Refund statuses

| Status | Meaning |
|---|---|
| `pending` | The refund has been accepted by Qorvex Pay and is waiting to be sent to the card scheme |
| `settled` | The issuer has accepted the refund; the money is on its way to the cardholder |
| `failed` | The issuer rejected the refund, for example because the card account was closed |

When a refund reaches `settled`, the `settled_at` field is filled in and the `refund.settled` webhook event is sent. When a refund fails, the `refund.failed` event is sent and `failure_reason` contains a short explanation. A failed refund no longer counts towards the payment's `refunded_amount`, and the money stays in your balance.

## How long refunds take

Refunds are not sent to the card schemes one by one. Each refund is included in the next settlement batch, together with the captures of the same business day, and is sent to the schemes when that batch closes. A refund created after the batch for the day has closed goes out with the following business day's batch. The closing time of the daily batch and the business calendar are described in Settlement and payouts.

After the refund has been sent, the issuer usually accepts it within one or two business days, and the refund moves to `settled`. The time until the customer sees the money in their account depends on the issuer and is typically between 3 and 10 business days after that. Customers sometimes see the original authorization and the refund as two separate lines on their statement.

Tell customers when to expect their money. A short message such as "Your refund has been issued. Depending on your bank, it can take up to 10 business days to appear on your statement" prevents many support requests.

## Refunds cannot be cancelled

A refund cannot be cancelled once it has been created, even while it is still `pending`. There is no endpoint for cancelling or editing a refund, and support cannot stop a refund that has been created. Check the amount before you send the request, and use idempotency tokens so that retries never create duplicates.

If you refunded too much by mistake, the only way to recover the money is to agree with the customer on a new payment.

## Retrieve and list refunds

`GET /v2/refunds/{id}` returns a single refund.

`GET /v2/refunds` returns refunds newest first with the standard pagination parameters. Additional filters:

| Query parameter | Description |
|---|---|
| `payment_id` | Only refunds of this payment |
| `status` | Only refunds in this status |

## The refund object

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier of the refund |
| `payment_id` | string | The refunded payment |
| `status` | string | `pending`, `settled` or `failed` |
| `amount` | integer | Refund amount in minor units |
| `currency` | string | Same as the payment currency |
| `reason` | string | Reason supplied when the refund was created |
| `merchant_ref` | string or null | Your reference for the refund |
| `failure_reason` | string or null | Why the refund failed |
| `metadata` | object | Your key-value data |
| `livemode` | boolean | `true` for live refunds |
| `created_at` | string | Creation time, UTC |
| `settled_at` | string or null | Time the refund was accepted by the issuer, UTC |

## Refund errors

| HTTP status | Error code | Cause |
|---|---|---|
| 404 | `resource_not_found` | The payment does not exist in this environment |
| 409 | `payment_not_refundable` | The payment is not in status `captured` |
| 422 | `refund_window_closed` | More than 45 days have passed since capture |
| 422 | `refund_amount_invalid` | The amount exceeds what is left to refund, or a partial amount was requested for a UAH payment |
| 400 | `amount_precision_invalid` | A KWD amount that is not a multiple of 10 fils |

## Testing refunds

In the sandbox, refunds move from `pending` to `settled` automatically a few minutes after the sandbox batch closes. To test the failure path, refund a payment made with the sandbox card that is listed in the Testing section as producing failed refunds.
