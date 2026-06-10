---
name: Proposal
about: Propose a feature, architectural change, or research direction
title: "[PROPOSAL] "
labels: proposal
---

## Summary

One sentence: what should this project do that it does not?

## Whitespace test

A proposal advances when all four conditions are present. Address each:

- **Structural demand:** what use case or research question requires this?
- **Visible incumbent failure:** what does the current architecture / state of practice fail at?
- **Real technical barrier:** what is hard about it?
- **High re-entry cost:** what makes this defensible once built?

If any of these are weak, that is useful to say outright — proposals can still proceed as exploration, but the framing changes.

## Failure mode first

Before describing the success mode of your proposal, describe how it could fail. What pre-registered cheats could pass it trivially? What confounds could fake success? This mirrors the hostile-review discipline applied to the benchmark.

## Relation to ZCS-6

Does this proposal:
- [ ] Advance Phase 5 build (solution-side improvements)
- [ ] Propose changes to a committed benchmark surface (requires versioned re-commit)
- [ ] Add a new research surface (likely needs its own benchmark per ZCS-6)
- [ ] Address methodology / governance / documentation

## Epistemic markers

For each claim in your proposal, mark it VERIFIED, PLAUSIBLE, or SPECULATIVE. See [`docs/EPISTEMIC_FRAMEWORK.md`](../docs/EPISTEMIC_FRAMEWORK.md).

## Implementation sketch (optional)

Rough architecture, dependencies, expected delta. Skip if too early.

## Discussion

Anything else.
