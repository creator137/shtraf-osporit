# Stage 5 - Payment Intent Validation

This file defines the currently paid/development scope.

## Included In Stage 5

- Three fixed paid-service offers with price ranges.
- Telegram calls to action shown after the existing legal analysis.
- A `PaymentIntent` event recorded for every payment-button click.
- Total-click, unique-user, unique-case, and per-offer statistics.
- A read-only admin page with summary metrics and the latest 100 events.
- A clear message that payment is still under development.

The intended flow is:

```text
Offers
    ->
payment CTA
    ->
payment intent tracking
    ->
admin statistics
    ->
payment unavailable message
```

## Result Of This Stage

The project can measure interest in each proposed paid service without accepting
money or pretending that a payment has occurred. Repeated clicks are stored as
separate events, while unique users and unique cases are counted separately.

## Excluded From Stage 5

- Payment providers, invoices, checkout pages, bank links, or QR codes.
- Amount calculation inside a price range.
- Transactions, payment statuses, subscriptions, refunds, or receipts.
- Paid access control or document blocking.
- Lawyer handoff or CRM workflows.
- External analytics services or a complex conversion funnel.

> Stage 5 validates demand only. No payment is accepted or processed.
