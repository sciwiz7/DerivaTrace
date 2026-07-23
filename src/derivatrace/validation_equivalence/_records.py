from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from derivatrace.canonical import CanonicalizationLimits
from derivatrace.contracts import ValidationLimits
from derivatrace.payoffgraph import PayoffGraphLimits

from ._encoding import structural_bytes as _compute_structural_bytes
from ._errors import (
    ValidationEquivalenceInputError,
    ValidationEquivalenceReportCollisionError,
)
from ._identity import _safe_report_identity
from ._schema import (
    PROVENANCE_POLICY,
    CapturedFailureClassification,
    ComparisonReason,
    ComparisonStatus,
    DiffLimits,
    DiffOperation,
    DiffSelection,
    FailureStage,
    TruncationReason,
    UnavailableReason,
    ValidationLevel,
    ValidationOutcome,
    _validate_exact_enum,
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FAILURE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")

_FAILURE_STAGE_NAMESPACE: dict[str, tuple[str, ...]] = {
    "structural": (
        "contract.validation",
        "contract.input",
    ),
    "canonical": ("canonicalization",),
    "payoff": ("payoff_graph",),
}

_CODE_SUFFIX_CLASSIFICATION: dict[str, CapturedFailureClassification] = {
    ".complexity": CapturedFailureClassification.COMPLEXITY_FAILURE,
    ".collision": CapturedFailureClassification.COLLISION_FAILURE,
    ".encoding": CapturedFailureClassification.ENCODING_FAILURE,
}


# ---------------------------------------------------------------------------
# R1A diff invariant (shared by _StructuralPayload, CompleteReport, _build_report)
# ---------------------------------------------------------------------------


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
    if type(diff_representation) is not DiffSelection:
        raise ValidationEquivalenceInputError(
            "diff_representation must be a DiffSelection enum member"
        )
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


# ---------------------------------------------------------------------------
# Identity validation (full syntax, not prefixes alone)
# ---------------------------------------------------------------------------


def _validate_identity(value: str | None, allowed_prefix: str, name: str) -> None:
    """Validate full identity syntax: ``<prefix><64 lowercase hex>``."""
    if value is None:
        return
    if type(value) is not str:
        raise ValidationEquivalenceInputError(f"{name} must be a string or None")
    if not value.startswith(allowed_prefix):
        raise ValidationEquivalenceInputError(
            f"{name} must start with {allowed_prefix!r}"
        )
    suffix = value[len(allowed_prefix) :]
    if not _HEX64_RE.fullmatch(suffix):
        raise ValidationEquivalenceInputError(
            f"{name} must have exactly 64 lowercase hex characters after the prefix"
        )


def _validate_report_id_identity(value: str) -> None:
    """Validate the report_id identity field with full syntax."""
    if type(value) is not str:
        raise ValidationEquivalenceInputError(
            "CompleteReport.report_id must be a string"
        )
    if not value.startswith("validation-equivalence:sha256:"):
        raise ValidationEquivalenceInputError(
            "CompleteReport.report_id must start with 'validation-equivalence:sha256:'"
        )
    suffix = value[len("validation-equivalence:sha256:") :]
    if not _HEX64_RE.fullmatch(suffix):
        raise ValidationEquivalenceInputError(
            "CompleteReport.report_id must have exactly 64 lowercase hex "
            "characters after the prefix"
        )


# ---------------------------------------------------------------------------
# Status/reason coherence (single validator)
# ---------------------------------------------------------------------------


def validate_comparison_coherence(
    status: ComparisonStatus, reason: ComparisonReason | None
) -> None:
    """Validate the exact status/reason matrix.

    - equivalent -> reason None
    - different -> reason None
    - not_evaluated -> shallower_level_requested
    - not_comparable ->
        upstream_stage_failure
        representation_unavailable
        runtime_precondition_failed

    Rejects not_comparable + shallower_level_requested.
    """
    _validate_exact_enum(status, ComparisonStatus, "comparison_status")
    if reason is not None:
        _validate_exact_enum(reason, ComparisonReason, "reason")
    if (
        status is ComparisonStatus.EQUIVALENT or status is ComparisonStatus.DIFFERENT
    ) and reason is not None:
        raise ValidationEquivalenceInputError(
            f"comparison_status={status.value!r} requires reason=None"
        )
    if (
        status is ComparisonStatus.NOT_EVALUATED
        and reason is not ComparisonReason.SHALLOWER_LEVEL_REQUESTED
    ):
        raise ValidationEquivalenceInputError(
            "comparison_status=not_evaluated requires reason=shallower_level_requested"
        )
    if status is ComparisonStatus.NOT_COMPARABLE:
        if reason is None:
            raise ValidationEquivalenceInputError(
                "comparison_status=not_comparable requires a non-null reason"
            )
        if reason is ComparisonReason.SHALLOWER_LEVEL_REQUESTED:
            raise ValidationEquivalenceInputError(
                "comparison_status=not_comparable rejects reason="
                "shallower_level_requested"
            )


# ---------------------------------------------------------------------------
# Captured failure code validation
# ---------------------------------------------------------------------------


def _validate_failure_code(code: str, stage: FailureStage) -> None:
    """Validate captured-failure code is a stable ASCII namespaced code."""
    if type(code) is not str or not code:
        raise ValidationEquivalenceInputError(
            "CapturedFailure.code must be a non-empty string"
        )
    if not _FAILURE_CODE_RE.fullmatch(code):
        raise ValidationEquivalenceInputError(
            "CapturedFailure.code must match ^[a-z][a-z0-9_]*(?:\\.[a-z][a-z0-9_]*)+$"
        )
    ns_tuple = _FAILURE_STAGE_NAMESPACE[stage.value]
    matched = False
    for ns in ns_tuple:
        if code == ns or code.startswith(ns + "."):
            matched = True
            break
    if not matched:
        raise ValidationEquivalenceInputError(
            f"CapturedFailure.code for stage {stage.value!r} "
            "must match an accepted namespace"
        )


_STAGE_DEFAULT_CLASSIFICATION: dict[str, CapturedFailureClassification] = {
    "structural": CapturedFailureClassification.VALIDATION_FAILURE,
    "canonical": CapturedFailureClassification.CANONICALIZATION_FAILURE,
    "payoff": CapturedFailureClassification.PAYOFF_COMPILATION_FAILURE,
}


def _validate_classification_coherence(
    code: str,
    classification: CapturedFailureClassification,
    stage: FailureStage,
) -> None:
    """Reject contradictory code-suffix / classification pairings.

    Suffix rules take priority. If no suffix matches, the classification
    must match the stage default.
    """
    for suffix, required_cls in _CODE_SUFFIX_CLASSIFICATION.items():
        if code.endswith(suffix):
            if classification is not required_cls:
                raise ValidationEquivalenceInputError(
                    "CapturedFailure.classification contradicts code suffix"
                )
            return
    default_cls = _STAGE_DEFAULT_CLASSIFICATION.get(stage.value)
    if default_cls is not None and classification is not default_cls:
        raise ValidationEquivalenceInputError(
            "CapturedFailure.classification contradicts stage default"
        )


# ---------------------------------------------------------------------------
# Nested identity-bearing records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LimitsUsed:
    """Nested limit record using exact upstream types.

    The ``diff`` sub-record is the upstream frozen ``DiffLimits`` object.
    Serialization emits the exact nested JSON shape.
    """

    validation: ValidationLimits = field(default_factory=ValidationLimits)
    canonicalization: CanonicalizationLimits = field(
        default_factory=CanonicalizationLimits
    )
    payoff: PayoffGraphLimits = field(default_factory=PayoffGraphLimits)
    diff: DiffLimits = field(default_factory=DiffLimits)

    def __post_init__(self) -> None:
        if type(self.validation) is not ValidationLimits:
            raise ValidationEquivalenceInputError("LimitsUsed.validation malformed")
        if type(self.canonicalization) is not CanonicalizationLimits:
            raise ValidationEquivalenceInputError(
                "LimitsUsed.canonicalization malformed"
            )
        if type(self.payoff) is not PayoffGraphLimits:
            raise ValidationEquivalenceInputError("LimitsUsed.payoff malformed")
        if type(self.diff) is not DiffLimits:
            raise ValidationEquivalenceInputError("LimitsUsed.diff malformed")


@dataclass(frozen=True)
class CanonicalMetadata:
    """Canonical schema metadata sub-record."""

    schema_name: str = "derivatrace.contract.canonical"
    schema_version: str = "1.0.0"
    node_identity_domain: str = "derivatrace.canonical.node"
    representation_identity_domain: str = "derivatrace.canonical.contract"

    def __post_init__(self) -> None:
        if type(self.schema_name) is not str or self.schema_name != (
            "derivatrace.contract.canonical"
        ):
            raise ValidationEquivalenceInputError("CanonicalMetadata.schema_name exact")
        if type(self.schema_version) is not str or self.schema_version != "1.0.0":
            raise ValidationEquivalenceInputError(
                "CanonicalMetadata.schema_version exact"
            )
        if type(self.node_identity_domain) is not str or self.node_identity_domain != (
            "derivatrace.canonical.node"
        ):
            raise ValidationEquivalenceInputError(
                "CanonicalMetadata.node_identity_domain exact"
            )
        if type(self.representation_identity_domain) is not str or (
            self.representation_identity_domain != "derivatrace.canonical.contract"
        ):
            raise ValidationEquivalenceInputError(
                "CanonicalMetadata.representation_identity_domain exact"
            )


@dataclass(frozen=True)
class PayoffMetadata:
    """Payoff schema metadata sub-record."""

    schema_name: str = "derivatrace.payoffgraph"
    schema_version: str = "1.0.0"
    node_identity_domain: str = "derivatrace.payoffgraph.node"
    representation_identity_domain: str = "derivatrace.payoffgraph.graph"

    def __post_init__(self) -> None:
        if type(self.schema_name) is not str or self.schema_name != (
            "derivatrace.payoffgraph"
        ):
            raise ValidationEquivalenceInputError("PayoffMetadata.schema_name exact")
        if type(self.schema_version) is not str or self.schema_version != "1.0.0":
            raise ValidationEquivalenceInputError("PayoffMetadata.schema_version exact")
        if type(self.node_identity_domain) is not str or self.node_identity_domain != (
            "derivatrace.payoffgraph.node"
        ):
            raise ValidationEquivalenceInputError(
                "PayoffMetadata.node_identity_domain exact"
            )
        if type(self.representation_identity_domain) is not str or (
            self.representation_identity_domain != "derivatrace.payoffgraph.graph"
        ):
            raise ValidationEquivalenceInputError(
                "PayoffMetadata.representation_identity_domain exact"
            )


@dataclass(frozen=True)
class SchemaMetadataRecord:
    """Deterministic nested schema metadata recorded for reproducibility."""

    canonical: CanonicalMetadata = field(default_factory=CanonicalMetadata)
    payoff: PayoffMetadata = field(default_factory=PayoffMetadata)

    def __post_init__(self) -> None:
        if type(self.canonical) is not CanonicalMetadata:
            raise ValidationEquivalenceInputError("SchemaMetadataRecord.canonical")
        if type(self.payoff) is not PayoffMetadata:
            raise ValidationEquivalenceInputError("SchemaMetadataRecord.payoff")


def _validate_diff_scalar(value: object, name: str) -> None:
    """Validate that ``value`` is a non-bool-subclassed JSON scalar or None."""
    if value is None:
        return
    if type(value) is str or type(value) is int or type(value) is bool:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValidationEquivalenceInputError(f"{name} must not be nan or inf")
        return
    raise ValidationEquivalenceInputError(
        f"{name} must be an immutable JSON scalar or None"
    )


# ---------------------------------------------------------------------------
# Per-side and diff records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapturedFailure:
    """Single captured-failure record inside a per-side failures array.

    ``stage`` and ``classification`` are exact enum members. ``code`` is a
    non-empty stable ASCII namespaced code (never exception text).
    """

    stage: FailureStage
    code: str
    classification: CapturedFailureClassification

    def __post_init__(self) -> None:
        _validate_exact_enum(self.stage, FailureStage, "stage")
        _validate_failure_code(self.code, self.stage)
        _validate_exact_enum(
            self.classification, CapturedFailureClassification, "classification"
        )
        _validate_classification_coherence(self.code, self.classification, self.stage)


@dataclass(frozen=True)
class DiffEntry:
    """A single structural-diff entry (unused in R1A; reserved)."""

    path: str
    op: DiffOperation
    left_value: object = None
    right_value: object = None

    def __post_init__(self) -> None:
        if type(self.path) is not str or not self.path:
            raise ValidationEquivalenceInputError(
                "DiffEntry.path must be a non-empty string"
            )
        _validate_exact_enum(self.op, DiffOperation, "op")
        _validate_diff_scalar(self.left_value, "DiffEntry.left_value")
        _validate_diff_scalar(self.right_value, "DiffEntry.right_value")


@dataclass(frozen=True)
class DiffSummary:
    """Deterministic structural-diff summary."""

    entries: tuple[DiffEntry, ...] = ()
    truncated: bool = False
    truncation_reason: TruncationReason | None = None
    unavailable_reason: UnavailableReason | None = None

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple:
            raise ValidationEquivalenceInputError(
                "DiffSummary.entries must be an exact tuple"
            )
        for e in self.entries:
            if type(e) is not DiffEntry:
                raise ValidationEquivalenceInputError(
                    "DiffSummary.entries must contain only DiffEntry records"
                )
            if self.entries.count(e) > 1:
                raise ValidationEquivalenceInputError(
                    "DiffSummary.entries must not contain duplicates"
                )
        if type(self.truncated) is not bool:
            raise ValidationEquivalenceInputError(
                "DiffSummary.truncated must be an exact bool"
            )
        if self.truncation_reason is not None:
            _validate_exact_enum(
                self.truncation_reason, TruncationReason, "truncation_reason"
            )
        if self.unavailable_reason is not None:
            _validate_exact_enum(
                self.unavailable_reason, UnavailableReason, "unavailable_reason"
            )


@dataclass(frozen=True)
class ReportSide:
    """Per-side structured capture in the report."""

    contract_identity: str | None = None
    payoff_graph_identity: str | None = None
    failures: tuple[CapturedFailure, ...] = ()

    def __post_init__(self) -> None:
        _validate_identity(
            self.contract_identity, "canonical:sha256:", "ReportSide.contract_identity"
        )
        _validate_identity(
            self.payoff_graph_identity,
            "payoffgraph:sha256:",
            "ReportSide.payoff_graph_identity",
        )
        if type(self.failures) is not tuple:
            raise ValidationEquivalenceInputError(
                "ReportSide.failures must be an exact tuple"
            )
        seen: set[tuple[str, str, str]] = set()
        ordered: list[CapturedFailure] = []
        for f in self.failures:
            if type(f) is not CapturedFailure:
                raise ValidationEquivalenceInputError(
                    "ReportSide.failures must contain only CapturedFailure records"
                )
            key = (f.stage.value, f.code, f.classification.value)
            if key in seen:
                raise ValidationEquivalenceInputError(
                    "duplicate CapturedFailure records are rejected"
                )
            seen.add(key)
            ordered.append(f)
        expected = tuple(
            sorted(
                ordered,
                key=lambda c: (
                    list(FailureStage).index(c.stage),
                    c.code,
                    c.classification.value,
                ),
            )
        )
        if tuple(ordered) != expected:
            raise ValidationEquivalenceInputError(
                "ReportSide.failures must be in deterministic stage/code/"
                "classification order"
            )


# ---------------------------------------------------------------------------
# Provenance record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProvenanceRecord:
    """Compiler tag, exclusion policy, and source canonical identities."""

    compiler: str = "derivatrace.validation-equivalence/1.0.0"
    policy: str = PROVENANCE_POLICY
    source_left_identity: str | None = None
    source_right_identity: str | None = None

    def __post_init__(self) -> None:
        if type(self.compiler) is not str or self.compiler != (
            "derivatrace.validation-equivalence/1.0.0"
        ):
            raise ValidationEquivalenceInputError(
                "ProvenanceRecord.compiler must be exact: "
                "derivatrace.validation-equivalence/1.0.0"
            )
        if type(self.policy) is not str or self.policy != PROVENANCE_POLICY:
            raise ValidationEquivalenceInputError(
                f"ProvenanceRecord.policy must be exact: {PROVENANCE_POLICY}"
            )
        _validate_identity(
            self.source_left_identity,
            "canonical:sha256:",
            "ProvenanceRecord.source_left_identity",
        )
        _validate_identity(
            self.source_right_identity,
            "canonical:sha256:",
            "ProvenanceRecord.source_right_identity",
        )


# ---------------------------------------------------------------------------
# Structural payload (private, no report_id)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _StructuralPayload:
    """Private draft payload carrying all fields needed for structural bytes.

    This avoids constructing a CompleteReport with an empty report_id.
    """

    schema_name: str
    schema_version: str
    requested_level: ValidationLevel
    canonical_schema_version: str
    payoff_schema_version: str
    left_validation_outcome: ValidationOutcome
    right_validation_outcome: ValidationOutcome
    canonical_comparison_status: ComparisonStatus
    canonical_comparison_reason: ComparisonReason | None
    payoff_comparison_status: ComparisonStatus
    payoff_comparison_reason: ComparisonReason | None
    left: ReportSide
    right: ReportSide
    diff_representation: DiffSelection
    diff_summary: DiffSummary
    limits_used: LimitsUsed
    schema_metadata: SchemaMetadataRecord

    def __post_init__(self) -> None:
        if type(self.schema_name) is not str or self.schema_name != (
            "derivatrace.validation-equivalence.report"
        ):
            raise ValidationEquivalenceInputError(
                "_StructuralPayload.schema_name must be exact: "
                "derivatrace.validation-equivalence.report"
            )
        if type(self.schema_version) is not str or self.schema_version != "1.0.0":
            raise ValidationEquivalenceInputError(
                "_StructuralPayload.schema_version must be exact: 1.0.0"
            )
        _validate_exact_enum(self.requested_level, ValidationLevel, "requested_level")
        if type(self.canonical_schema_version) is not str:
            raise ValidationEquivalenceInputError(
                "_StructuralPayload.canonical_schema_version must be a string"
            )
        if self.canonical_schema_version != "1.0.0":
            raise ValidationEquivalenceInputError(
                "_StructuralPayload.canonical_schema_version must be exact: 1.0.0"
            )
        if type(self.payoff_schema_version) is not str:
            raise ValidationEquivalenceInputError(
                "_StructuralPayload.payoff_schema_version must be a string"
            )
        if self.payoff_schema_version != "1.0.0":
            raise ValidationEquivalenceInputError(
                "_StructuralPayload.payoff_schema_version must be exact: 1.0.0"
            )
        _validate_exact_enum(
            self.left_validation_outcome, ValidationOutcome, "left_validation_outcome"
        )
        _validate_exact_enum(
            self.right_validation_outcome,
            ValidationOutcome,
            "right_validation_outcome",
        )
        _validate_exact_enum(
            self.canonical_comparison_status,
            ComparisonStatus,
            "canonical_comparison_status",
        )
        if self.canonical_comparison_reason is not None:
            _validate_exact_enum(
                self.canonical_comparison_reason,
                ComparisonReason,
                "canonical_comparison_reason",
            )
        _validate_exact_enum(
            self.payoff_comparison_status,
            ComparisonStatus,
            "payoff_comparison_status",
        )
        if self.payoff_comparison_reason is not None:
            _validate_exact_enum(
                self.payoff_comparison_reason,
                ComparisonReason,
                "payoff_comparison_reason",
            )
        validate_comparison_coherence(
            self.canonical_comparison_status, self.canonical_comparison_reason
        )
        validate_comparison_coherence(
            self.payoff_comparison_status, self.payoff_comparison_reason
        )
        _validate_exact_enum(
            self.diff_representation, DiffSelection, "diff_representation"
        )
        if type(self.diff_summary) is not DiffSummary:
            raise ValidationEquivalenceInputError("diff_summary must be a DiffSummary")
        if type(self.left) is not ReportSide:
            raise ValidationEquivalenceInputError("left must be a ReportSide")
        if type(self.right) is not ReportSide:
            raise ValidationEquivalenceInputError("right must be a ReportSide")
        if type(self.limits_used) is not LimitsUsed:
            raise ValidationEquivalenceInputError("limits_used must be a LimitsUsed")
        if type(self.schema_metadata) is not SchemaMetadataRecord:
            raise ValidationEquivalenceInputError(
                "schema_metadata must be a SchemaMetadataRecord"
            )
        _validate_r1a_diff_invariant(self.diff_representation, self.diff_summary)


# ---------------------------------------------------------------------------
# Complete report record (identity-bearing, exact enum types internally)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompleteReport:
    """Complete validation-equivalence report (immutable).

    Identity-bearing fields use exact enum types internally; serialization
    emits their ``.value`` strings. This is the structural projection used
    for report_id computation. Provenance is excluded from the structural
    projection (section 7).
    """

    report_id: str
    schema_name: str
    schema_version: str
    requested_level: ValidationLevel
    canonical_schema_version: str
    payoff_schema_version: str
    left_validation_outcome: ValidationOutcome
    right_validation_outcome: ValidationOutcome
    canonical_comparison_status: ComparisonStatus
    canonical_comparison_reason: ComparisonReason | None
    payoff_comparison_status: ComparisonStatus
    payoff_comparison_reason: ComparisonReason | None
    left: ReportSide
    right: ReportSide
    diff_representation: DiffSelection
    diff_summary: DiffSummary
    limits_used: LimitsUsed
    schema_metadata: SchemaMetadataRecord
    provenance: ProvenanceRecord

    def __post_init__(self) -> None:
        _validate_report_id_identity(self.report_id)
        if type(self.schema_name) is not str or self.schema_name != (
            "derivatrace.validation-equivalence.report"
        ):
            raise ValidationEquivalenceInputError(
                "CompleteReport.schema_name must be exact: "
                "derivatrace.validation-equivalence.report"
            )
        if type(self.schema_version) is not str or self.schema_version != "1.0.0":
            raise ValidationEquivalenceInputError(
                "CompleteReport.schema_version must be exact: 1.0.0"
            )
        _validate_exact_enum(self.requested_level, ValidationLevel, "requested_level")
        if type(self.canonical_schema_version) is not str:
            raise ValidationEquivalenceInputError(
                "CompleteReport.canonical_schema_version must be a string"
            )
        if self.canonical_schema_version != "1.0.0":
            raise ValidationEquivalenceInputError(
                "CompleteReport.canonical_schema_version must be exact: 1.0.0"
            )
        if type(self.payoff_schema_version) is not str:
            raise ValidationEquivalenceInputError(
                "CompleteReport.payoff_schema_version must be a string"
            )
        if self.payoff_schema_version != "1.0.0":
            raise ValidationEquivalenceInputError(
                "CompleteReport.payoff_schema_version must be exact: 1.0.0"
            )
        _validate_exact_enum(
            self.left_validation_outcome, ValidationOutcome, "left_validation_outcome"
        )
        _validate_exact_enum(
            self.right_validation_outcome,
            ValidationOutcome,
            "right_validation_outcome",
        )
        _validate_exact_enum(
            self.canonical_comparison_status,
            ComparisonStatus,
            "canonical_comparison_status",
        )
        if self.canonical_comparison_reason is not None:
            _validate_exact_enum(
                self.canonical_comparison_reason,
                ComparisonReason,
                "canonical_comparison_reason",
            )
        _validate_exact_enum(
            self.payoff_comparison_status,
            ComparisonStatus,
            "payoff_comparison_status",
        )
        if self.payoff_comparison_reason is not None:
            _validate_exact_enum(
                self.payoff_comparison_reason,
                ComparisonReason,
                "payoff_comparison_reason",
            )
        validate_comparison_coherence(
            self.canonical_comparison_status, self.canonical_comparison_reason
        )
        validate_comparison_coherence(
            self.payoff_comparison_status, self.payoff_comparison_reason
        )
        _validate_exact_enum(
            self.diff_representation, DiffSelection, "diff_representation"
        )
        if type(self.diff_summary) is not DiffSummary:
            raise ValidationEquivalenceInputError("diff_summary must be a DiffSummary")
        if type(self.left) is not ReportSide:
            raise ValidationEquivalenceInputError("left must be a ReportSide")
        if type(self.right) is not ReportSide:
            raise ValidationEquivalenceInputError("right must be a ReportSide")
        if type(self.limits_used) is not LimitsUsed:
            raise ValidationEquivalenceInputError("limits_used must be a LimitsUsed")
        if type(self.schema_metadata) is not SchemaMetadataRecord:
            raise ValidationEquivalenceInputError(
                "schema_metadata must be a SchemaMetadataRecord"
            )
        if type(self.provenance) is not ProvenanceRecord:
            raise ValidationEquivalenceInputError(
                "provenance must be a ProvenanceRecord"
            )
        _validate_r1a_diff_invariant(self.diff_representation, self.diff_summary)
        s_bytes = _compute_structural_bytes(self)
        recomputed_rid = _safe_report_identity(s_bytes)
        if recomputed_rid != self.report_id:
            raise ValidationEquivalenceReportCollisionError(
                "failed to produce report identity"
            )


__all__: list[str] = [
    "CanonicalMetadata",
    "CanonicalizationLimits",
    "CapturedFailure",
    "CompleteReport",
    "DiffEntry",
    "DiffLimits",
    "DiffSummary",
    "LimitsUsed",
    "PayoffGraphLimits",
    "PayoffMetadata",
    "ProvenanceRecord",
    "ReportSide",
    "SchemaMetadataRecord",
    "ValidationLimits",
    "_StructuralPayload",
    "_validate_classification_coherence",
    "_validate_failure_code",
    "_validate_identity",
    "_validate_r1a_diff_invariant",
    "_validate_report_id_identity",
    "validate_comparison_coherence",
]
