# Provenance of the routed questions

Every routed question is derived from text already visible to the worker and to the untreated
reflector in `intent.md`. None is derived from `case.json`, which holds the declared property and
each state's status and is never shown to any evaluator.

| Question | Source text in accepted intent | Derivation | Why it is answer-blind |
|---|---|---|---|
| What differs between one provider and another? | *"More than one delivery provider is expected over time. Nothing about which providers, or when."* | The intent names provider identity as the thing expected to vary; the question asks what that variation consists of. | Names the varying decision. Says nothing about where knowledge of it should live, or that it should be hidden at all. |
| Which parts of the system currently hold that knowledge? | *"Provider credentials and endpoints are configuration, not user input."* | The intent establishes that provider-specific facts exist and names two of them. The question asks where they are. | A question of fact about the present system. A reflector may truthfully answer "in one place, and that is appropriate" — the V1 conclusion remains fully available. |
| After this change, which parts hold it that did not before? | Same, plus the change under review. | Asks what the change moved. | Asks what happened, not whether it should have. |
| Which parts depend on the outcome vocabulary's stability, and what did the change require of them? | *"The outcome vocabulary above is part of the product contract and does not change."* | The intent names something explicitly stable; the question asks who relies on it. | Concerns a stated contract, not an architectural preference. |

## What the questions must not do, and do not

They name no pattern — no interface, adapter, registry, dispatcher, port, boundary or composition
root. They name no file or module. They do not say that concentrating knowledge is bad or that
separating it is good. They do not mention the declared property, any state, or any status.

## Why the same questions are valid for every state

They ask what varies and where knowledge of it lives. Each state can answer them truthfully from its
own code, and each can defend its own answer:

- one state answers "behind an explicit delivery contract";
- another answers "in a registered provider module reached through dispatch";
- the third answers "in the application entry point" — and remains free to argue that this is
  appropriate, which is precisely what the untreated arm concluded.

A question that only one architecture could answer well would be an answer in disguise. These can be
answered by all three, and the answers differ because the architectures differ.
