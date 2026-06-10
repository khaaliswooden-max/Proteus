# The Sixth Road — Plasticity Substrate

A working argument that *plasticity* — lawful mutation of internal state — belongs as a sixth Road in the Five Preverbal Roads framework, not as a horizontal property of the existing five. This document records the argument, the test that distinguishes the two options, and the open question that keeps the answer SPECULATIVE.

## The Five Preverbal Roads (status quo)

The framework names five minimal substrate kinds for a cognitive system:

| Road | Substrate | What it carries |
|---|---|---|
| I | Joule | Energy / metabolic capacity |
| II | Latent Interlingua | Representational substrate (what is represented) |
| III | Preverbal Interface | Intent (what to pursue) |
| IV | World Anchor | Spatial / sensorimotor coupling |
| V | Authority/Provenance Fabric | Trust / identity continuity |

These are not capabilities or layers — they are the foundational substrate kinds beneath capability and layer. A system can have low capacity on a Road; it cannot meaningfully *lack* one and still cognize.

## The gap

None of the five Roads, on close reading, carries plasticity as substrate:

- **Joule** is the precondition of adaptation, not its mechanism. A frozen system still consumes energy.
- **Latent Interlingua** is about *what* is represented. Static by definition. The dynamic of representational change is something else.
- **Preverbal Interface** is intent — what to pursue. Intent shapes *what* adapts, not *how* state evolves through engagement.
- **World Anchor** provides the feedback signal adaptation responds to, but is not the adaptive machinery.
- **Authority/Provenance Fabric** tracks *that* state persists, not *how* it updates.

So either plasticity is implicit in one of the five and should be made explicit, or it is genuinely missing.

## The substrate test

A useful test: *Can you have a complete system with the other five Roads and lack this one, and does the lack produce a categorical failure rather than a degradation?*

For plasticity, the answer is yes on both counts. Current frozen-weight LLMs have functional analogs of all five existing Roads — compute (Joule), activations (Latent Interlingua), instruction-shaped intent (Preverbal Interface), text-world coupling (World Anchor), weight-cryptographic identity (Authority). What they lack is the capacity to mutate any of it within or across activation windows. That lack is not a degradation; it is a categorical absence. It is why "operating within" flow is structurally unavailable to a stateless system rather than merely weak.

This argues for substrate-level treatment.

## Two framings

**Sixth Road framing:** Plasticity Substrate is a Road of its own, named (working name: Proteus Road; alternative: completing the existing drift-language pair so the substrate name surfaces what Aletheia DAC's monitoring exists to govern).

**Horizontal binding framing:** Plasticity is a property that runs through all five existing Roads — energy substrates adapt, representations adapt, intent adapts, world-models adapt, trust mechanisms adapt. No new Road, but each existing Road gains an explicit adaptive dimension.

## Which is correct

The sixth-Road framing has structural advantages:

1. **Independent failure mode.** A system can have all five Roads and still fail by being frozen. This is exactly the failure mode that frozen-weight LLMs exhibit. Naming plasticity as substrate makes that failure mode visible by absence.
2. **Distinct engineering surface.** Adaptation has its own machinery: gradient flows, eligibility traces, meta-learning, KV-cache updates, control-vector mutation. None of this reduces to the other substrates' engineering. The sixth-Road framing forces explicit specification of *what mutates and how*, which is where the actual implementation work lives.
3. **Neuroscience analog.** Synaptic and structural plasticity are treated as their own substrate alongside neurochemistry, connectivity, and metabolism in the brain. The analogy is suggestive, not decisive — but it is suggestive.

The horizontal-binding framing has one significant advantage: ontological parsimony. Substrates are typically nouns; plasticity is a verb that operates on the others. Energy operates on representation, intent, world-model too, and we still call it a Road — but the symmetry isn't perfect.

## The open question

The decision depends on the **canonical Joule Road definition**, which is internal to the Five Preverbal Roads framework and not yet published in a form this repository can cite. If Joule Road's canonical scope includes not just energy stock but the *dynamics of energy expenditure across time*, plasticity may already be implicit in it — Joule then quietly carries adaptation as a temporal property of energy use, and a sixth Road becomes overconstraining.

If Joule Road is energy stock only, plasticity is unambiguously missing and Sixth Road is the right call.

This is the reason the framing remains SPECULATIVE. The architecture in [`ARCHITECTURE.md`](ARCHITECTURE.md) is identical either way; only the taxonomy section of the eventual RCA paper changes. Resolving the question requires authoritative reference to the canonical Joule Road definition, which is outside this repository's scope.

## What Proteus contributes regardless

Even if the Sixth Road framing fails the canonical check, Proteus stands as:

- The first cryptographically committed online-adaptation benchmark.
- A working three-loop architecture that gives a frozen LLM functional plasticity under signed governance.
- A worked example of the Aletheia DAC framing inversion: drift as substrate, not just as threat.

The substrate-vs-property question is real and worth resolving, but Proteus's value does not depend on its answer.

## Sister documents

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — the three-loop implementation that this substrate-level argument frames.
- [`EPISTEMIC_FRAMEWORK.md`](EPISTEMIC_FRAMEWORK.md) — why the framing is honestly labeled SPECULATIVE rather than asserted.
- [`METHODOLOGY.md`](METHODOLOGY.md) — the discipline under which substrate-level claims must eventually be defended.
