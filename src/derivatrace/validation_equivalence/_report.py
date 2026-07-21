from __future__ import annotations

from dataclasses import dataclass, field

from derivatrace.canonical import CanonicalSchemaVersion
from derivatrace.payoffgraph import PayoffGraphSchemaVersion

from ._encoding import encode_report as _encode_report
from ._encoding import structural_bytes
from ._errors import (
    ValidationEquivalenceEncodingError,
    ValidationEquivalenceInputError,
    ValidationEquivalenceReportCollisionError,
)
from ._identity import report_identity as _report_identity
from ._records import (
    CompleteReport,
    DiffSummary,
    LimitsUsed,
    ProvenanceRecord,
    ReportSide,
    SchemaMetadataRecord,
    _StructuralPayload,
)
from ._schema import (
    COMPILER_TAG,
    ComparisonReason,
    ComparisonStatus,
    DiffSelection,
    ValidationLevel,
    ValidationOutcome,
    _validate_diff_selection,
    _validate_exact_enum,
    _validate_validation_level,
)


def _safe_report_identity(structural_bytes: bytes) -> str:
    """Single private helper wrapping ``report_identity``.

    Normalizes any internal failure into
    ``ValidationEquivalenceEncodingError`` with a fixed message.
    """
    try:
        return _report_identity(structural_bytes)
    except Exception as exc:
        raise ValidationEquivalenceEncodingError(
            "failed to compute report identity"
        ) from exc


def _validate_r1a_diff_invariant(
    diff_representation: DiffSelection,
    diff_summary: DiffSummary,
) -> None:
    """Enforce the exact R1A diff invariant.

    The R1A factory may construct only:
    - DiffSelection.NONE
    - entries == ()
    - truncated is False
    - truncation_reason is None
    - unavailable_reason is None
    """
    _validate_diff_selection(diff_representation)
    if diff_representation is not DiffSelection.NONE:
        raise ValidationEquivalenceInputError("R1A requires diff_representation=none")
    if type(diff_summary) is not DiffSummary:
        raise ValidationEquivalenceInputError("diff_summary must be a DiffSummary")
    if diff_summary.entries != ():
        raise ValidationEquivalenceInputError(
            "R1A requires diff_summary.entries to be empty"
        )
    if diff_summary.truncated is not False:
        raise ValidationEquivalenceInputError(
            "R1A requires diff_summary.truncated=False"
        )
    if diff_summary.truncation_reason is not None:
        raise ValidationEquivalenceInputError(
            "R1A requires diff_summary.truncation_reason=None"
        )
    if diff_summary.unavailable_reason is not None:
        raise ValidationEquivalenceInputError(
            "R1A requires diff_summary.unavailable_reason=None"
        )


def _validate_record_types(
    *,
    left_validation_outcome: ValidationOutcome,
    right_validation_outcome: ValidationOutcome,
    canonical_comparison_status: ComparisonStatus,
    canonical_comparison_reason: ComparisonReason | None,
    payoff_comparison_status: ComparisonStatus,
    payoff_comparison_reason: ComparisonReason | None,
    left: ReportSide,
    right: ReportSide,
    limits_used: LimitsUsed,
    schema_metadata: SchemaMetadataRecord,
) -> None:
    """Validate exact enum types of all identity-bearing fields."""
    _validate_exact_enum(
        left_validation_outcome, ValidationOutcome, "left_validation_outcome"
    )
    _validate_exact_enum(
        right_validation_outcome, ValidationOutcome, "right_validation_outcome"
    )
    _validate_exact_enum(
        canonical_comparison_status, ComparisonStatus, "canonical_comparison_status"
    )
    if canonical_comparison_reason is not None:
        _validate_exact_enum(
            canonical_comparison_reason, ComparisonReason, "canonical_comparison_reason"
        )
    _validate_exact_enum(
        payoff_comparison_status, ComparisonStatus, "payoff_comparison_status"
    )
    if payoff_comparison_reason is not None:
        _validate_exact_enum(
            payoff_comparison_reason, ComparisonReason, "payoff_comparison_reason"
        )
    if type(left) is not ReportSide:
        raise ValidationEquivalenceInputError("left must be a ReportSide")
    if type(right) is not ReportSide:
        raise ValidationEquivalenceInputError("right must be a ReportSide")
    if type(limits_used) is not LimitsUsed:
        raise ValidationEquivalenceInputError("limits_used must be a LimitsUsed")
    if type(schema_metadata) is not SchemaMetadataRecord:
        raise ValidationEquivalenceInputError(
            "schema_metadata must be a SchemaMetadataRecord"
        )


