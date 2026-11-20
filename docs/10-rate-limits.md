---
title: Rate limits
section_id: 10-rate-limits
api_version: v2
---

# Rate limits

Rate limits protect the platform and every merchant on it from sudden traffic spikes, runaway scripts and retry storms. This section lists the limits, explains how they are counted and shows how to react when you reach them.

## How limits are counted

Limits are applied per API key and are measured in requests per second, using a token bucket. Each key has a bucket that refills continuously at the rate of its limit, and every request takes one token from it. When the bucket is empty, further requests are rejected until it refills. The bucket can hold up to one second's worth of tokens, which lets short bursts through without allowing sustained traffic above the limit.

The default rate limit is 40 requests per second per live API key. In the sandbox, the default is 10 requests per second per key. Every request counts, whatever its outcome, including requests that fail with validation errors.

Some endpoint groups have their own, lower limits. A request to such an endpoint takes a token from the group's bucket and from the key's default bucket, so a group limit never lets a key exceed its default limit. Report downloads are the one exception; they are described in the note below the table.

Additional keys of the same account have their own buckets. This is not a way to raise throughput, though: an account-wide ceiling of four times the default limit applies to the sum of all live keys of one merchant account.

## Limits by endpoint

| Endpoint group | Live | Sandbox |
|---|---|---|
| All endpoints (default) | 40 requests per second | 10 requests per second |
| `POST /v2/payments` | 40 requests per second | 10 requests per second |
| `POST /v2/payments/{id}/capture`, `POST /v2/payments/{id}/release` | 40 requests per second | 10 requests per second |
| `GET /v2/payments`, `GET /v2/refunds` | 25 requests per second | 10 requests per second |
| `POST /v2/refunds` | 20 requests per second | 4 requests per second |
| `POST /v2/payouts` | 5 requests per second | 2 requests per second |
| `GET /v2/payouts`, `GET /v2/balance` | 10 requests per second | 4 requests per second |
| `GET /v2/settlements`, `GET /v2/settlements/{id}` | 10 requests per second | 4 requests per second |
| `GET /v2/settlements/{id}/report` | See note ¹ | See note ¹ |
| Webhook endpoint management | 10 requests per second | 4 requests per second |
| `GET /v2/events`, `GET /v2/events/{id}` | 25 requests per second | 10 requests per second |
| `GET /v2/payments/{id}`, `GET /v2/refunds/{id}` | 40 requests per second | 10 requests per second |

¹ The general limit does not apply to `GET /v2/settlements/{id}/report`. Report downloads are limited to 6 requests per minute per merchant account, shared by all keys of the account, in both environments. Reports are large and do not change after a batch is closed, so download each report once and keep a copy.

If your business needs higher limits, for example for a planned sales campaign, contact support at least 10 business days in advance with your expected peak traffic. Limits for `POST /v2/payments` can be raised temporarily; limits for report downloads cannot.

## Rate limit headers

Every response includes headers that show the state of the bucket that is closest to running out for this request:

| Header | Description |
|---|---|
| `Qx-RateLimit-Limit` | The limit of the bucket, in requests per second |
| `Qx-RateLimit-Remaining` | Whole requests that can still be made right now |

Use these headers to slow down before you hit the limit, especially in batch jobs that list many objects.

## When you exceed a limit

A request that exceeds a limit is rejected with HTTP 429 Too Many Requests before any processing happens, so it never creates or changes anything. The response carries a `Qx-Retry-In` header with the number of **milliseconds** to wait before the next request will be accepted. The body is a standard error object of type `rate_limit`; its code is listed in the Errors section.

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Qx-RateLimit-Limit: 40
Qx-RateLimit-Remaining: 0
Qx-Retry-In: 850
```

Note that `Qx-Retry-In` is expressed in milliseconds, not seconds. A value of `850` means you can retry after 0.85 seconds.

### Retrying throttled requests

1. Wait at least the number of milliseconds given in `Qx-Retry-In`. Add a small random delay so that parallel workers do not retry at the same instant.
2. Retry with the same `Qx-Idempotency-Token` for `POST` requests. Throttled requests are not executed, so a retry is always safe.
3. If you are throttled repeatedly, reduce concurrency instead of retrying faster.

```python
import random
import time

import requests


def call_with_throttling(session: requests.Session, method: str, url: str, **kwargs) -> requests.Response:
    for _ in range(6):
        response = session.request(method, url, **kwargs)
        if response.status_code != 429:
            return response
        wait_ms = int(response.headers.get("Qx-Retry-In", "1000"))
        time.sleep(wait_ms / 1000 + random.uniform(0, 0.2))
    return response
```

## Designing for the limits

- **Use webhooks instead of polling.** A loop that checks the status of every open order once per second grows with your order volume: ten open orders already use a quarter of your default limit.
- **Spread batch jobs.** Run large exports and reconciliation jobs outside your peak sales hours, and pace them with the rate limit headers.
- **Limit concurrency.** A worker pool with a fixed number of workers is easier to keep under the limit than unbounded parallelism.
- **Cache what does not change.** Closed settlement batches, settlement reports and final payment statuses never change; fetch them once.
- **Separate keys by workload.** Give your checkout and your back-office tools different keys, so that a heavy report job cannot throttle checkout traffic. Remember the account-wide ceiling when you plan this.

## What does not count towards your limits

- **Webhook deliveries.** Events that Qorvex Pay sends to your endpoints are outgoing traffic and do not use your buckets. Your own calls back to the API while handling a webhook do count.
- **Qorvex.js requests.** Card tokens are created in the customer's browser with a publishable key. These requests are limited per customer IP address by the platform's own abuse protection, not by the buckets of your secret keys.
- **Dashboard activity.** Actions that your team performs in the Dashboard do not use API buckets.

## Monitoring your usage

The Dashboard shows request volume and the number of throttled requests per key for the last 30 calendar days under **Developers → API usage**. A small number of throttled requests during peaks is normal and harmless if your retry logic works. A steady share of throttled requests usually means that a job is polling too often or that too many workers share one key. Set up an alert on the share of HTTP 429 responses in your own monitoring, so that you notice the problem before it affects checkout.

## Sandbox differences

Sandbox limits are deliberately lower than live limits, so that load tests against the sandbox do not give a misleading picture of live capacity. Do not run performance tests against the live API; contact support if you need to plan a load test.

Throttling in the sandbox behaves exactly like in live mode, including the response headers. You can therefore test your retry logic in the sandbox by sending requests faster than the sandbox limit.
