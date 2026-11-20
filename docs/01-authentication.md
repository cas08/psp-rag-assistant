---
title: Authentication
section_id: 01-authentication
api_version: v2
---

# Authentication

Every request to the Qorvex Pay API must be authenticated with an API key that belongs to your merchant account. The API uses the key to identify the account, to choose between live and sandbox data, and to check what the caller is allowed to do.

## Key types

Each environment has two kinds of keys.

| Key type | Prefix | Where it is used | What it can do |
|---|---|---|---|
| Live secret key | `qx_live_` | Your servers only | Every API operation on live data |
| Sandbox secret key | `qx_test_` | Your servers, CI pipelines | Every API operation on sandbox data |
| Live publishable key | `qxp_live_` | Browser, through Qorvex.js | Create card tokens for live payments |
| Sandbox publishable key | `qxp_test_` | Browser, through Qorvex.js | Create card tokens for sandbox payments |

The prefix tells you at a glance which environment a key belongs to. A key with the `qx_test_` prefix only works against the sandbox base URL, and a key with the `qx_live_` prefix only works against the live base URL. Sending a key to the wrong environment is treated the same way as sending an unknown key.

Secret keys grant full access to your account and must stay on your servers. Publishable keys are safe to embed in web pages and mobile apps: they can only be used by Qorvex.js to turn card details into card tokens and cannot read or change any other data.

## Sending the key

Pass the secret key in the `Qx-Api-Key` request header. The header is required on every server-side request; no other authentication method is accepted by API v2.

```bash
curl https://sandbox.qorvex.example/v2/payments/pmt_01JC8Z5V4QK2M7T3XW9RBN6D0F \
  -H "Qx-Api-Key: qx_test_9fK2mW7rLx3QvB8nT4yZ1cDe"
```

Some points to keep in mind:

- The header name is case-insensitive, as with any HTTP header, but the key value is case-sensitive.
- Do not put the key in the query string or in the request body. Keys sent in those places are ignored and the request fails as unauthenticated.
- All requests must use HTTPS. The API only accepts TLS 1.2 or newer, and connections negotiated with older protocol versions are closed during the handshake.

If the header is missing, empty, malformed, revoked or belongs to the other environment, the API responds with HTTP 401 and the error code `api_key_invalid`. A 401 response never reveals whether a key exists; the message is the same for every failure reason.

## Read-only keys

In addition to the standard secret key, you can create up to five additional secret keys in the Dashboard under **Developers → API keys**. Each additional key is either *full access* or *read-only*.

| Permission | Allowed requests |
|---|---|
| Full access | All `GET`, `POST` and `DELETE` requests |
| Read-only | `GET` requests only |

Read-only keys are useful for reporting tools, BI exports and support dashboards that should never move money. A read-only key uses the same prefix as other secret keys of its environment.

When a key is valid but not allowed to perform an operation, the API responds with HTTP 403 and the error code `key_not_permitted`. The same response is returned when a publishable key is sent to a server-side endpoint.

## Sandbox and live keys

Sandbox keys are created automatically when you open your account, so you can start building right away.

Live keys are not available immediately. They are issued only after your integration passes the integration check, a set of end-to-end scenarios that you run against the sandbox from the Dashboard. The Testing section lists the scenarios and explains how to start the check. Once the check is marked as passed, the **Request live keys** button in the Dashboard becomes active, and the keys appear in the live environment after the account review is complete.

Because live and sandbox keys have different prefixes and different base URLs, we recommend keeping both in configuration and switching them together:

| Setting | Sandbox | Live |
|---|---|---|
| Base URL | `https://sandbox.qorvex.example` | `https://api.qorvex.example` |
| Secret key | `qx_test_…` | `qx_live_…` |
| Publishable key | `qxp_test_…` | `qxp_live_…` |

## Rotating keys

Rotate a secret key if it may have been exposed, when an employee who had access leaves, or on a regular schedule required by your security policy.

To rotate a key, open **Developers → API keys**, choose the key and click **Roll key**. The Dashboard generates a new key and shows it once. From that moment:

1. The new key is active immediately.
2. The previous key keeps working for 36 hours, so you can deploy the new key to all servers without downtime.
3. When the 36 hours have passed, the previous key is revoked and requests that still use it fail with HTTP 401.

If you believe a key has been compromised, choose **Roll and revoke now** instead. This option skips the overlap period and revokes the old key at once, so deploy the new key before you use it.

Publishable keys are rolled the same way. Because publishable keys are embedded in front-end code, remember to rebuild and redeploy your pages or apps after rolling one.

Key creation, rolling and revocation are recorded in the Dashboard audit log together with the user who performed the action.

## Restricting access by IP address

For additional protection, you can restrict live secret keys to a list of IP addresses. Open **Developers → Security** and add up to 20 IPv4 addresses or CIDR ranges. When the list is not empty, requests that use a live secret key from any other address are rejected with HTTP 403 and the error code `key_not_permitted`.

The IP allowlist does not apply to sandbox keys or to publishable keys. Changes to the list take effect within one minute.

## Storing keys safely

API keys are credentials and should be handled like passwords:

- Keep secret keys in a secrets manager or in environment variables injected at deploy time. Never commit them to source control.
- Never embed a secret key in a browser page, a mobile app or any other code that runs on a customer's device.
- Give each service its own key, so you can rotate or revoke one without affecting the others.
- Use read-only keys for any system that only needs to read data.
- Remove keys from log output. API keys are never needed to debug a request; the error object and the request time are enough.

If a secret key appears in a public repository, a ticket, a chat message or a log file, roll it immediately with **Roll and revoke now**.

## Authentication errors

| HTTP status | Error code | Typical cause | What to do |
|---|---|---|---|
| 401 | `api_key_invalid` | Header missing or misspelled, key revoked, key from the other environment, key rolled more than 36 hours ago | Check the header name, the key value and the base URL |
| 403 | `key_not_permitted` | Read-only key used for a write request, publishable key used on the server, request from an address outside the IP allowlist | Use a full-access secret key from an allowed address |

The full list of error codes and the structure of error responses are described in the Errors section.
