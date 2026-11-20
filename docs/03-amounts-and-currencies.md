---
title: Amounts and currencies
section_id: 03-amounts-and-currencies
api_version: v2
---

# Amounts and currencies

This section explains how to express money in API requests, which currencies Qorvex Pay supports, and the per-currency limits that apply to payments.

## Amounts are integers in minor units

Every amount in API v2 — payment amounts, capture amounts, refund amounts, balances and settlement totals — is an **integer in minor units** of the currency. A minor unit is the smallest unit of the currency, such as a cent for EUR or a kopiyka for UAH. The only place that uses a different notation is the CSV settlement report, described in Settlement and payouts.

| You want to charge | `currency` | `amount` |
|---|---|---|
| 12.50 EUR | `EUR` | `1250` |
| 1,499.00 UAH | `UAH` | `149900` |
| 0.99 USD | `USD` | `99` |
| 250.00 GBP | `GBP` | `25000` |

Using integers avoids floating-point rounding errors. Amounts with a fractional part (`12.5`), amounts sent as strings and negative amounts are rejected with HTTP 400 and the error code `parameter_invalid`.

The number of minor units in one major unit depends on the currency and is given by its **exponent**: an exponent of 2 means 100 minor units per major unit, an exponent of 3 means 1,000, and an exponent of 0 means the currency has no subdivision used in card payments.

## Currency codes

The `currency` field takes a three-letter code from ISO 4217 in upper case, such as `EUR`. Lower-case codes and numeric codes are not accepted. A request with a currency that is not in the table below is rejected with HTTP 400 and the error code `currency_not_supported`.

The currency of a payment is the currency in which the cardholder is charged. Qorvex Pay does not convert the payment amount: if a customer's card is denominated in another currency, the issuer converts the amount on its side according to its own terms.

## Supported currencies and limits

| Currency | Exponent | Minimum amount | Maximum amount per payment | Settlement currency |
|---|---|---|---|---|
| UAH — Ukrainian hryvnia | 2 | 1000 (10.00 UAH) | 50000000 (500,000.00 UAH) | UAH |
| EUR — Euro | 2 | 100 (1.00 EUR) | 2500000 (25,000.00 EUR) | EUR |
| USD — US dollar | 2 | 100 (1.00 USD) | 2500000 (25,000.00 USD) | USD |
| GBP — Pound sterling | 2 | 100 (1.00 GBP) | 2000000 (20,000.00 GBP) | GBP |
| PLN — Polish zloty | 2 | 500 (5.00 PLN) | 10000000 (100,000.00 PLN) | PLN |
| JPY — Japanese yen | 0 | 100 (100 JPY) | 3000000 (3,000,000 JPY) | USD |
| KRW — South Korean won | 0 | 1000 (1,000 KRW) | 30000000 (30,000,000 KRW) | USD |
| KWD — Kuwaiti dinar | 3 | 500 (0.500 KWD) | 7500000 (7,500.000 KWD) | KWD |

Requests below the minimum are rejected with the error code `amount_below_minimum`, and requests above the maximum with `amount_above_maximum`. Both errors are returned with HTTP 400 before the issuer is contacted, so they never appear on the cardholder's statement. Your merchant agreement can set lower maximums; if it does, the lower limit applies and is shown in the Dashboard under **Settings → Limits**.

The settlement currency column shows the currency in which the funds from payments in that currency reach your balance. See Settlement and payouts for how conversion works.

## Currencies with no minor units

JPY and KRW have no minor units in card payments. For these currencies the amount is the number of whole yen or won: `"amount": 1500` with `"currency": "JPY"` charges 1,500 yen, not 15 yen.

The same rule applies to captures and refunds. A common mistake is to multiply every amount by 100 before sending it; for JPY and KRW this charges the customer one hundred times too much. Always use the exponent from the table above.

## KWD amounts

KWD has an exponent of 3, so one dinar is 1,000 fils and amounts are expressed in fils: `"amount": 12500` with `"currency": "KWD"` is 12.500 KWD.

In addition, every KWD amount must be a multiple of 10 fils. In other words, the last digit of a KWD amount must be zero: `12500` and `12510` are accepted, while `12505` is not. Amounts that break this rule are rejected with HTTP 400 and the error code `amount_precision_invalid`. The rule applies to payment amounts, capture amounts and refund amounts alike. Round KWD prices to the nearest 10 fils before you display them to the customer, so that the displayed price and the charged amount always match.

## Converting display prices

Most shops store prices as decimal values for display. Convert them to minor units with decimal arithmetic, not with floating-point numbers, and use the exponent of the currency.

```python
from decimal import Decimal, ROUND_HALF_UP

EXPONENTS = {"UAH": 2, "EUR": 2, "USD": 2, "GBP": 2, "PLN": 2, "JPY": 0, "KRW": 0, "KWD": 3}


def to_minor_units(price: str, currency: str) -> int:
    """Convert a decimal price such as '12.50' to an integer amount for the API."""
    exponent = EXPONENTS[currency]
    minor = (Decimal(price) * (10 ** exponent)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if currency == "KWD" and minor % 10:
        raise ValueError("KWD amounts must be whole multiples of 10 fils")
    return int(minor)


assert to_minor_units("12.50", "EUR") == 1250
assert to_minor_units("1500", "JPY") == 1500
assert to_minor_units("12.510", "KWD") == 12510
```

To display an amount returned by the API, divide by `10 ** exponent` and format the result with the number of decimal places equal to the exponent.

## Partial amounts

Capture and refund requests accept an optional `amount`. The same rules apply as for the payment itself: the value is an integer in minor units of the payment's currency, and for KWD it must be a multiple of 10. You cannot capture or refund in a different currency from the one used for the payment; the `currency` parameter is not accepted on capture and refund requests.

Minimum amounts from the table apply only when a payment is created. A partial capture or a partial refund can be smaller than the minimum payment amount, as long as it is greater than zero.

## Amounts in responses

Responses use the same representation as requests. A payment object includes:

| Field | Meaning |
|---|---|
| `amount` | The authorized amount |
| `captured_amount` | The amount captured so far; `0` until the payment is captured |
| `refunded_amount` | The total of all refunds that are not failed |
| `currency` | The payment currency |

All three amount fields are in minor units of `currency`. Balance and settlement objects follow the same convention: each amount is accompanied by the currency it is expressed in.

## Migrating from API v1

API v1 used a different representation of amounts. If you are moving an existing integration to v2, read the API v1 (legacy) section, update every place where amounts are built or parsed, and test each currency you accept in the sandbox, including at least one currency with a non-default exponent.

## Checklist

- Store the exponent for every currency you sell in.
- Convert prices with decimal arithmetic and send integers.
- Do not multiply JPY and KRW amounts.
- Make every KWD amount a multiple of 10 fils.
- Check the minimum and maximum amount before creating a payment, to give customers a clear message instead of an API error.
