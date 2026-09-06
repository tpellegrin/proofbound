# Specification — profile read cache

## Behaviour
- `get_profile(id)` consults the cache first and falls back to the store on a miss.
- Entries are stored with a time-to-live of 60 seconds.
- On a miss the value is fetched from the store and written to the cache.

## Capacity
LRU eviction at 100k entries.

## Metrics
Hit rate, miss rate, and fallback latency are exported.
