---
title: Testing
section_id: 11-testing
api_version: v2
---

# Testing

The Qorvex Pay sandbox is a complete copy of the API that runs against simulated card schemes and issuers. Use it to build and test your integration, to run automated tests in your CI pipeline, and to pass the integration check.

## Sandbox basics

| Item | Sandbox value |
|---|---|
| Base URL | `https://sandbox.qorvex.example` |
| Secret keys | Start with `qx_test_` |
| Publishable keys | Start with `qxp_test_` |
| Money | None; no real funds move and no real cards are charged |
| Rate limit | 10 requests per second per key by default; see Rate limits |
| Data retention | Objects are kept for 90 days, then deleted |

The sandbox implements the same endpoints, parameters, validation rules, error codes and webhook events as live mode. Differences are limited to the points listed under *How the sandbox differs from live mode* below.

Real card numbers are rejected in the sandbox, and test card numbers are rejected in live mode. Never use a real card to test your integration.

## Test cards

Enter these numbers into the Qorvex.js card fields on your sandbox checkout page. Use any expiry date in the future, any three-digit security code and any cardholder name. Test card numbers are not real card numbers and work only in the sandbox; the scheme column shows which scheme the sandbox simulates for each of them.

| # | Card number | Scheme | Result |
|---|---|---|---|
| 1 | 9990 0000 0000 0102 | Visa | Authorized; 3-D Secure not attempted |
| 2 | 9990 0000 0000 0219 | Mastercard | Authorized after frictionless 3-D Secure |
| 3 | 9990 0000 0000 0326 | Visa | 3-D Secure challenge; complete it with the one-time code described in 3-D Secure |
| 4 | 9990 0000 0000 0433 | Mastercard | 3-D Secure challenge that always fails; payment declined |
| 5 | 9990 0000 0000 0540 | Visa | Declined with `issuer_declined` |
| 6 | 9990 0000 0000 0656 | Mastercard | Declined with `card_balance_low` |
| 7 | 9990 0000 0000 0763 | Visa | Declined with `card_expired` |
| 8 | 9990 0000 0000 0870 | Mastercard | Declined with `cvc_mismatch` |
| 9 | 9990 0000 0000 0987 | Visa | Declined with `suspected_fraud` |
| 10 | 9990 0000 0000 1092 | Mastercard | Declined with `issuer_unavailable` |
| 11 | 9990 0000 0000 1100 | Visa | Authorized; any refund of this payment ends in `failed` |
| 12 | 9990 0000 0000 1217 | Mastercard | Declined with `card_not_supported` |

The result depends only on the card number. Amount, currency and customer data do not change the simulated outcome, except where validation rules apply, such as minimum amounts or KWD precision.

With card 3 you can also test an abandoned challenge: open the challenge page and do nothing until the session expires. With card 11 you can test how your system reacts when a refund fails after it was created.

## Testing webhooks

Register a webhook endpoint with your sandbox key exactly as in live mode. Every action you take in the sandbox produces the same events that live mode would produce. In addition, the **Send test event** button on the endpoint page in the Dashboard sends a sample event of any type, signed with the endpoint's secret.

Your endpoint must be reachable from the internet. During local development, use a tunnelling tool that exposes your local server through an HTTPS URL, and register that URL as a sandbox endpoint.

## How the sandbox differs from live mode

- **Settlement.** Sandbox batches open and close on the same schedule as live batches, but nothing is sent to card schemes. Refunds in a closed sandbox batch move to `settled` a few minutes after the batch closes, unless they belong to a payment made with test card 11.
- **Payouts.** Sandbox payouts follow the same timeline and statuses as live payouts and move to `paid` automatically. No bank transfer takes place.
- **3-D Secure.** The challenge page is a simulated ACS page served by the sandbox, not a real bank page.
- **Limits.** Rate limits are lower than in live mode.
- **Retention.** Sandbox objects are deleted after 90 days.

## The integration check

The integration check confirms that your integration handles the flows that matter most in production, using your own sandbox traffic rather than a questionnaire. Authentication explains when the check is required. It consists of six mandatory scenarios:

| # | Scenario | Passed when |
|---|---|---|
| 1 | Authorize and capture | A payment created with manual capture is captured in a separate request |
| 2 | 3-D Secure challenge | A payment with test card 3 completes the challenge, and your server retrieves the payment after the customer returns |
| 3 | Decline handling | A payment with one of the decline test cards is declined, and no automatic retry with the same card follows within one minute |
| 4 | Release | An authorized payment is released |
| 5 | Partial refund | A captured payment in a currency other than UAH is partially refunded, using an idempotency token |
| 6 | Webhook handling | Your endpoint acknowledges a signed event with a 2xx status, and rejects a test event with an invalid signature |

### Running the check

1. Open the Dashboard in sandbox mode and go to **Developers → Integration check**.
2. Click **Start check**. From this moment the platform watches the traffic of your sandbox keys for seven calendar days.
3. Run through the scenarios using your real checkout and back-office code, not hand-written requests. Each scenario is marked as passed as soon as matching traffic is observed.
4. For scenario 6, click **Send invalid test event** on the check page while your endpoint is running.
5. When all six scenarios are marked as passed, the check is complete and its status in the Dashboard changes to **Passed**.

If the seven days run out before all scenarios have passed, start the check again; scenarios that already passed must be repeated. The check can be run any number of times.

A passed check stays valid for the merchant account: you do not need to repeat it when you roll keys or add read-only keys. If you rebuild your integration from scratch, we recommend running the check again to confirm that the new code handles every scenario.

## Automated tests

The sandbox is suitable for automated integration tests in CI pipelines. Some recommendations:

- Use a dedicated sandbox key for CI, separate from the keys developers use, so that you can rotate it independently.
- Generate a fresh idempotency token for every test run, otherwise a second run returns the stored responses of the first one.
- Add the CI job number to `merchant_ref`, so you can find the payments of a test run in the Dashboard.
- Keep tests within the sandbox rate limit; a test suite that runs many payments in parallel can be throttled.
- Do not depend on sandbox objects older than 90 days.

## From sandbox to live

When your live keys have been issued (see Authentication):

1. Replace the base URL, the secret key and the publishable key in your production configuration.
2. Register your live webhook endpoints; sandbox endpoints are not copied.
3. Make a small live payment with your own card, capture it, and refund it.
4. Check that the live payment, capture and refund events reached your endpoint and passed signature verification.
