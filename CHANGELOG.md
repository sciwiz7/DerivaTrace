# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to semantic versioning once a stable release is published.

## [Unreleased]

### Added (Stage 1A — Immutable contract algebra and runtime type system)

- `derivatrace.contracts`: an immutable, strongly typed contract AST and a
  deterministic structural validator, with no pricing, models, or engines.
- Exact-domain value objects: `ExactNumber`, `Currency`, `Unit`/`UnitKind`,
  `ObservableId`, `ObservationTime`, `SettlementTime`.
- Scalar expression nodes (`Number`, `Observable`, `Add`, `Subtract`,
  `Multiply`, `Divide`, `Negate`, `Maximum`, `Minimum`, `ConditionalValue`).
- Boolean expression nodes (`BooleanConstant`, `Comparison`, `AllOf`, `AnyOf`,
  `Not`).
- Contract nodes (`Zero`, `Payment`, `Both`, `Scale`, `ConditionalContract`).
- `validate_contract`, returning deterministic `ContractMetrics` (unique node
  count and maximum depth), with iterative traversal, cycle detection, DAG
  sharing, and complexity limits.
- A stable error taxonomy (`DerivaTraceError`, `ContractError`,
  `ContractInputError`, `ContractTypeMismatchError`, `ContractValidationError`,
  `ContractCycleError`, `ContractComplexityError`) carrying structural paths.
- 100% statement and branch coverage; strict mypy; Ruff clean.

### Not implemented

- Canonicalization, canonical contract identity, serialization, hashing, the
  payoff graph, models, numerical engines, market data, and evidence
  certificates remain outside Stage 1A.

### Added (Stage 1B — Canonical architecture baseline, specification-only)

- A rigorous Stage 1B design baseline specifying the canonical contract
  representation and canonical payoff graph. No runtime canonicalization,
  serialization, hashing, or payoff-graph code is introduced.
- `docs/canonicalization-spec.md` — canonical schema (`derivatrace.contract
  .canonical` `1.0.0`), canonical byte encoding (ASCII UTF-8 JSON, sorted keys),
  exact `Decimal` / UTC / currency / unit / enum encoding, per-node commutativity
  and associative-flattening decisions, duplicate-operand policy, safe
  literal-only simplifications, forbidden transformations, DAG-sharing and
  node-identity policy, cycle and complexity protections, deterministic
  graph-node identifiers, SHA-256 domain separation, canonicalization error
  taxonomy, and version-migration policy.
- `docs/payoff-graph-spec.md` — model-independent payoff-graph node taxonomy and
  compilation mapping (specification-only).
- `docs/canonical-test-vectors.md` — test-vector format and illustrative vectors
  pinning the Stage 1B decisions.
- `docs/adr/0007-canonical-contract-identity-and-payoff-graph.md` — the
  constitutional decision recording the conservative, enumerated-law approach.

### Not implemented

- Runtime canonicalization, serialization, hashing, canonical contract identity,
  equivalence checks, and payoff-graph compilation remain unimplemented in the
  Stage 1B baseline; they are deferred to the Stage 1B implementation phase.
- Pricing, valuation, Greeks, models, numerical engines, market data, and
  evidence certificates remain outside Stage 1B.

## [0.1.0.dev0] — Stage 0 (Unreleased)

Stage 0 is the project foundation and system specification. It contains no
pricing functionality.

### Added

- Minimal, importable, dependency-free Python package `derivatrace`.
- `derivatrace.__version__` pinned to `0.1.0.dev0`.
- `derivatrace.ProjectMetadata`, an immutable, frozen value object holding safe
  static project facts.
- `derivatrace.project_metadata()`, a deterministic metadata accessor.
- `py.typed` marker for downstream type checking.
- Repository constitution: README, vision, product specification, architecture,
  contract semantics, certificate specification, threat model, glossary.
- Five architectural decision records (ADRs).
- Staged roadmap (Stages 0–12).
- Contributor, code-of-conduct, security, and governance documents.
- Continuous integration for Python 3.11, 3.12, 3.13, and 3.14.

### Not implemented

- All pricing, valuation, Greeks, Monte Carlo, PDE, tree, and calibration
  functionality. See the roadmap and the "what does not exist today" section of
  the README.

[0.1.0.dev0]: https://github.com/sciwiz7/DerivaTrace/releases/tag/0.1.0.dev0
