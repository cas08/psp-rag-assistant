---
title: Payments
section_id: 04-payments
api_version: v2
---

# Payments

A payment represents one attempt to charge a customer's card. This section explains the payment lifecycle, the endpoints that create and manage payments, and every field of the payment object.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/v2/payments` | Create a payment and authorize the card |
| `GET` | `/v2/payments/{id}` | Retrieve a payment |
| `GET` | `/v2/payments` | List payments |
| `POST` | `/v2/payments/{id}/capture` | Capture an authorized payment, fully or partially |
| `POST` | `/v2/payments/{id}/release` | Release an authorized payment that you will not capture |
| `GET` | `/v2/payments/{id}/authentication` | Retrieve the 3-D Secure details of a payment; see 3-D Secure |

## Before you create a payment: card tokens

Your server never receives card numbers. On the checkout page, Qorvex.js renders secure input fields for the card number, expiry date and CVC, and exchanges them for a **card token** when the customer submits the form. You then send the card token to your server and create the payment with it.

```html
<script src="https://js.qorvex.example/v2/qorvex.js"></script>
<script>
  const qorvex = Qorvex("qxp_test_3hT8kL2mQ9xR5vN1");
  const card = qorvex.mountCardFields("#card-fields");
  document.querySelector("#pay").addEventListener("click", async () => {
    const { token, error } = await card.createToken();
    if (error) { showError(error.message); return; }
    await fetch("/checkout/pay", { method: "POST", body: JSON.stringify({ token }) });
  });
</script>
```

A card token is valid for 15 minutes and can be used for one payment only. If the token has expired or has already been used, the payment request fails with HTTP 400 and the error code `parameter_invalid` on the `payment_method.card_token` parameter; ask the customer to submit the form again.

The API does not accept raw card numbers in any parameter.

## Lifecycle

| Status | Meaning | Next possible statuses |
|---|---|---|
| `pending` | The payment has been created and the platform is contacting the issuer | `awaiting_3ds`, `authorized`, `declined` |
| `awaiting_3ds` | The issuer requires cardholder authentication; the customer must complete a 3-D Secure challenge | `authorized`, `declined` |
| `authorized` | The issuer approved the amount and holds it on the card | `captured`, `released`, `expired` |
| `captured` | The funds have been captured and will be settled | — |
| `released` | You released the authorization; the hold is removed | — |
| `declined` | The issuer or the risk engine refused the payment, or authentication failed | — |
| `expired` | The authorization was not captured in time and was released automatically | — |

Most payments leave `pending` within a few seconds, and the create request usually returns the payment already in its next status. If the issuer is slow to answer, the request returns the payment in `pending`; use webhooks or retrieve the payment later to learn the outcome.

`captured`, `released`, `declined` and `expired` are final statuses. Refunds do not change the status of a payment; they are tracked with the `refunded_amount` field and with separate refund objects.

## Create a payment

`POST /v2/payments`

Creates a payment and immediately asks the issuer to authorize it. Remember to send a `Qx-Idempotency-Token` header, as with every `POST` request.

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `amount` | integer | Yes | Amount in minor units of `currency`. See Amounts and currencies for limits. |
| `currency` | string | Yes | Three-letter ISO 4217 code in upper case. |
| `payment_method.type` | string | Yes | Always `card`. |
| `payment_method.card_token` | string | Yes | Card token created by Qorvex.js. Valid for one payment within 15 minutes. |
| `merchant_ref` | string | Yes | Your own reference for the order, for example the order number in your shop. Up to 64 characters: letters, digits, `-`, `_` and `/`. Shown in the Dashboard and in settlement reports. |
| `capture_mode` | string | No | `manual` or `auto`. Defaults to `manual`. With `manual` the payment stops at `authorized` and waits for a capture request; with `auto` the platform captures it right after authorization. |
| `statement_descriptor` | string | No | Text shown on the cardholder's bank statement. Max 18 characters. Latin letters, digits, spaces and the characters `.` `-` `*`. If omitted, the default descriptor from your Dashboard settings is used. |
| `return_url` | string | Yes | HTTPS URL where the customer returns after a 3-D Secure challenge. Required for every payment, because the issuer decides during the request whether a challenge is needed. Up to 2,048 characters. |
| `authentication.mode` | string | No | `auto` or `force`. Defaults to `auto`. See 3-D Secure. |
| `customer.email` | string | No | Customer's email address, up to 254 characters. Improves frictionless 3-D Secure rates. |
| `customer.ip` | string | No | Customer's IPv4 or IPv6 address as seen by your server. Improves risk scoring. |
| `description` | string | No | Free-text description for your own use, up to 255 characters. Not shown to the cardholder. |
| `metadata` | object | No | Your own key-value data. See Request conventions for limits. |

