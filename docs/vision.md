# Vision

## The industry problem

Pricing a derivative is rarely the hard part; *understanding* the price is. In
practice, a valuation arrives as a number supported by scattered notebooks,
undocumented engine settings, and assumptions that live only in the heads of a
few specialists. Reproducing a result, comparing it across models, or
challenging it during model-risk review can be slow, error-prone, and
incomplete. The context required to trust a number is frequently disconnected
from the number itself.

## Why a price alone is insufficient

A number without a self-contained record of how it was produced cannot be
independently reproduced, compared, or audited. The questions that matter are:

- Which exact contract definition produced this value?
- Which market-data snapshot was used, and what is its identity?
- Which model and parameters were assumed?
- Which numerical engine and configuration computed the result?
- What uncertainty and tolerances apply?
- Which validation and arbitrage checks passed or failed?
- Which software version and source commit were involved?

DerivaTrace is designed so that the evidence required to answer these questions
travels with the result.

## Contract, model, and engine separation

DerivaTrace treats a financial contract as a declaration of *what is paid*,
independent of *how it is valued*. A contract definition must not bake in a
specific model or numerical method. Models declare stochastic assumptions;
numerical engines declare how calculations are performed. This separation lets
the same canonical contract be valued by multiple models and engines, and lets
disagreement between them become visible information rather than a hidden
choice.

## Evidence-carrying result philosophy

DerivaTrace adopts an evidence-carrying philosophy: a valuation result should be
accompanied by an **evidence certificate** describing the contract identity, the
market snapshot identity, the model and parameters, the engine configuration,
the value and sensitivities, numerical uncertainty, validation outcomes,
software and source versions, and deterministic integrity hashes.

It is important to be precise about what a certificate is. A certificate is
*evidence* and a record of *validation outcomes* and *assertions*. Passing
checks does **not** constitute a mathematical proof, and DerivaTrace does not
claim that it does. The certificate is designed to make a result auditable and
reproducible, not to assert infallibility.

## Model disagreement as information

Different models and engines can legitimately disagree. DerivaTrace is designed
to surface that disagreement as explicit, recorded information: model comparison
and uncertainty decomposition are first-class, not afterthoughts. A single
authoritative number is replaced by a transparent comparison of assumptions and
their consequences.

## Reproducibility and governance

Reproducibility is a design requirement, not a hope. Given the same canonical
contract, market snapshot, model configuration, engine configuration, random
seed (where applicable), and software version, the system is designed to
reproduce the same result within a declared numerical reproducibility policy.
Governance documents, ADRs, and a staged roadmap make the project's
constitutional choices explicit and reviewable.

## Long-term ambition

DerivaTrace aims to become a trusted open laboratory in which derivatives are
defined once, valued transparently across models and engines, and accompanied
by auditable evidence. It aspires to support contract algebras, market
snapshots, reference engines, evidence-carrying certificates, sensitivities,
calibration diagnostics, richer models, hedging experiments, model-risk
decomposition, path-dependent contracts, and an interactive explorer.

## Defensible novelty language

DerivaTrace does **not** claim to be the first system of its kind, nor to be
institutionally validated or production-ready. Its aims are modest and
defensible: to separate contract semantics from models and engines,
to make evidence the default companion of every result, and to keep the
deterministic core authoritative over calculations and validation. Where it
builds on established ideas in programming languages, financial engineering, and
reproducible research, it does so openly.

## Ethical and regulatory boundaries

DerivaTrace is a research and educational project. It is not a validated pricing
system, not financial advice, and not a substitute for professional model-risk
governance or regulatory compliance. Users are responsible for ensuring that any
use of related ideas complies with applicable law and internal controls.
