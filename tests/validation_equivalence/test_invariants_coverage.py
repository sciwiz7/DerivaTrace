from __future__ import annotations

import pytest

from derivatrace.canonical import (
    CanonicalizationInputError,
    CanonicalizationLimits,
    CanonicalSchemaVersion,
)
from derivatrace.contracts import ContractInputError
from derivatrace.payoffgraph import (
    PayoffGraphInputError,
    PayoffGraphLimits,
    PayoffGraphSchemaVersion,
)
from derivatrace.validation_equivalence._encoding import (
    encode_report,
    report_to_jsonable,
    structural_bytes,
)
from derivatrace.validation_equivalence._errors import (
    ValidationEquivalenceEncodingError,
    ValidationEquivalenceInputError,
)
from derivatrace.validation_equivalence._records import (
    CanonicalMetadata,
    CapturedFailure,
    CompleteReport,
    DiffEntry,
    DiffLimits,
    DiffSummary,
    LimitsUsed,
    PayoffMetadata,
    ProvenanceRecord,
    ReportSide,
    SchemaMetadataRecord,
    ValidationLimits,
    _StructuralPayload,
    _validate_identity,
    _validate_report_id_identity,
    validate_comparison_coherence,
)
from derivatrace.validation_equivalence._report import (
    ValidationEquivalenceReport,
    _build_report,
    _validate_record_types,
)
from derivatrace.validation_equivalence._schema import (
    CapturedFailureClassification,
    ComparisonReason,
    ComparisonStatus,
    DiffOperation,
    DiffSelection,
    FailureStage,
    ValidationLevel,
    ValidationOutcome,
    _validate_exact_enum,
)


def _valid_side() -> ReportSide:
    return ReportSide(
        contract_identity="canonical:sha256:" + "a" * 64,
        payoff_graph_identity=None,
        failures=(),
    )


def _valid_complete_report(**overrides: object) -> CompleteReport:
    kwargs: dict[str, object] = {
        "report_id": "validation-equivalence:sha256:" + "a" * 64,
        "schema_name": "derivatrace.validation-equivalence.report",
        "schema_version": "1.0.0",
        "requested_level": ValidationLevel.CANONICAL,
        "canonical_schema_version": "1.0.0",
        "payoff_schema_version": "1.0.0",
        "left_validation_outcome": ValidationOutcome.VALID,
        "right_validation_outcome": ValidationOutcome.VALID,
        "canonical_comparison_status": ComparisonStatus.EQUIVALENT,
        "canonical_comparison_reason": None,
        "payoff_comparison_status": ComparisonStatus.NOT_EVALUATED,
        "payoff_comparison_reason": ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
        "left": _valid_side(),
        "right": _valid_side(),
        "diff_representation": DiffSelection.NONE,
        "diff_summary": DiffSummary(),
        "limits_used": LimitsUsed(),
        "schema_metadata": SchemaMetadataRecord(),
        "provenance": ProvenanceRecord(),
    }
    kwargs.update(overrides)
    return CompleteReport(**kwargs)  # type: ignore[arg-type]


class TestLimitValidationBranches:
    def test_validation_limits_bool_rejected(self) -> None:
        with pytest.raises(ContractInputError):
            ValidationLimits(max_depth=True)

    def test_validation_limits_zero_rejected(self) -> None:
        with pytest.raises(ContractInputError):
            ValidationLimits(max_unique_nodes=0)

    def test_canonicalization_limits_bool_rejected(self) -> None:
        with pytest.raises(CanonicalizationInputError):
            CanonicalizationLimits(max_canonical_nodes=True)

    def test_canonicalization_limits_zero_rejected(self) -> None:
        with pytest.raises(CanonicalizationInputError):
            CanonicalizationLimits(max_canonical_bytes=0)

    def test_payoff_limits_bool_rejected(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_payoff_nodes=True)

    def test_payoff_limits_zero_rejected(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_document_bytes=0)


class TestDiffEntryValidation:
    def test_empty_path_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffEntry(path="", op=DiffOperation.ADD)

    def test_non_enum_op_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffEntry(path="/x", op="add")  # type: ignore[arg-type]

    def test_unsafe_left_value_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffEntry(path="/x", op=DiffOperation.ADD, left_value=object())


class TestDiffSummaryValidation:
    def test_non_tuple_entries_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffSummary(entries=[DiffEntry(path="/x", op=DiffOperation.ADD)])  # type: ignore[arg-type]

    def test_non_entry_element_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffSummary(entries=(object(),))  # type: ignore[arg-type]

    def test_truncated_not_bool_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffSummary(truncated="no")  # type: ignore[arg-type]


class TestReportSideValidation:
    def test_non_tuple_failures_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ReportSide(
                failures=[  # type: ignore[arg-type]
                    CapturedFailure(
                        stage=FailureStage.STRUCTURAL,
                        code="contract.input",
                        classification=CapturedFailureClassification.VALIDATION_FAILURE,
                    )
                ]
            )

    def test_unsorted_failures_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ReportSide(
                contract_identity="canonical:sha256:" + "a" * 64,
                failures=(
                    CapturedFailure(
                        stage=FailureStage.PAYOFF,
                        code="payoff_graph.compile",
                        classification=CapturedFailureClassification.PAYOFF_COMPILATION_FAILURE,
                    ),
                    CapturedFailure(
                        stage=FailureStage.STRUCTURAL,
                        code="contract.input",
                        classification=CapturedFailureClassification.VALIDATION_FAILURE,
                    ),
                ),
            )


