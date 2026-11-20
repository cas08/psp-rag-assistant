---
title: Changelog
section_id: 13-changelog
api_version: v2
---

# Changelog

This page lists every change to the Qorvex Pay API, newest first. Backward-compatible changes are released without a new major version; see Request conventions for what counts as backward compatible. Entries marked **Action required** need a change in existing integrations.

Release numbers such as v2.6 identify the documentation and platform release. They are not part of the API path: every v2 release is served from `/v2`.

## Upcoming

### 2027-03-31 — API v1 switch-off

- **Action required.** API v1 will be switched off on 2027-03-31. From that date, every request to a `/v1` path returns HTTP 410 Gone, v1 callbacks stop, and the legacy credentials are deleted.
- Payments made through v1 before the switch-off stay visible in the Dashboard and in settlement reports. They can no longer be refunded through the API after the switch-off; contact support if you need to return money for such a payment.
- See API v1 (legacy) for the migration checklist.

## v2.8 — 2026-11-02

- Added `GET /v2/payments/{id}/authentication`. The endpoint returns the 3-D Secure details of a payment together with the directory server transaction ID and the time the challenge was completed, which simplifies investigations with issuers.
- Raised the `metadata` limit from 10 to 20 keys per object. The limits for key and value length are unchanged.
- The Dashboard now shows the number of throttled requests per API key on the **Developers → API usage** page.
- Fixed: `GET /v2/refunds` ignored the `status` filter when it was combined with `payment_id`.

## v2.7 — 2026-10-01

- API v1 requests now return a `Qx-Deprecation` response header with the switch-off date, to make the deprecation visible in your logs.
- Added the decline code `limit_exceeded`. Declines caused by issuer spending or frequency limits were previously reported as `issuer_declined`. Handle unknown decline codes as `issuer_declined`, as recommended in Errors.
- Statement descriptors are now validated when the payment is created. Characters outside the allowed set used to be removed silently; they are still removed, and the cleaned value is now returned in the payment object so you can see what the cardholder will see.
- Improved: error messages for `parameter_invalid` on nested parameters now name the full parameter path.

## v2.6 — 2026-08-17

- Added KWD as a supported currency. KWD has three decimal places, and amounts must respect the precision rule described in Amounts and currencies. Requests that break the rule are rejected with `amount_precision_invalid`, a new error code.
- Added the `payout.returned` event, sent when your bank returns a payout. Previously such payouts moved to `failed` without a separate event.
- Added the `deductions_amount` field to settlement batches. It was previously included in `net_amount` without being shown separately.

## v2.5 — 2026-06-09

- Raised the maximum number of webhook endpoints per environment from 5 to 10.
- Added the `types` filter to `GET /v2/events`, so you can fetch only the events you need after an outage.
- Webhook deliveries are now also sent from the address range `192.0.2.128/26`. This change was announced on 2026-05-04. **Action required** if your firewall allows only the original range: add the new range.
- Fixed: the `Qx-RateLimit-Remaining` header could show a negative value for a short time after a burst.

## v2.4 — 2026-03-23

- Added JPY and KRW as supported currencies. Both have no minor units. Funds from these payments use a different settlement currency from the payment currency; see Settlement and payouts.
- HTTP 429 responses now include a header with the time to wait before retrying, in milliseconds. See Rate limits for how to use it in your retry logic.
- Added the `customer.ip` parameter to `POST /v2/payments`. Sending it improves risk scoring and the share of frictionless 3-D Secure authentications.
- Added the `paid_out` status for settlement batches and the `payout_id` field, which link each batch to the payout that contains it.

## v2.3 — 2026-01-15

- **Action required for v1 users.** API v1 is deprecated and closed to new merchant accounts. The switch-off date is 2027-03-31.
- The integration check is now required before the first live keys of a merchant account are issued. Accounts that already had live v2 keys are not affected. The scenarios are listed in Testing.
- Added the `force` value for `authentication.mode`, which requests 3-D Secure for every payment regardless of regulation and risk score.
- Added PLN as a supported currency.

## v2.2 — 2025-10-06

- Refunds now have a lifecycle. A refund starts in `pending`, and moves to `settled` when the issuer accepts it or to `failed` when the issuer rejects it. Previously refunds were final when created, and failures were reported only by email.
- Added the `refund.settled` and `refund.failed` events and the `settled_at` and `failure_reason` fields.
- Failed refunds no longer count towards a payment's `refunded_amount`, so the amount can be refunded again.

## v2.1 — 2025-07-14

- Added read-only secret keys. Use them for reporting tools and anything else that should never move money.
- Added the IP allowlist for live secret keys under **Developers → Security**.
- Key rolling now has an overlap period during which the previous key keeps working, so you can deploy a new key without downtime. The length of the overlap is described in Authentication. **Roll and revoke now** remains available for compromised keys.
- Added the `Qx-RateLimit-Limit` and `Qx-RateLimit-Remaining` response headers.

## v2.0 — 2025-04-01

API v2 is generally available. It is a new major version with the following changes compared to API v1:

- **Authentication.** Requests are authenticated with the `Qx-Api-Key` header and new key formats that show the environment in the prefix. Legacy credentials do not work with v2.
- **Amounts.** All amounts are integers in minor units. The legacy decimal representation is not accepted.
- **Identifiers.** Payments are identified by a platform-generated ID. Your own reference moves to the new `merchant_ref` field.
- **Capture.** Payments are authorized only, and captured in a separate request, unless automatic capture is requested when the payment is created. This reverses the default behaviour of v1.
- **Release.** Uncaptured authorizations are released with the new release endpoint.
- **Idempotency.** Every `POST` request requires an idempotency token, which makes retries safe.
- **3-D Secure.** Full EMV 3-D Secure 2.2 support through the API, including the challenge flow with `return_url`.
- **Refunds.** The refund window is longer than in v1, and refunds are created with their own endpoint and identifiers.
- **Webhooks.** Callbacks are replaced by webhooks: multiple endpoints per environment, a selectable list of event types, an event envelope with a snapshot of the object, signatures that include a timestamp and replace the legacy signature scheme, a longer retry schedule, and the events API for recovering missed deliveries.
- **Errors.** Errors use HTTP status codes and string codes in a consistent error object.
- **Pagination.** List endpoints use cursor-based pagination.

Supported currencies at launch were UAH, EUR, USD and GBP. Later releases added the remaining currencies listed in Amounts and currencies.
