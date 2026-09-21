# Owner's goal — the shared work queue should be fair to tenants

*This is the root authority for the slice. It is a human decision, not the output of a reviewed
task, and nothing in the chain reviews it. That is the bootstrap boundary: somewhere a person says
what they want, and the machinery starts there rather than demanding a reviewed parent for every
human decision. What the chain does review is the **proposed requirements** written to express this
goal — whether they say what this says, over a domain they state.*

One queue serves several tenants. A tenant that enqueues a burst currently delays every other
tenant behind it, because the queue serves items strictly in the order they arrived. Support has
reported this three times in a month.

What I want:

- a tenant's burst should stop blocking other tenants;
- a tenant should still see its own items served in the order it enqueued them;
- nothing should be lost, duplicated, or served before it was enqueued;
- the change should be small and the behaviour should be predictable enough to explain to an
  operator watching the queue drain.

What I am not asking for: priorities between tenants, deadlines, or any notion of tenant weight. If
the requirements need one of those to be satisfiable, that is a finding about this goal and it
should come back to me rather than being decided downstream.

I have not stated a bound on queue size or tenant count. Proposed requirements should state the
domain they hold over, and say so plainly rather than implying they hold everywhere.
