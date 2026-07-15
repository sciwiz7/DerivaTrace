from __future__ import annotations

from derivatrace.contracts import Contract, ValidationLimits

from ._normalization import canonicalize_contract
from ._schema import CanonicalizationLimits, CanonicalSchemaVersion


def canonical_contract_bytes(
    contract: Contract,
    *,
    schema: CanonicalSchemaVersion | None = None,
    limits: CanonicalizationLimits | None = None,
    validation_limits: ValidationLimits | None = None,
) -> bytes:
    """Return the byte-exact canonical document for ``contract``."""
    return canonicalize_contract(
        contract, schema=schema, limits=limits, validation_limits=validation_limits
    ).canonical_bytes


def canonical_contract_identity(
    contract: Contract,
    *,
    schema: CanonicalSchemaVersion | None = None,
    limits: CanonicalizationLimits | None = None,
    validation_limits: ValidationLimits | None = None,
) -> str:
    """Return the prefixed SHA-256 canonical contract identity for ``contract``."""
    return canonicalize_contract(
        contract, schema=schema, limits=limits, validation_limits=validation_limits
    ).identity


__all__: list[str] = ["canonical_contract_bytes", "canonical_contract_identity"]
