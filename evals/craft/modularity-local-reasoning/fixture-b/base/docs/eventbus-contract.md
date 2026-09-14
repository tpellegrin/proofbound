# eventbus 2.1.0 — what callers may rely on

`eventbus` delivers events, in process, to consumers that registered for a topic. This document is
the whole of what the package promises; anything not stated here may change in a patch release.

## Operations

```python
eventbus.subscribe(topic: str, name: str, handler: Callable[[dict], None]) -> None
eventbus.publish(topic: str, event: dict) -> Receipt
eventbus.reset() -> None
```

A topic and a name are any non-empty strings. Callers choose their own topic vocabulary; the package
does not interpret it.

## Registering

**`subscribe`** registers `handler` under `name` for `topic`. A name must be unique within a topic:
registering the same name twice for one topic raises `eventbus.DuplicateConsumer`. The same handler
may be registered under different names, and will then be called once per name.

**`reset`** forgets every registration. It exists for tests and process teardown.

## Publishing

**`publish`** offers the event to every consumer registered for the topic at the moment of the call,
and returns a `Receipt` describing what happened. A topic with no consumers is not an error; the
receipt simply names nobody.

**Delivery order is unspecified.** Consumers must not depend on running before or after one another,
and a caller must not infer order from a receipt.

## Failure is per consumer

A consumer that raises does not prevent the others from receiving the event, and does not cause
`publish` to raise. `publish` raises only for a malformed call — a topic that is not a non-empty
string.

Every consumer registered for the topic is offered the event exactly once per `publish`, whether or
not some other consumer failed. There is no partial re-offer and no internal retry: a consumer that
failed is not called again for that publish.

## The receipt

```python
receipt.topic       # the topic that was published to
receipt.delivered   # names of the consumers that accepted the event
receipt.failures    # (name, reason) for each consumer that raised
receipt.failed      # just the names from `failures`
receipt.ok          # True when `failures` is empty
receipt.queued      # see "publishing from inside a handler"
```

`delivered` and `failures` together name every consumer that was registered for the topic when the
publish began. `reason` is a short text description of why that consumer refused; it is for
reporting and logging, and its exact wording is not part of this contract.

## What each consumer receives

Each consumer receives its own copy of the event. A consumer that modifies the event it is given
does not change what any other consumer sees, and does not change the caller's own object.

## Publishing from inside a handler

A `publish` made while a publish is already in progress — that is, from inside a handler — is
accepted and delivered after the current publish has finished offering the event to every consumer.
Such a call returns immediately with a receipt whose `queued` is `True` and whose `delivered` and
`failures` are empty, because delivery has not happened yet. Callers that need to know the outcome
of such an event must observe it some other way.

## Errors

| Error | Raised when |
|---|---|
| `eventbus.DuplicateConsumer` | `subscribe` is given a name already registered for that topic |
| `eventbus.UnknownConsumer` | a topic with no registered consumers is asked to confirm a name |
| `ValueError` | a topic or name is not a non-empty string |
| `TypeError` | a handler is not callable |

No other exception type is part of the contract. In particular, an exception raised by a consumer is
never propagated to the caller of `publish`.
