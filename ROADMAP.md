# Roadmap

DerivaTrace is developed in bounded stages. Completed work is separated from
planned work so that specifications never imply an unavailable capability.

Status vocabulary:

- **Complete** — implemented, reviewed and merged.
- **In progress** — at least one bounded increment remains open.
- **Planned** — not implemented.

The project is pre-alpha, not published and has no stable release.

## Stage 0 — Foundation and system specification

- **Status:** Complete.
- **Delivered:** package skeleton, project constitution, architecture,
  documentation, ADR process, governance, security policy, CI and packaging
  validation.
- **Quality boundary:** Python 3.11–3.14, strict typing, no runtime dependencies.
- **Excluded:** pricing, numerical engines, market data and trading connectivity.

## Stage 1 — Immutable contract and representation core

- **Status:** In progress.
- **Sub-stages:** Stage 1A Complete; Stage 1B architecture baseline Complete;
  Stage 1B-R1 canonical runtime Implemented; Stage 1B-R2 payoff-graph runtime
  Implemented; Stage 1C architecture baseline Established; Stage 1C-R1 Complete
  privately; Stage 1C-R2 Planned; public Stage 1C API Unimplemented.
- **Objective:** provide deterministic, bounded and auditable contract and payoff
  representations without performing valuation.
- **Whole-stage exclusions:** pricing, market data, numerical models, engines,
  Greeks, calibration and hedging.

### Stage 1A — Contract algebra and runtime type system

- **Status:** Complete.
- **Delivered:** exact domain values; immutable scalar, Boolean and contract nodes;
  iterative whole-graph validation; cycle, forgery and complexity protection;
  deterministic metrics and a stable error taxonomy.
- **Excluded:** canonical identity, payoff compilation, equivalence reporting,
  pricing, models, engines and certificates.

### Stage 1B — Canonical contract and payoff representations

- **Status:** In progress as a parent stage because later Stage 1 work remains;
  both Stage 1B runtime increments are implemented.

#### Stage 1B architecture baseline

- **Status:** Complete.
- **Delivered:** schema, byte encoding, exact-value encoding, node laws, DAG policy,
  complexity limits, collision handling, domain-separated identities, migration
  policy and normative vectors.

#### Stage 1B-R1 — Canonical runtime

- **Status:** Implemented.
- **Delivered:** `derivatrace.canonical`, byte-exact canonical JSON,
  content-addressed nodes, collision detection and deterministic
  `canonical:sha256:` contract identity.

#### Stage 1B-R2 — Payoff-graph runtime

- **Status:** Implemented.
- **Delivered:** `derivatrace.payoffgraph`, deterministic reachable-only payoff
  DAGs, compact structural bytes, provenance-bearing document bytes and
  `payoffgraph:sha256:` identity.

### Stage 1C — Validation levels and equivalence reporting

- **Status:** Architecture baseline Established; Stage 1C-R1 Complete privately;
  Stage 1C-R2 Planned; public API Unimplemented.
- **Objective:** provide graded structural, canonical and payoff evaluation with
  deterministic reports and later bounded structural diffing.

#### Stage 1C architecture baseline

- **Status:** Established.
- **Delivered:** validation-level taxonomy, report schema, comparison vocabulary,
  error taxonomy, versioning, limits, security rules, conformance vectors and
  ADRs 0008 and 0009.

#### Stage 1C-R1A — Private report foundation

- **Status:** Implemented.
- **Delivered:** closed enums and records, deterministic report encoding and
  identity, collision defence, schema metadata, frozen limits and the exact empty
  diff state.

#### Stage 1C-R1B — Private orchestration

- **Status:** Implemented.
- **Delivered:** private `_compare_contracts` orchestration; authoritative use-time
  configuration validation; independent per-side structural, canonical and payoff
  processing; upstream failure capture; double-canonicalization consistency;
  deterministic report construction; `diff_representation="none"` only.

#### Stage 1C-R2 — Private structural diff engine

- **Status:** Planned.
- **Planned scope:** deterministic bounded diffing over canonical and payoff
  representations, stable paths and ordering, admission and output limits, and
  truncation semantics.
- **Export gate:** only after R2 is reviewed may a public `compare_contracts` API be
  considered. No public API exists today.

## Stage 2 — Market snapshots and deterministic evidence identity

- **Status:** Planned.
- **Objective:** define explicit, versioned market-data snapshots with deterministic
  identity and rejection of ambiguous numeric input.
- **Excluded:** pricing engines.

## Stage 3 — Reference numerical engines

- **Status:** Planned.
- **Objective:** add separately selectable closed-form, lattice and Monte Carlo
  engines with explicit numerical configuration and reproducibility evidence.
- **Excluded:** hidden or automatic model selection.

## Stage 4 — Evidence-carrying valuation certificates

- **Status:** Planned.
- **Objective:** emit versioned certificates recording inputs, model, engine,
  outputs, checks, uncertainty and integrity identifiers.
- **Excluded:** claims that hashes are digital signatures or proofs of correctness.

## Stage 5 — Greeks and independent sensitivity verification

- **Status:** Planned.
- **Objective:** calculate sensitivities through explicit methods and preserve
  independent cross-check evidence.

## Stage 6 — Volatility surfaces and calibration diagnostics

- **Status:** Planned.
- **Objective:** represent calibration inputs, fitted surfaces, diagnostics and
  uncertainty as evidence.

## Stage 7 — Additional models and model comparison

- **Status:** Planned.
- **Objective:** add Heston, local-volatility and jump models while reporting model
  disagreement rather than selecting a hidden authoritative answer.

## Stage 8 — Hedging laboratory and P&L attribution

- **Status:** Planned.
- **Objective:** support reproducible hedging experiments and attribution.
- **Excluded:** live execution or brokerage connectivity.

## Stage 9 — Model-risk and uncertainty decomposition

- **Status:** Planned.
- **Objective:** separate and report sources of model, parameter and numerical
  uncertainty.

## Stage 10 — Path-dependent and callable contracts

- **Status:** Planned.
- **Objective:** add explicit path observations, barriers and exercise rights while
  keeping contract semantics separate from numerical path generation.

## Stage 11 — Graph and certificate explorer

- **Status:** Planned.
- **Objective:** provide a read-only interactive view of deterministic contracts,
  payoff graphs and evidence certificates.

## Stage 12 — Secure extensions, interoperability and governance maturity

- **Status:** Planned.
- **Objective:** mature extension boundaries, interchange formats, release
  security, governance and contributor processes.

## Permanent boundaries

Across every stage, DerivaTrace must not silently alter user-authored contracts,
select models or engines without explicit configuration, execute arbitrary user
code, or claim economic, legal, accounting, tax or suitability equivalence from
structural comparisons.