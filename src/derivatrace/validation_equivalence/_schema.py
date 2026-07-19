from __future__ import annotations

import enum
from dataclasses import dataclass

from ._errors import ValidationEquivalenceInputError


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


SUPPORTED_REPORT_SCHEMA_NAME: str = "derivatrace.validation-equivalence.report"
SUPPORTED_REPORT_SCHEMA_VERSION: str = "1.0.0"

DOMAIN_REPORT: str = "derivatrace.validation-equivalence.report"
REPORT_ID_PREFIX: str = "validation-equivalence:sha256:"

COMPILER_TAG: str = "derivatrace.validation-equivalence/1.0.0"


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


@dataclass(frozen=True)
class ValidationMetadata:
    """Schema metadata for the validation-equivalence report itself."""

    schema_name: str = SUPPORTED_REPORT_SCHEMA_NAME
    schema_version: str = SUPPORTED_REPORT_SCHEMA_VERSION


@dataclass(frozen=True)
class ReportSchemaMetadata:
    """Deterministic schema metadata recorded for reproducibility."""

    canonical_schema_name: str = "derivatrace.contract.canonical"
    canonical_schema_version: str = "1.0.0"
    canonical_node_identity_domain: str = "derivatrace.canonical.node"
    canonical_representation_identity_domain: str = "derivatrace.canonical.contract"
    payoff_schema_name: str = "derivatrace.payoffgraph"
    payoff_schema_version: str = "1.0.0"
    payoff_node_identity_domain: str = "derivatrace.payoffgraph.node"
    payoff_representation_identity_domain: str = "derivatrace.payoffgraph.graph"


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
        if type(value) is not int:
            raise ValidationEquivalenceInputError(
                f"DiffLimits.{field_name} must be an int > 0"
            )
        if value <= 0:
            raise ValidationEquivalenceInputError(
                f"DiffLimits.{field_name} must be an int > 0"
            )


def _validate_validation_level(level: object) -> None:
    """Validate a ValidationLevel at the API boundary.

    Raises ValidationEquivalenceInputError if level is not exactly
    a ValidationLevel enum member.
    """
    if type(level) is not ValidationLevel:
        raise ValidationEquivalenceInputError(
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


__all__: list[str] = [
    "COMPILER_TAG",
    "DOMAIN_REPORT",
    "REPORT_ID_PREFIX",
    "SUPPORTED_REPORT_SCHEMA_NAME",
    "SUPPORTED_REPORT_SCHEMA_VERSION",
    "DiffLimits",
    "DiffOperation",
    "DiffSelection",
    "ReportSchemaMetadata",
    "TruncationReason",
    "UnavailableReason",
    "ValidationLevel",
    "ValidationMetadata",
    "_validate_diff_limits",
    "_validate_diff_selection",
    "_validate_validation_level",
]
