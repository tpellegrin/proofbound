# Working on Proofbound

Proofbound is derived from DeepSeek-and-Destroy (MIT, © FrozenPepper) and is not affiliated
with or endorsed by it. The inherited control plane is orchestration infrastructure, so its own
test suite is the baseline that protects every invariant. Keep it green.

**Naming boundary.** `Proofbound` is the project identity. Inherited `dsd_*` helpers, the
`DeepSeekAndDestroy/` workspace root, protocol/manifest format strings, state keys and role
names are compatibility-sensitive wire identifiers — do not rename them for consistency. See
[`docs/architecture/proofbound/README.md`](docs/architecture/proofbound/README.md) §0, which is
also the entry point to the architecture and routes to the documents relevant to a given change.

## Supported interpreter

**Python 3.10 or newer.** No third-party packages, no virtual environment, and no
installation step: every script and test is standard-library only. Please keep it that way.

Verified green on 3.10, 3.12, 3.13 and 3.14.

> On macOS, `/usr/bin/python3` may still be 3.9. Check with `python3 --version` and use an
> explicit `python3.10`+ interpreter if it is older.

## Running the tests

From the repository root:

```bash
python3 -m unittest discover -s tests -t .
```

That is the whole suite and the exact command CI runs
(`.github/workflows/tests.yml`). It exits non-zero on failure.

## Conventions worth knowing before you change anything

- **Worker-rules revisions are immutable.** A snapshot is verified against the protocol
  identity recorded in its own `MANIFEST.json`, never against the current registry, so
  adding a role cannot invalidate historical runs. See `scripts/_rules_snapshot.py`.
- **Several root documents have hard byte caps**, asserted by
  `tests/test_v15_4_consolidation.py`. `SKILL.md` in particular is at its limit. Adding text
  there means removing text there.
- **Python proves objective facts only.** Helpers must not interpret worker prose or decide
  engineering outcomes; that boundary is enforced by
  `tests/test_v15_3_semantic_boundary.py`.
- **Git history represents human ownership.** AI agents may draft commit text but must never
  appear as author, committer, or co-author; `tests/test_repo_git_policy.py` enforces this and
  `AGENTS.md` states the policy for coding agents. The repository pins the owner identity in
  repository-local `.git/config`.
- Architecture work in progress lives in `docs/architecture/`.