### Example request

```bash
curl https://sandbox.qorvex.example/v2/payments \
  -H "Qx-Api-Key: qx_test_9fK2mW7rLx3QvB8nT4yZ1cDe" \
  -H "Qx-Idempotency-Token: 0b8e3f7a-5c21-4f6d-a9e2-7d14c3b8f560" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 4990,
    "currency": "EUR",
    "merchant_ref": "ORD-20261014-0042",
    "payment_method": {"type": "card", "card_token": "ctok_01JC8YV2B6N3K8Q4R7T1W5X9ZA"},
    "statement_descriptor": "NORDLY STORE",
    "return_url": "https://shop.example/checkout/return",
    "customer": {"email": "olena@example.com", "ip": "198.51.100.24"},
    "metadata": {"channel": "web"}
  }'
```

### Example response

```json
{
  "id": "pmt_01JC9A2M7QX4R8T6W1Y3Z5B0CD",
  "status": "authorized",
  "amount": 4990,
  "currency": "EUR",
  "captured_amount": 0,
  "refunded_amount": 0,
  "merchant_ref": "ORD-20261014-0042",
  "capture_mode": "manual",
  "statement_descriptor": "NORDLY STORE",
  "description": null,
  "decline_code": null,
  "authentication": {
    "status": "frictionless",
    "challenge_url": null,
    "eci": "05",
    "liability_shift": true,
    "version": "2.2.0"
  },
  "metadata": {
    "channel": "web"
  },
  "livemode": false,
  "created_at": "2026-10-14T09:12:44Z",
  "updated_at": "2026-10-14T09:12:46Z"
}
```

The request returns HTTP 201 when a payment object was created, whatever its status. A declined payment is still a created payment: check `status` and `decline_code` in the response rather than the HTTP status code. HTTP 4xx responses mean that the request itself was invalid and no payment was created.

## Capture a payment

`POST /v2/payments/{id}/capture`

Captures an authorized payment. Only payments in status `authorized` can be captured; for any other status the request fails with HTTP 409 and the error code `payment_not_capturable`.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `amount` | integer | No | Amount to capture in minor units. Defaults to the full authorized amount. Must be greater than zero and not greater than `amount`. |

A payment can be captured only once. If you capture less than the authorized amount, the payment moves to `captured` with the lower `captured_amount`, and the rest of the authorization is released back to the cardholder at the same moment. Multiple partial captures of one authorization are not supported. If you ship an order in several parts, capture the total amount you will charge when the first part ships, or create a separate payment for each part.

```bash
curl https://sandbox.qorvex.example/v2/payments/pmt_01JC9A2M7QX4R8T6W1Y3Z5B0CD/capture \
  -H "Qx-Api-Key: qx_test_9fK2mW7rLx3QvB8nT4yZ1cDe" \
  -H "Qx-Idempotency-Token: 3c7d1e9b-8a24-4b6f-b0d5-1e2f9a7c4b38" \
  -H "Content-Type: application/json" \
  -d '{"amount": 3990}'
```

The response is the updated payment object with `status` set to `captured` and `captured_amount` set to `3990`.

### Authorization validity

