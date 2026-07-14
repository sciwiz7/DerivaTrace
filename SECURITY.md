# Security policy

## Supported versions

DerivaTrace is at **Stage 0** and is **pre-alpha**. There are no supported
stable releases yet. Security fixes are applied to the `main` branch only.

## Reporting a vulnerability

If you discover a security vulnerability, please report it privately. Do **not**
open a public GitHub issue for security-sensitive problems.

Please report vulnerabilities by opening a private security advisory on the
project repository or by contacting the maintainers through the repository's
security reporting mechanism:

- Repository: <https://github.com/sciwiz7/DerivaTrace>
- Use the "Security" tab → "Report a vulnerability" workflow provided by GitHub.

Include as much detail as possible:

- A description of the vulnerability and its impact.
- Steps to reproduce or a proof of concept.
- Affected versions or commit references.
- Any suggested mitigation.

You can expect an acknowledgement, and we will work with you on a coordinated
disclosure timeline.

## Security assumptions

DerivaTrace is designed around the following assumptions, detailed further in
[docs/threat-model.md](docs/threat-model.md):

- Contract definitions, market snapshots, serialized certificates, plugin
  metadata, and future contribution inputs are **untrusted**.
- The deterministic core must remain authoritative for contract semantics,
  canonicalization, calculations, tolerances, validation, and certificates.
- Integrity hashes are **not** digital signatures. Signing, if added later, will
  be an explicit optional capability.

## Incident response

When a vulnerability is confirmed:

1. A maintainer acknowledges receipt and opens a private tracking item.
2. A fix is developed on a private branch where possible.
3. A coordinated disclosure date is agreed with the reporter.
4. The fix is merged to `main` and referenced from the
   [Changelog](CHANGELOG.md).
5. If a published release exists at that time, a patched release is prepared.

## Scope and non-goals

Security tooling in this repository is for the project's own development and
governance. It is not a substitute for institutional model-risk or
cyber-security controls.
