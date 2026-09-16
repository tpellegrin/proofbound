# Clarification — an unintended real-executor invocation during lifecycle repair

**2026-09-16.** A dated correction to the record, written because the milestone reports that
preceded it described this event only in passing and in terms that were too favourable. It changes
no experimental result: this happened while building deterministic tests for the attempt-deadline
repair, after b1 had finished, and touches neither b1 nor q1.

## What happened

While writing `tests/test_worker_deadline_lifecycle.py` I constructed an environment that put a
fake `opencode` first on `PATH` and then failed to pass that environment to `subprocess.run`. The
test therefore ran with the inherited environment. Stated plainly:

- **a real executor was invoked** — the host's Homebrew `opencode`, version `1.18.30`, not the
  frozen `1.18.29` build;
- **it ran with real credentials**, because the inherited `HOME` exposes the provider auth file;
- **a provider request occurred** and reached a server, which answered with
  `{"name": "UnknownError", "data": {"message": "Unexpected server error", "ref": "err_45813b15"}}`;
- **locally observed completion, tokens and cost were zero.** The session database it left behind
  held one `user` message, no `assistant` message, `cost = 0.0`, and `tokens_input`,
  `tokens_output`, `tokens_reasoning` and `tokens_cache_read` all `0`.

The same mistake ran more than once before it was noticed — several cases in one failing test
module, each a fast server error rather than a completion.

## What is not established

**Actual billing is unverified.** Zero locally recorded usage is the executor's own account of a
request that failed server-side; it is not an authoritative statement about what the provider
charged. No provider-side invoice, usage export or dashboard reading was obtained, so the honest
position is that the charge is **unknown and probably zero**, not zero.

Earlier phrasing in the milestone reports — "no billable completion appears locally" — was accurate
as far as it went but was offered in a context that invited the reading "no charge". That reading is
withdrawn. The claim "no provider call occurred" would be simply false and is not made anywhere.

**Retrospective verification is now limited.** I deleted the stray temporary directories, including
the session database quoted above, as part of clearing host residue before continuing. The figures
in this document were read from it *before* deletion and are recorded here because the artifact no
longer exists. Nothing has been reconstructed: what is written here is what was observed at the
time, and what was not observed then cannot be recovered now.

## What was changed so it cannot recur by the same route

The demonstrated escape was a two-condition failure — a real executor became selectable *and* a
real credential was reachable — so both conditions are now closed in the lifecycle tests, in
`WorkerDeadlineTest.sealed_env`:

- `PATH` is **replaced**, not prepended to, and the resolved `opencode` is asserted to be this
  test's fake **by content**, not merely by path;
- `HOME` is redirected to a throwaway directory, and the absence of a provider auth file under it is
  asserted. `run_worker` resolves the executor by name, so `PATH` is the only route by which one is
  selected — but the harm comes from the credential, and separating the two means a future slip in
  either one is not sufficient on its own;
- `OPENCODE_*` variables are dropped rather than inherited, so a value naming a real session store
  or credential path cannot survive the reset unnoticed;
- the environment is passed explicitly at every call site, which is the specific thing that was
  forgotten.

`ControllerEnforcementTest` is unaffected by that route: it passes an explicit fake executable to
`run_bounded_attempt` and stages no credential, and the view's own `PATH` contains only the staged
tools directory and system directories.

This is deliberately narrow. It addresses the escape that actually occurred and does not attempt a
general redesign of how credentials are held.
