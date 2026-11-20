---
title: Overview
section_id: 00-overview
api_version: v2
---

# Qorvex Pay API overview

Qorvex Pay is a card acquiring platform for online merchants based in Ukraine and in the European Economic Area. The Qorvex Pay API lets your servers accept card payments, authenticate cardholders with 3-D Secure, refund customers, receive real-time notifications about payment activity, and reconcile the money that reaches your bank account.

This documentation describes **API v2**, the current version. API v1 is deprecated; it still works for existing integrations, but new integrations must use v2. Differences between the two versions are collected in the *API v1 (legacy)* section.

## What you can build

| Capability | What it covers | Section |
|---|---|---|
| Card payments | Authorize a card, capture the funds later or immediately, release an authorization you no longer need | Payments |
| 3-D Secure | Strong customer authentication for cardholders in the EEA and for risky transactions elsewhere | 3-D Secure |
| Refunds | Return all or part of a captured payment to the cardholder | Refunds |
| Webhooks | Push notifications about payments, refunds, settlement and payouts | Webhooks |
| Settlement and payouts | Daily settlement batches, reports, and transfers to your bank account | Settlement and payouts |
| Sandbox | A full copy of the API with simulated card networks for development | Testing |

Card schemes accepted on the platform are Visa and Mastercard. Debit, credit and prepaid cards are accepted, subject to the risk rules configured for your merchant account.

## Environments

Qorvex Pay runs two fully separate environments. Each one has its own base URL, its own API keys and its own data. Objects created in the sandbox never appear in live mode and the other way round.

| Environment | Base URL | Purpose |
|---|---|---|
| Live | `https://api.qorvex.example` | Real cards, real money |
| Sandbox | `https://sandbox.qorvex.example` | Development and automated tests; no money moves |

Every API path starts with the version, for example `https://api.qorvex.example/v2/payments`. The Dashboard for both environments is available at `https://dashboard.qorvex.example`; a toggle in the top bar switches between live and sandbox data.

All traffic to the API, to the Dashboard and to the Qorvex.js library is encrypted. The API accepts connections over HTTPS only, and the server requires TLS 1.2 or newer. Plain HTTP requests are refused at the network edge and never reach the application, so they do not produce an API error response.

## How an integration fits together

A typical online store integration has four moving parts:

1. **Browser.** The checkout page loads Qorvex.js from `https://js.qorvex.example/v2/qorvex.js`. The library collects card details in secure fields and exchanges them for a short-lived card token. Raw card numbers never touch your servers, which keeps your PCI DSS scope small.
2. **Your server.** It sends the card token to the API to create a payment, decides when to capture it, and issues refunds. Every server request is authenticated with your secret API key.
3. **3-D Secure.** When the issuer asks for cardholder authentication, the API tells your server where to send the customer. After the challenge the customer returns to your site.
4. **Webhooks.** Qorvex Pay notifies your server about status changes, so you do not need to poll the API for long-running operations such as refunds and payouts.

## Payment lifecycle at a glance

A card payment moves through a small set of states. The Payments section describes each state in detail; this summary only shows the overall shape.

1. You create the payment. The platform contacts the issuer and either authorizes the amount, asks for 3-D Secure authentication first, or declines.
2. An authorized payment holds the funds on the cardholder's account. You capture it when you are ready to take the money, or you release it if the order is cancelled.
3. Captured payments are included in the next settlement batch. After the batch closes, the money is paid out to your bank account.
4. While the refund window is open, you can return the money to the cardholder in full or in part.

By default, payments are authorized first and captured in a separate call. You can ask for automatic capture per payment when you create it.

## Integration path

Getting from a first test request to live traffic usually takes these steps:

1. Create an account and open the sandbox in the Dashboard. Sandbox keys are available immediately.
2. Build the integration against the sandbox: payments, 3-D Secure, refunds and webhook handling.
3. Run the integration check from the Dashboard. The check confirms that your integration handles the flows that matter in production. Its scenarios are listed in the Testing section.
4. After the check passes, request live keys. The Authentication section explains how keys are issued and rotated.
5. Switch the base URL and the keys in your configuration, and monitor the first live payments.

## Documentation map

| Section | Read it when you need to |
|---|---|
| Authentication | Create, store, rotate and restrict API keys |
| Request conventions | Understand headers, idempotency, pagination, timestamps and metadata |
| Amounts and currencies | Express amounts correctly and check currency limits |
| Payments | Create, capture, release and look up payments |
| 3-D Secure | Handle cardholder authentication and challenges |
| Refunds | Return money to cardholders |
| Webhooks | Receive and verify event notifications |
| Errors | Interpret HTTP status codes, error codes and decline codes |
| Settlement and payouts | Reconcile batches, download reports and track payouts |
| Rate limits | Stay within request limits and handle throttling |
| Testing | Use the sandbox, test cards and the integration check |
| API v1 (legacy) | Maintain or migrate an old integration |
| Changelog | See what changed in each release |
| FAQ | Find quick answers to common questions |

## How to read this documentation

Each reference section contains **parameter tables** that list every request parameter and response field with its type, whether it is required, and its constraints. Guides, tutorials, examples and FAQ answers explain how to use those parameters in practice and sometimes simplify the details.

If a guide, a tutorial or an FAQ answer gives a value that differs from the one in a parameter table, the parameter table is authoritative. Build validation and limits in your integration from the parameter tables, and treat the surrounding prose as explanation.

Other conventions used throughout the documentation:

- Code samples use the sandbox base URL and sandbox keys. Replace both before going live.
- Path parameters are written in braces, for example `/v2/payments/{id}`.
- Field names are written in `monospace`, and enumerated values are lowercase strings.
- Examples are shortened where noted; real responses may contain additional fields. Your code must ignore fields it does not recognise.

## Versioning and compatibility

The version is part of the URL path. Within a major version, Qorvex Pay only makes backward-compatible changes:

- adding new endpoints;
- adding optional request parameters;
- adding fields to responses;
- adding new event types and new values to enumerations that are documented as extensible.

Changes that could break a working integration, such as removing a field or changing its type, are released only in a new major version. All releases, including additive ones, are listed in the Changelog.

## Glossary

| Term | Meaning |
|---|---|
| Authorization | The issuer's confirmation that the card can be charged for an amount; the amount is held on the card |
| Capture | Taking the authorized funds so they are included in settlement |
| Release | Cancelling an authorization before capture so the hold disappears from the card |
| Refund | Returning captured money to the cardholder |
| Issuer | The bank that issued the card |
| ACS | Access Control Server: the issuer's system that runs the 3-D Secure challenge |
| Settlement batch | The set of captures and refunds that the platform processes together for one business day |
| Payout | A bank transfer of settled funds to your account |
| Minor unit | The smallest unit of a currency, such as a cent; amounts in the API are expressed in minor units |
| Live mode | Requests made with live keys against real cards |

## Getting help

The Dashboard contains a support form for technical questions. When you report a problem with a specific request, include the endpoint, the time of the request in UTC, and the full error object returned by the API; the Errors section explains what the error object contains. Do not send API keys, card tokens or customer personal data to support.

Planned maintenance windows and incidents are announced on the status page linked from the Dashboard. Maintenance that affects the live environment is announced at least seven calendar days in advance.
