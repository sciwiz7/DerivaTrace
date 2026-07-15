# Roadmap

This roadmap defines the staged evolution of DerivaTrace. Stage 0 is the
foundation and system specification. Stage 1 introduces the immutable contract
algebra; it is delivered in three parts (1A, 1B, 1C). Later stages are
**planned** and their scope may change through architectural review.

Stages are marked as:

- **Complete** — finished, reviewed, and merged.
- **In progress** — actively being established.
- **Planned** — not yet started.

## Stage 0 — Foundation and system specification

- **Status:** Complete.
- **Objective:** Establish the project constitution, architecture, and a minimal
  dependency-free package.
- **Main deliverables:** Package skeleton, deterministic metadata, full
  specification documents, ADRs, CI, governance and security policies.
- **Acceptance criteria:** CI green on Python 3.11–3.14; 100% coverage of the
  Stage 0 package; all documentation links resolve; no runtime dependencies.
- **Explicit exclusions:** Pricing, Greeks, Monte Carlo, PDEs, calibration,
  hedging, and advanced contract logic.

## Stage 1 — Immutable contract algebra

- **Status:** In progress.
- **Sub-stages:** Stage 1A implemented; **Stage 1B architecture baseline
  established (specification-only)**; Stage 1C planned.
- **Objective:** Introduce an immutable, typed contract AST, a deterministic
  structural validator, and (later) a canonical payoff graph.
- **Explicit exclusions for the whole of Stage 1:** Numerical valuation, market
  data, and any pricing engine.

### Stage 1A — Contract algebra and runtime type system

- **Status:** Complete.
- **Objective:** A strongly typed, immutable contract algebra with exact-domain
  value objects and whole-graph structural validation.
- **Main deliverables:** `ExactNumber`; `Currency`; `Unit`/`UnitKind`;
  `ObservableId`; `ObservationTime`/`SettlementTime`; scalar expression nodes
  (`Number`, `Observable`, `Add`, `Subtract`, `Multiply`, `Divide`, `Negate`,
  `Maximum`, `Minimum`, `ConditionalValue`); boolean expression nodes
  (`BooleanConstant`, `Comparison`, `AllOf`, `AnyOf`, `Not`); contract nodes
  (`Zero`, `Payment`, `Both`, `Scale`, `ConditionalContract`); structural
  validation with deterministic `ContractMetrics`; a stable error taxonomy.
- **Acceptance criteria:** `validate_contract` runs iteratively; re-checks every
  node's invariants; rejects forged objects, unsupported subclasses, cycles, and
  excessive depth or node count; returns reproducible metrics.
- **Explicit exclusions:** Canonicalization, canonical identity, serialization,
  hashing, equivalence checks, the payoff graph, models, engines, market data,
  and certificates.

### Stage 1B — Canonical payoff graph and structural canonicalization

- **Status:** In progress (architecture baseline; implementation follows separate
  review).
- **Objective:** Compile the validated contract graph into a canonical payoff
  graph and produce a structural canonical form with a deterministic identity.
- **Baseline deliverables (this stage):** A rigorous design baseline specifying
  canonical schema and versioning, canonical byte encoding (UTF-8 JSON, sorted
  keys), exact `Decimal` / UTC / currency / unit / enum encoding, per-node
  commutativity and associative-flattening decisions, duplicate-operand policy,
  safe literal-only simplifications, forbidden transformations, DAG-sharing and
  node-identity policy, cycle and complexity protections, deterministic
  graph-node identifiers, SHA-256 domain separation, canonicalization error
  taxonomy, version-migration policy, and test vectors — plus
  [ADR 0007](docs/adr/0007-canonical-contract-identity-and-payoff-graph.md).
- **Main deliverables (implementation, not yet built):** Payoff-graph
  compilation, canonicalization of contract structure, canonical contract
  identity, equivalence checks.
- **Acceptance criteria:** Equivalent contracts produce identical canonical
  forms and identities; non-equivalent contracts do not collapse through
  undocumented transformations.
- **Explicit exclusions:** Runtime canonicalization/hashing code in the baseline;
  numerical valuation and market data.

### Stage 1C — Validation levels and equivalence reporting

- **Status:** Planned.
- **Objective:** Define graded validation levels and equivalence reporting on
  top of the canonical form.
- **Main deliverables:** Validation levels, equivalence reports, structural
  diffing.
- **Acceptance criteria:** Validation levels are documented and reproducible.
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
