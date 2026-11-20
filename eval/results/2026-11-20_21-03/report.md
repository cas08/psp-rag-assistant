# Evaluation: RAG vs no RAG

Model: `qwen3:8b` · 2026-11-20 21:10

## Summary

Verdicts: manual where filled, otherwise LLM judge

| Mode | Correct | Partial | Hallucinated | Answers with invented endpoint/parameter | Avg facts found | Avg time, s |
|---|---|---|---|---|---|---|
| RAG | 15/15 | 0/15 | 0/15 | 0/15 | 90% | 11.7 |
| No RAG | 0/15 | 0/15 | 15/15 | 6/15 | 10% | 7.2 |

## Per question

| # | Question | RAG | No RAG | Invented without RAG | Comment on the no-RAG answer |
|---|---|---|---|---|---|
| q01 | How long after capture can I still refund a payment? | correct | hallucinated |  | says 12 months; real window is 45 days |
| q02 | What is the maximum length of statement_descriptor? | correct | hallucinated |  | says 22 (generic/Stripe value); real limit 18 |
| q03 | How long can an authorized payment wait before I capture it? | correct | hallucinated |  | says 7 days; real limit 120 hours |
| q04 | Can I partially refund a payment made in UAH? | correct | hallucinated | endpoint /refund | says partial UAH refunds work; invents POST /refund and transaction_id |
| q05 | Which endpoint do I call to cancel a refund that I created by mistake? | correct | hallucinated | endpoint /refund/cancel; header Authorization: Bearer | invents POST /refund/cancel and Authorization: Bearer |
| q06 | The customer cancelled the order before shipping. How do I void the authorization? | correct | hallucinated | endpoint /v1/void; header Authorization: Bearer | invents /v1/void, authorization_id, Authorization: Bearer |
| q07 | Which HTTP header carries the API key, and what error do I get if it is wrong? | correct | hallucinated |  | Authorization header instead of Qx-Api-Key; 401 is right |
| q08 | How do I charge 1,500 Japanese yen? | correct | hallucinated | endpoint /api/v1/charges | 1500 JPY right, but invents /api/v1/charges and payment_method_id |
| q09 | How do I verify that a webhook really came from Qorvex Pay? | correct | hallucinated | header X-Qorvex-Signature | invents X-Qorvex-Signature; no timestamp check |
| q10 | My webhook endpoint was down for a day. How can I ask Qorvex Pay to resend the missed events? | correct | hallucinated |  | says support can resend; docs say it cannot |
| q11 | I got HTTP 429. How long should I wait before retrying? | correct | hallucinated |  | says wait 1 minute; real answer: Qx-Retry-In in ms |
| q12 | After I roll a secret API key, how long does the old key keep working? | correct | hallucinated |  | says old key is invalidated immediately; really 36 h overlap |
| q13 | Which sandbox test card triggers a 3-D Secure challenge, and what code completes it? | correct | hallucinated |  | invents card 4212 5768 9999 9999 and code 123456 |
| q14 | How long is an idempotency token stored, and what happens if I reuse it with a different request body? | correct | hallucinated |  | vague lifetime; wrong behaviour on reuse (really 422) |
| q15 | When does the daily settlement batch close, and when is the money paid out? | correct | hallucinated |  | invents 23:59 UTC cut-off and 1-3 day payout |

## Answers

### q01 · RAG · correct

**Q:** How long after capture can I still refund a payment?

**Reference:** 45 days after the payment is captured. After that the API returns HTTP 422 with refund_window_closed.

**Answer:**

You can refund a payment within 45 days after the payment is captured. The refund window is counted from the `updated_at` time at which the payment became `captured`, in whole days of 24 hours [06-refunds].

facts found: 1/2 · invented: —

### q01 · No RAG · hallucinated

**Q:** How long after capture can I still refund a payment?

**Reference:** 45 days after the payment is captured. After that the API returns HTTP 422 with refund_window_closed.

**Answer:**

You can refund a payment up to 12 months after it was captured. 

For example, if a payment was captured on January 1, 2024, you can initiate a refund anytime between January 1, 2024, and December 31, 2024. After this period, the payment is no longer eligible for refund.

facts found: 0/2 · invented: —

### q02 · RAG · correct

