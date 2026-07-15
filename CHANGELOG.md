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
