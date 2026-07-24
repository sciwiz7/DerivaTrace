from __future__ import annotations

import enum
from dataclasses import dataclass

from ._errors import (
    ValidationEquivalenceInputError,
    ValidationEquivalenceUnsupportedLevelError,
)

# ---------------------------------------------------------------------------
# Closed taxonomy enums (v1 frozen)
# ---------------------------------------------------------------------------


class ComparisonStatus(enum.Enum):
    """Closed enum of per-representation comparison outcomes."""

    EQUIVALENT = "equivalent"
    DIFFERENT = "different"
    NOT_COMPARABLE = "not_comparable"
    NOT_EVALUATED = "not_evaluated"


class ValidationOutcome(enum.Enum):
    """Closed enum of per-side validation outcomes."""

    VALID = "valid"
    INVALID = "invalid"


class FailureStage(enum.Enum):
    """Closed enum of captured-failure stages."""

    STRUCTURAL = "structural"
    CANONICAL = "canonical"
    PAYOFF = "payoff"


class CapturedFailureClassification(enum.Enum):
    """Closed enum of captured-failure classifications."""

    VALIDATION_FAILURE = "validation_failure"
    CANONICALIZATION_FAILURE = "canonicalization_failure"
    PAYOFF_COMPILATION_FAILURE = "payoff_compilation_failure"
    COMPLEXITY_FAILURE = "complexity_failure"
    COLLISION_FAILURE = "collision_failure"
    ENCODING_FAILURE = "encoding_failure"


class ComparisonReason(enum.Enum):
    """Closed enum of comparison-reason values."""

    UPSTREAM_STAGE_FAILURE = "upstream_stage_failure"
    REPRESENTATION_UNAVAILABLE = "representation_unavailable"
    RUNTIME_PRECONDITION_FAILED = "runtime_precondition_failed"
    SHALLOWER_LEVEL_REQUESTED = "shallower_level_requested"


# ---------------------------------------------------------------------------
# Existing exact enums (kept as-is)
# ---------------------------------------------------------------------------


class ValidationLevel(enum.Enum):
    """Closed, ordered enum of validation levels."""

    STRUCTURAL = "structural"
    CANONICAL = "canonical"
    PAYOFF = "payoff"


class DiffOperation(enum.Enum):
    """Closed enum of structural-diff operation types."""

    ADD = "add"
    REMOVE = "remove"
    CHANGE = "change"
    REPLACE = "replace"


class DiffSelection(enum.Enum):
    """Closed enum of diff representation selections."""

    CANONICAL = "canonical"
    PAYOFF = "payoff"
    NONE = "none"


class TruncationReason(enum.Enum):
    """Closed enum of output-limit truncation reasons."""

    ENTRY_LIMIT = "entry_limit"
    REPORT_BYTE_LIMIT = "report_byte_limit"
    PATH_LIMIT = "path_limit"


class UnavailableReason(enum.Enum):
    """Closed enum of reasons a diff is unavailable."""

    COMPARISON_LIMIT_EXCEEDED = "comparison_limit_exceeded"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_REPORT_SCHEMA_NAME: str = "derivatrace.validation-equivalence.report"
SUPPORTED_REPORT_SCHEMA_VERSION: str = "1.0.0"

DOMAIN_REPORT: str = "derivatrace.validation-equivalence.report"
REPORT_ID_PREFIX: str = "validation-equivalence:sha256:"

COMPILER_TAG: str = "derivatrace.validation-equivalence/1.0.0"

PROVENANCE_POLICY: str = "excluded_from_identity"


# ---------------------------------------------------------------------------
# Frozen upstream limit object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiffLimits:
    """Conservative, documented complexity limits for structural diffing.

    Admission limits (input validation, evaluated before diffing begins):
    - ``max_compared_bytes``: maximum combined structural bytes.
    - ``max_compared_nodes``: maximum combined reachable nodes.

    Output limits (entry emission, evaluated after successful admission):
    - ``max_entries``: maximum diff entries.
    - ``max_report_bytes``: maximum serialized report size.
    - ``max_path_length``: maximum path string length.
    """

    max_compared_bytes: int = 2_097_152
    max_compared_nodes: int = 4096
    max_entries: int = 1024
    max_report_bytes: int = 8_388_608
    max_path_length: int = 256

    def __post_init__(self) -> None:
        _validate_diff_limits(self)

    @classmethod
    def default(cls) -> DiffLimits:
        return DiffLimits()


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


def _validate_diff_limits(limits: object) -> None:
    """Validate a DiffLimits at the API boundary.

    Raises ValidationEquivalenceInputError if:
    - type(limits) is not exactly DiffLimits
    - any field is not an exact int (not bool)
    - any field is <= 0
    """
    if type(limits) is not DiffLimits:
        raise ValidationEquivalenceInputError("limits must be a DiffLimits")
    for field_name in (
        "max_compared_bytes",
        "max_compared_nodes",
        "max_entries",
        "max_report_bytes",
        "max_path_length",
    ):
        value = getattr(limits, field_name)
        if type(value) is not int or isinstance(value, bool):
            raise ValidationEquivalenceInputError(
                f"DiffLimits.{field_name} must be an exact int > 0"
            )
        if value <= 0:
            raise ValidationEquivalenceInputError(
                f"DiffLimits.{field_name} must be an int > 0"
            )


def _validate_validation_level(level: object) -> None:
    """Validate a ValidationLevel at the API boundary.

    Raises ValidationEquivalenceUnsupportedLevelError if level is not exactly
    a ValidationLevel enum member.
    """
    if type(level) is not ValidationLevel:
        raise ValidationEquivalenceUnsupportedLevelError(
            "level must be a ValidationLevel enum member"
        )


def _validate_diff_selection(selection: object) -> None:
    """Validate a DiffSelection at the API boundary.

    Raises ValidationEquivalenceInputError if selection is not exactly
    a DiffSelection enum member.
    """
    if type(selection) is not DiffSelection:
        raise ValidationEquivalenceInputError(
            "diff selection must be a DiffSelection enum member"
        )


def _validate_exact_enum(value: object, enum_type: type[enum.Enum], name: str) -> None:
    """Validate that ``value`` is exactly ``enum_type``.

    Rejects raw strings, subclasses and bool/int substitutes.
    """
    if type(value) is not enum_type:
        raise ValidationEquivalenceInputError(
            f"{name} must be a {enum_type.__name__} enum member"
        )


__all__: list[str] = [
    "COMPILER_TAG",
    "DOMAIN_REPORT",
    "PROVENANCE_POLICY",
    "REPORT_ID_PREFIX",
    "SUPPORTED_REPORT_SCHEMA_NAME",
    "SUPPORTED_REPORT_SCHEMA_VERSION",
    "CapturedFailureClassification",
    "ComparisonReason",
    "ComparisonStatus",
    "DiffLimits",
    "DiffOperation",
    "DiffSelection",
    "FailureStage",
    "TruncationReason",
    "UnavailableReason",
    "ValidationLevel",
    "ValidationOutcome",
    "_validate_diff_limits",
    "_validate_diff_selection",
    "_validate_exact_enum",
    "_validate_validation_level",
]
