from __future__ import annotations

from derivatrace.contracts._errors import DerivaTraceError


class ValidationEquivalenceError(DerivaTraceError):
    """Base class for all Stage 1C validation-equivalence errors."""

    code: str = "validation_equivalence.error"


class ValidationEquivalenceInputError(ValidationEquivalenceError):
    """Raised for wrong exact input types, malformed limits, unsupported
    level, or unsupported diff representation selection at the API boundary."""

    code: str = "validation_equivalence.input"


class ValidationEquivalenceEncodingError(ValidationEquivalenceError):
    """Raised when report serialization fails; no partial report is returned."""

    code: str = "validation_equivalence.encoding"


class ValidationEquivalenceReportCollisionError(ValidationEquivalenceError):
    """Raised when two distinct structural projections hash to the same
    report_id; no report is returned."""

    code: str = "validation_equivalence.report_collision"


class ValidationEquivalenceUnsupportedLevelError(ValidationEquivalenceError):
    """Raised when the requested validation level is not a recognized
    ValidationLevel member."""

    code: str = "validation_equivalence.unsupported_level"


class ValidationEquivalenceComparisonError(ValidationEquivalenceError):
    """Raised when an internal consistency violation is detected during
    comparison orchestration; no report is returned."""

    code: str = "validation_equivalence.comparison_failed"


class ValidationEquivalenceMalformedRepresentationError(ValidationEquivalenceError):
    """Raised when a trusted Stage 1B output fails internal consistency
    checks."""

    code: str = "validation_equivalence.malformed_representation"


__all__: list[str] = [
    "ValidationEquivalenceComparisonError",
    "ValidationEquivalenceEncodingError",
    "ValidationEquivalenceError",
    "ValidationEquivalenceInputError",
    "ValidationEquivalenceMalformedRepresentationError",
    "ValidationEquivalenceReportCollisionError",
    "ValidationEquivalenceUnsupportedLevelError",
]
