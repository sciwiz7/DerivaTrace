# DerivaTrace

> An open-source evidence-carrying derivatives compiler and model-risk laboratory.

- **Current status:** Stage 1A implemented — Immutable contract algebra and
  runtime type system. Stage 1B architecture baseline complete; **Stage 1B-R1
  canonical runtime implemented** (byte-exact canonicalization and canonical
  contract identity). **Stage 1B-R2 payoff-graph runtime implemented** (CV-011:
  byte-exact payoff-graph identity, deterministic node graph, and provenance).
  **Stage 1C architecture baseline established** (graded validation levels,
  equivalence reporting, structural diffing; runtimes planned for 1C-R1 and
  1C-R2). Stage 0 foundation complete.
- **Release stage:** Pre-Alpha. **Not published.** Not available on PyPI.
- **License:** [MIT](LICENSE)

## What DerivaTrace aims to be

DerivaTrace is a planned open-source system in which a user defines a financial
contract once and the system compiles it into a canonical, model-independent
payoff representation. That representation can later be valued by different
models and numerical engines, and every valuation is designed to produce an
auditable **evidence certificate**.

The guiding architectural principle is:

> **A valuation without evidence is an incomplete output.**

A certificate is designed to capture the contract identity, the market-data
snapshot identity, the model and parameters, the numerical-engine configuration,
the resulting value and sensitivities, numerical uncertainty, validation and
arbitrage checks, software and source versions, and deterministic integrity
hashes.

## Problem statement

In contemporary derivatives analytics, a number is often delivered without a
self-contained record of *how* it was produced. Reproducing a price, comparing
it across models, or challenging it during model-risk review can require
scattered notebooks, undocumented engine settings, and tribal knowledge.

DerivaTrace is designed so that the evidence required to understand, reproduce,
and challenge a valuation travels with the result.

## Proposed system

DerivaTrace separates concerns that are too often entangled:

- **Contract semantics** — what the instrument pays.
- **Market data** — observable inputs and snapshots.
- **Model** — assumptions governing stochastic behaviour.
- **Numerical engine** — the method used to calculate results.
- **Risk** — sensitivities and uncertainty.
- **Validation** — invariants and arbitrage checks.
- **Evidence certificate** — what was calculated and how.

No layer silently absorbs another layer's responsibility. The canonicalization,
determinism, and certificate design are specified in the architecture and
supporting documents below.

## Architectural principle

A price is treated as an *incomplete* output unless it is accompanied by
auditable evidence. The deterministic core remains authoritative for contract
semantics, canonicalization, calculations, tolerances, validation, and
certificates. Future assistive features may explain or summarize results, but
they must not silently change contracts, models, market inputs, engine
settings, or validation outcomes.

## Planned capabilities

These capabilities are **planned** for later stages and do **not** exist today:

- Immutable, typed contract algebra (delivered in Stage 1A), a canonical
  contract representation with deterministic identity (Stage 1B-R1 implemented),
  and a canonical payoff-graph runtime with deterministic payoff-graph identity
  (Stage 1B-R2 implemented).
- Market snapshots with deterministic evidence identity.
- Reference pricing engines (Black–Scholes, trees, Monte Carlo).
- Evidence-carrying valuation certificates.
- Greeks with independent sensitivity verification.
- Volatility surfaces and calibration diagnostics.
- Additional models (Heston, local volatility, jumps) and model comparison.
- Hedging laboratory and P&L attribution.
- Model-risk and uncertainty decomposition.
- Path-dependent and callable contracts.
- Interactive graph and certificate explorer.
- Secure extensions, interoperability, and governance maturity.

See [ROADMAP.md](ROADMAP.md) for the staged plan.

## What exists today (Stage 1A)

Stage 1A delivers the immutable contract algebra and its runtime type system on
top of the Stage 0 foundation. You can:

- Create exact domain values: `ExactNumber`, `Currency`, `Unit`/`UnitKind`,
  `ObservableId`, `ObservationTime`, `SettlementTime`.
- Construct immutable scalar expressions (`Number`, `Observable`, `Add`,
  `Subtract`, `Multiply`, `Divide`, `Negate`, `Maximum`, `Minimum`,
  `ConditionalValue`) and boolean expressions (`BooleanConstant`, `Comparison`,
  `AllOf`, `AnyOf`, `Not`).
- Compose contractual obligations (`Zero`, `Payment`, `Both`, `Scale`,
  `ConditionalContract`).
- Structurally validate a contract graph with `validate_contract`, which
  re-checks every node's invariants, rejects forged objects, unsupported
  subclasses, cycles, and excessive depth or node count.
- Inspect deterministic `ContractMetrics` (unique node count and maximum depth).

## What exists today (Stage 1B-R2)

Stage 1B-R2 delivers the canonical payoff-graph runtime on top of the Stage 1B-R1
canonical contract identity. You can:

- Compile an immutable contract into a deterministic payoff graph with
  `compile_payoff_graph`, yielding a byte-exact `payoffgraph:sha256:` identity
  derived from a canonical structural document (the `structural_bytes`).
- Inspect the compact canonical `structural_bytes` (the structural projection
  only), the `document_bytes` (same structural fields plus deterministic
  provenance), the `root_node_id`, the `node_count`, and the
  `source_contract_identity` (the canonical contract identity of the compiled
  contract). Neither representation is pretty-printed; the graph identity hashes
  `structural_bytes` only.
- Rely on provenance: the `PayoffGraph` records the compiler tag and source
  contract identity; changing provenance alone never changes the payoff-graph
  identity.