def _build_report(
    *,
    requested_level: ValidationLevel,
    canonical_schema_version: CanonicalSchemaVersion,
    payoff_schema_version: PayoffGraphSchemaVersion,
    left_validation_outcome: ValidationOutcome,
    right_validation_outcome: ValidationOutcome,
    canonical_comparison_status: ComparisonStatus,
    canonical_comparison_reason: ComparisonReason | None,
    payoff_comparison_status: ComparisonStatus,
    payoff_comparison_reason: ComparisonReason | None,
    left: ReportSide,
    right: ReportSide,
    diff_representation: DiffSelection,
    diff_summary: DiffSummary,
    limits_used: LimitsUsed,
    schema_metadata: SchemaMetadataRecord,
    source_left_identity: str | None = None,
    source_right_identity: str | None = None,
) -> ValidationEquivalenceReport:
    """Single validated report-construction path.

    Required sequence:
    1. validate all factory inputs;
    2. create structural payload;
    3. encode structural bytes;
    4. compute report_id;
    5. create final CompleteReport carrying the exact valid report_id;
    6. recompute and verify structural bytes and identity;
    7. encode complete report bytes;
    8. return ValidationEquivalenceReport retaining exact immutable
       structural and complete bytes.
    """
    _validate_validation_level(requested_level)
    _validate_r1a_diff_invariant(diff_representation, diff_summary)
    _validate_record_types(
        left_validation_outcome=left_validation_outcome,
        right_validation_outcome=right_validation_outcome,
        canonical_comparison_status=canonical_comparison_status,
        canonical_comparison_reason=canonical_comparison_reason,
        payoff_comparison_status=payoff_comparison_status,
        payoff_comparison_reason=payoff_comparison_reason,
        left=left,
        right=right,
        limits_used=limits_used,
        schema_metadata=schema_metadata,
    )
    if type(canonical_schema_version) is not CanonicalSchemaVersion:
        raise ValidationEquivalenceInputError(
            "canonical_schema_version must be an exact CanonicalSchemaVersion"
        )
    if type(payoff_schema_version) is not PayoffGraphSchemaVersion:
        raise ValidationEquivalenceInputError(
            "payoff_schema_version must be an exact PayoffGraphSchemaVersion"
        )

    canonical_version_str = canonical_schema_version.version
    payoff_version_str = payoff_schema_version.version

    provenance = ProvenanceRecord(
        compiler=COMPILER_TAG,
        policy="excluded_from_identity",
        source_left_identity=source_left_identity,
        source_right_identity=source_right_identity,
    )

    # Step 2: create structural payload (no report_id)
    payload = _StructuralPayload(
        schema_name="derivatrace.validation-equivalence.report",
        schema_version="1.0.0",
        requested_level=requested_level,
        canonical_schema_version=canonical_version_str,
        payoff_schema_version=payoff_version_str,
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
    )

    # Step 3: encode structural bytes
    try:
        s_bytes = structural_bytes(payload)
    except Exception as exc:
        raise ValidationEquivalenceEncodingError(
            "failed to encode structural projection"
        ) from exc

    # Step 4: compute report_id
    rid = _safe_report_identity(s_bytes)

    # Step 5: create final CompleteReport carrying the exact valid report_id
    final_report = CompleteReport(
        report_id=rid,
        schema_name=payload.schema_name,
        schema_version=payload.schema_version,
        requested_level=payload.requested_level,
        canonical_schema_version=payload.canonical_schema_version,
        payoff_schema_version=payload.payoff_schema_version,
        left_validation_outcome=payload.left_validation_outcome,
        right_validation_outcome=payload.right_validation_outcome,
        canonical_comparison_status=payload.canonical_comparison_status,
        canonical_comparison_reason=payload.canonical_comparison_reason,
        payoff_comparison_status=payload.payoff_comparison_status,
        payoff_comparison_reason=payload.payoff_comparison_reason,
        left=payload.left,
        right=payload.right,
        diff_representation=payload.diff_representation,
        diff_summary=payload.diff_summary,
        limits_used=payload.limits_used,
        schema_metadata=payload.schema_metadata,
        provenance=provenance,
    )

    # Step 6: recompute and verify structural bytes and identity
    try:
        recomputed_s = structural_bytes(final_report)
    except Exception as exc:
        raise ValidationEquivalenceEncodingError(
            "failed to encode structural projection"
        ) from exc
    if recomputed_s != s_bytes:
        raise ValidationEquivalenceEncodingError(
            "structural bytes mismatch: report may be forged"
        )
    recomputed_rid = _safe_report_identity(recomputed_s)
    if recomputed_rid != rid:
        raise ValidationEquivalenceEncodingError(
            "report_id mismatch: report may be forged"
        )

    # Step 7: encode complete report bytes
    try:
        r_bytes = _encode_report(final_report)
    except Exception as exc:
        raise ValidationEquivalenceEncodingError(
            "failed to encode complete report"
        ) from exc

    # Step 8: return ValidationEquivalenceReport
    return ValidationEquivalenceReport(final_report, s_bytes, r_bytes)


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
    _report_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        """Verify identity integrity of the stored report.

        Recompute and verify:
        - stored structural bytes equal recomputed structural bytes;
        - stored report_id equals report_identity(structural bytes);
        - stored complete bytes equal encode_report(final report).
        """
        if type(self._report) is not CompleteReport:
            raise ValidationEquivalenceInputError(
                "ValidationEquivalenceReport requires a CompleteReport"
            )
        if type(self._structural_bytes) is not bytes:
            raise ValidationEquivalenceInputError(
                "ValidationEquivalenceReport requires exact bytes for structural_bytes"
            )
        if type(self._report_bytes) is not bytes:
            raise ValidationEquivalenceInputError(
                "ValidationEquivalenceReport requires exact bytes for report_bytes"
            )
        recomputed_s = structural_bytes(self._report)
        if self._structural_bytes != recomputed_s:
            raise ValidationEquivalenceEncodingError(
                "structural bytes mismatch: report may be forged"
            )
        recomputed_rid = _safe_report_identity(self._structural_bytes)
        if self._report.report_id != recomputed_rid:
            raise ValidationEquivalenceEncodingError(
                "report_id mismatch: report may be forged"
            )
        try:
            recomputed_rb = _encode_report(self._report)
        except Exception as exc:
            raise ValidationEquivalenceEncodingError(
                "failed to encode complete report"
            ) from exc
        if self._report_bytes != recomputed_rb:
            raise ValidationEquivalenceEncodingError(
                "complete report bytes mismatch: report may be forged"
            )

    @property
    def report_id(self) -> str:
        return self._report.report_id

    @property
    def report(self) -> CompleteReport:
        return self._report

    @property
    def structural_bytes(self) -> bytes:
        return self._structural_bytes

    @property
    def report_bytes(self) -> bytes:
        return self._report_bytes

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


__all__: list[str] = [
    "ValidationEquivalenceReport",
    "_build_report",
    "structural_bytes",
]
