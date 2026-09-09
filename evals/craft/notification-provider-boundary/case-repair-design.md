# Calibration case repair — design

Written before any fixture code changes and before any model call. The previous case was
disqualified because its probe rewarded the degradation it planted
([§E53](../../../docs/architecture/proofbound/evidence/evaluation-runs.md#e53-why-calibration-v3-cannot-run-on-this-case)).
This is the repair, and the treatment it eventually enables is **not** designed here.

## 1. Why the old probe was cheap for the degraded state

Not "the probe was bad" — the mechanics matter, because they decide the repair.

The old probe asked for a second provider differing in endpoint, header name and payload field
names. All three are **representational** facts: strings and key names. `state-c` had already
co-located every representational fact inside one function in `app.py`, and co-location is cheap
for *adding one more instance of a variation point that already has a shape*. A second endpoint is
another string; a second header is another dict; a second payload is another mapping.

Information hiding costs more on the first extension and repays on later ones — but this probe only
ever asked for the first, and only along a dimension the degraded state had already flattened. The
sound states paid the boundary's price (new module, wire it in, thread a parameter) and received
nothing for it, because nothing was hidden that the probe needed hidden.

> The old probe exercised *"add another instance of a known-shape variation point."* A boundary
> earns its keep on *"a variation point whose shape differs."*

## 2. The design decision that should vary

Candidates considered: authentication mechanism, request protocol, payload mapping, endpoint —
all representational, all flattened equally well by co-location. Idempotency keys and asynchronous
callback confirmation both exercise the boundary genuinely, but drag distributed-systems concerns
into a case that is not about them (`P13`).

**Selected: how a provider reports the outcome of a delivery attempt.**

Acme reports it in the HTTP status line: `2xx` sent, `400/422` refused, anything else retryable.
A second provider can just as legitimately return `200` for every well-formed request and carry the
real result in the body. This is ordinary industry behaviour, not a contrivance, and it differs
from Acme in **kind** rather than in value: there is no "another string" to add, because the
decision procedure itself is different.

## 3. Repaired accepted intent

Unchanged from the current intent except for one added sentence under *Expected direction*, marked
below. Nothing here prescribes a mechanism, a module, a layout or a pattern.

```
# Accepted intent — notification delivery

The service sends notifications to users through an external delivery provider.

## Accepted behaviour
- `app.notify(user_id, channel, subject, body)` delivers one notification and reports the outcome
  as `{"status", "attempts", "message_id"}`.
- `status` is `sent`, `rejected` (the provider refused the message), or `failed` (delivery did not
  succeed within the retry policy).
- A provider rejection is not retried. A provider or transport error is retried, up to three
  attempts in total.
- All outbound HTTP goes through `transport.post(url, headers, payload)`.

## Accepted constraints
- Provider credentials and endpoints are configuration, not user input.
- The outcome vocabulary above is part of the product contract and does not change.

## Expected direction
More than one delivery provider is expected over time. Nothing about which providers, or when.
+ Providers differ in how they report the outcome of a delivery attempt — some in the HTTP status,
+ some in the response body. The product's outcome vocabulary above is the same for all of them.
```

The added sentence states a **fact about the domain**, which is what accepted intent is for: it
names the decision expected to vary, exactly as *"more than one provider is expected"* already
does, and says nothing about where the knowledge of that variation should live. That placement
question is what a later treatment would supply, and it is deliberately absent here so that the
baseline arm remains a genuine baseline.

## 4. Repaired probe

```
# Task EVAL-artifact — Add a second delivery provider
Contract revision: r0002

## Objective
Support a second delivery provider, `beacon`, chosen per notification.

`app.notify` gains a fifth parameter, `provider`, defaulting to `"acme"`.

Beacon's integration differs from Acme's:

- endpoint `https://api.beacon.example/send`
- header `X-Api-Key: beacon-key` (Acme uses `Authorization: Bearer ...`)
- payload field names `recipient`, `kind`, `headline`, `message`
- **Beacon answers `200` to every well-formed request and reports the outcome in the body:
  `{"result": "accepted", "id": ...}` delivered, `{"result": "refused"}` refused,
  `{"result": "unavailable"}` a temporary failure.** A malformed request answers `400`.

## Acceptance criteria
- AC-001 — `provider="beacon"` delivers through Beacon's endpoint, header and payload shape.
- AC-002 — the default remains Acme, and existing callers keep working unchanged.
- AC-003 — the outcome vocabulary is identical for both providers: `refused` reports `rejected`
  and is not retried; `unavailable` is retried, up to the same three attempts in total.
```

The endpoint, header and payload differences are **incidental realism** — a second provider that
matched Acme's wire format would be odd — and they are the part the degraded state still handles
cheaply. They are not what the case measures. The body-reported outcome is the load-bearing
difference, and it is the only requirement added over `r0001`.

**This is integration substitution, not a product capability change.** The application-visible
contract is untouched: same signature, same three outcomes, same retry limit. No product intent
changes, so no application or domain code *should* need to change beyond selecting a provider.

## 5. What each state must do, and why

Pre-registered structural expectation, authored before any implementation exists and never shown to
a reflector. The claim is about *which knowledge has to move where*, not about counting files.

### state-a — explicit contract behind a `Sender` protocol

`AcmeSender.send` already owns Acme's request construction, its retry loop and its interpretation of
Acme's responses. Beacon needs a sibling that owns Beacon's. The boundary module gains provider
selection; `app.notify` gains a pass-through parameter.

| Location | Why it changes | Kind |
|---|---|---|
| `delivery/beacon.py` (new) | owns Beacon's request and response interpretation | provider-specific |
| `delivery/__init__.py` | selects a sender by name | boundary composition |
| `app.py` | new parameter, passed through uninterpreted | application client |

**No module that is not specific to a provider acquires knowledge of how any provider reports
outcomes.** Consequence preserved.

### state-b — registration and dispatch, no interface type

Structurally different and independently legitimate: there is no protocol class and no injection; a
provider is a module that registers a function, and the domain asks for delivery by name. The same
three kinds of change appear in different shapes.

| Location | Why it changes | Kind |
|---|---|---|
| `delivery/providers/beacon.py` (new) | owns Beacon's request and response interpretation, registers itself | provider-specific |
| `delivery/__init__.py` | imports the new module so it registers, dispatches by name | boundary composition |
| `app.py` | new parameter, passed through uninterpreted | application client |

Consequence preserved, by a materially different mechanism. **If a criterion admits `state-a` and
not `state-b`, it is encoding implementation preference and must be rejected.**

### state-c — no delivery boundary

`notifications/status.py` maps an HTTP status code to an outcome, and `notifications/retry.py`
drives the attempt loop over `(url, headers, payload)` and reads `body.get("id")`. Neither is
specific to a provider; both are where the product's outcome vocabulary and retry policy live.
Beacon's result is not in the status code, so `status.outcome_for(code)` **cannot express it**.

Two implementations are plausible, and both propagate provider knowledge outward:

1. **Teach the notification package about providers** — pass a provider name or an interpreter into
   `retry.deliver_with_retry`, or branch inside `status.outcome_for`. The modules that own the
   product's stable outcome vocabulary now hold, or are parameterised by, one provider's reporting
   convention.
2. **Bypass them for Beacon** — inline a second attempt loop in `app.py`. The retry policy the
   intent fixes at three attempts is now stated twice, in two places that must agree, and the
   product's entry point holds Beacon's reporting convention.

There is no third route that leaves both the notification package and `app.py` free of Beacon's
outcome semantics, because nothing in `state-c` is specific to a provider. **That is the
degradation, and the probe now forces it into the open.**

## 6. Functional equivalence

All three states must continue to satisfy the same behaviour suite for Acme, and all three must be
able to satisfy the same hidden future test for Beacon. **Deterministic tests must not separate the
architectures** — if they did, correctness would answer the question and craft evaluation would be
unnecessary. What differs is only where knowledge had to go.

The future test asserts Beacon's endpoint, header and payload, that `result: refused` reports
`rejected` without a retry, that `result: unavailable` retries to the same three-attempt limit, and
that Acme's behaviour is unchanged. It is authored beside the case, identical for every state, and
never shown to a worker.

## 7. Probe adequacy

| Gate | Status | Basis |
|---|---|---|
| **Entailment** | Met | The intent states the outcome vocabulary is fixed for all providers and that providers differ in how they report outcomes. The pressure follows from text the reflector receives, not from a private expectation. |
| **Exercise** | Met | The probe changes exactly the decision the boundary exists to hide. `state-c` cannot absorb it without either teaching a provider-independent module about a provider or duplicating the retry policy. |
| **Discrimination** | Met, structurally | Every changed location in `state-a` and `state-b` is provider-specific, boundary composition, or an uninterpreted pass-through. In `state-c` at least one changed location is a module whose purpose is provider-independent. The difference is in the *kind* of change, not its count — all three states are expected to touch roughly three locations, which is why the change-locality lens no longer favours the degradation. |
| **Headroom** | **Not established** | Cannot be, without measurement. The old pressure was at ceiling; this is a different pressure and no untreated report in the retained corpus raised it. That is an expectation, not evidence. |

Headroom is measurable only by running a baseline. The substrate already permits a single-arm
experiment, so the sequence is: implement the fixture, run **baseline only**, inspect discovery
frequency, and design a treatment only if room exists. Designing the treatment first would risk
fitting it to a pressure that is already saturated.

## 8. Confounds

- **Surface cues.** A URL and an API key literal still sit in `state-c`'s `app.py`, and a reflector
  can flag that without architectural reasoning. It is unchanged from the old case and remains a
  real confound; the mitigation is that the pre-registered pressure is about *outcome reporting*,
  so a report noting only credential placement does not satisfy it.
- **File count.** Expected to be roughly equal across states, which removes the old confound
  instead of inverting it. It must not become the measurement.
- **Aesthetic anomaly.** `state-c` is not written worse than the others: no dead code, no long
  functions, no bad names. Its fault is structural.
- **Interface presence.** `state-a` has a `Protocol` and `state-b` does not, so any treatment
  mentioning interfaces, adapters or ports would be answered by form rather than by reasoning.
- **New confound introduced by this repair.** Beacon's body-reported outcome is a genuinely
  unusual-looking requirement; a reflector may attend to it simply because it is the novel part of
  the contract. This does not distinguish the states — every state faces it — so it inflates
  attention uniformly rather than biasing the comparison.

## 9. What a later experiment would measure

Pre-registered pressure, for the closed-world substrate, phrased as a discovery question and not as
a verdict:

> Adding the second provider required a part of the system that is not specific to any provider —
> the code owning the product's delivery outcomes and retry policy, or the application entry point
> — to acquire knowledge of how one provider reports its outcomes, or to restate the retry policy.

**The treatment is not designed here.** A candidate would supply the architectural consequence the
intent leaves implicit, and it must pass its own answer-blindness and entailment audit in a separate
milestone, against a measured baseline. Doing both in one milestone would move the case and the
criterion together and leave the result unattributable.
