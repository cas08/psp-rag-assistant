---
title: Settlement and payouts
section_id: 09-settlement-and-payouts
api_version: v2
---

# Settlement and payouts

Captured payments do not reach your bank account one by one. Qorvex Pay groups captures and refunds into daily **settlement batches**, credits the net result to your balance, and transfers the balance to your bank account as **payouts**. This section explains the schedule, the objects involved, and how to reconcile them with your own records.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/v2/settlements` | List settlement batches |
| `GET` | `/v2/settlements/{id}` | Retrieve a settlement batch |
| `GET` | `/v2/settlements/{id}/report` | Download the transaction-level report of a batch as CSV |
| `GET` | `/v2/balance` | Retrieve your current balance per currency |
| `POST` | `/v2/payouts` | Create a payout (manual payout mode only) |
| `GET` | `/v2/payouts/{id}` | Retrieve a payout |
| `GET` | `/v2/payouts` | List payouts |

## Business days

Settlement follows the Kyiv business calendar. A business day is Monday to Friday, excluding public holidays in Ukraine. The calendar for the current and the next year is published in the Dashboard under **Reports → Settlement calendar**.

## Settlement batches

There is one batch per settlement currency per business day. A batch is `open` during the day and collects the captures made while it is open.

The daily batch closes at 16:30 Europe/Kyiv on business days. At that moment:

1. The batch moves to status `closed`, and no more transactions are added to it.
2. Captured payments in the batch are submitted to the card schemes for clearing.
3. A new batch opens for the next business day, and the `settlement.closed` webhook event is sent.

Captures made after 16:30 Europe/Kyiv, or on a weekend or holiday, belong to the batch of the next business day. For example, a payment captured on Friday at 17:05 Kyiv time is settled in Monday's batch.

The cut-off follows Kyiv local time throughout the year, including daylight saving time changes. Because API timestamps are in UTC, the cut-off corresponds to 13:30 UTC in summer and 14:30 UTC in winter. Convert carefully if you assign transactions to batches on your side; the simplest way is to read the batch assignment from the settlement report.

### Batch statuses

| Status | Meaning |
|---|---|
| `open` | The batch is collecting transactions for the current business day |
| `closed` | The batch is closed and its net amount is credited to your pending balance |
| `paid_out` | The net amount has been included in a payout |

## Settlement currency

Funds settle in the currency of the payment, so EUR payments produce EUR batches, UAH payments produce UAH batches, and so on. The exception is JPY and KRW: payments in these currencies are settled in USD and appear in your USD batch. The conversion uses the Qorvex Pay rate fixed at the moment the batch closes, and the rate used for each transaction is listed in the settlement report.

| Payment currency | Settlement currency |
|---|---|
| UAH, EUR, USD, GBP, PLN, KWD | Same as the payment currency |
| JPY, KRW | Settled in USD |

To receive payouts in a currency, you need a bank account for that currency registered in the Dashboard. Until it is registered, settled funds in that currency remain in your balance.

## The settlement batch object

```json
{
  "id": "stl_01JCD0F2H4K6M8P0R2T4V6X8Z0",
  "status": "closed",
  "currency": "EUR",
  "business_date": "2026-10-15",
  "captured_amount": 1874250,
  "refunded_amount": 42000,
  "deductions_amount": 37210,
  "net_amount": 1795040,
  "capture_count": 412,
  "refund_count": 9,
  "closed_at": "2026-10-15T13:30:00Z",
  "payout_id": null,
  "livemode": true
}
```

| Field | Description |
|---|---|
| `business_date` | The Kyiv business day the batch belongs to |
| `captured_amount` | Total of captures in the batch, in minor units of the batch currency |
| `refunded_amount` | Total of refunds in the batch |
| `deductions_amount` | Amounts withheld under the terms of your merchant agreement |
| `net_amount` | `captured_amount` minus `refunded_amount` minus `deductions_amount`; can be negative |
| `capture_count`, `refund_count` | Number of transactions |
| `closed_at` | When the batch closed, UTC |
| `payout_id` | The payout that includes this batch, once there is one |

As everywhere in the API, amounts in the batch object are integers in minor units. If refunds in a batch exceed its captures, `net_amount` is negative and is subtracted from the next payout.

## Listing batches

`GET /v2/settlements` returns batches oldest first, ordered by business date. This is different from other list endpoints, which return the newest objects first: settlement data is usually processed in chronological order for accounting, so the API returns it in that order. Use `created_from` and `created_to` to restrict the period, and `currency` to get batches of one currency only.

## Settlement reports

`GET /v2/settlements/{id}/report` returns a CSV file with one line per transaction in the batch. Reports are available as soon as a batch is closed and stay available for 24 months. The endpoint has its own, much stricter rate limit than the rest of the API; see Rate limits before you automate report downloads.

Unlike the JSON API, the CSV report shows amounts in major units with a decimal point, for example `49.90` for forty-nine euros and ninety cents and `1500` for 1,500 yen. This format is designed for spreadsheets and accounting systems that import it directly. When you match report lines to API objects, convert one of the two representations using the currency exponent.

| Column | Description |
|---|---|
| `business_date` | Business day of the batch |
| `transaction_type` | `capture` or `refund` |
| `payment_id` | Payment ID |
| `refund_id` | Refund ID; empty for captures |
| `merchant_ref` | Your reference for the payment or the refund |
| `transaction_time` | Time of capture or refund creation, UTC |
| `amount` | Transaction amount in major units, in the payment currency |
| `currency` | Payment currency |
| `fx_rate` | Conversion rate to the settlement currency; `1` when no conversion applies |
| `settlement_amount` | Amount in major units of the settlement currency |
| `settlement_currency` | Batch currency |

```csv
business_date,transaction_type,payment_id,refund_id,merchant_ref,transaction_time,amount,currency,fx_rate,settlement_amount,settlement_currency
2026-10-15,capture,pmt_01JC9A2M7QX4R8T6W1Y3Z5B0CD,,ORD-20261014-0042,2026-10-15T07:41:02Z,39.90,EUR,1,39.90,EUR
2026-10-15,refund,pmt_01JC9A2M7QX4R8T6W1Y3Z5B0CD,rfd_01JCB4N6Q8S0U2W4Y6A8C0E2G4,RET-20261015-0007,2026-10-15T11:20:37Z,10.00,EUR,1,10.00,EUR
```

## Balance

`GET /v2/balance` returns, for every currency, the amount that is `pending` (in closed batches that are not yet available for payout) and the amount that is `available` (ready to be paid out). Both are integers in minor units.

```json
{
  "balances": [
    {"currency": "EUR", "pending": 1795040, "available": 1286410},
    {"currency": "USD", "pending": 0, "available": 118450}
  ],
  "livemode": true
}
```

## Payouts

Funds from a closed batch become available for payout T+4 business days after the batch closes, where T is the business date of the batch. In the default **automatic** payout mode, a payout of all available funds in each currency is initiated on that day, so a payout is initiated T+4 business days after its settlement batch closes. Once initiated, the transfer usually reaches a bank in Ukraine or the EEA on the same or the next business day.

| Batch business date | Funds available and automatic payout initiated |
|---|---|
| Monday | Friday of the same week |
| Wednesday | Tuesday of the next week |
| Friday | Thursday of the next week |

These examples assume there are no public holidays in between; holidays push the date further.

In **manual** payout mode, which you can enable in the Dashboard, funds still become available at T+4, but nothing is sent until you create a payout yourself with `POST /v2/payouts`.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `amount` | integer | Yes | Amount in minor units; cannot exceed the available balance in the currency |
| `currency` | string | Yes | Currency of the payout; a bank account for it must be registered |
| `description` | string | No | Text for your records, up to 255 characters |

Payouts are sent only to IBAN bank accounts registered in the Dashboard. The account holder must be the legal entity that owns the merchant account.

### Payout statuses

| Status | Meaning |
|---|---|
| `scheduled` | The payout has been created and will be sent |
| `in_transit` | The transfer has been sent to your bank |
| `paid` | Your bank confirmed receipt |
| `returned` | Your bank returned the transfer, for example because the account was closed; the amount is credited back to your available balance |
| `failed` | The transfer could not be sent; the amount is credited back to your available balance |

```json
{
  "id": "pyt_01JCF2H4K6M8P0R2T4V6X8Z0B2",
  "status": "in_transit",
  "amount": 2410380,
  "currency": "EUR",
  "destination_iban_last4": "4417",
  "settlement_ids": ["stl_01JC7W9Y1A3C5E7G9J1L3N5Q7S", "stl_01JC9B1D3F5H7K9M1P3R5T7V9X"],
  "description": null,
  "initiated_at": "2026-10-20T06:00:00Z",
  "livemode": true
}
```

## Reconciliation tips

- Store the payment ID returned by the API next to your order, and use `merchant_ref` to find orders in reports.
- Reconcile at the batch level first: the sum of report lines must equal the batch totals.
- Then reconcile payouts: the sum of `net_amount` of the batches in `settlement_ids` equals the payout amount.
- Use the `settlement.closed` and `payout.*` webhook events to trigger your reconciliation jobs instead of polling.
