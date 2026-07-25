# Governance

DerivaTrace currently uses a lightweight maintainer-led governance model suitable
for an early open-source project. The model is expected to mature as the project
and contributor base grow.

## Project roles

- **Primary maintainer:** Amrut Deshmukh, creator and founding principal architect.
  The maintainer owns the roadmap, architectural constitution, release decisions,
  security coordination and final scope decisions.
- **Contributors:** anyone who submits issues, documentation, tests or code.
- **Reviewers:** contributors trusted to review pull requests or specific technical
  areas.

## Current maintenance responsibilities

The primary maintainer is responsible for:

- triaging issues and reviewing pull requests;
- maintaining specifications and architectural decision records;
- preserving deterministic identities and schema compatibility;
- maintaining tests, CI, packaging and documentation consistency;
- coordinating vulnerability reports and security fixes;
- preventing unsupported scope expansion or capability overclaims.

## Decision-making

- **Architectural decisions** are captured in Architectural Decision Records under
  [`docs/adr/`](docs/adr/).
- **Routine changes** are made through focused pull requests and merged only after
  required checks pass.
- **Constitutional changes** require explicit maintainer approval and an ADR or ADR
  update.

Constitutional changes include:

- boundaries between contract, market, model, engine, risk, validation and
  certificate layers;
- deterministic encoding, canonical identity or schema changes;
- security and trust-boundary changes;
- introduction or removal of runtime dependencies;
- public API expansion;
- introduction of pricing, valuation, model or numerical-engine functionality.

## Proposal and review process

1. Open an issue describing the problem, proposed scope and exclusions.
2. Add or update an ADR for significant design changes.
3. Implement the smallest bounded increment on a focused branch.
4. Add deterministic tests and documentation guards.
5. Open a pull request referencing the issue and relevant ADR.
6. Require Ruff, strict mypy, Python 3.11–3.14 tests, 100% statement and branch
   coverage, and packaging validation.
7. Merge only after the exact reviewed head is green.

## Scope control

The deterministic core must remain authoritative. Contributions must not silently:

- alter user-authored contracts or identities;
- select models or engines;
- reinterpret validation or comparison outcomes;
- execute arbitrary user code;
- introduce financial advice, production-readiness or ecosystem-adoption claims;
- bypass the Stage 1C-R2 and public-export gates.

## Security and conflicts

Security-sensitive reports follow [SECURITY.md](SECURITY.md) and should not be
opened publicly. The maintainer should disclose material conflicts of interest when
a proposed change could privilege a proprietary integration or commercial user.

## Amendments

This document may be amended through a reviewed pull request. Substantive changes
should be recorded in the [Changelog](CHANGELOG.md).

## Licence

DerivaTrace is released under the [MIT License](LICENSE). Contributions are
accepted under the same licence.