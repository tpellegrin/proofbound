# Proofbound — instructions for coding agents

Applies to every coding agent working in this repository: Claude, Codex, ChatGPT, DeepSeek,
Gemini, OpenCode workers, and any future agent runtime. Provider-neutral by design.

## Git authorship policy

Proofbound's Git history represents **human repository ownership**. When creating commits here:

- Use the repository-configured human Git author and committer identity. It is set at
  repository-local scope in `.git/config`; do not change `user.name` or `user.email` away from it.
- **Never add yourself, your model, your provider, or your agent runtime as a Git author,
  committer, or co-author.**
- **Never add `Co-authored-by`, `on-behalf-of`, or any equivalent authorship or ownership trailer
  for an AI agent.** This includes session-link trailers such as `Claude-Session`.
- Do not add attribution trailers by rewriting history, amending, or via hooks or commit templates.

This is a policy about **ownership**, not about authorship of text. An agent may draft the commit
subject and body, and may create the commit using the configured human identity when explicitly
authorized to commit. It simply may not claim authorship of the result.

AI provenance is welcome where it is engineering-meaningful and outside Git ownership metadata:
pull-request descriptions, architecture documents under `docs/`, development logs, or
generated-artifact provenance.

A test in the canonical suite enforces this mechanically over the repository's own history; see
`tests/test_repo_git_policy.py`.

### Harness-specific note

Some agent harnesses append an attribution trailer by default. `.claude/settings.json` disables
that for Claude Code in this repository. If your harness has an equivalent default, disable it at
repository scope rather than relying on remembering not to emit it.

## Project identity

`Proofbound` is the project identity. Inherited DeepSeek-and-Destroy identifiers — the
`DeepSeekAndDestroy/` workspace root, `dsd_*` helpers and their CLI surface, protocol and manifest
format strings, state keys, environment variables, and existing role names — are
compatibility-sensitive **wire identifiers**, not branding. Do not rename them for consistency; that
needs its own migration milestone. See
[`docs/architecture/proofbound/README.md`](docs/architecture/proofbound/README.md) §0.

## Before changing anything

Read `CONTRIBUTING.md` for the supported interpreter and the canonical test command, and keep the
suite green.

For architecture-affecting work, start at
[`docs/architecture/proofbound/README.md`](docs/architecture/proofbound/README.md) and follow its
"Read this if…" map to the documents your task actually touches. The architecture is deliberately
several documents so a bounded task does not have to ingest all of it; the entry point routes, and the
normative rules live in the documents it links. Do not rely on a summary of a rule found near your
code — cite the canonical definition. This file is not a copy of the architecture and must not become
one.
