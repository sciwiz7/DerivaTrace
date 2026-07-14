# Product specification

This document defines the target users, requirements, scope, and success
criteria for DerivaTrace. It is part of the Stage 0 specification and describes
planned behaviour; it is **not** an implementation status report.

## Target users

- **Quantitative researchers** who define and value derivatives and want
  reproducible, comparable results.
- **Model-risk professionals** who review, challenge, and document model
  behaviour.
- **Educators and students** of financial engineering who need transparent,
  inspectable examples.
- **Open-source contributors** building reproducible financial-computation
  tooling.

## User problems

- Valuations arrive without a self-contained record of how they were produced.
- Comparing results across models and engines is manual and error-prone.
- Reproducing a historical price requires reconstructing scattered context.
- Validation and arbitrage checks are not attached to the result.
- Assumptions are implicit and hard to audit.

## Primary jobs to be done

1. Define a contract once in a canonical, model-independent form.
2. Value that contract with a chosen model and engine.
3. Receive an evidence certificate attached to the result.
4. Compare results across models and engines with disagreement made explicit.
5. Reproduce a past valuation from its certificate.
6. Challenge and audit assumptions through transparent evidence.

## Core workflows

- **Author contract:** express a contract using compositional primitives.
- **Select model and engine:** choose assumptions and a numerical method
  explicitly (never silently).
- **Value:** run the engine and produce a result.
- **Certify:** assemble an evidence certificate.
- **Review:** inspect certificate, validation outcomes, and warnings.
- **Compare:** evaluate the same contract under multiple models/engines.

## Functional requirements

- FR1: Represent contracts as an immutable, typed structure (planned Stage 1).
- FR2: Canonicalize equivalent inputs to a stable representation (planned
  Stage 2).
- FR3: Capture market snapshots with deterministic identity (planned Stage 2).
- FR4: Provide selectable reference numerical engines (planned Stage 3).
- FR5: Emit versioned evidence certificates (planned Stage 4).
- FR6: Report sensitivities and uncertainty (planned Stage 5+).
- FR7: Record validation and arbitrage checks (planned Stage 4+).
- FR8: Separate contract, market, model, engine, risk, validation, and
  certificate concerns at the architecture level (now, Stage 0). This
  separation of concerns is a constitutional requirement of the project.

## Non-functional requirements

- NFR1: **Determinism** — identical inputs yield identical results within the
  declared policy.
- NFR2: **Immutability and typing** — favour frozen, typed, explicit values.
- NFR3: **Dependency minimalism** — the foundational package is
  runtime-dependency-free.
- NFR4: **Reproducibility** — software version and source commit are recorded.
- NFR5: **Auditability** — evidence travels with the result.
- NFR6: **Portability** — supports Python 3.11, 3.12, 3.13, and 3.14.

## Evidence requirements

- ER1: Every valuation is designed to carry a certificate with contract
  identity, market-snapshot identity, model/parameter identity, engine
  configuration, value, uncertainty, validation outcomes, software/source
  versions, and integrity hashes.
- ER2: Hashes are deterministic SHA-256 integrity hashes; they are **not**
  digital signatures.
- ER3: Certificates must distinguish evidence, assertions, validation outcomes,
  warnings, and unsupported claims.

## Safety requirements

- SR1: No hidden model or engine selection.
- SR2: No hidden intelligence altering contracts, inputs, settings, or
  validation outcomes.
- SR3: Untrusted inputs (contracts, snapshots, certificates, plugin metadata)
  are validated and never executed as code.
- SR4: No silent precision conversion between exact contract terms and
  numerical inputs.

## Success criteria

- SC1: Equivalent serialized contracts canonicalize identically.
- SC2: A valuation is reproducible from its certificate under the same
  software and configuration.
- SC3: Model disagreement is recorded as information, not hidden.
- SC4: CI passes on Python 3.11–3.14 with strict typing, linting, and full
  coverage of the Stage 0 package.

## Non-goals

- Not a trading system, broker, or exchange.
- Not a source of financial advice.
- Not a formally verified system (unless explicitly pursued later with evidence).
- Not a substitute for institutional model-risk governance.

## Stage 0 scope

Establish the project constitution: package skeleton, deterministic metadata,
specification documents, ADRs, CI, and governance/security policies. No pricing
functionality.

## Proposed Stage 1 scope

Immutable contract algebra and canonical payoff graph: contract node
primitives, canonicalization, equivalence, and validation levels.

## Long-term scope

Reference engines, evidence-carrying certificates, Greeks, calibration diagnostics,
richer models, hedging laboratory, model-risk decomposition, path-dependent
contracts, interactive explorer, and secure extension boundaries.

## Open design questions

- What is the precise minimal contract algebra for Stage 1?
- How should currency and unit conversions be recorded and validated?
- What is the canonical schema-version migration policy for certificates?
- What external signature formats should be supported as optional later?
- How should plugin boundaries enforce the no-hidden-intelligence rule?
