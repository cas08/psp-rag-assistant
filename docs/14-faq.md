---
title: FAQ
section_id: 14-faq
api_version: v2
---

# Frequently asked questions

Short answers to the questions our integration support team hears most often. Each answer names the section with the full details.

## Getting started

### What is the difference between the sandbox and live mode?

The sandbox is a separate environment with its own base URL, its own keys and simulated card networks. No money moves there, and real cards are rejected. Live mode processes real cards. Data never crosses between the two environments. Build and test everything in the sandbox first. See Testing.

### How do I get live API keys?

Live keys are issued after your integration passes the integration check, which you start from the Dashboard in sandbox mode. The check watches your sandbox traffic and confirms that your integration handles the key payment, refund and webhook flows. When the check has passed, request live keys in the Dashboard. See Authentication and Testing.

### Why does every request fail with HTTP 401?

The most common causes are a misspelled header name, a sandbox key sent to the live base URL (or the other way round), and a key that was rolled some time ago and has since been revoked. Check that the key is sent in the `Qx-Api-Key` header and that its prefix matches the environment. See Authentication.

### Can I send card numbers from my server?

No. The API does not accept raw card numbers. Card details are collected in the browser by Qorvex.js and exchanged for a single-use card token, which your server sends when creating the payment. This keeps your PCI DSS scope small. See Payments.

## Payments

### Should I capture payments immediately or later?

It depends on your business. If you ship physical goods, authorize when the customer orders and capture when the order ships; this is the default behaviour. If you deliver immediately, for example digital goods, request automatic capture when you create the payment. Remember that uncaptured authorizations expire after a few days. See Payments for the exact validity period.

### Can I change the amount after the payment is authorized?

You can capture less than the authorized amount, and the rest of the hold is released automatically. You cannot capture more than was authorized, and you can capture a payment only once. If the customer adds items to the order, create a new payment for the difference.

### The customer cancelled the order before it shipped. What should I do?

If the payment has not been captured yet, release it. This removes the hold from the customer's card quickly and moves no money. If the payment was already captured, create a refund instead.

### How long can the text on the customer's bank statement be?

The statement descriptor can be up to 22 characters long, including spaces. Use the trading name customers know you by, so that they recognise the charge. You can set a default descriptor in the Dashboard and override it for individual payments with the `statement_descriptor` parameter. See Payments for the allowed characters.

### Why was a payment declined?

The payment object contains a `decline_code` that describes the reason in general terms, such as an expired card or a decline by the issuer. The full list with suggested customer messages is in Errors. Do not retry declined payments automatically; let the customer try another card.

### What happens if the customer never returns from the 3-D Secure page?

The payment stays in `awaiting_3ds` until the challenge session expires, and is then declined. Your server learns about it from the `payment.declined` webhook event or by retrieving the payment. See 3-D Secure for the session lifetime.

## Amounts and currencies

### Which currencies can I accept?

UAH, EUR, USD, GBP, PLN, JPY, KRW and KWD. Each currency has its own minimum and maximum payment amount, listed in Amounts and currencies.

### How do I charge 1,500 yen?

Send `amount` 1500 with `currency` JPY. JPY and KRW have no minor units, so you must not multiply the amount by 100. For all other currencies, multiply by 100, except KWD, which uses 1,000 fils per dinar.

### Why was my KWD payment rejected with `amount_precision_invalid`?

Every KWD amount must be a multiple of 10 fils. Round KWD prices accordingly before showing them to the customer. See Amounts and currencies.

## Refunds

### How long do refunds take to reach the customer?

A refund is sent to the card schemes with the next settlement batch, then the issuer usually accepts it within one or two business days. After that, it typically takes 3 to 10 business days until the money appears on the customer's statement, depending on the bank. You receive the `refund.settled` webhook event when the issuer accepts the refund.

### Can I refund part of a payment?

Yes, for all currencies except UAH, and you can make several partial refunds as long as their total does not exceed the captured amount. UAH payments can only be refunded in full. See Refunds.

### Can I cancel a refund I created by mistake?

No. Refunds cannot be cancelled or edited once created, not even while they are pending. Always use idempotency tokens so that retries do not create duplicate refunds.

### Is there a time limit for refunds?

Yes. Refunds must be created within the refund window, which starts when the payment is captured. After the window closes, the API rejects refund requests. See Refunds for the length of the window.

## Webhooks

### Why did my webhook endpoint stop receiving events?

If your endpoint keeps failing deliveries, for example because it times out or returns errors, Qorvex Pay retries for many hours and eventually disables the endpoint. You receive an email when this happens. Fix the problem, re-enable the endpoint in the Dashboard, and fetch the events you missed from `GET /v2/events`.

### I received the same event twice. Is that a bug?

No. Deliveries can be duplicated, for example when your server processed an event but the acknowledgement was lost. They can also arrive out of order. Store the identifiers of processed events and skip duplicates. See Webhooks.

### How do I know a webhook really comes from Qorvex Pay?

Verify the signature in the `Qx-Signature` header with your endpoint's signing secret, and check that the `Qx-Timestamp` header is recent. The Webhooks section has a complete example.

## Settlement and payouts

### When will I receive the money from my sales?

Captures are grouped into a settlement batch every business day. Funds from a batch become available T+4 business days after the batch closes, and in automatic payout mode they are paid out on that day. The transfer usually reaches your bank on the same or the next business day. See Settlement and payouts.

### Which time zone does the API use?

All API timestamps are in UTC. Settlement follows the Kyiv business calendar, and the batch cut-off is defined in Kyiv local time. See Settlement and payouts.

### Why does the amount in the settlement report look different from the API?

The CSV report is designed for spreadsheets and accounting systems, so it uses a different number format from the JSON API. Convert between the two formats with the currency exponent when you reconcile. See Settlement and payouts.

## Limits and versions

### I am getting HTTP 429. What should I do?

You have exceeded a rate limit. Wait for the time given in the response headers, then retry with the same idempotency token. If it happens often, reduce concurrency or replace polling with webhooks. See Rate limits.

### Can I still use API v1?

Existing v1 integrations keep working until API v1 is switched off on 2027-03-31. New merchant accounts cannot use v1. Follow the migration checklist in API v1 (legacy) well before that date.