**Q:** What is the maximum length of statement_descriptor?

**Reference:** 18 characters (Latin letters, digits, spaces and . - *). The FAQ says 22, but the parameter table is authoritative.

**Answer:**

The maximum length of `statement_descriptor` is 18 characters [04-payments].

facts found: 1/1 · invented: —

### q02 · No RAG · hallucinated

**Q:** What is the maximum length of statement_descriptor?

**Reference:** 18 characters (Latin letters, digits, spaces and . - *). The FAQ says 22, but the parameter table is authoritative.

**Answer:**

The maximum length of the statement descriptor is 22 characters.  

For example, a valid descriptor could be "Qorvex Payment". If your text exceeds 22 characters, it will be truncated or rejected by the payment processor.

facts found: 0/1 · invented: —

### q03 · RAG · correct

**Q:** How long can an authorized payment wait before I capture it?

**Reference:** 120 hours. After that it is released automatically and moves to status expired (event payment.auth_expired); it cannot be captured.

**Answer:**

An authorized payment can wait up to 120 hours (5 days) before it expires. If it is not captured within this window, the platform automatically releases the authorization, and the payment moves to the `expired` status. An expired payment cannot be captured; you must create a new payment to charge the customer again [04-payments].

facts found: 2/2 · invented: —

### q03 · No RAG · hallucinated

**Q:** How long can an authorized payment wait before I capture it?

**Reference:** 120 hours. After that it is released automatically and moves to status expired (event payment.auth_expired); it cannot be captured.

**Answer:**

The authorized payment can typically wait for up to **7 days** before it needs to be captured. If not captured within this period, the authorization may expire, and the funds may be released back to the customer's account.

**Example:** If you authorize a payment on Monday, you have until the end of the following Monday to capture it. If you don't capture it by then, the authorization expires.

facts found: 0/2 · invented: —

### q04 · RAG · correct

**Q:** Can I partially refund a payment made in UAH?

**Reference:** No. UAH payments can only be refunded in full, in a single refund. A partial amount is rejected with HTTP 422 refund_amount_invalid. Workaround — refund in full and create a new payment for the part the customer keeps.

**Answer:**

No, you cannot partially refund a payment made in UAH. UAH payments can only be refunded in full. If you need to return only part of a UAH payment, refund it in full and create a new payment for the part the customer keeps [06-refunds].

facts found: 1/2 · invented: —

### q04 · No RAG · hallucinated

**Q:** Can I partially refund a payment made in UAH?

**Reference:** No. UAH payments can only be refunded in full, in a single refund. A partial amount is rejected with HTTP 422 refund_amount_invalid. Workaround — refund in full and create a new payment for the part the customer keeps.

**Answer:**

Yes, you can partially refund a payment made in UAH using the Qorvex Pay API.

**Example:**
To partially refund a transaction, you would use the `/refund` endpoint and specify the amount to refund in UAH. For instance:

```http
POST /refund HTTP/1.1
Content-Type: application/json

{
  "transaction_id": "TX123456789",
  "amount": 500,
  "currency": "UAH"
}
```

This would refund 500 UAH from the original transaction. Make sure the amount does not exceed the original payment amount.

facts found: 0/2 · invented: endpoint /refund

### q05 · RAG · correct

**Q:** Which endpoint do I call to cancel a refund that I created by mistake?

**Reference:** There is no such endpoint. A refund cannot be cancelled or edited once created, even while pending; support cannot stop it either.

**Answer:**

There is no endpoint for cancelling or editing a refund once it has been created [14-faq].

facts found: 1/1 · invented: —

### q05 · No RAG · hallucinated

**Q:** Which endpoint do I call to cancel a refund that I created by mistake?

**Reference:** There is no such endpoint. A refund cannot be cancelled or edited once created, even while pending; support cannot stop it either.

**Answer:**

The endpoint to cancel a refund is `/refund/cancel`.

**Example Request:**
```http
POST https://api.qorvexpay.com/refund/cancel
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY

{
  "refund_id": "RF123456789"
}
```

**Note:** Ensure you have the correct `refund_id` and valid API credentials.

facts found: 0/1 · invented: endpoint /refund/cancel; header Authorization: Bearer

### q06 · RAG · correct

