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
from derivatrace.validation_equivalence._schema import (
    DiffLimits,
    DiffOperation,
    DiffSelection,
    TruncationReason,
    UnavailableReason,
    ValidationLevel,
    _validate_diff_limits,
    _validate_diff_selection,
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
            DiffLimits(max_compared_bytes=True)  # type: ignore[arg-type]
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_compared_nodes=True)  # type: ignore[arg-type]
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_entries=True)  # type: ignore[arg-type]

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
