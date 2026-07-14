# Governance

This document describes the governance model for DerivaTrace during its early
stage. The model is intentionally lightweight and is expected to mature as the
project grows (see [ROADMAP.md](ROADMAP.md), Stage 12).

## Project roles

- **Maintainer:** Amrut Deshmukh, the founding principal architect. The
  maintainer is responsible for the architectural constitution, releases, and
  final decisions on scope.
- **Contributors:** Anyone who submits issues, documentation, or code.
- **Reviewers:** Contributors entrusted by the maintainer to review pull
  requests.

## Decision-making

- **Architectural decisions** are captured as Architectural Decision Records
  (ADRs) under [`docs/adr/`](docs/). ADRs are the canonical record of
  significant design choices and their context.
- **Routine changes** are made through pull requests and reviewed before merge.
- **Constitutional changes** (separation of concerns, determinism guarantees,
  evidence-certificate design, security boundaries) require explicit
  maintainer approval and an accompanying ADR or ADR update.

## Scope control

To protect the integrity of the deterministic core, the following are treated as
constitutional and require maintainer review:

- Changes to the separation of contract, market, model, engine, risk,
  validation, and certificate layers.
- Changes that could affect determinism or reproducibility.
- Introduction or removal of runtime dependencies.
- Introduction of model or engine selection logic.

## Proposals and review

1. Open an issue describing the proposal.
2. For significant design changes, write or update an ADR.
3. Submit a pull request referencing the issue and ADR.
4. Obtain review, run CI, and merge only after checks pass.

## Amendments

This governance document may be amended by the maintainer through a pull
request. Substantive changes should be announced in the
[Changelog](CHANGELOG.md) and discussed with contributors.

## Licence

DerivaTrace is released under the [MIT licence](LICENSE). Contributions are
accepted under the same licence.