**Q:** The customer cancelled the order before shipping. How do I void the authorization?

**Reference:** Call POST /v2/payments/{id}/release (no parameters). Only payments in status authorized can be released; otherwise 409 payment_not_releasable. If already captured, refund instead.

**Answer:**

To void the authorization, release the payment using the `POST /v2/payments/{id}/release` endpoint. This removes the hold from the customer's card and is the correct way to void an authorization in Qorvex Pay [04-payments].

The endpoint takes no parameters. Only payments in status `authorized` can be released; for any other status the request fails with HTTP 409 and the error code `payment_not_releasable` [04-payments].

facts found: 1/1 · invented: —

### q06 · No RAG · hallucinated

**Q:** The customer cancelled the order before shipping. How do I void the authorization?

**Reference:** Call POST /v2/payments/{id}/release (no parameters). Only payments in status authorized can be released; otherwise 409 payment_not_releasable. If already captured, refund instead.

**Answer:**

To void the authorization, you need to send a **void request** to the Qorvex Pay API using the **authorization ID** obtained during the payment process. This will cancel the transaction and release the funds back to the customer's account.

### Example (using cURL):
```bash
curl -X POST https://api.qorvexpay.com/v1/void \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "authorization_id": "AUTH_123456789"
  }'
```

### Notes:
- Ensure the authorization is still valid (not yet settled).
- Voiding is only possible before the payment is captured or settled.
- Always confirm the success of the void operation via the API response.

facts found: 0/1 · invented: endpoint /v1/void; header Authorization: Bearer

### q07 · RAG · correct

**Q:** Which HTTP header carries the API key, and what error do I get if it is wrong?

**Reference:** Qx-Api-Key header. A missing, invalid, revoked or wrong-environment key gives HTTP 401 with error code api_key_invalid.

**Answer:**

The HTTP header `Qx-Api-Key` carries the API key. If it is wrong, you get the error `api_key_invalid` with HTTP status 401 [01-authentication].

facts found: 3/3 · invented: —

### q07 · No RAG · hallucinated

**Q:** Which HTTP header carries the API key, and what error do I get if it is wrong?

**Reference:** Qx-Api-Key header. A missing, invalid, revoked or wrong-environment key gives HTTP 401 with error code api_key_invalid.

**Answer:**

The `Authorization` header carries the API key. If the API key is incorrect, you will receive a `401 Unauthorized` error.

facts found: 1/3 · invented: —

### q08 · RAG · correct

**Q:** How do I charge 1,500 Japanese yen?

**Reference:** Send amount 1500 with currency JPY. JPY has no minor units (exponent 0), so do not multiply by 100.

**Answer:**

Send `amount` 1500 with `currency` JPY. JPY has no minor units, so you must not multiply the amount by 100 [03-amounts-and-currencies].

facts found: 2/2 · invented: —

### q08 · No RAG · hallucinated

**Q:** How do I charge 1,500 Japanese yen?

**Reference:** Send amount 1500 with currency JPY. JPY has no minor units (exponent 0), so do not multiply by 100.

**Answer:**

To charge 1,500 Japanese yen, send a request to the Qorvex Pay API with the amount set to `1500` and the currency code set to `JPY`.  

**Example request:**
```http
POST /api/v1/charges
Content-Type: application/json

{
  "amount": 1500,
  "currency": "JPY",
  "payment_method_id": "pm_1234567890",
  "description": "Test charge"
}
```

Make sure you have a valid payment method ID and proper API authentication.

facts found: 1/2 · invented: endpoint /api/v1/charges

### q09 · RAG · correct

**Q:** How do I verify that a webhook really came from Qorvex Pay?

**Reference:** Compute HMAC-SHA256 with the endpoint's signing secret over "<Qx-Timestamp>.<raw body>", compare with the Qx-Signature header using a constant-time comparison, and reject deliveries whose timestamp differs from server time by more than 180 seconds.

**Answer:**

Verify the signature in the `Qx-Signature` header with your endpoint's signing secret, and check that the `Qx-Timestamp` header is recent [14-faq]. The process involves:

