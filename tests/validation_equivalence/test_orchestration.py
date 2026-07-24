"""Focused tests for the private Stage 1C-R1B orchestration runtime.

Covers:
- Caller boundary validation
- Structural-level processing
- Canonical-level processing
- Payoff-level processing
- Internal consistency (second-pass, identity mismatch, unexpected exception)
- Report integration
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import patch

import pytest

from derivatrace.canonical import (
    CanonicalSchemaVersion,
)
from derivatrace.contracts import (
    Both,
    Contract,
    Currency,
    ExactNumber,
    Number,
    Payment,
    Scale,
    SettlementTime,
    Unit,
    UnitKind,
    Zero,
)
from derivatrace.payoffgraph import (
    PayoffGraphSchemaVersion,
)
from derivatrace.validation_equivalence._errors import (
    ValidationEquivalenceComparisonError,
    ValidationEquivalenceInputError,
    ValidationEquivalenceMalformedRepresentationError,
    ValidationEquivalenceUnsupportedLevelError,
)
from derivatrace.validation_equivalence._orchestration import (
    _compare_contracts,
)
from derivatrace.validation_equivalence._report import ValidationEquivalenceReport
from derivatrace.validation_equivalence._schema import (
    ComparisonStatus,
    DiffSelection,
    ValidationLevel,
)

# ---------------------------------------------------------------------------
# Contract fixtures
# ---------------------------------------------------------------------------

_USD = Currency("USD")
_SETTLE = SettlementTime(datetime(2025, 1, 1, tzinfo=UTC))


def _payment(amount: str = "100") -> Payment:
    return Payment(
        amount=Number(ExactNumber.from_string(amount), unit=Unit(UnitKind.MONEY, _USD)),
        currency=_USD,
        settlement_time=_SETTLE,
    )


def _simple_contract() -> Payment:
    return _payment("100")


def _identical_contract() -> Payment:
    return _payment("100")


def _different_amount_contract() -> Payment:
    return _payment("200")


def _zero_contract() -> Zero:
    return Zero()


def _both_contract() -> Both:
    return Both(operands=(_payment("100"), _payment("200")))


class UnsupportedContract(Contract):
    """Minimal unsupported Contract subclass for testing."""

    __slots__ = ()


# ---------------------------------------------------------------------------
# 1. Caller boundary tests
# ---------------------------------------------------------------------------


class TestCallerBoundary:
    """Wrong exact types at the API boundary raise InputError."""

    def test_wrong_left_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError, match="left must be"):
            _compare_contracts(
                "not a contract",  # type: ignore[arg-type]
                _simple_contract(),
                level=ValidationLevel.STRUCTURAL,
            )

    def test_wrong_right_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError, match="right must be"):
            _compare_contracts(_simple_contract(), 42, level=ValidationLevel.STRUCTURAL)  # type: ignore[arg-type]

    def test_unsupported_level_raises(self) -> None:
        with pytest.raises(ValidationEquivalenceUnsupportedLevelError):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level="canonical",  # type: ignore[arg-type]
            )

    def test_int_level_raises(self) -> None:
        with pytest.raises(ValidationEquivalenceUnsupportedLevelError):
            _compare_contracts(_simple_contract(), _simple_contract(), level=0)  # type: ignore[arg-type]

    def test_wrong_canonical_schema_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError, match="canonical_schema"):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.CANONICAL,
                canonical_schema=PayoffGraphSchemaVersion(),  # type: ignore[arg-type]
            )

    def test_wrong_payoff_schema_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError, match="payoff_schema"):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.PAYOFF,
                payoff_schema=CanonicalSchemaVersion(),  # type: ignore[arg-type]
            )

    def test_wrong_canonicalization_limits_type(self) -> None:
        with pytest.raises(
            ValidationEquivalenceInputError, match="canonicalization_limits"
        ):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.CANONICAL,
                canonicalization_limits="bad",  # type: ignore[arg-type]
            )

    def test_wrong_payoff_limits_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError, match="payoff_limits"):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.PAYOFF,
                payoff_limits="bad",  # type: ignore[arg-type]
            )

    def test_wrong_validation_limits_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError, match="validation_limits"):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.STRUCTURAL,
                validation_limits="bad",  # type: ignore[arg-type]
            )

    def test_unsupported_diff_selection(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError, match="diff_selection"):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.STRUCTURAL,
                diff_selection=DiffSelection.CANONICAL,
            )

    def test_diff_selection_string_raises(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.STRUCTURAL,
                diff_selection="none",  # type: ignore[arg-type]
            )

    def test_wrong_diff_limits_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError, match="diff_limits"):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.STRUCTURAL,
                diff_limits="bad",  # type: ignore[arg-type]
            )

    def test_no_report_returned_for_input_error(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _compare_contracts(
                "bad",  # type: ignore[arg-type]
                "bad",  # type: ignore[arg-type]
                level=ValidationLevel.STRUCTURAL,
            )

    def test_none_canonical_schema_accepted(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.CANONICAL,
            canonical_schema=None,
        )
        assert isinstance(report, ValidationEquivalenceReport)


# ---------------------------------------------------------------------------
# 2. Structural-level processing
# ---------------------------------------------------------------------------


class TestStructuralProcessing:
    """Structural-level comparison."""

    def test_valid_valid(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _identical_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert report.report.left_validation_outcome.value == "valid"
        assert report.report.right_validation_outcome.value == "valid"
        assert report.report.left.contract_identity is None
        assert report.report.right.contract_identity is None
        assert report.report.left.payoff_graph_identity is None
        assert report.report.right.payoff_graph_identity is None

    def test_canonical_status_not_evaluated(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert (
            report.report.canonical_comparison_status is ComparisonStatus.NOT_EVALUATED
        )
        assert report.report.payoff_comparison_status is ComparisonStatus.NOT_EVALUATED

    def test_structural_identities_are_null(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert report.report.left.contract_identity is None
        assert report.report.right.contract_identity is None
        assert report.report.left.payoff_graph_identity is None
        assert report.report.right.payoff_graph_identity is None

    def test_unsupported_contract_invalid_left(self) -> None:
        report = _compare_contracts(
            UnsupportedContract(),
            _simple_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert report.report.left_validation_outcome.value == "invalid"
        assert report.report.right_validation_outcome.value == "valid"
        assert len(report.report.left.failures) == 1

    def test_unsupported_contract_invalid_right(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            UnsupportedContract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert report.report.left_validation_outcome.value == "valid"
        assert report.report.right_validation_outcome.value == "invalid"
        assert len(report.report.right.failures) == 1

    def test_forged_ve_018_money_denominated_factor(self) -> None:
        """ve_018: caller-forged money-denominated Scale.factor."""
        # Build a valid Scale with scalar factor first
        scale = Scale(
            factor=Number(
                ExactNumber.from_string("1"), unit=Unit(UnitKind.SCALAR, None)
            ),
            contract=Zero(),
        )
        # Forge the factor's unit kind to MONEY with a Currency
        # via object.__setattr__ (bypasses constructor validation)
        money_unit = object.__new__(Unit)
        object.__setattr__(money_unit, "kind", UnitKind.MONEY)
        object.__setattr__(money_unit, "currency", Currency("USD"))
        object.__setattr__(scale.factor, "unit", money_unit)
        report = _compare_contracts(
            scale,
            _simple_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert report.report.left_validation_outcome.value == "invalid"


# ---------------------------------------------------------------------------
# 3. Canonical-level processing
# ---------------------------------------------------------------------------


class TestCanonicalProcessing:
    """Canonical-level comparison."""

    def test_equivalent_canonical_identities(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _identical_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert report.report.left_validation_outcome.value == "valid"
        assert report.report.right_validation_outcome.value == "valid"
        assert report.report.left.contract_identity is not None
        assert report.report.right.contract_identity is not None
        assert report.report.canonical_comparison_status is ComparisonStatus.EQUIVALENT
        assert (
            report.report.left.contract_identity
            == report.report.right.contract_identity
        )

    def test_different_canonical_identities(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _different_amount_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert report.report.left.contract_identity is not None
        assert report.report.right.contract_identity is not None
        assert report.report.canonical_comparison_status is ComparisonStatus.DIFFERENT
        assert (
            report.report.left.contract_identity
            != report.report.right.contract_identity
        )

    def test_one_structural_failure_canonical_blocked(self) -> None:
        report = _compare_contracts(
            UnsupportedContract(),
            _simple_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert report.report.left_validation_outcome.value == "invalid"
        assert report.report.left.contract_identity is None
        assert report.report.right.contract_identity is not None
        assert (
            report.report.canonical_comparison_status is ComparisonStatus.NOT_COMPARABLE
        )

    def test_payoff_status_not_evaluated_at_canonical_level(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert report.report.payoff_comparison_status is ComparisonStatus.NOT_EVALUATED

    def test_both_structural_failure_canonical_not_comparable(self) -> None:
        report = _compare_contracts(
            UnsupportedContract(),
            UnsupportedContract(),
            level=ValidationLevel.CANONICAL,
        )
        assert report.report.left_validation_outcome.value == "invalid"
        assert report.report.right_validation_outcome.value == "invalid"
        assert (
            report.report.canonical_comparison_status is ComparisonStatus.NOT_COMPARABLE
        )


# ---------------------------------------------------------------------------
# 4. Payoff-level processing
# ---------------------------------------------------------------------------


class TestPayoffProcessing:
    """Payoff-level comparison."""

    def test_equivalent_payoff_identities(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _identical_contract(),
            level=ValidationLevel.PAYOFF,
        )
        assert report.report.left.payoff_graph_identity is not None
        assert report.report.right.payoff_graph_identity is not None
        assert report.report.payoff_comparison_status is ComparisonStatus.EQUIVALENT
        assert report.report.left.contract_identity is not None
        assert report.report.right.contract_identity is not None
        assert report.report.canonical_comparison_status is ComparisonStatus.EQUIVALENT

    def test_different_payoff_identities(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _different_amount_contract(),
            level=ValidationLevel.PAYOFF,
        )
        assert report.report.left.payoff_graph_identity is not None
        assert report.report.right.payoff_graph_identity is not None
        assert report.report.payoff_comparison_status is ComparisonStatus.DIFFERENT

    def test_genuine_payoff_failure_captured(self) -> None:
        """A non-canonicalization PayoffGraphError is captured as a payoff failure."""
        from derivatrace.payoffgraph._errors import PayoffGraphCompilationError

        def _fail_compile_left(*args: Any, **kwargs: Any) -> Any:
            raise PayoffGraphCompilationError("internal compilation failure")

        with patch(
            "derivatrace.validation_equivalence._orchestration.compile_payoff_graph",
            side_effect=_fail_compile_left,
        ):
            report = _compare_contracts(
                UnsupportedContract(),
                _simple_contract(),
                level=ValidationLevel.PAYOFF,
            )

        # UnsupportedContract fails at structural, so canonical is blocked.
        # Payoff for left is never attempted (no canonical success).
        assert report.report.left.payoff_graph_identity is None
        assert report.report.left_validation_outcome.value == "invalid"
        assert report.report.payoff_comparison_status is ComparisonStatus.NOT_COMPARABLE

    def test_canonical_retained_when_payoff_fails(self) -> None:
        """Canonical identity is retained when payoff compilation fails."""
        from derivatrace.payoffgraph._errors import PayoffGraphCompilationError

        def _fail_compile(*args: Any, **kwargs: Any) -> Any:
            raise PayoffGraphCompilationError("internal compilation failure")

        with patch(
            "derivatrace.validation_equivalence._orchestration.compile_payoff_graph",
            side_effect=_fail_compile,
        ):
            report = _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.PAYOFF,
            )

        assert report.report.left.contract_identity is not None
        assert report.report.left.payoff_graph_identity is None
        assert report.report.right.contract_identity is not None
        assert report.report.right.payoff_graph_identity is None

    def test_no_payoff_attempt_after_canonical_failure(self) -> None:
        """When canonicalization fails, compile_payoff_graph is never called."""
        call_count = 0

        from derivatrace.payoffgraph._compiler import (
            compile_payoff_graph as real_compile,
        )

        def _counting_compile(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            return real_compile(*args, **kwargs)

        report = _compare_contracts(
            UnsupportedContract(),
            _simple_contract(),
            level=ValidationLevel.PAYOFF,
        )
        assert call_count == 0
        assert report.report.left_validation_outcome.value == "invalid"
        assert report.report.left.payoff_graph_identity is None

    def test_one_structural_failure_payoff_not_comparable(self) -> None:
        report = _compare_contracts(
            UnsupportedContract(),
            _simple_contract(),
            level=ValidationLevel.PAYOFF,
        )
        assert report.report.payoff_comparison_status is ComparisonStatus.NOT_COMPARABLE

    def test_both_structural_failure_payoff_not_comparable(self) -> None:
        report = _compare_contracts(
            UnsupportedContract(),
            UnsupportedContract(),
            level=ValidationLevel.PAYOFF,
        )
        assert report.report.payoff_comparison_status is ComparisonStatus.NOT_COMPARABLE


# ---------------------------------------------------------------------------
# 5. Internal consistency (private monkeypatching)
# ---------------------------------------------------------------------------


class TestInternalConsistency:
    """Second-pass consistency rules via controlled monkeypatching."""

    def test_second_canonicalization_raises_comparison_error(self) -> None:
        """First explicit canonicalization succeeds; internal second pass
        raises CanonicalizationError → ValidationEquivalenceComparisonError."""
        from derivatrace.canonical import CanonicalizationError as CE

        def _fail_compile_with_canon_error(*args: Any, **kwargs: Any) -> Any:
            raise CE("internal second pass failed")

        with (
            patch(
                "derivatrace.validation_equivalence._orchestration.compile_payoff_graph",
                side_effect=_fail_compile_with_canon_error,
            ),
            pytest.raises(
                ValidationEquivalenceComparisonError,
                match="internal second canonicalization failed",
            ),
        ):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.PAYOFF,
            )

    def test_source_identity_mismatch_raises(self) -> None:
        """payoff_graph.source_contract_identity mismatch →
        ValidationEquivalenceMalformedRepresentationError."""
        from derivatrace.payoffgraph._compiler import (
            compile_payoff_graph as real_compile_fn,
        )
        from derivatrace.payoffgraph._result import PayoffGraph as RealPayoffGraph

        def _mismatched_compile(*args: Any, **kwargs: Any) -> RealPayoffGraph:
            result = real_compile_fn(*args, **kwargs)
            return RealPayoffGraph(
                schema_version=result.schema_version,
                document_bytes=result.document_bytes,
                structural_bytes=result.structural_bytes,
                identity=result.identity,
                root_node_id=result.root_node_id,
                node_count=result.node_count,
                source_contract_identity="canonical:sha256:" + "ff" * 32,
            )

        with (
            patch(
                "derivatrace.validation_equivalence._orchestration.compile_payoff_graph",
                side_effect=_mismatched_compile,
            ),
            pytest.raises(
                ValidationEquivalenceMalformedRepresentationError,
                match="mismatch",
            ),
        ):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.PAYOFF,
            )

    def test_unexpected_exception_raises_comparison_error(self) -> None:
        """Unexpected ordinary Exception → ValidationEquivalenceComparisonError."""

        def _explode(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("unexpected internal failure")

        with (
            patch(
                "derivatrace.validation_equivalence._orchestration.compile_payoff_graph",
                side_effect=_explode,
            ),
            pytest.raises(
                ValidationEquivalenceComparisonError,
                match="internal comparison error",
            ),
        ):
            _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.PAYOFF,
            )

    def test_no_partial_report_on_payoff_consistency_error(self) -> None:
        """No report is returned when an internal consistency error occurs."""
        from derivatrace.payoffgraph._errors import PayoffGraphCompilationError

        def _fail_compile(*args: Any, **kwargs: Any) -> Any:
            raise PayoffGraphCompilationError("boom")

        with patch(
            "derivatrace.validation_equivalence._orchestration.compile_payoff_graph",
            side_effect=_fail_compile,
        ):
            report = _compare_contracts(
                _simple_contract(),
                _simple_contract(),
                level=ValidationLevel.PAYOFF,
            )
            # Still returns a report, but payoff status is NOT_COMPARABLE
            assert isinstance(report, ValidationEquivalenceReport)
            assert (
                report.report.payoff_comparison_status
                is ComparisonStatus.NOT_COMPARABLE
            )


# ---------------------------------------------------------------------------
# 6. Report integration
# ---------------------------------------------------------------------------


class TestReportIntegration:
    """Report construction and identity guarantees."""

    def test_exact_empty_diff_state(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert report.report.diff_representation is DiffSelection.NONE
        assert report.report.diff_summary.entries == ()
        assert report.report.diff_summary.truncated is False
        assert report.report.diff_summary.truncation_reason is None
        assert report.report.diff_summary.unavailable_reason is None

    def test_deterministic_report_bytes(self) -> None:
        r1 = _compare_contracts(
            _simple_contract(),
            _identical_contract(),
            level=ValidationLevel.CANONICAL,
        )
        r2 = _compare_contracts(
            _simple_contract(),
            _identical_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert r1.report_bytes == r2.report_bytes

    def test_deterministic_report_id(self) -> None:
        r1 = _compare_contracts(
            _simple_contract(),
            _identical_contract(),
            level=ValidationLevel.CANONICAL,
        )
        r2 = _compare_contracts(
            _simple_contract(),
            _identical_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert r1.report_id == r2.report_id

    def test_is_a_validation_equivalence_report(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert isinstance(report, ValidationEquivalenceReport)

    def test_package_remains_private(self) -> None:
        import derivatrace.validation_equivalence as ve_pkg

        assert ve_pkg.__all__ == []
        assert not hasattr(ve_pkg, "compare_contracts")

    def test_no_public_compare_contracts(self) -> None:
        import derivatrace.validation_equivalence as ve_pkg

        assert "compare_contracts" not in dir(ve_pkg)

    def test_provenance_source_identities_at_canonical_level(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _different_amount_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert report.report.left.contract_identity is not None
        assert report.report.right.contract_identity is not None

    def test_provenance_source_identities_null_at_structural(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert report.report.left.contract_identity is None
        assert report.report.right.contract_identity is None

    def test_zero_vs_nonzero(self) -> None:
        """ve_021: Zero vs non-zero contract."""
        report = _compare_contracts(
            _zero_contract(),
            _simple_contract(),
            level=ValidationLevel.CANONICAL,
        )
        assert report.report.canonical_comparison_status is ComparisonStatus.DIFFERENT

    def test_both_order(self) -> None:
        """ve_009: Both order produces different canonical identities."""
        c1 = Both(operands=(_payment("100"), _payment("200")))
        c2 = Both(operands=(_payment("200"), _payment("100")))
        report = _compare_contracts(c1, c2, level=ValidationLevel.CANONICAL)
        assert report.report.canonical_comparison_status is ComparisonStatus.DIFFERENT

    def test_self_equivalence_canonical(self) -> None:
        """ve_001: Same contract compared to itself is equivalent."""
        c = _both_contract()
        report = _compare_contracts(c, c, level=ValidationLevel.CANONICAL)
        assert report.report.canonical_comparison_status is ComparisonStatus.EQUIVALENT
        assert (
            report.report.left.contract_identity
            == report.report.right.contract_identity
        )

    def test_report_bytes_are_bytes(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert isinstance(report.report_bytes, bytes)
        assert isinstance(report.structural_bytes, bytes)

    def test_report_id_is_valid_format(self) -> None:
        report = _compare_contracts(
            _simple_contract(),
            _simple_contract(),
            level=ValidationLevel.STRUCTURAL,
        )
        assert report.report_id.startswith("validation-equivalence:sha256:")
        assert len(report.report_id) == 94


__all__: list[str] = []
