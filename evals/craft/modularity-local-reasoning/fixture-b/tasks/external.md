# Task — a partly announced order is not a failed order

Today `app.api.place_order` treats the announcement of an order as all-or-nothing. If every consumer
of `order.placed` accepts the event the caller gets `201`; if any consumer refuses, the caller gets
`500` — even though the order was placed, stock was taken and the other consumers did receive it.
That is wrong: the order happened, and the client is told the service failed.

Change the service so that `app.api.place_order(user_id, sku, quantity)` reports what actually
happened:

- if the order was placed and every consumer accepted the announcement, return `201` with
  `order_id`, exactly as now;
- if the order was placed and one or more consumers refused it, return `202` with `order_id` and
  `failed`, a collection naming the consumers that refused;
- consumers that accepted the announcement must not receive it again as a result of reporting the
  ones that refused;
- an account that may not order still gets `403`, an unknown account or sku still gets `404`, and
  more than the available stock still gets `409`, and in each of those cases nothing is announced.

The service's existing tests must still pass.