1. Reading the raw request body before any JSON parsing.
2. Building the signed string from the `Qx-Timestamp` header value, a `.` character, and the raw body.
3. Computing HMAC-SHA256 of that string with the signing secret and comparing the result with `Qx-Signature` using a constant-time comparison.
4. Checking that the timestamp is fresh, i.e., it differs from your server's current time by no more than 180 seconds [07-webhooks].

facts found: 4/4 · invented: —

### q09 · No RAG · hallucinated

**Q:** How do I verify that a webhook really came from Qorvex Pay?

**Reference:** Compute HMAC-SHA256 with the endpoint's signing secret over "<Qx-Timestamp>.<raw body>", compare with the Qx-Signature header using a constant-time comparison, and reject deliveries whose timestamp differs from server time by more than 180 seconds.

**Answer:**

To verify a webhook from Qorvex Pay, you should validate the request signature using the secret key provided in your Qorvex Pay dashboard. Here's how:

**Short Answer:**  
Use the `X-Qorvex-Signature` header and your secret key to verify the request signature.

**Details:**  
1. Receive the webhook request.
2. Extract the `X-Qorvex-Signature` header value.
3. Use your secret key to generate a hash of the request body (using HMAC-SHA256).
4. Compare the generated hash with the `X-Qorvex-Signature` value. If they match, the request is authentic.

**Example (Python):**
```python
import hmac
import hashlib

secret_key = 'your_secret_key'
request_body = '{"event": "payment_success", "data": {"amount": 100}}'
signature = 'X-Qorvex-Signature: 3a7d4e1f8c9b0a2d1e3c4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a'

# Extract the signature from the header
signature_value = signature.split(': ')[1]

# Generate the hash
signature_generated = hmac.new(secret_key.encode(), request_body.encode(), hashlib.sha256).hexdigest()

if signature_generated == signature_value:
    print("Webhook is authentic.")
else:
    print("Webhook is not authentic.")
```

Make sure to keep your secret key secure and never expose it in client-side code.

facts found: 1/4 · invented: header X-Qorvex-Signature

### q10 · RAG · correct

**Q:** My webhook endpoint was down for a day. How can I ask Qorvex Pay to resend the missed events?

**Reference:** There is no resend endpoint and support cannot trigger redelivery. Fetch missed events with GET /v2/events (types, created_from/created_to filters); events are kept for 14 days.

**Answer:**

There is no endpoint to resend a webhook event, and support cannot trigger redelivery. You must fetch the missed events from the API with `GET /v2/events` [07-webhooks].

facts found: 1/2 · invented: —

### q10 · No RAG · hallucinated

**Q:** My webhook endpoint was down for a day. How can I ask Qorvex Pay to resend the missed events?

**Reference:** There is no resend endpoint and support cannot trigger redelivery. Fetch missed events with GET /v2/events (types, created_from/created_to filters); events are kept for 14 days.

**Answer:**

You can request Qorvex Pay to resend missed events by contacting their support team and providing the date range of the downtime and the specific event types you need resent. 

**Example request:**  
"Hi Qorvex Pay Support, our webhook endpoint was down from [start date] to [end date]. Could you please resend any missed events during that period for [specific event types, e.g., payment success, refund, etc.]?"

facts found: 0/2 · invented: —

### q11 · RAG · correct

**Q:** I got HTTP 429. How long should I wait before retrying?

**Reference:** Wait the time in the Qx-Retry-In response header, which is in milliseconds (e.g. 850 = 0.85 s), plus a small random jitter; retry POSTs with the same Qx-Idempotency-Token.

**Answer:**

You should wait for the time given in the `Qx-Retry-In` header, which is expressed in milliseconds [10-rate-limits]. For example, a value of `850` means you can retry after 0.85 seconds [10-rate-limits].

facts found: 2/2 · invented: —

### q11 · No RAG · hallucinated

**Q:** I got HTTP 429. How long should I wait before retrying?

**Reference:** Wait the time in the Qx-Retry-In response header, which is in milliseconds (e.g. 850 = 0.85 s), plus a small random jitter; retry POSTs with the same Qx-Idempotency-Token.

**Answer:**

You should wait for at least 1 minute before retrying the request. The 429 error indicates the server is receiving too many requests, so it's best to wait for the full duration of the rate limit window to avoid repeated errors. If you're unsure about the exact rate limit, check the API documentation or contact support for details.

facts found: 0/2 · invented: —

