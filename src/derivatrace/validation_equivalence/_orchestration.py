from __future__ import annotations

from derivatrace.canonical import (
    CanonicalizationError,
    CanonicalizationLimits,
    CanonicalSchemaVersion,
    canonicalize_contract,
)
from derivatrace.canonical._schema import (
    _validate_canonical_schema_version,
    _validate_canonicalization_limits,
)
from derivatrace.contracts import (
    Contract,
    ContractError,
    ValidationLimits,
    validate_contract,
)
from derivatrace.contracts._validation import (
    _validate_validation_limits_invariants,
)
from derivatrace.payoffgraph import (
    PayoffGraphError,
    PayoffGraphLimits,
    PayoffGraphSchemaVersion,
    compile_payoff_graph,
)
from derivatrace.payoffgraph._schema import (
    _validate_payoff_graph_limits,
    _validate_payoff_schema_version,
)

from ._errors import (
    ValidationEquivalenceComparisonError,
    ValidationEquivalenceInputError,
    ValidationEquivalenceMalformedRepresentationError,
)
from ._records import CapturedFailure, DiffSummary, LimitsUsed, ReportSide
from ._report import ValidationEquivalenceReport, _build_report
from ._schema import (
    CapturedFailureClassification,
    ComparisonReason,
    ComparisonStatus,
    DiffLimits,
    DiffSelection,
    FailureStage,
    ValidationLevel,
    ValidationOutcome,
    _validate_diff_limits,
    _validate_diff_selection,
    _validate_validation_level,
)


def _map_validation_error(exc: ContractError) -> CapturedFailure:
    """Map an upstream Stage 1A ContractError to a CapturedFailure.

    Uses the original error code and the correct classification for the
    error namespace.  ``ContractCycleError`` and ``ContractComplexityError``
    carry ``.complexity`` or ``.cycle`` suffixes and map to the
    corresponding ``CapturedFailureClassification``.  Other
    ``ContractValidationError`` and ``ContractInputError`` use the stage
    default.
    """
    code = exc.code
    classification: CapturedFailureClassification
    if code.endswith(".complexity"):
        classification = CapturedFailureClassification.COMPLEXITY_FAILURE
    elif code.endswith(".cycle"):
        classification = CapturedFailureClassification.VALIDATION_FAILURE
    else:
        classification = CapturedFailureClassification.VALIDATION_FAILURE
    return CapturedFailure(
        stage=FailureStage.STRUCTURAL,
        code=code,
        classification=classification,
    )


def _map_canonicalization_error(exc: CanonicalizationError) -> CapturedFailure:
    """Map an upstream Stage 1B-R1 CanonicalizationError to a CapturedFailure.

    Uses the original error code.  Complexity, cycle, encoding and collision
    codes carry their documented suffixes and map to the corresponding
    ``CapturedFailureClassification``.  Other canonicalization errors use
    the stage default.
    """
    code = exc.code
    classification: CapturedFailureClassification
    if code.endswith(".complexity"):
        classification = CapturedFailureClassification.COMPLEXITY_FAILURE
    elif code.endswith(".encoding"):
        classification = CapturedFailureClassification.ENCODING_FAILURE
    elif code.endswith(".collision"):
        classification = CapturedFailureClassification.COLLISION_FAILURE
    elif code.endswith(".cycle"):
        classification = CapturedFailureClassification.CANONICALIZATION_FAILURE
    else:
        classification = CapturedFailureClassification.CANONICALIZATION_FAILURE
    return CapturedFailure(
        stage=FailureStage.CANONICAL,
        code=code,
        classification=classification,
    )


def _map_payoff_error(exc: PayoffGraphError) -> CapturedFailure:
    """Map an upstream Stage 1B-R2 PayoffGraphError to a CapturedFailure.

    Uses the original error code.  Complexity, encoding and collision codes
    carry their documented suffixes and map to the corresponding
    ``CapturedFailureClassification``.  Other payoff errors use the stage
    default (``PAYOFF_COMPILATION_FAILURE``).
    """
    code = exc.code
    classification: CapturedFailureClassification
    if code.endswith(".complexity"):
        classification = CapturedFailureClassification.COMPLEXITY_FAILURE
    elif code.endswith(".encoding"):
        classification = CapturedFailureClassification.ENCODING_FAILURE
    elif code.endswith(".collision"):
        classification = CapturedFailureClassification.COLLISION_FAILURE
    else:
        classification = CapturedFailureClassification.PAYOFF_COMPILATION_FAILURE
    return CapturedFailure(
        stage=FailureStage.PAYOFF,
        code=code,
        classification=classification,
    )