An authorization does not last forever. If an authorized payment is not captured within 120 hours of authorization, the platform releases it automatically and the payment moves to status `expired`. An expired payment cannot be captured; to charge the customer you must create a new payment, which may require the customer to enter the card details and complete 3-D Secure again.

Plan your fulfilment process around this window. If you usually ship later than 120 hours after the order, consider `capture_mode: auto` and refunding cancelled orders instead.

Payments created with `capture_mode` set to `auto` skip the `authorized` status in practice: they are captured as soon as the issuer approves them, and the create request returns them in status `captured`.

## Release a payment

`POST /v2/payments/{id}/release`

Releases an authorized payment that you are not going to capture, for example because the customer cancelled the order before it shipped. Releasing removes the hold from the customer's card sooner than waiting for the authorization to expire, and is the correct way to void an authorization in Qorvex Pay.

The endpoint takes no parameters. Only payments in status `authorized` can be released; for any other status the request fails with HTTP 409 and the error code `payment_not_releasable`. A captured payment cannot be released: return the money with a refund instead.

```bash
curl -X POST https://sandbox.qorvex.example/v2/payments/pmt_01JC98K3P5V7N9Q2S4U6W8Y0AB/release \
  -H "Qx-Api-Key: qx_test_9fK2mW7rLx3QvB8nT4yZ1cDe" \
  -H "Qx-Idempotency-Token: 9a2b4c6d-1e3f-4a5b-8c7d-0e9f1a2b3c4d"
```

How quickly the hold disappears from the cardholder's online banking depends on the issuer. Most issuers update the available balance within minutes, but some take up to several business days.

## Retrieve a payment

`GET /v2/payments/{id}`

Returns the payment object. Use it to check the current status, for example after the customer returns from a 3-D Secure challenge or when a create request timed out.

## List payments

`GET /v2/payments`

Returns payments in the current environment, newest first, using the pagination parameters described in Request conventions. Additional filters:

| Query parameter | Description |
|---|---|
| `status` | Only payments in this status |
| `merchant_ref` | Only payments with this exact reference |
| `currency` | Only payments in this currency |

## The payment object

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier of the payment |
| `status` | string | Current status; see Lifecycle |
| `amount` | integer | Authorized amount in minor units |
| `currency` | string | ISO 4217 code |
| `captured_amount` | integer | Amount captured; `0` before capture |
| `refunded_amount` | integer | Sum of refunds that are not failed |
| `merchant_ref` | string | Your reference |
| `capture_mode` | string | `manual` or `auto` |
| `statement_descriptor` | string | Descriptor sent to the issuer |
| `description` | string or null | Your description |
| `decline_code` | string or null | Reason for a decline; see Errors |
| `authentication` | object or null | 3-D Secure details; see 3-D Secure |
| `metadata` | object | Your key-value data |
| `livemode` | boolean | `true` for live payments |
| `created_at` | string | Creation time, UTC |
| `updated_at` | string | Time of the last status change, UTC |

## Statement descriptors

The statement descriptor is the text your customers see on their bank statement next to the charge. A clear descriptor reduces the number of customers who do not recognise a payment and contact their bank.

Good descriptors contain your shop's trading name, the name customers know you by. Avoid generic words such as "PAYMENT" or "ONLINE", and avoid characters outside the allowed set, which are removed before the descriptor is sent to the issuer. Some issuers shorten the descriptor further or show it in capital letters only.

You can set a default descriptor in the Dashboard under **Settings → Public details** and override it per payment with `statement_descriptor`.

## Handling declined payments

When a payment is declined, the response contains `status: declined` and a `decline_code` that describes the reason in general terms. Show the customer a neutral message, such as "Your card was declined. Please try another card or contact your bank", and do not reveal specific risk reasons. The meaning of every decline code is listed in the Errors section.

You can retry a declined payment with a different card, or with the same card after the customer has resolved the problem with their bank. Each retry is a new payment and needs a new idempotency token and a new card token.
