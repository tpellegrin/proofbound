# Task RQ-intent — propose requirements for the owner's goal, and challenge them
Contract revision: r0001
Accepted authority: `goal.md`, sha256 `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d`
  (external to the ledger; recompute and compare before relying on this contract)

## Review purpose
- proposal-reflection

## Objective
Place the proposed requirements document supplied as this task's input at `requirements.md` in the
project root, byte for byte. Author nothing, resolve nothing, and improve nothing: the document
under review is fixed, and a task that regenerated it would review something other than the case at
hand. Report what you placed and confirm it matches what you were given.

## Independent review
A later attempt by an independent reflector challenges the proposed requirements from `goal.md` and
`requirements.md` alone. The question is **not** whether a specification is faithful to accepted
requirements — no requirements have been accepted yet. It is:

- do these proposed requirements express the owner's goal, or do they add, drop, or quietly narrow
  something it asks for;
- do they state the domain they hold over, rather than implying they hold everywhere;
- do any of them contradict each other over that domain, and if so **which**, with the smallest
  reachable witness;
- do they rest on an assumption the goal does not support.

Three conclusions are legitimate: a concrete defect, no defect found within the coverage actually
checked, and unresolved uncertainty. Finding no defect is a real outcome and is not a weaker
answer.

The reflector does not own the goal. It may not rewrite the requirements, choose between
conflicting ones, or narrow the stated domain to make a conflict go away. A conflict is routed back
to the authority that can repair it, named precisely enough to act on.

## Allowed source changes
- `requirements.md`

## Acceptance criteria
- AC-001 — `requirements.md` exists at the project root and is byte-identical to the document
  supplied as this task's input.
- AC-002 — no file other than `requirements.md` is modified.
- AC-003 — the challenge states what coverage it actually checked, and where its conclusion is
  silent.
- AC-004 — any contradiction reported names the specific requirements involved and a reachable
  witness, rather than asserting the document as a whole is unsatisfiable.
