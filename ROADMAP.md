# Roadmap

This roadmap defines the staged evolution of DerivaTrace. Stage 0 is the
foundation and system specification. All later stages are **planned** and their
scope may change through architectural review.

Stages are marked as:

- **In progress** — actively being established (Stage 0 until independently
  reviewed and merged).
- **Planned** — not yet started.

## Stage 0 — Foundation and system specification

- **Status:** In progress (until independently reviewed and merged).
- **Objective:** Establish the project constitution, architecture, and a minimal
  dependency-free package.
- **Main deliverables:** Package skeleton, deterministic metadata, full
  specification documents, ADRs, CI, governance and security policies.
- **Acceptance criteria:** CI green on Python 3.11–3.14; 100% coverage of the
  Stage 0 package; all documentation links resolve; no runtime dependencies.
- **Explicit exclusions:** Pricing, Greeks, Monte Carlo, PDEs, calibration,
  hedging, and advanced contract logic.

## Stage 1 — Immutable contract algebra and canonical payoff graph

- **Status:** Planned.
- **Objective:** Introduce an immutable, typed contract AST and a canonical
  payoff graph.
- **Main deliverables:** Contract node primitives, canonicalization of contract
  structure, equivalence checks, validation levels.
- **Acceptance criteria:** Equivalent serialized contracts produce identical
  canonical forms; contract semantics are separated from models.
- **Explicit exclusions:** Numerical valuation and market data.

## Stage 2 — Market snapshots and deterministic evidence identity

- **Status:** Planned.
- **Objective:** Define market-data snapshots with deterministic identity.
- **Main deliverables:** Snapshot schema, deterministic hashing, currency and
  unit handling, rejection of ambiguous input.
- **Acceptance criteria:** Identical snapshots hash identically; no NaN/Infinity
  enters certificates.
- **Explicit exclusions:** Pricing engines.

## Stage 3 — Black–Scholes, tree, and Monte Carlo reference engines

- **Status:** Planned.
- **Objective:** Provide selectable reference numerical engines.
- **Main deliverables:** Closed-form, lattice, and Monte Carlo engines with
  explicit seeds, path counts, and time steps.
- **Acceptance criteria:** Reproducible results under fixed seeds; documented
  error estimates.
- **Explicit exclusions:** Automatic model selection.

## Stage 4 — Evidence-carrying valuation certificates

- **Status:** Planned.
- **Objective:** Emit versioned evidence certificates for valuations.
- **Main deliverables:** Certificate envelope, hashing procedure, identity,
  reproducibility configuration.
- **Acceptance criteria:** Certificates are self-describing and tamper-evident.
- **Explicit exclusions:** External digital signatures (planned as optional).

## Stage 5 — Greeks and independent sensitivity verification

- **Status:** Planned.
- **Objective:** Compute sensitivities and verify them independently.
- **Main deliverables:** Greeks via multiple methods; cross-check evidence.
- **Acceptance criteria:** Sensitivities reproducible and independently checked.
- **Explicit exclusions:** Hedging execution.

## Stage 6 — Volatility surfaces and calibration diagnostics

- **Status:** Planned.
- **Objective:** Represent volatility surfaces and calibration diagnostics.
- **Main deliverables:** Surface schema, calibration diagnostics, fit evidence.
- **Acceptance criteria:** Calibration inputs and outputs recorded as evidence.
- **Explicit exclusions:** Production calibration service.

## Stage 7 — Heston, local volatility, jumps, and model comparison

- **Status:** Planned.
- **Objective:** Add stochastic-volatility and local-volatility models.
- **Main deliverables:** Heston, local volatility, jump-diffusion models;
  model-disagreement reporting.
- **Acceptance criteria:** Model comparison recorded as evidence, not a single
  authoritative answer.
- **Explicit exclusions:** Model selection automation.

## Stage 8 — Hedging laboratory and P&L attribution

- **Status:** Planned.
- **Objective:** Experiment with hedging strategies and attribute P&L.
- **Main deliverables:** Hedging simulations, P&L attribution evidence.
- **Acceptance criteria:** Hedging experiments reproducible.
- **Explicit exclusions:** Live trading connectivity.

## Stage 9 — Model-risk and uncertainty decomposition

- **Status:** Planned.
- **Objective:** Decompose valuation uncertainty across models and engines.
- **Main deliverables:** Uncertainty decomposition, model-risk reports.
- **Acceptance criteria:** Uncertainty sources itemized in evidence.
- **Explicit exclusions:** Regulatory sign-off.

## Stage 10 — Path-dependent and callable contracts

- **Status:** Planned.
- **Objective:** Support path observations, barriers, and exercise rights.
- **Main deliverables:** Path-dependent nodes, callable/puttable semantics.
- **Acceptance criteria:** Path logic separated from numerical path generation.
- **Explicit exclusions:** Exotic pricing guarantees.

## Stage 11 — Interactive graph and certificate explorer

- **Status:** Planned.
- **Objective:** Provide an interactive exploration of contracts and
  certificates.
- **Main deliverables:** Graph viewer, certificate explorer.
- **Acceptance criteria:** UI reflects the deterministic core without altering
  it.
- **Explicit exclusions:** AI rewriting of contracts or results.

## Stage 12 — Secure extensions, interoperability, and governance maturity

- **Status:** Planned.
- **Objective:** Mature the plugin boundaries, interoperability, and governance.
- **Main deliverables:** Plugin policy, interchange formats, governance review
  cadence.
- **Acceptance criteria:** Extensions cannot silently alter the deterministic
  core.
- **Explicit exclusions:** Proprietary model substitution without evidence.