def _validate_caller_config(
    *,
    canonical_schema_resolved: CanonicalSchemaVersion,
    payoff_schema_resolved: PayoffGraphSchemaVersion,
    canonicalization_limits_resolved: CanonicalizationLimits,
    payoff_limits_resolved: PayoffGraphLimits,
    validation_limits_resolved: ValidationLimits,
    diff_limits_resolved: DiffLimits,
) -> None:
    """Validate resolved caller-owned configuration using authoritative
    upstream validators.

    Malformed or unsupported state is translated into
    ``ValidationEquivalenceInputError`` with a stable generic message.
    Upstream exception chaining is suppressed with ``from None``.
    """
    try:
        _validate_canonical_schema_version(canonical_schema_resolved)
    except Exception:
        raise ValidationEquivalenceInputError(
            "canonical_schema is malformed or unsupported"
        ) from None

    try:
        _validate_payoff_schema_version(payoff_schema_resolved)
    except Exception:
        raise ValidationEquivalenceInputError(
            "payoff_schema is malformed or unsupported"
        ) from None

    try:
        _validate_canonicalization_limits(canonicalization_limits_resolved)
    except Exception:
        raise ValidationEquivalenceInputError(
            "canonicalization_limits is malformed"
        ) from None

    try:
        _validate_payoff_graph_limits(payoff_limits_resolved)
    except Exception:
        raise ValidationEquivalenceInputError("payoff_limits is malformed") from None

    try:
        _validate_validation_limits_invariants(validation_limits_resolved, ())
    except Exception:
        raise ValidationEquivalenceInputError(
            "validation_limits is malformed"
        ) from None

    try:
        _validate_diff_limits(diff_limits_resolved)
    except Exception:
        raise ValidationEquivalenceInputError("diff_limits is malformed") from None