## What exists today (Stage 1C architecture baseline)

Stage 1C defines the **validation-equivalence layer**: graded validation levels
(`structural`, `canonical`, `payoff`), a deterministic equivalence report
schema (`derivatrace.validation-equivalence.report`), and deterministic
structural diffing over trusted Stage 1B representations. The specification is
in `docs/validation-equivalence-spec.md` and the architectural decision is
recorded in [ADR 0008](docs/adr/0008-validation-levels-equivalence-and-structural-diffing.md).
No runtime implementation exists yet; Stage 1C-R1 (validation levels and
reports) and Stage 1C-R2 (structural diffing) are planned increments.

## What does not exist today

Explicitly unimplemented:

- Any pricing, valuation, or Greeks computation.
- Monte Carlo, PDE, tree, or closed-form numerical engines.
- Calibration, hedging, or advanced contract logic.
- Any financial calculation of any kind.
- Market data, snapshots, or evaluation of observables.
- Any canonical payoff-graph **valuation**, or any pricing, model, or engine
  behaviour. (The canonical contract representation and its identity are
  implemented in Stage 1B-R1; the canonical payoff-graph runtime — byte-exact
  payoff-graph identity, deterministic node graph, and provenance — is
  implemented in Stage 1B-R2; see `docs/canonicalization-spec.md`,
  `docs/payoff-graph-spec.md`, `docs/canonical-test-vectors.md`, and
  [ADR 0007](docs/adr/0007-canonical-contract-identity-and-payoff-graph.md).)
- **Stage 1C validation levels, equivalence reports, or structural diffing
  runtime** (architecture baseline established in `docs/validation-equivalence-spec.md`
  and ADR 0008; runtimes planned for Stage 1C-R1 and 1C-R2).
- An evidence certificate or reproducibility hash.
- A published package or PyPI release.

## Intended users

- Quantitative researchers and model-risk professionals.
- Financial-engineering educators and students.
- Open-source contributors interested in reproducible, evidence-carrying
  financial computation.

## Repository architecture

```text
DerivaTrace/
├── .github/workflows/ci.yml
├── docs/
│   ├── index.md
│   ├── vision.md
│   ├── product-spec.md
│   ├── architecture.md
│   ├── contract-semantics.md
│   ├── contract-api.md
│   ├── certificate-spec.md
│   ├── threat-model.md
│   ├── glossary.md
│   └── adr/
│       ├── 0001-separation-of-contract-model-engine.md
│       ├── 0002-deterministic-canonicalization.md
│       ├── 0003-evidence-carrying-results.md
│       ├── 0004-exact-contract-terms-and-numerical-boundaries.md
│       ├── 0005-no-hidden-model-selection.md
│       └── 0006-stage-1-contract-algebra-and-runtime-type-system.md
├── src/derivatrace/
├── tests/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── GOVERNANCE.md
└── LICENSE
```

## Installation (contributors only)

DerivaTrace is **not** published and must not be installed from PyPI. For local
development only:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Development commands

```bash
ruff format .
ruff format --check .
ruff check .
mypy
pytest --cov=derivatrace --cov-branch --cov-report=term-missing --cov-fail-under=100
python -m build
```

## Safety and financial disclaimer

DerivaTrace is a research and educational project. It is **pre-alpha**,
**not validated**, and **not suitable for production use**. Nothing in this
repository constitutes financial advice, a validated pricing system, or a
substitute for professional model-risk governance. Do not use it to make
investment, trading, or risk decisions. Claims about future capabilities are
aspirational and subject to change.

## Documentation

- [Documentation index](docs/index.md)
- [Vision](docs/vision.md)
- [Product specification](docs/product-spec.md)
- [Architecture](docs/architecture.md)
- [Contract semantics](docs/contract-semantics.md)
- [Contract API (Stage 1A)](docs/contract-api.md)
- [Canonicalization specification (Stage 1B)](docs/canonicalization-spec.md)
- [Payoff-graph specification (Stage 1B)](docs/payoff-graph-spec.md)
- [Canonical test vectors (Stage 1B)](docs/canonical-test-vectors.md)
- [Validation-equivalence specification (Stage 1C)](docs/validation-equivalence-spec.md)
- [Certificate specification](docs/certificate-spec.md)
- [Threat model](docs/threat-model.md)
- [Glossary](docs/glossary.md)
- [Architectural decision records](docs/adr/)
  - [ADR 0001: Separation of contract, model, and engine](docs/adr/0001-separation-of-contract-model-engine.md)
  - [ADR 0002: Deterministic canonicalization](docs/adr/0002-deterministic-canonicalization.md)
  - [ADR 0003: Evidence-carrying results](docs/adr/0003-evidence-carrying-results.md)
  - [ADR 0004: Exact contract terms and numerical boundaries](docs/adr/0004-exact-contract-terms-and-numerical-boundaries.md)
  - [ADR 0005: No hidden model selection](docs/adr/0005-no-hidden-model-selection.md)
  - [ADR 0006: Stage 1 contract algebra and runtime type system](docs/adr/0006-stage-1-contract-algebra-and-runtime-type-system.md)
  - [ADR 0007: Canonical contract identity and payoff graph](docs/adr/0007-canonical-contract-identity-and-payoff-graph.md)
  - [ADR 0008: Validation levels, equivalence, and structural diffing](docs/adr/0008-validation-levels-equivalence-and-structural-diffing.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Code of conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [Governance](GOVERNANCE.md)
- [Changelog](CHANGELOG.md)

## Licence

DerivaTrace is released under the [MIT licence](LICENSE).
