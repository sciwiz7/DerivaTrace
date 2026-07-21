from __future__ import annotations

import enum

import pytest

from derivatrace.contracts._errors import DerivaTraceError
from derivatrace.validation_equivalence._errors import (
    ValidationEquivalenceEncodingError,
    ValidationEquivalenceError,
    ValidationEquivalenceInputError,
    ValidationEquivalenceMalformedRepresentationError,
    ValidationEquivalenceReportCollisionError,
)
from derivatrace.validation_equivalence._records import (
    validate_comparison_coherence,
)
from derivatrace.validation_equivalence._schema import (
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
    _validate_diff_limits,
    _validate_diff_selection,
    _validate_exact_enum,
    _validate_validation_level,
)


class TestErrorHierarchy:
    def test_base_derives_from_derivatrace_error(self) -> None:
        assert issubclass(ValidationEquivalenceError, DerivaTraceError)

    def test_input_error_derives_from_base(self) -> None:
        assert issubclass(ValidationEquivalenceInputError, ValidationEquivalenceError)

    def test_encoding_error_derives_from_base(self) -> None:
        assert issubclass(
            ValidationEquivalenceEncodingError, ValidationEquivalenceError
        )

    def test_collision_error_derives_from_base(self) -> None:
        assert issubclass(
            ValidationEquivalenceReportCollisionError, ValidationEquivalenceError
        )

    def test_malformed_repr_error_derives_from_base(self) -> None:
        assert issubclass(
            ValidationEquivalenceMalformedRepresentationError,
            ValidationEquivalenceError,
        )

    def test_no_complexity_error(self) -> None:
        """ValidationEquivalenceComplexityError is absent from the v1 taxonomy."""
        import derivatrace.validation_equivalence._errors as err_mod

        assert not hasattr(err_mod, "ValidationEquivalenceComplexityError")

    def test_error_codes(self) -> None:
        assert ValidationEquivalenceError.code == "validation_equivalence.error"
        assert ValidationEquivalenceInputError.code == "validation_equivalence.input"
        assert (
            ValidationEquivalenceEncodingError.code == "validation_equivalence.encoding"
        )
        assert (
            ValidationEquivalenceReportCollisionError.code
            == "validation_equivalence.report_collision"
        )


class TestNewEnums:
    """Test frozen closed taxonomies added in R1A."""

    def test_comparison_status_is_enum(self) -> None:
        assert issubclass(ComparisonStatus, enum.Enum)

    def test_comparison_status_values(self) -> None:
        assert ComparisonStatus.EQUIVALENT.value == "equivalent"
        assert ComparisonStatus.DIFFERENT.value == "different"
        assert ComparisonStatus.NOT_COMPARABLE.value == "not_comparable"
        assert ComparisonStatus.NOT_EVALUATED.value == "not_evaluated"

    def test_comparison_status_closed(self) -> None:
        assert len(ComparisonStatus) == 4

    def test_validation_outcome_is_enum(self) -> None:
        assert issubclass(ValidationOutcome, enum.Enum)

    def test_validation_outcome_values(self) -> None:
        assert ValidationOutcome.VALID.value == "valid"
        assert ValidationOutcome.INVALID.value == "invalid"

    def test_validation_outcome_closed(self) -> None:
        assert len(ValidationOutcome) == 2

    def test_failure_stage_is_enum(self) -> None:
        assert issubclass(FailureStage, enum.Enum)

    def test_failure_stage_values(self) -> None:
        assert FailureStage.STRUCTURAL.value == "structural"
        assert FailureStage.CANONICAL.value == "canonical"
        assert FailureStage.PAYOFF.value == "payoff"

    def test_failure_stage_closed(self) -> None:
        assert len(FailureStage) == 3

    def test_captured_failure_classification_is_enum(self) -> None:
        assert issubclass(CapturedFailureClassification, enum.Enum)

    def test_captured_failure_classification_values(self) -> None:
        assert (
            CapturedFailureClassification.VALIDATION_FAILURE.value
            == "validation_failure"
        )
        assert (
            CapturedFailureClassification.CANONICALIZATION_FAILURE.value
            == "canonicalization_failure"
        )
        assert (
            CapturedFailureClassification.PAYOFF_COMPILATION_FAILURE.value
            == "payoff_compilation_failure"
        )
        assert (
            CapturedFailureClassification.COMPLEXITY_FAILURE.value
            == "complexity_failure"
        )
        assert (
            CapturedFailureClassification.COLLISION_FAILURE.value == "collision_failure"
        )
        assert (
            CapturedFailureClassification.ENCODING_FAILURE.value == "encoding_failure"
        )

    def test_captured_failure_classification_closed(self) -> None:
        assert len(CapturedFailureClassification) == 6

    def test_comparison_reason_is_enum(self) -> None:
        assert issubclass(ComparisonReason, enum.Enum)

    def test_comparison_reason_values(self) -> None:
        assert ComparisonReason.UPSTREAM_STAGE_FAILURE.value == "upstream_stage_failure"
        assert (
            ComparisonReason.REPRESENTATION_UNAVAILABLE.value
            == "representation_unavailable"
        )
        assert (
            ComparisonReason.RUNTIME_PRECONDITION_FAILED.value
            == "runtime_precondition_failed"
        )
        assert (
            ComparisonReason.SHALLOWER_LEVEL_REQUESTED.value
            == "shallower_level_requested"
        )

    def test_comparison_reason_closed(self) -> None:
        assert len(ComparisonReason) == 4

    def test_all_new_enums_reject_raw_strings(self) -> None:
        """Raw strings are rejected for all new enum types."""
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_exact_enum("equivalent", ComparisonStatus, "test")
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_exact_enum("valid", ValidationOutcome, "test")
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_exact_enum("structural", FailureStage, "test")
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_exact_enum(
                "validation_failure", CapturedFailureClassification, "test"
            )
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_exact_enum("upstream_stage_failure", ComparisonReason, "test")


