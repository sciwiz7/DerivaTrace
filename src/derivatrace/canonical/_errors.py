from __future__ import annotations

from derivatrace.contracts._errors import DerivaTraceError, Path, format_path

# The canonicalization error taxonomy mirrors the Stage 1A taxonomy. Every error
# derives from ``DerivaTraceError`` and carries a stable machine-readable ``.code``
# plus an optional immutable structural ``.path``. Stable codes:
#
# * ``canonicalization.error``            unexpected internal failure
# * ``canonicalization.input``            not a supported, validated contract graph
# * ``canonicalization.input.not_validated``  ``validate_contract`` did not pass
# * ``canonicalization.cycle``            residual cycle detected
# * ``canonicalization.complexity``       depth / node / byte limit exceeded
# * ``canonicalization.encoding``         value object could not be encoded
# * ``canonicalization.collision``        distinct payloads share a node identity


class CanonicalizationError(DerivaTraceError):
    """Base class for all canonicalization errors."""

    code: str = "canonicalization.error"


class CanonicalizationInputError(CanonicalizationError):
    """Input is not a supported, validated Stage 1A contract graph root."""

    code: str = "canonicalization.input"


class CanonicalizationNotValidatedError(CanonicalizationInputError):
    """The contract graph did not pass Stage 1A validation."""

    code: str = "canonicalization.input.not_validated"


class CanonicalizationCycleError(CanonicalizationError):
    """A residual reference cycle was detected during canonicalization."""

    code: str = "canonicalization.cycle"


class CanonicalizationComplexityError(CanonicalizationError):
    """A canonicalization complexity limit was exceeded."""

    code: str = "canonicalization.complexity"


class CanonicalizationEncodingError(CanonicalizationError):
    """A value object could not be encoded canonically."""

    code: str = "canonicalization.encoding"


class CanonicalizationCollisionError(CanonicalizationError):
    """Two distinct canonical payloads hashed to the same node identity."""

    code: str = "canonicalization.collision"


__all__: list[str] = [
    "CanonicalizationCollisionError",
    "CanonicalizationComplexityError",
    "CanonicalizationCycleError",
    "CanonicalizationEncodingError",
    "CanonicalizationError",
    "CanonicalizationInputError",
    "CanonicalizationNotValidatedError",
    "Path",
    "format_path",
]