class TestProvenanceValidation:
    def test_wrong_compiler_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ProvenanceRecord(compiler="wrong")

    def test_wrong_policy_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ProvenanceRecord(policy="wrong")


class TestCompleteReportValidation:
    def test_report_id_not_str(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(report_id=123)

    def test_report_id_empty_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(report_id="")

    def test_report_id_prefix_only_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(report_id="validation-equivalence:sha256:")

    def test_report_id_uppercase_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                report_id="validation-equivalence:sha256:" + "A" * 64
            )

    def test_report_id_short_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                report_id="validation-equivalence:sha256:" + "a" * 32
            )

    def test_report_id_long_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                report_id="validation-equivalence:sha256:" + "a" * 128
            )

    def test_report_id_non_hex_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                report_id="validation-equivalence:sha256:" + "g" * 64
            )

    def test_report_id_with_newline_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                report_id="validation-equivalence:sha256:" + "a" * 63 + "\n"
            )

    def test_wrong_schema_name(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(schema_name="wrong")

    def test_wrong_schema_version(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(schema_version="2.0.0")

    def test_canonical_schema_version_not_str(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(canonical_schema_version=123)

    def test_payoff_schema_version_not_str(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(payoff_schema_version=123)

    def test_requested_level_not_enum(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(requested_level="canonical")

    def test_left_outcome_not_enum(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(left_validation_outcome="valid")

    def test_canonical_status_not_enum(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(canonical_comparison_status="equivalent")

    def test_diff_representation_not_enum(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(diff_representation=123)

    def test_left_not_report_side(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(left="x")

    def test_right_not_report_side(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(right="x")

    def test_diff_summary_not_diff_summary(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(diff_summary="x")

    def test_limits_used_not_limits_used(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(limits_used="x")

    def test_schema_metadata_not_schema_metadata(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(schema_metadata="x")

    def test_provenance_not_provenance(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(provenance="x")


class TestStatusReasonCoherenceInRecord:
    def test_equivalent_with_reason_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                canonical_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            )

    def test_not_comparable_without_reason_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                canonical_comparison_status=ComparisonStatus.NOT_COMPARABLE,
                canonical_comparison_reason=None,
            )

    def test_not_evaluated_without_shallower_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                payoff_comparison_reason=ComparisonReason.UPSTREAM_STAGE_FAILURE,
            )

    def test_not_comparable_with_shallower_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _valid_complete_report(
                canonical_comparison_status=ComparisonStatus.NOT_COMPARABLE,
                canonical_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            )


class TestEncodingErrorBranches:
    def test_report_to_jsonable_rejects_non_dataclass(self) -> None:
        with pytest.raises(ValidationEquivalenceEncodingError):
            report_to_jsonable(object())

    def test_report_to_jsonable_rejects_non_dict(self) -> None:
        import derivatrace.validation_equivalence._encoding as enc_mod

        original = enc_mod._to_jsonable
        enc_mod._to_jsonable = lambda obj: "not a dict"
        try:
            with pytest.raises(ValidationEquivalenceEncodingError):
                report_to_jsonable(_valid_side())
        finally:
            enc_mod._to_jsonable = original

    def test_to_jsonable_dict_branch(self) -> None:
        from derivatrace.validation_equivalence._encoding import _to_jsonable

        assert _to_jsonable({"a": 1}) == {"a": 1}

    def test_to_jsonable_unserializable_raises(self) -> None:
        from derivatrace.validation_equivalence._encoding import _to_jsonable

        with pytest.raises(ValidationEquivalenceEncodingError):
            _to_jsonable(object())


class TestRecordTypeValidation:
    def _valid(self) -> dict[str, object]:
        return {
            "left_validation_outcome": ValidationOutcome.VALID,
            "right_validation_outcome": ValidationOutcome.VALID,
            "canonical_comparison_status": ComparisonStatus.EQUIVALENT,
            "canonical_comparison_reason": None,
            "payoff_comparison_status": ComparisonStatus.NOT_EVALUATED,
            "payoff_comparison_reason": ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            "left": _valid_side(),
            "right": _valid_side(),
            "limits_used": LimitsUsed(),
            "schema_metadata": SchemaMetadataRecord(),
        }

    def test_left_outcome_not_enum(self) -> None:
        kw = self._valid()
        kw["left_validation_outcome"] = 1
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_right_outcome_not_enum(self) -> None:
        kw = self._valid()
        kw["right_validation_outcome"] = 1
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_canonical_status_not_enum(self) -> None:
        kw = self._valid()
        kw["canonical_comparison_status"] = 1
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_canonical_reason_not_enum(self) -> None:
        kw = self._valid()
        kw["canonical_comparison_reason"] = 1
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_payoff_status_not_enum(self) -> None:
        kw = self._valid()
        kw["payoff_comparison_status"] = 1
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_payoff_reason_not_enum(self) -> None:
        kw = self._valid()
        kw["payoff_comparison_reason"] = 1
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_left_not_report_side(self) -> None:
        kw = self._valid()
        kw["left"] = "x"
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_right_not_report_side(self) -> None:
        kw = self._valid()
        kw["right"] = "x"
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_limits_used_not_limits_used(self) -> None:
        kw = self._valid()
        kw["limits_used"] = "x"
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]

    def test_schema_metadata_not_schema_metadata(self) -> None:
        kw = self._valid()
        kw["schema_metadata"] = "x"
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_record_types(**kw)  # type: ignore[arg-type]


class TestWrappedReportIdentityProperties:
    def test_report_property_and_bytes(self) -> None:
        wrapped = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            left=ReportSide(),
            right=ReportSide(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )
        assert wrapped.report.schema_name == "derivatrace.validation-equivalence.report"
        assert isinstance(wrapped.structural_bytes, bytes)
        assert isinstance(wrapped.report_bytes, bytes)

    def test_post_init_encode_failure_raises(self) -> None:
        report = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            left=_valid_side(),
            right=_valid_side(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )

        def _failing(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("injected")

        import derivatrace.validation_equivalence._report as report_mod

        original_encode = report_mod._encode_report
        report_mod._encode_report = _failing
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                ValidationEquivalenceReport(
                    report.report,
                    report.structural_bytes,
                    encode_report(report.report),
                )
            assert "injected" not in str(exc_info.value)
            assert "failed to encode complete report" in str(exc_info.value)
        finally:
            report_mod._encode_report = original_encode


class TestDiffStageLimitsValidation:
    def test_bool_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_compared_bytes=True)

    def test_zero_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffLimits(max_entries=0)


class TestDiffEntryRightValue:
    def test_unsafe_right_value_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffEntry(path="/x", op=DiffOperation.ADD, right_value=object())


class TestReportSideIdentityPrefixes:
    def test_bad_contract_identity_prefix(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ReportSide(contract_identity="wrong:sha256:" + "a" * 64)

    def test_bad_payoff_identity_prefix(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ReportSide(payoff_graph_identity="wrong:sha256:" + "a" * 64)

    def test_non_captured_failure_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ReportSide(failures=(object(),))  # type: ignore[arg-type]


class TestExactEnumValueValidator:
    def test_rejects_bad_value(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_exact_enum("bogus", ComparisonStatus, "status")

    def test_accepts_good_value(self) -> None:
        _validate_exact_enum(ComparisonStatus.EQUIVALENT, ComparisonStatus, "status")


class TestR1ADiffInvariantType:
    def test_diff_summary_wrong_type_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(
                requested_level=ValidationLevel.CANONICAL,
                canonical_schema_version=CanonicalSchemaVersion(),
                payoff_schema_version=PayoffGraphSchemaVersion(),
                left_validation_outcome=ValidationOutcome.VALID,
                right_validation_outcome=ValidationOutcome.VALID,
                canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                canonical_comparison_reason=None,
                payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                left=ReportSide(),
                right=ReportSide(),
                diff_representation=DiffSelection.NONE,
                diff_summary="none",  # type: ignore[arg-type]
                limits_used=LimitsUsed(),
                schema_metadata=SchemaMetadataRecord(),
            )


class TestLimitZeroRejection:
    def test_validation_limits_zero_rejected(self) -> None:
        with pytest.raises(ContractInputError):
            ValidationLimits(max_depth=0)

    def test_canonicalization_limits_zero_rejected(self) -> None:
        with pytest.raises(CanonicalizationInputError):
            CanonicalizationLimits(max_canonical_bytes=0)

    def test_payoff_limits_zero_rejected(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_structural_bytes=0)


class TestLimitsUsedValidation:
    def test_validation_wrong_type_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            LimitsUsed(validation="bad")  # type: ignore[arg-type]

    def test_canonicalization_wrong_type_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            LimitsUsed(canonicalization="bad")  # type: ignore[arg-type]

    def test_payoff_wrong_type_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            LimitsUsed(payoff="bad")  # type: ignore[arg-type]

    def test_diff_wrong_type_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            LimitsUsed(diff="bad")  # type: ignore[arg-type]


class TestSchemaMetadataExactness:
    def test_canonical_metadata_wrong_schema_name(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CanonicalMetadata(schema_name="wrong")

    def test_canonical_metadata_wrong_version(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CanonicalMetadata(schema_version="2.0.0")

    def test_canonical_metadata_wrong_node_domain(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CanonicalMetadata(node_identity_domain="wrong")

    def test_canonical_metadata_wrong_repr_domain(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CanonicalMetadata(representation_identity_domain="wrong")

    def test_payoff_metadata_wrong_schema_name(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            PayoffMetadata(schema_name="wrong")

    def test_payoff_metadata_wrong_version(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            PayoffMetadata(schema_version="2.0.0")

    def test_payoff_metadata_wrong_node_domain(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            PayoffMetadata(node_identity_domain="wrong")

    def test_payoff_metadata_wrong_repr_domain(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            PayoffMetadata(representation_identity_domain="wrong")

    def test_schema_metadata_canonical_wrong_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            SchemaMetadataRecord(canonical="bad")  # type: ignore[arg-type]

    def test_schema_metadata_payoff_wrong_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            SchemaMetadataRecord(payoff="bad")  # type: ignore[arg-type]


class TestDiffSummaryDuplicateEntries:
    def test_duplicate_entry_rejected(self) -> None:
        entry = DiffEntry(path="/x", op=DiffOperation.ADD)
        with pytest.raises(ValidationEquivalenceInputError):
            DiffSummary(entries=(entry, entry))


class TestComparisonCoherenceBranches:
    def test_not_comparable_with_reason_accepted(self) -> None:
        _valid_complete_report(
            canonical_comparison_status=ComparisonStatus.NOT_COMPARABLE,
            canonical_comparison_reason=ComparisonReason.UPSTREAM_STAGE_FAILURE,
        )

    def test_not_evaluated_with_shallower_accepted(self) -> None:
        _valid_complete_report(
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
        )


class TestWrappedReportIdentityEdgeCases:
    def test_non_complete_report_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ValidationEquivalenceReport("bad", b"", b"")  # type: ignore[arg-type]

    def test_empty_report_id_rejected(self) -> None:
        report = _valid_complete_report(
            report_id="validation-equivalence:sha256:" + "f" * 64
        )
        s_bytes = structural_bytes(report)
        with pytest.raises(ValidationEquivalenceEncodingError):
            ValidationEquivalenceReport(report, s_bytes, encode_report(report))

    def test_payoff_reason_none_branch(self) -> None:
        report = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.EQUIVALENT,
            payoff_comparison_reason=None,
            left=ReportSide(),
            right=ReportSide(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )
        assert report.report.payoff_comparison_reason is None


# ---------------------------------------------------------------------------
# Regression tests for Stage 1C-R1A correction pass
# ---------------------------------------------------------------------------


class TestIdentityValidationExactSyntax:
    """Requirement 3: full identity syntax validation, not prefixes alone."""

    def test_short_identity_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(
                "canonical:sha256:" + "a" * 32,
                "canonical:sha256:",
                "test",
            )

    def test_long_identity_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(
                "canonical:sha256:" + "a" * 128,
                "canonical:sha256:",
                "test",
            )

    def test_uppercase_hex_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(
                "canonical:sha256:" + "A" * 64,
                "canonical:sha256:",
                "test",
            )

    def test_non_hex_identity_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(
                "canonical:sha256:" + "g" * 64,
                "canonical:sha256:",
                "test",
            )

    def test_identity_prefix_only_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(
                "canonical:sha256:",
                "canonical:sha256:",
                "test",
            )

    def test_identity_with_extra_suffix_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(
                "canonical:sha256:" + "a" * 64 + "extra",
                "canonical:sha256:",
                "test",
            )

    def test_identity_with_whitespace_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(
                "canonical:sha256:" + "a" * 63 + " ",
                "canonical:sha256:",
                "test",
            )

    def test_identity_with_newline_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(
                "canonical:sha256:" + "a" * 63 + "\n",
                "canonical:sha256:",
                "test",
            )

    def test_valid_canonical_identity_accepted(self) -> None:
        _validate_identity(
            "canonical:sha256:" + "a" * 64,
            "canonical:sha256:",
            "test",
        )

    def test_valid_payoff_identity_accepted(self) -> None:
        _validate_identity(
            "payoffgraph:sha256:" + "a" * 64,
            "payoffgraph:sha256:",
            "test",
        )

    def test_valid_report_id_identity_accepted(self) -> None:
        _validate_report_id_identity(
            "validation-equivalence:sha256:" + "a" * 64,
        )

    def test_report_id_prefix_only_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_report_id_identity("validation-equivalence:sha256:")

    def test_report_id_short_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_report_id_identity("validation-equivalence:sha256:" + "a" * 32)

    def test_report_id_uppercase_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_report_id_identity("validation-equivalence:sha256:" + "A" * 64)

    def test_none_identity_accepted(self) -> None:
        _validate_identity(None, "canonical:sha256:", "test")


class TestSchemaSelectionBoundaryTypes:
    """Requirement 2: exact upstream schema-selection types at factory boundary."""

    def test_arbitrary_schema_version_string_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(
                requested_level=ValidationLevel.CANONICAL,
                canonical_schema_version="1.0.0",  # type: ignore[arg-type]
                payoff_schema_version=PayoffGraphSchemaVersion(),
                left_validation_outcome=ValidationOutcome.VALID,
                right_validation_outcome=ValidationOutcome.VALID,
                canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                canonical_comparison_reason=None,
                payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                left=ReportSide(),
                right=ReportSide(),
                diff_representation=DiffSelection.NONE,
                diff_summary=DiffSummary(),
                limits_used=LimitsUsed(),
                schema_metadata=SchemaMetadataRecord(),
            )

    def test_exact_canonical_schema_version_accepted(self) -> None:
        report = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            left=ReportSide(),
            right=ReportSide(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )
        assert report.report.canonical_schema_version == "1.0.0"

    def test_exact_payoff_schema_version_accepted(self) -> None:
        report = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            left=ReportSide(),
            right=ReportSide(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )
        assert report.report.payoff_schema_version == "1.0.0"


class TestUpstreamLimitTypes:
    """Requirement 1: actual upstream limit classes used."""

    def test_shadow_limits_rejected(self) -> None:
        class FakeValidationLimits:
            max_depth: int = 64
            max_unique_nodes: int = 4096

        with pytest.raises(ValidationEquivalenceInputError):
            LimitsUsed(validation=FakeValidationLimits())  # type: ignore[arg-type]

    def test_actual_upstream_validation_limits_accepted(self) -> None:
        from derivatrace.contracts import ValidationLimits as UpstreamVL

        lu = LimitsUsed(validation=UpstreamVL())
        assert type(lu.validation) is UpstreamVL

    def test_actual_upstream_canonicalization_limits_accepted(self) -> None:
        from derivatrace.canonical import CanonicalizationLimits as UpstreamCL

        lu = LimitsUsed(canonicalization=UpstreamCL())
        assert type(lu.canonicalization) is UpstreamCL

    def test_actual_upstream_payoff_limits_accepted(self) -> None:
        from derivatrace.payoffgraph import PayoffGraphLimits as UpstreamPL

        lu = LimitsUsed(payoff=UpstreamPL())
        assert type(lu.payoff) is UpstreamPL

    def test_subclass_limit_rejected(self) -> None:
        class SubLimits(ValidationLimits):
            pass

        with pytest.raises(ValidationEquivalenceInputError):
            LimitsUsed(validation=SubLimits())


class TestImmutableValuePolicy:
    """Requirement 4: no mutable collection leakage."""

    def test_dict_diff_entry_left_value_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffEntry(
                path="/x",
                op=DiffOperation.CHANGE,
                left_value={"key": "val"},
            )

    def test_list_diff_entry_left_value_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffEntry(
                path="/x",
                op=DiffOperation.CHANGE,
                left_value=[1, 2, 3],
            )

    def test_dict_diff_entry_right_value_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffEntry(
                path="/x",
                op=DiffOperation.CHANGE,
                right_value={"key": "val"},
            )

    def test_list_diff_entry_right_value_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            DiffEntry(
                path="/x",
                op=DiffOperation.CHANGE,
                right_value=[1, 2, 3],
            )

    def test_tuple_subclass_failures_rejected(self) -> None:
        class MyTuple(tuple[CapturedFailure, ...]):
            pass

        with pytest.raises(ValidationEquivalenceInputError):
            ReportSide(
                contract_identity="canonical:sha256:" + "a" * 64,
                failures=MyTuple(),
            )

    def test_tuple_subclass_entries_rejected(self) -> None:
        class MyTuple(tuple[DiffEntry, ...]):
            pass

        with pytest.raises(ValidationEquivalenceInputError):
            DiffSummary(entries=MyTuple())

    def test_bytearray_structural_bytes_rejected(self) -> None:
        report = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            left=ReportSide(),
            right=ReportSide(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )
        with pytest.raises(ValidationEquivalenceInputError):
            ValidationEquivalenceReport(
                report.report,
                bytearray(report.structural_bytes),  # type: ignore[arg-type]
                report.report_bytes,
            )

    def test_memoryview_structural_bytes_rejected(self) -> None:
        report = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            left=ReportSide(),
            right=ReportSide(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )
        with pytest.raises(ValidationEquivalenceInputError):
            ValidationEquivalenceReport(
                report.report,
                memoryview(report.structural_bytes),  # type: ignore[arg-type]
                report.report_bytes,
            )


class TestStatusReasonRejection:
    """Requirement 5: not_comparable + shallower_level_requested rejected."""

    def test_not_comparable_with_shallower_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            validate_comparison_coherence(
                ComparisonStatus.NOT_COMPARABLE,
                ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            )


class TestCapturedFailureCodeValidation:
    """Requirement 6: namespace, ASCII, whitespace, exception-like codes."""

    def test_wrong_namespace_structural_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="canonicalization.bad",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_wrong_namespace_canonical_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.CANONICAL,
                code="validation.bad",
                classification=CapturedFailureClassification.CANONICALIZATION_FAILURE,
            )

    def test_wrong_namespace_payoff_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.PAYOFF,
                code="validation.bad",
                classification=CapturedFailureClassification.PAYOFF_COMPILATION_FAILURE,
            )

    def test_empty_code_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_whitespace_code_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="validation bad",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_newline_code_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="validation\nbad",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_exception_message_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="ValueError: something went wrong",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_traceback_like_code_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code='File "test.py", line 1',
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_exception_parens_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="RuntimeError()",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_non_ascii_code_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="validation.\u00e9",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_correct_structural_namespace_accepted(self) -> None:
        f = CapturedFailure(
            stage=FailureStage.STRUCTURAL,
            code="contract.input",
            classification=CapturedFailureClassification.VALIDATION_FAILURE,
        )
        assert f.code == "contract.input"

    def test_correct_canonical_namespace_accepted(self) -> None:
        f = CapturedFailure(
            stage=FailureStage.CANONICAL,
            code="canonicalization.bad_input",
            classification=CapturedFailureClassification.CANONICALIZATION_FAILURE,
        )
        assert f.code == "canonicalization.bad_input"

    def test_correct_payoff_namespace_accepted(self) -> None:
        f = CapturedFailure(
            stage=FailureStage.PAYOFF,
            code="payoff_graph.compile",
            classification=CapturedFailureClassification.PAYOFF_COMPILATION_FAILURE,
        )
        assert f.code == "payoff_graph.compile"


class TestReportConstructionPath:
    """Requirement 7: single construction path, no empty report_id."""

    def test_no_complete_report_with_empty_id(self) -> None:
        """CompleteReport(report_id='') must be rejected."""
        with pytest.raises(ValidationEquivalenceInputError):
            CompleteReport(
                report_id="",
                schema_name="derivatrace.validation-equivalence.report",
                schema_version="1.0.0",
                requested_level=ValidationLevel.CANONICAL,
                canonical_schema_version="1.0.0",
                payoff_schema_version="1.0.0",
                left_validation_outcome=ValidationOutcome.VALID,
                right_validation_outcome=ValidationOutcome.VALID,
                canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                canonical_comparison_reason=None,
                payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                left=ReportSide(),
                right=ReportSide(),
                diff_representation=DiffSelection.NONE,
                diff_summary=DiffSummary(),
                limits_used=LimitsUsed(),
                schema_metadata=SchemaMetadataRecord(),
                provenance=ProvenanceRecord(),
            )

    def test_only_one_factory_path_exported(self) -> None:
        """Only _build_report is exported as the internal factory."""
        from derivatrace.validation_equivalence import _report as report_mod

        assert hasattr(report_mod, "_build_report")
        assert not hasattr(report_mod, "build_wrapped_report")
        public = [n for n in dir(report_mod) if not n.startswith("_")]
        assert "build_wrapped_report" not in public


class TestIdentityAndEncodingErrorMapping:
    """Requirement 8: normalized identity and encoding error messages."""

    def test_structural_projection_failure_message(self) -> None:
        import derivatrace.validation_equivalence._report as report_mod

        original = report_mod.structural_bytes

        def _fail(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("underlying")

        report_mod.structural_bytes = _fail
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                _build_report(
                    requested_level=ValidationLevel.CANONICAL,
                    canonical_schema_version=CanonicalSchemaVersion(),
                    payoff_schema_version=PayoffGraphSchemaVersion(),
                    left_validation_outcome=ValidationOutcome.VALID,
                    right_validation_outcome=ValidationOutcome.VALID,
                    canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                    canonical_comparison_reason=None,
                    payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                    payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                    left=ReportSide(),
                    right=ReportSide(),
                    diff_representation=DiffSelection.NONE,
                    diff_summary=DiffSummary(),
                    limits_used=LimitsUsed(),
                    schema_metadata=SchemaMetadataRecord(),
                )
            assert "failed to encode structural projection" in str(exc_info.value)
            assert "underlying" not in str(exc_info.value)
        finally:
            report_mod.structural_bytes = original

    def test_complete_report_failure_message(self) -> None:
        report = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            left=ReportSide(),
            right=ReportSide(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )
        import derivatrace.validation_equivalence._report as report_mod

        original_encode = report_mod._encode_report

        def _fail(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("underlying")

        report_mod._encode_report = _fail
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                ValidationEquivalenceReport(
                    report.report,
                    report.structural_bytes,
                    encode_report(report.report),
                )
            assert "failed to encode complete report" in str(exc_info.value)
            assert "underlying" not in str(exc_info.value)
        finally:
            report_mod._encode_report = original_encode

    def test_encoding_error_not_in_encoding_all(self) -> None:
        """ValidationEquivalenceEncodingError must not be in _encoding.__all__."""
        from derivatrace.validation_equivalence import _encoding as enc_mod

        assert "ValidationEquivalenceEncodingError" not in enc_mod.__all__


# ---------------------------------------------------------------------------
# Remaining coverage: _records.py _validate_identity non-str branch
# ---------------------------------------------------------------------------


class TestValidateIdentityNonStr:
    def test_int_identity_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(123, "canonical:sha256:", "test")  # type: ignore[arg-type]

    def test_bool_identity_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _validate_identity(True, "canonical:sha256:", "test")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Remaining coverage: control character in failure code
# ---------------------------------------------------------------------------


class TestCapturedFailureControlChar:
    def test_control_char_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="validation.\x01bad",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_tab_in_code_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="validation.\tbad",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_carriage_return_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="validation.\rbad",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )


# ---------------------------------------------------------------------------
# Remaining coverage: _StructuralPayload type checks
# ---------------------------------------------------------------------------


class TestStructuralPayloadTypeChecks:
    def _valid_kwargs(self) -> dict[str, object]:
        return {
            "schema_name": "derivatrace.validation-equivalence.report",
            "schema_version": "1.0.0",
            "requested_level": ValidationLevel.CANONICAL,
            "canonical_schema_version": "1.0.0",
            "payoff_schema_version": "1.0.0",
            "left_validation_outcome": ValidationOutcome.VALID,
            "right_validation_outcome": ValidationOutcome.VALID,
            "canonical_comparison_status": ComparisonStatus.EQUIVALENT,
            "canonical_comparison_reason": None,
            "payoff_comparison_status": ComparisonStatus.NOT_EVALUATED,
            "payoff_comparison_reason": ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            "left": ReportSide(),
            "right": ReportSide(),
            "diff_representation": DiffSelection.NONE,
            "diff_summary": DiffSummary(),
            "limits_used": LimitsUsed(),
            "schema_metadata": SchemaMetadataRecord(),
        }

    def test_wrong_schema_name(self) -> None:
        kw = self._valid_kwargs()
        kw["schema_name"] = "wrong"
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]

    def test_wrong_schema_version(self) -> None:
        kw = self._valid_kwargs()
        kw["schema_version"] = "2.0.0"
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]

    def test_canonical_schema_version_not_str(self) -> None:
        kw = self._valid_kwargs()
        kw["canonical_schema_version"] = 123  # type: ignore[assignment]
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]

    def test_payoff_schema_version_not_str(self) -> None:
        kw = self._valid_kwargs()
        kw["payoff_schema_version"] = 123  # type: ignore[assignment]
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]

    def test_diff_summary_wrong_type(self) -> None:
        kw = self._valid_kwargs()
        kw["diff_summary"] = "bad"  # type: ignore[assignment]
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]

    def test_left_wrong_type(self) -> None:
        kw = self._valid_kwargs()
        kw["left"] = "bad"  # type: ignore[assignment]
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]

    def test_right_wrong_type(self) -> None:
        kw = self._valid_kwargs()
        kw["right"] = "bad"  # type: ignore[assignment]
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]

    def test_limits_used_wrong_type(self) -> None:
        kw = self._valid_kwargs()
        kw["limits_used"] = "bad"  # type: ignore[assignment]
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]

    def test_schema_metadata_wrong_type(self) -> None:
        kw = self._valid_kwargs()
        kw["schema_metadata"] = "bad"  # type: ignore[assignment]
        with pytest.raises(ValidationEquivalenceInputError):
            _StructuralPayload(**kw)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Remaining coverage: _report.py payoff_schema_version type check
# ---------------------------------------------------------------------------


class TestBuildReportSchemaVersionChecks:
    def test_payoff_schema_version_wrong_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(
                requested_level=ValidationLevel.CANONICAL,
                canonical_schema_version=CanonicalSchemaVersion(),
                payoff_schema_version="1.0.0",  # type: ignore[arg-type]
                left_validation_outcome=ValidationOutcome.VALID,
                right_validation_outcome=ValidationOutcome.VALID,
                canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                canonical_comparison_reason=None,
                payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                left=ReportSide(),
                right=ReportSide(),
                diff_representation=DiffSelection.NONE,
                diff_summary=DiffSummary(),
                limits_used=LimitsUsed(),
                schema_metadata=SchemaMetadataRecord(),
            )

    def test_canonical_schema_version_wrong_type(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(
                requested_level=ValidationLevel.CANONICAL,
                canonical_schema_version="1.0.0",  # type: ignore[arg-type]
                payoff_schema_version=PayoffGraphSchemaVersion(),
                left_validation_outcome=ValidationOutcome.VALID,
                right_validation_outcome=ValidationOutcome.VALID,
                canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                canonical_comparison_reason=None,
                payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                left=ReportSide(),
                right=ReportSide(),
                diff_representation=DiffSelection.NONE,
                diff_summary=DiffSummary(),
                limits_used=LimitsUsed(),
                schema_metadata=SchemaMetadataRecord(),
            )


# ---------------------------------------------------------------------------
# Remaining coverage: _report.py report_bytes type check in __post_init__
# ---------------------------------------------------------------------------


class TestWrappedReportBytesTypeCheck:
    def test_report_bytes_not_bytes(self) -> None:
        report = _build_report(
            requested_level=ValidationLevel.CANONICAL,
            canonical_schema_version=CanonicalSchemaVersion(),
            payoff_schema_version=PayoffGraphSchemaVersion(),
            left_validation_outcome=ValidationOutcome.VALID,
            right_validation_outcome=ValidationOutcome.VALID,
            canonical_comparison_status=ComparisonStatus.EQUIVALENT,
            canonical_comparison_reason=None,
            payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
            payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
            left=ReportSide(),
            right=ReportSide(),
            diff_representation=DiffSelection.NONE,
            diff_summary=DiffSummary(),
            limits_used=LimitsUsed(),
            schema_metadata=SchemaMetadataRecord(),
        )
        with pytest.raises(ValidationEquivalenceInputError):
            ValidationEquivalenceReport(
                report.report,
                report.structural_bytes,
                "not_bytes",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# Remaining coverage: _report.py _build_report encode failure in step 7
# ---------------------------------------------------------------------------


class TestBuildReportEncodeFailure:
    def test_encode_report_failure_in_build_report(self) -> None:
        import derivatrace.validation_equivalence._report as report_mod

        original = report_mod._encode_report

        def _fail(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("injected")

        report_mod._encode_report = _fail
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                _build_report(
                    requested_level=ValidationLevel.CANONICAL,
                    canonical_schema_version=CanonicalSchemaVersion(),
                    payoff_schema_version=PayoffGraphSchemaVersion(),
                    left_validation_outcome=ValidationOutcome.VALID,
                    right_validation_outcome=ValidationOutcome.VALID,
                    canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                    canonical_comparison_reason=None,
                    payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                    payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                    left=ReportSide(),
                    right=ReportSide(),
                    diff_representation=DiffSelection.NONE,
                    diff_summary=DiffSummary(),
                    limits_used=LimitsUsed(),
                    schema_metadata=SchemaMetadataRecord(),
                )
            assert "failed to encode complete report" in str(exc_info.value)
            assert "injected" not in str(exc_info.value)
        finally:
            report_mod._encode_report = original


# ---------------------------------------------------------------------------
# Remaining coverage: _report.py report_identity failure paths
# ---------------------------------------------------------------------------


class TestBuildReportIdentityFailure:
    def test_report_identity_failure(self) -> None:
        import derivatrace.validation_equivalence._report as report_mod

        original = report_mod.report_identity

        def _fail_identity(data: bytes) -> str:
            raise ValidationEquivalenceEncodingError("identity failure")

        report_mod.report_identity = _fail_identity
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                _build_report(
                    requested_level=ValidationLevel.CANONICAL,
                    canonical_schema_version=CanonicalSchemaVersion(),
                    payoff_schema_version=PayoffGraphSchemaVersion(),
                    left_validation_outcome=ValidationOutcome.VALID,
                    right_validation_outcome=ValidationOutcome.VALID,
                    canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                    canonical_comparison_reason=None,
                    payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                    payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                    left=ReportSide(),
                    right=ReportSide(),
                    diff_representation=DiffSelection.NONE,
                    diff_summary=DiffSummary(),
                    limits_used=LimitsUsed(),
                    schema_metadata=SchemaMetadataRecord(),
                )
            assert "failed to encode structural projection" in str(exc_info.value)
        finally:
            report_mod.report_identity = original

    def test_structural_bytes_mismatch_forge_detected(self) -> None:
        import derivatrace.validation_equivalence._report as report_mod

        original_sbytes = report_mod.structural_bytes
        original_rid = report_mod.report_identity
        call_count = 0

        def _intercepting_sbytes(obj: object, *args: object, **kwargs: object) -> bytes:
            nonlocal call_count
            call_count += 1
            real = original_sbytes(obj, *args, **kwargs)  # type: ignore[misc]
            if call_count == 2:
                return real + b"\x00"
            return real

        report_mod.structural_bytes = _intercepting_sbytes  # type: ignore[assignment]
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                _build_report(
                    requested_level=ValidationLevel.CANONICAL,
                    canonical_schema_version=CanonicalSchemaVersion(),
                    payoff_schema_version=PayoffGraphSchemaVersion(),
                    left_validation_outcome=ValidationOutcome.VALID,
                    right_validation_outcome=ValidationOutcome.VALID,
                    canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                    canonical_comparison_reason=None,
                    payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                    payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                    left=ReportSide(),
                    right=ReportSide(),
                    diff_representation=DiffSelection.NONE,
                    diff_summary=DiffSummary(),
                    limits_used=LimitsUsed(),
                    schema_metadata=SchemaMetadataRecord(),
                )
            assert "structural bytes mismatch" in str(exc_info.value)
        finally:
            report_mod.structural_bytes = original_sbytes
            report_mod.report_identity = original_rid

    def test_report_id_mismatch_forge_detected(self) -> None:
        import derivatrace.validation_equivalence._report as report_mod

        original_sbytes = report_mod.structural_bytes
        original_rid = report_mod.report_identity
        rid_call_count = 0

        def _intercepting_rid(data: bytes) -> str:
            nonlocal rid_call_count
            rid_call_count += 1
            real = original_rid(data)
            if rid_call_count == 2:
                return "validation-equivalence:sha256:" + "0" * 64
            return real

        report_mod.report_identity = _intercepting_rid
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                _build_report(
                    requested_level=ValidationLevel.CANONICAL,
                    canonical_schema_version=CanonicalSchemaVersion(),
                    payoff_schema_version=PayoffGraphSchemaVersion(),
                    left_validation_outcome=ValidationOutcome.VALID,
                    right_validation_outcome=ValidationOutcome.VALID,
                    canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                    canonical_comparison_reason=None,
                    payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                    payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                    left=ReportSide(),
                    right=ReportSide(),
                    diff_representation=DiffSelection.NONE,
                    diff_summary=DiffSummary(),
                    limits_used=LimitsUsed(),
                    schema_metadata=SchemaMetadataRecord(),
                )
            assert "report_id mismatch" in str(exc_info.value)
        finally:
            report_mod.structural_bytes = original_sbytes
            report_mod.report_identity = original_rid

    def test_recomputed_structural_bytes_exception(self) -> None:
        import derivatrace.validation_equivalence._report as report_mod

        original_sbytes = report_mod.structural_bytes
        call_count = 0

        def _fail_on_second(obj: object, *args: object, **kwargs: object) -> bytes:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValidationEquivalenceEncodingError("recompute failure")
            return original_sbytes(obj, *args, **kwargs)  # type: ignore[misc]

        report_mod.structural_bytes = _fail_on_second  # type: ignore[assignment]
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                _build_report(
                    requested_level=ValidationLevel.CANONICAL,
                    canonical_schema_version=CanonicalSchemaVersion(),
                    payoff_schema_version=PayoffGraphSchemaVersion(),
                    left_validation_outcome=ValidationOutcome.VALID,
                    right_validation_outcome=ValidationOutcome.VALID,
                    canonical_comparison_status=ComparisonStatus.EQUIVALENT,
                    canonical_comparison_reason=None,
                    payoff_comparison_status=ComparisonStatus.NOT_EVALUATED,
                    payoff_comparison_reason=ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
                    left=ReportSide(),
                    right=ReportSide(),
                    diff_representation=DiffSelection.NONE,
                    diff_summary=DiffSummary(),
                    limits_used=LimitsUsed(),
                    schema_metadata=SchemaMetadataRecord(),
                )
            assert "failed to encode structural projection" in str(exc_info.value)
        finally:
            report_mod.structural_bytes = original_sbytes
