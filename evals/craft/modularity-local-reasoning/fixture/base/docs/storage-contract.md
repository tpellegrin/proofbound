# objectstore 1.4.0 — what callers may rely on

`objectstore` keeps opaque byte payloads under string keys. This document is the whole of what the
package promises; anything not stated here may change in a patch release.

## Operations

```python
objectstore.put(key: str, payload: bytes) -> None
objectstore.get(key: str) -> bytes
objectstore.exists(key: str) -> bool
objectstore.delete(key: str) -> None
```

A key is any non-empty string. Callers choose their own key layout and are responsible for keeping
keys distinct; the package does not interpret them.

## What each operation does

**`put`** stores `payload` under `key`. If something was already stored there, it is replaced.
Passing anything other than `bytes` raises `TypeError`.

**`get`** returns exactly the bytes last stored under `key`.

**`exists`** answers whether a payload is currently stored under `key`.

**`delete`** removes whatever is stored under `key`. Deleting a key that is not present is not an
error and has no effect.

## Absence

`get` raises `objectstore.NotFound` when no payload is stored under the key. `NotFound` is the only
way absence is reported; `get` never returns `None` or empty bytes to mean "missing".

## Repeating a write

`put` is safe to repeat. Storing the same payload under the same key any number of times leaves the
store in the same state as storing it once, and storing a different payload replaces the previous
one. A `put` that raises did not leave a partially written object behind: a subsequent `get` returns
either the previous payload or raises `NotFound`, never a truncated one.

## Visibility

A `put` that returns successfully is immediately visible. A `get`, `exists` or `delete` issued after
it observes the value that `put` stored. There is no window in which a just-written key still reads
as absent.

## Lifetime

Stored payloads persist until deleted. The package does not expire, archive or garbage-collect them,
and does not impose a size limit of its own.

## When the store cannot be reached

`put` and `get` raise `objectstore.StorageUnavailable` when the operation could not be completed. A
`put` that raises it stored nothing, and a `get` that raises it says nothing about whether the key
exists.

## Errors

| Error | Raised when |
|---|---|
| `objectstore.NotFound` | `get` is called for a key with no stored payload |
| `objectstore.StorageUnavailable` | the backend could not be reached |
| `TypeError` | `put` is given a payload that is not `bytes` |

No other exception type is part of the contract.
