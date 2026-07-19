from __future__ import annotations

from dataclasses import dataclass

from ._encoding import (
    structural_bytes,
)
from ._errors import (
    ValidationEquivalenceEncodingError,
    ValidationEquivalenceReportCollisionError,
)
from ._identity import report_identity
from ._records import (
    CompleteReport,
    DiffSummary,
    LimitsUsed,
    ProvenanceRecord,
    ReportSide,
    SchemaMetadataRecord,
)
from ._schema import (
    COMPILER_TAG,
    DiffSelection,
    ValidationLevel,
)


def build_report(
    *,
    requested_level: ValidationLevel,
    canonical_schema_version: str,
    payoff_schema_version: str,
    left_validation_outcome: str,
    right_validation_outcome: str,
    canonical_comparison_status: str,
    canonical_comparison_reason: str | None,
    payoff_comparison_status: str,
    payoff_comparison_reason: str | None,
    left: ReportSide,
    right: ReportSide,
    diff_representation: DiffSelection,
    diff_summary: DiffSummary,
    limits_used: LimitsUsed,
    schema_metadata: SchemaMetadataRecord,
    source_left_identity: str | None = None,
    source_right_identity: str | None = None,
) -> CompleteReport:
    """Construct and validate a validation-equivalence report.

    Computes structural_bytes and report_id from the complete structural
    projection (excluding provenance). If the report cannot be encoded or
    its identity cannot be produced, raises
    ValidationEquivalenceEncodingError with no report returned.

    Raises ValidationEquivalenceEncodingError on encoding failure.
    Raises ValidationEquivalenceReportCollisionError on identity collision.
    """
    provenance = ProvenanceRecord(
        compiler=COMPILER_TAG,
        policy="excluded_from_identity",
        source_left_identity=source_left_identity,
        source_right_identity=source_right_identity,
    )

    report = CompleteReport(
        report_id="",
        schema_name="derivatrace.validation-equivalence.report",
        schema_version="1.0.0",
        requested_level=requested_level.value,
        canonical_schema_version=canonical_schema_version,
        payoff_schema_version=payoff_schema_version,
        left_validation_outcome=left_validation_outcome,
        right_validation_outcome=right_validation_outcome,
        canonical_comparison_status=canonical_comparison_status,
        canonical_comparison_reason=canonical_comparison_reason,
        payoff_comparison_status=payoff_comparison_status,
        payoff_comparison_reason=payoff_comparison_reason,
        left=left,
        right=right,
        diff_representation=diff_representation.value,
        diff_summary=diff_summary,
        limits_used=limits_used,
        schema_metadata=schema_metadata,
        provenance=provenance,
    )

    try:
        s_bytes = structural_bytes(report)
    except Exception as exc:
        raise ValidationEquivalenceEncodingError(
            f"failed to compute structural bytes: {exc}"
        ) from exc

    rid = report_identity(s_bytes)

    return CompleteReport(
        report_id=rid,
        schema_name=report.schema_name,
        schema_version=report.schema_version,
        requested_level=report.requested_level,
        canonical_schema_version=report.canonical_schema_version,
        payoff_schema_version=report.payoff_schema_version,
        left_validation_outcome=report.left_validation_outcome,
        right_validation_outcome=report.right_validation_outcome,
        canonical_comparison_status=report.canonical_comparison_status,
        canonical_comparison_reason=report.canonical_comparison_reason,
        payoff_comparison_status=report.payoff_comparison_status,
        payoff_comparison_reason=report.payoff_comparison_reason,
        left=report.left,
        right=report.right,
        diff_representation=report.diff_representation,
        diff_summary=report.diff_summary,
        limits_used=report.limits_used,
        schema_metadata=report.schema_metadata,
        provenance=report.provenance,
    )


def _structural_bytes_for_identity(report: CompleteReport) -> bytes:
    """Compute the structural bytes used for identity of a CompleteReport."""
    return structural_bytes(report)


@dataclass(frozen=True)
class ValidationEquivalenceReport:
    """Immutable validation-equivalence report with identity-based equality.

    Equality: same report_id + same structural bytes -> True
    Equality: same report_id + different structural bytes -> raises
        ValidationEquivalenceReportCollisionError
    Equality: different report_id -> False
    __hash__: based on report_id
    """

    _report: CompleteReport
    _structural_bytes: bytes

    @property
    def report_id(self) -> str:
        return self._report.report_id

    @property
    def report(self) -> CompleteReport:
        return self._report

    @property
    def structural_bytes(self) -> bytes:
        return self._structural_bytes

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValidationEquivalenceReport):
            return NotImplemented
        if self._report.report_id != other._report.report_id:
            return False
        if self._structural_bytes != other._structural_bytes:
            raise ValidationEquivalenceReportCollisionError(
                "same report_id with different structural bytes"
            )
        return True

    def __hash__(self) -> int:
        return hash(self._report.report_id)

    def __repr__(self) -> str:
        return f"ValidationEquivalenceReport(report_id={self._report.report_id!r})"


def build_wrapped_report(
    *,
    requested_level: ValidationLevel,
    canonical_schema_version: str,
    payoff_schema_version: str,
    left_validation_outcome: str,
    right_validation_outcome: str,
    canonical_comparison_status: str,
    canonical_comparison_reason: str | None,
    payoff_comparison_status: str,
    payoff_comparison_reason: str | None,
    left: ReportSide,
    right: ReportSide,
    diff_representation: DiffSelection,
    diff_summary: DiffSummary,
    limits_used: LimitsUsed,
    schema_metadata: SchemaMetadataRecord,
    source_left_identity: str | None = None,
    source_right_identity: str | None = None,
) -> ValidationEquivalenceReport:
    """Construct a wrapped ValidationEquivalenceReport.

    Raises ValidationEquivalenceEncodingError on encoding failure.
    """
    report = build_report(
        requested_level=requested_level,
        canonical_schema_version=canonical_schema_version,
        payoff_schema_version=payoff_schema_version,
        left_validation_outcome=left_validation_outcome,
        right_validation_outcome=right_validation_outcome,
        canonical_comparison_status=canonical_comparison_status,
        canonical_comparison_reason=canonical_comparison_reason,
        payoff_comparison_status=payoff_comparison_status,
        payoff_comparison_reason=payoff_comparison_reason,
        left=left,
        right=right,
        diff_representation=diff_representation,
        diff_summary=diff_summary,
        limits_used=limits_used,
        schema_metadata=schema_metadata,
        source_left_identity=source_left_identity,
        source_right_identity=source_right_identity,
    )
    s_bytes = structural_bytes(report)
    return ValidationEquivalenceReport(report, s_bytes)


__all__: list[str] = [
    "ValidationEquivalenceReport",
    "build_report",
    "build_wrapped_report",
]