class TestEnums:
    def test_validation_level_is_enum(self) -> None:
        assert issubclass(ValidationLevel, enum.Enum)

    def test_validation_level_values(self) -> None:
        assert ValidationLevel.STRUCTURAL.value == "structural"
        assert ValidationLevel.CANONICAL.value == "canonical"
        assert ValidationLevel.PAYOFF.value == "payoff"

    def test_validation_level_closed(self) -> None:
        assert len(ValidationLevel) == 3

    def test_diff_operation_is_enum(self) -> None:
        assert issubclass(DiffOperation, enum.Enum)

    def test_diff_operation_values(self) -> None:
        assert DiffOperation.ADD.value == "add"
        assert DiffOperation.REMOVE.value == "remove"
        assert DiffOperation.CHANGE.value == "change"
        assert DiffOperation.REPLACE.value == "replace"

    def test_diff_operation_closed(self) -> None:
        assert len(DiffOperation) == 4

    def test_diff_selection_is_enum(self) -> None:
        assert issubclass(DiffSelection, enum.Enum)

    def test_diff_selection_values(self) -> None:
        assert DiffSelection.CANONICAL.value == "canonical"
        assert DiffSelection.PAYOFF.value == "payoff"
        assert DiffSelection.NONE.value == "none"

    def test_diff_selection_closed(self) -> None:
        assert len(DiffSelection) == 3

    def test_diff_selection_no_both(self) -> None:
        names = [s.name for s in DiffSelection]
        assert "BOTH" not in names

    def test_truncation_reason_is_enum(self) -> None:
        assert issubclass(TruncationReason, enum.Enum)

    def test_truncation_reason_values(self) -> None:
        assert TruncationReason.ENTRY_LIMIT.value == "entry_limit"
        assert TruncationReason.REPORT_BYTE_LIMIT.value == "report_byte_limit"
        assert TruncationReason.PATH_LIMIT.value == "path_limit"

    def test_truncation_reason_closed(self) -> None:
        assert len(TruncationReason) == 3

    def test_unavailable_reason_is_enum(self) -> None:
        assert issubclass(UnavailableReason, enum.Enum)

    def test_unavailable_reason_value(self) -> None:
        assert (
            UnavailableReason.COMPARISON_LIMIT_EXCEEDED.value
            == "comparison_limit_exceeded"
        )

    def test_unavailable_reason_closed(self) -> None:
        assert len(UnavailableReason) == 1


class TestDiffLimits:
    def test_default_limits(self) -> None:
        limits = DiffLimits()
        assert limits.max_compared_bytes == 2_097_152
        assert limits.max_compared_nodes == 4096
        assert limits.max_entries == 1024
        assert limits.max_report_bytes == 8_388_608
        assert limits.max_path_length == 256

    def test_frozen(self) -> None:
        limits = DiffLimits()
        with pytest.raises(AttributeError):
            limits.max_entries = 999  # type: ignore[misc]

    def test_bool_rejection_for_integer_limits(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_compared_bytes=True)
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_compared_nodes=True)
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_entries=True)

    def test_zero_rejection(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_compared_bytes=0)
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_entries=0)

    def test_negative_rejection(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_compared_bytes=-1)

    def test_subclass_rejection(self) -> None:
        class FakeDiffLimits(DiffLimits):
            pass

        with pytest.raises(ValidationEquivalenceInputError):
            _validate_diff_limits(FakeDiffLimits())

    def test_default_classmethod(self) -> None:
        limits = DiffLimits.default()
        assert limits.max_compared_bytes == 2_097_152


class TestValidationLevelBoundary:
    def test_exact_type_check(self) -> None:
        _validate_validation_level(ValidationLevel.CANONICAL)

    def test_reject_string(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_validation_level("canonical")

    def test_reject_int(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_validation_level(0)


class TestDiffSelectionBoundary:
    def test_exact_type_check(self) -> None:
        _validate_diff_selection(DiffSelection.NONE)

    def test_reject_string(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_diff_selection("none")

    def test_reject_both(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_diff_selection("both")


class TestComparisonStatusReasonValidation:
    def test_equivalent_with_none_reason(self) -> None:
        validate_comparison_coherence(ComparisonStatus.EQUIVALENT, None)

    def test_different_with_none_reason(self) -> None:
        validate_comparison_coherence(ComparisonStatus.DIFFERENT, None)

    def test_not_comparable_requires_reason(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            validate_comparison_coherence(ComparisonStatus.NOT_COMPARABLE, None)

    def test_not_comparable_with_reason(self) -> None:
        validate_comparison_coherence(
            ComparisonStatus.NOT_COMPARABLE,
            ComparisonReason.UPSTREAM_STAGE_FAILURE,
        )

    def test_not_evaluated_requires_shallower(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            validate_comparison_coherence(
                ComparisonStatus.NOT_EVALUATED,
                ComparisonReason.UPSTREAM_STAGE_FAILURE,
            )

    def test_not_evaluated_with_shallower(self) -> None:
        validate_comparison_coherence(
            ComparisonStatus.NOT_EVALUATED,
            ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
        )

    def test_equivalent_with_reason_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            validate_comparison_coherence(
                ComparisonStatus.EQUIVALENT,
                ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            )
