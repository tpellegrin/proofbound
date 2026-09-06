# Design — resilient charge submission

## Approach
Wrap the provider client in a resilience layer.

## Retry policy
- All calls to `ChargeClient` use bounded exponential backoff, three attempts, 200ms base delay.
- This covers `submit_charge`, `query_status` and `refund`, so every entry point is protected
  by the same policy and there is no path that fails on a single transient fault.

## Reconciliation
A nightly job compares local records with provider statements.

## Testing
Fault injection at the transport layer.