def _compare_contracts(
    left: Contract,
    right: Contract,
    *,
    level: ValidationLevel,
    canonical_schema: CanonicalSchemaVersion | None = None,
    payoff_schema: PayoffGraphSchemaVersion | None = None,
    canonicalization_limits: CanonicalizationLimits | None = None,
    payoff_limits: PayoffGraphLimits | None = None,
    validation_limits: ValidationLimits | None = None,
    diff_selection: DiffSelection = DiffSelection.NONE,
    diff_limits: DiffLimits | None = None,
) -> ValidationEquivalenceReport:
    """Private R1B comparison orchestration.

    Validates caller-owned configuration, processes each side independently
    through structural, canonical and payoff levels as requested, computes
    comparison statuses, and constructs a self-validating report through the
    existing R1A report builder.

    This function is private and absent from ``__all__``.  It accepts only
    ``diff_selection=DiffSelection.NONE`` (R1 constraint).
    """
    # ------------------------------------------------------------------
    # 1. Caller-owned configuration validation (all before processing)
    # ------------------------------------------------------------------

    # Exact-type checks for root operands
    if not isinstance(left, Contract):
        raise ValidationEquivalenceInputError("left must be a Contract instance")
    if not isinstance(right, Contract):
        raise ValidationEquivalenceInputError("right must be a Contract instance")

    # Level validation (raises UnsupportedLevelError)
    _validate_validation_level(level)

    # Exact-type checks for optional configuration (before accessing fields)
    if (
        canonical_schema is not None
        and type(canonical_schema) is not CanonicalSchemaVersion
    ):
        raise ValidationEquivalenceInputError(
            "canonical_schema must be an exact CanonicalSchemaVersion or None"
        )
    if (
        payoff_schema is not None
        and type(payoff_schema) is not PayoffGraphSchemaVersion
    ):
        raise ValidationEquivalenceInputError(
            "payoff_schema must be an exact PayoffGraphSchemaVersion or None"
        )
    if (
        canonicalization_limits is not None
        and type(canonicalization_limits) is not CanonicalizationLimits
    ):
        raise ValidationEquivalenceInputError(
            "canonicalization_limits must be an exact CanonicalizationLimits or None"
        )
    if payoff_limits is not None and type(payoff_limits) is not PayoffGraphLimits:
        raise ValidationEquivalenceInputError(
            "payoff_limits must be an exact PayoffGraphLimits or None"
        )
    if (
        validation_limits is not None
        and type(validation_limits) is not ValidationLimits
    ):
        raise ValidationEquivalenceInputError(
            "validation_limits must be an exact ValidationLimits or None"
        )

    # Diff selection validation (exact type + R1 NONE-only constraint)
    _validate_diff_selection(diff_selection)
    if diff_selection is not DiffSelection.NONE:
        raise ValidationEquivalenceInputError("R1B requires diff_selection=none")

    if diff_limits is not None and type(diff_limits) is not DiffLimits:
        raise ValidationEquivalenceInputError(
            "diff_limits must be an exact DiffLimits or None"
        )

    # ------------------------------------------------------------------
    # 2. Resolve default schemas and limits
    # ------------------------------------------------------------------
    canonical_schema_resolved = (
        canonical_schema if canonical_schema is not None else CanonicalSchemaVersion()
    )
    payoff_schema_resolved = (
        payoff_schema if payoff_schema is not None else PayoffGraphSchemaVersion()
    )
    canonicalization_limits_resolved = (
        canonicalization_limits
        if canonicalization_limits is not None
        else CanonicalizationLimits.default()
    )
    payoff_limits_resolved = (
        payoff_limits if payoff_limits is not None else PayoffGraphLimits.default()
    )
    validation_limits_resolved = (
        validation_limits
        if validation_limits is not None
        else ValidationLimits.default()
    )
    diff_limits_resolved = (
        diff_limits if diff_limits is not None else DiffLimits.default()
    )

    # ------------------------------------------------------------------
    # 2b. Authoritative validation of resolved configuration
    # ------------------------------------------------------------------
    _validate_caller_config(
        canonical_schema_resolved=canonical_schema_resolved,
        payoff_schema_resolved=payoff_schema_resolved,
        canonicalization_limits_resolved=canonicalization_limits_resolved,
        payoff_limits_resolved=payoff_limits_resolved,
        validation_limits_resolved=validation_limits_resolved,
        diff_limits_resolved=diff_limits_resolved,
    )

    # ------------------------------------------------------------------
    # 3. Per-side independent processing
    # ------------------------------------------------------------------

    # Structural-level results
    left_validation_outcome = ValidationOutcome.VALID
    right_validation_outcome = ValidationOutcome.VALID
    left_structural_failures: list[CapturedFailure] = []
    right_structural_failures: list[CapturedFailure] = []

    left_structurally_valid = True
    right_structurally_valid = True

    # Left structural validation
    try:
        validate_contract(left, limits=validation_limits_resolved)
    except ContractError as exc:
        left_validation_outcome = ValidationOutcome.INVALID
        left_structurally_valid = False
        left_structural_failures.append(_map_validation_error(exc))
    except Exception:
        raise ValidationEquivalenceComparisonError(
            "internal comparison error"
        ) from None

    # Right structural validation
    try:
        validate_contract(right, limits=validation_limits_resolved)
    except ContractError as exc:
        right_validation_outcome = ValidationOutcome.INVALID
        right_structurally_valid = False
        right_structural_failures.append(_map_validation_error(exc))
    except Exception:
        raise ValidationEquivalenceComparisonError(
            "internal comparison error"
        ) from None

    # Canonical-level results
    left_canonical_identity: str | None = None
    right_canonical_identity: str | None = None
    left_canonically_valid = False
    right_canonically_valid = False
    left_canonical_failures: list[CapturedFailure] = []
    right_canonical_failures: list[CapturedFailure] = []

    # Canonical-level processing (level >= canonical, side structurally valid)
    if level is ValidationLevel.CANONICAL or level is ValidationLevel.PAYOFF:
        if left_structurally_valid:
            try:
                left_canonical = canonicalize_contract(
                    left,
                    schema=canonical_schema_resolved,
                    limits=canonicalization_limits_resolved,
                    validation_limits=validation_limits_resolved,
                )
                left_canonical_identity = left_canonical.identity
                left_canonically_valid = True
            except CanonicalizationError as exc:
                left_canonical_failures.append(_map_canonicalization_error(exc))
            except Exception:
                raise ValidationEquivalenceComparisonError(
                    "internal comparison error"
                ) from None

        if right_structurally_valid:
            try:
                right_canonical = canonicalize_contract(
                    right,
                    schema=canonical_schema_resolved,
                    limits=canonicalization_limits_resolved,
                    validation_limits=validation_limits_resolved,
                )
                right_canonical_identity = right_canonical.identity
                right_canonically_valid = True
            except CanonicalizationError as exc:
                right_canonical_failures.append(_map_canonicalization_error(exc))
            except Exception:
                raise ValidationEquivalenceComparisonError(
                    "internal comparison error"
                ) from None

    # Payoff-level results
    left_payoff_identity: str | None = None
    right_payoff_identity: str | None = None
    left_payoff_failures: list[CapturedFailure] = []
    right_payoff_failures: list[CapturedFailure] = []

    # Payoff-level processing (only if level == payoff and side is canonically valid)
    if level is ValidationLevel.PAYOFF:
        if left_canonically_valid:
            try:
                left_payoff_graph = compile_payoff_graph(
                    left,
                    canonical_schema=canonical_schema_resolved,
                    payoff_schema=payoff_schema_resolved,
                    canonicalization_limits=canonicalization_limits_resolved,
                    payoff_limits=payoff_limits_resolved,
                    validation_limits=validation_limits_resolved,
                )
                # Second-pass consistency: source_contract_identity must match
                if (
                    left_payoff_graph.source_contract_identity
                    != left_canonical_identity
                ):
                    raise ValidationEquivalenceMalformedRepresentationError(
                        "payoff_graph.source_contract_identity mismatch"
                    )
                left_payoff_identity = left_payoff_graph.identity
            except ValidationEquivalenceMalformedRepresentationError:
                raise
            except PayoffGraphError as exc:
                left_payoff_failures.append(_map_payoff_error(exc))
            except CanonicalizationError:
                raise ValidationEquivalenceComparisonError(
                    "internal second canonicalization failed"
                ) from None
            except Exception:
                raise ValidationEquivalenceComparisonError(
                    "internal comparison error"
                ) from None

        if right_canonically_valid:
            try:
                right_payoff_graph = compile_payoff_graph(
                    right,
                    canonical_schema=canonical_schema_resolved,
                    payoff_schema=payoff_schema_resolved,
                    canonicalization_limits=canonicalization_limits_resolved,
                    payoff_limits=payoff_limits_resolved,
                    validation_limits=validation_limits_resolved,
                )
                if (
                    right_payoff_graph.source_contract_identity
                    != right_canonical_identity
                ):
                    raise ValidationEquivalenceMalformedRepresentationError(
                        "payoff_graph.source_contract_identity mismatch"
                    )
                right_payoff_identity = right_payoff_graph.identity
            except ValidationEquivalenceMalformedRepresentationError:
                raise
            except PayoffGraphError as exc:
                right_payoff_failures.append(_map_payoff_error(exc))
            except CanonicalizationError:
                raise ValidationEquivalenceComparisonError(
                    "internal second canonicalization failed"
                ) from None
            except Exception:
                raise ValidationEquivalenceComparisonError(
                    "internal comparison error"
                ) from None

    # ------------------------------------------------------------------
    # 4. Comparison status calculation
    # ------------------------------------------------------------------

    # Canonical comparison
    canonical_comparison_status: ComparisonStatus
    canonical_comparison_reason: ComparisonReason | None = None

    if level is ValidationLevel.STRUCTURAL:
        canonical_comparison_status = ComparisonStatus.NOT_EVALUATED
        canonical_comparison_reason = ComparisonReason.SHALLOWER_LEVEL_REQUESTED
    elif left_canonical_identity is not None and right_canonical_identity is not None:
        if left_canonical_identity == right_canonical_identity:
            canonical_comparison_status = ComparisonStatus.EQUIVALENT
        else:
            canonical_comparison_status = ComparisonStatus.DIFFERENT
    else:
        canonical_comparison_status = ComparisonStatus.NOT_COMPARABLE
        canonical_comparison_reason = ComparisonReason.UPSTREAM_STAGE_FAILURE

    # Payoff comparison
    payoff_comparison_status: ComparisonStatus
    payoff_comparison_reason: ComparisonReason | None = None

    if level is not ValidationLevel.PAYOFF:
        payoff_comparison_status = ComparisonStatus.NOT_EVALUATED
        payoff_comparison_reason = ComparisonReason.SHALLOWER_LEVEL_REQUESTED
    elif left_payoff_identity is not None and right_payoff_identity is not None:
        if left_payoff_identity == right_payoff_identity:
            payoff_comparison_status = ComparisonStatus.EQUIVALENT
        else:
            payoff_comparison_status = ComparisonStatus.DIFFERENT
    else:
        payoff_comparison_status = ComparisonStatus.NOT_COMPARABLE
        payoff_comparison_reason = ComparisonReason.UPSTREAM_STAGE_FAILURE

    # ------------------------------------------------------------------
    # 5. Collect all per-side failures in deterministic order
    # ------------------------------------------------------------------

    left_all_failures = tuple(
        sorted(
            left_structural_failures + left_canonical_failures + left_payoff_failures,
            key=lambda f: (
                list(FailureStage).index(f.stage),
                f.code,
                f.classification.value,
            ),
        )
    )
    right_all_failures = tuple(
        sorted(
            right_structural_failures
            + right_canonical_failures
            + right_payoff_failures,
            key=lambda f: (
                list(FailureStage).index(f.stage),
                f.code,
                f.classification.value,
            ),
        )
    )

    # ------------------------------------------------------------------
    # 6. Report side construction
    # ------------------------------------------------------------------

    left_report_side = ReportSide(
        contract_identity=left_canonical_identity,
        payoff_graph_identity=left_payoff_identity,
        failures=left_all_failures,
    )
    right_report_side = ReportSide(
        contract_identity=right_canonical_identity,
        payoff_graph_identity=right_payoff_identity,
        failures=right_all_failures,
    )

    # ------------------------------------------------------------------
    # 7. LimitsUsed and SchemaMetadata
    # ------------------------------------------------------------------

    limits_used = LimitsUsed(
        validation=validation_limits_resolved,
        canonicalization=canonicalization_limits_resolved,
        payoff=payoff_limits_resolved,
        diff=diff_limits_resolved,
    )

    from ._records import SchemaMetadataRecord

    schema_metadata = SchemaMetadataRecord()

    # ------------------------------------------------------------------
    # 8. Provenance source identities (canonical identities where available)
    # ------------------------------------------------------------------

    source_left_identity = left_canonical_identity
    source_right_identity = right_canonical_identity

    # ------------------------------------------------------------------
    # 9. Report construction through the existing R1A builder
    # ------------------------------------------------------------------

    return _build_report(
        requested_level=level,
        canonical_schema_version=canonical_schema_resolved,
        payoff_schema_version=payoff_schema_resolved,
        left_validation_outcome=left_validation_outcome,
        right_validation_outcome=right_validation_outcome,
        canonical_comparison_status=canonical_comparison_status,
        canonical_comparison_reason=canonical_comparison_reason,
        payoff_comparison_status=payoff_comparison_status,
        payoff_comparison_reason=payoff_comparison_reason,
        left=left_report_side,
        right=right_report_side,
        diff_representation=DiffSelection.NONE,
        diff_summary=DiffSummary(),
        limits_used=limits_used,
        schema_metadata=schema_metadata,
        source_left_identity=source_left_identity,
        source_right_identity=source_right_identity,
    )


__all__: list[str] = []
