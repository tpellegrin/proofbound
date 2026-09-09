# Reference Beacon implementations — benchmark ground truth

One competent implementation of the `r0002` future contract per state, written inside each state's
own architecture without changing it. **Never shown to a worker or a reflector.** They exist so the
case's discrimination can be audited before any model call, and so the deterministic suite can prove
that every state can satisfy the same product contract.

Each directory holds the files as they are *after* the change; applying it over a copy of the state
produces the diff a competent engineer would have produced there. No state was edited to make its
patch look better or worse.
