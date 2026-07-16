from __future__ import annotations

from derivatrace.contracts import Contract, ValidationLimits

from ._normalization import canonicalize_contract
from ._schema import CanonicalizationLimits, CanonicalSchemaVersion


def structurally_equivalent(
    left: Contract,
    right: Contract,
    *,
    schema: CanonicalSchemaVersion | None = None,
    limits: CanonicalizationLimits | None = None,
    validation_limits: ValidationLimits | None = None,
) -> bool:
    """Return ``True`` only when two contracts share a canonical identity.

    Both contracts are canonicalized under the same explicit schema and limits,
    and equivalence holds exactly when their canonical contract identities match.
    This is structural equivalence under the approved Stage 1B-R1 laws; it makes
    no claim of mathematical, economic, pricing, or legal equivalence, and has no
    model, market-data, or pricing dependency. Canonicalization failures
    propagate.
    """
    left_result = canonicalize_contract(
        left, schema=schema, limits=limits, validation_limits=validation_limits
    )
    right_result = canonicalize_contract(
        right, schema=schema, limits=limits, validation_limits=validation_limits
    )
    return left_result.identity == right_result.identity


__all__: list[str] = ["structurally_equivalent"]