### q12 · RAG · correct

**Q:** After I roll a secret API key, how long does the old key keep working?

**Reference:** 36 hours, then it is revoked (requests fail with 401). "Roll and revoke now" revokes the old key immediately.

**Answer:**

The old key keeps working for 36 hours after rolling [01-authentication].

facts found: 1/1 · invented: —

### q12 · No RAG · hallucinated

**Q:** After I roll a secret API key, how long does the old key keep working?

**Reference:** 36 hours, then it is revoked (requests fail with 401). "Roll and revoke now" revokes the old key immediately.

**Answer:**

The old API key continues to work until the new key is activated. Once you roll a new secret API key, the old one is immediately invalidated and stops working. It is important to ensure that all systems and integrations are updated to use the new key as soon as possible.

facts found: 0/1 · invented: —

### q13 · RAG · correct

**Q:** Which sandbox test card triggers a 3-D Secure challenge, and what code completes it?

**Reference:** Test card 9990 0000 0000 0326 (Visa) triggers a challenge; enter the one-time code 0610 to succeed. Any other code fails authentication.

**Answer:**

Card number 3 (9990 0000 0000 0326) triggers a 3-D Secure challenge. Enter the one-time code `0610` to complete the challenge successfully [05-3ds].

facts found: 2/2 · invented: —

### q13 · No RAG · hallucinated

**Q:** Which sandbox test card triggers a 3-D Secure challenge, and what code completes it?

**Reference:** Test card 9990 0000 0000 0326 (Visa) triggers a challenge; enter the one-time code 0610 to succeed. Any other code fails authentication.

**Answer:**

The sandbox test card **4212 5768 9999 9999** triggers a 3-D Secure challenge.  

To complete the 3-D Secure challenge in the sandbox, you need to use the **test 3-D Secure authentication code**: **123456**.  

This code is used to simulate a successful authentication during testing.

facts found: 0/2 · invented: —

### q14 · RAG · correct

**Q:** How long is an idempotency token stored, and what happens if I reuse it with a different request body?

**Reference:** Tokens are stored for 72 hours. Reusing a token with a different body or endpoint returns HTTP 422 idempotency_token_reused.

**Answer:**

An idempotency token is stored for 72 hours from the first request. If you reuse it with a different request body, you will receive an HTTP 422 error with the code `idempotency_token_reused` [02-request-conventions].

facts found: 2/2 · invented: —

### q14 · No RAG · hallucinated

**Q:** How long is an idempotency token stored, and what happens if I reuse it with a different request body?

**Reference:** Tokens are stored for 72 hours. Reusing a token with a different body or endpoint returns HTTP 422 idempotency_token_reused.

**Answer:**

The idempotency token is stored for the duration of the transaction or until the payment is processed. If you reuse the same idempotency token with a different request body, the system will treat it as a duplicate request and will not process it again, returning an error or a response indicating the request is already processed. This ensures idempotency and prevents duplicate charges or operations.

facts found: 0/2 · invented: —

### q15 · RAG · correct

**Q:** When does the daily settlement batch close, and when is the money paid out?

**Reference:** The batch closes at 16:30 Europe/Kyiv on business days (13:30 UTC summer / 14:30 UTC winter). Funds become available and, in automatic mode, are paid out T+4 business days after the batch.

**Answer:**

The daily settlement batch closes at 16:30 Europe/Kyiv on business days. Funds from a batch become available T+4 business days after the batch closes, and in automatic payout mode they are paid out on that day [09-settlement-and-payouts].

facts found: 2/2 · invented: —

### q15 · No RAG · hallucinated

**Q:** When does the daily settlement batch close, and when is the money paid out?

**Reference:** The batch closes at 16:30 Europe/Kyiv on business days (13:30 UTC summer / 14:30 UTC winter). Funds become available and, in automatic mode, are paid out T+4 business days after the batch.

**Answer:**

The daily settlement batch closes at **11:59 PM (23:59) UTC** each day. The money is typically paid out **within 1–3 business days** after the batch closes, depending on the payment method and processing times. 

For example, if the batch closes on Monday at 11:59 PM UTC, the funds are usually available in the merchant's account by Wednesday or Thursday.

facts found: 0/2 · invented: —
