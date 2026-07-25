# Security policy

## Supported versions

DerivaTrace is **pre-alpha**, not published, and has no supported stable releases.
Security fixes are applied to the `main` branch only.

Current implementation status:

- Stage 1A contract algebra and validation: complete.
- Stage 1B-R1 canonical runtime: implemented.
- Stage 1B-R2 payoff-graph runtime: implemented.
- Stage 1C-R1 private validation-equivalence runtime: complete.
- Stage 1C-R2 structural diffing and the public Stage 1C API: planned and unimplemented.

## Reporting a vulnerability

Please report security vulnerabilities privately. Do **not** open a public GitHub
issue for security-sensitive problems.

Use the repository's private vulnerability-reporting workflow:

- Repository: <https://github.com/sciwiz7/DerivaTrace>
- Open the **Security** tab and select **Report a vulnerability**.

Include:

- a description of the vulnerability and its impact;
- reproduction steps or a proof of concept;
- affected versions or commit references;
- suggested mitigation, when available.

The maintainer will acknowledge the report and coordinate investigation,
remediation and disclosure.

## Security assumptions

DerivaTrace treats external and caller-owned inputs as untrusted. The threat model
is documented in [docs/threat-model.md](docs/threat-model.md).

The implemented deterministic core uses:

- exact-type and use-time invariant validation;
- rejection of forged or unsupported objects;
- iterative bounded graph traversal;
- cycle and complexity protection;
- deterministic canonical encodings and identities;
- collision detection;
- exception containment at internal orchestration boundaries;
- no runtime dependencies.

Integrity hashes are **not** digital signatures. Signing, if added later, will be
an explicit and separately reviewed capability.

## Incident response

When a vulnerability is confirmed:

1. The maintainer acknowledges receipt and opens a private tracking item.
2. A fix is developed privately where practical.
3. The relevant deterministic and security boundaries are reviewed.
4. The complete CI and packaging suite is run.
5. The fix is merged to `main` and recorded in the [Changelog](CHANGELOG.md).
6. A coordinated disclosure is published when appropriate.

## Scope and non-goals

This policy governs the DerivaTrace repository and its development workflow. It
is not a substitute for institutional model-risk, cyber-security or financial
controls, and the project is not suitable for production use.