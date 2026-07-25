from __future__ import annotations

from typing import Any

import pytest

from derivatrace.canonical import CanonicalSchemaVersion
from derivatrace.payoffgraph import PayoffGraphSchemaVersion
from derivatrace.validation_equivalence._encoding import (
    encode_report,
    structural_bytes,
)
from derivatrace.validation_equivalence._errors import (
    ValidationEquivalenceEncodingError,
    ValidationEquivalenceInputError,
    ValidationEquivalenceReportCollisionError,
    ValidationEquivalenceUnsupportedLevelError,
)
from derivatrace.validation_equivalence._identity import _digest, report_identity
from derivatrace.validation_equivalence._records import (
    CapturedFailure,
    CompleteReport,
    DiffEntry,
    DiffSummary,
    LimitsUsed,
    ReportSide,
    SchemaMetadataRecord,
)
from derivatrace.validation_equivalence._report import (
    ValidationEquivalenceReport,
    _build_report,
)
from derivatrace.validation_equivalence._schema import (
    CapturedFailureClassification,
    ComparisonReason,
    ComparisonStatus,
    DiffOperation,
    DiffSelection,
    FailureStage,
    TruncationReason,
    UnavailableReason,
    ValidationLevel,
    ValidationOutcome,
)


def _valid_side() -> ReportSide:
    return ReportSide(
        contract_identity="canonical:sha256:" + "a" * 64,
        payoff_graph_identity=None,
        failures=(),
    )


def _default_report_kwargs() -> dict[str, Any]:
    """Return default kwargs for _build_report."""
    return {
        "requested_level": ValidationLevel.CANONICAL,
        "canonical_schema_version": CanonicalSchemaVersion(),
        "payoff_schema_version": PayoffGraphSchemaVersion(),
        "left_validation_outcome": ValidationOutcome.VALID,
        "right_validation_outcome": ValidationOutcome.VALID,
        "canonical_comparison_status": ComparisonStatus.EQUIVALENT,
        "canonical_comparison_reason": None,
        "payoff_comparison_status": ComparisonStatus.NOT_EVALUATED,
        "payoff_comparison_reason": ComparisonReason.SHALLOWER_LEVEL_REQUESTED,
        "left": _valid_side(),
        "right": _valid_side(),
        "diff_representation": DiffSelection.NONE,
        "diff_summary": DiffSummary(
            entries=(),
            truncated=False,
            truncation_reason=None,
            unavailable_reason=None,
        ),
        "limits_used": LimitsUsed(),
        "schema_metadata": SchemaMetadataRecord(),
    }


def _build_report_with_real_id(**overrides: Any) -> CompleteReport:
    """Build a CompleteReport through _build_report and return the inner report."""
    r = _build_report(**overrides)
    return r.report


class TestVe014ProvenanceOnlyDiff:
    """ve_014: equal structural projection, different excluded provenance,
    identical report_id."""

    def test_identical_report_id_despite_provenance_difference(self) -> None:
        kwargs = _default_report_kwargs()

        report_a = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "a" * 64,
            source_right_identity="canonical:sha256:" + "b" * 64,
        )
        report_b = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "c" * 64,
            source_right_identity="canonical:sha256:" + "d" * 64,
        )

        assert report_a.report_id == report_b.report_id

    def test_structural_bytes_identical_despite_provenance(self) -> None:
        kwargs = _default_report_kwargs()

        report_a = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "a" * 64,
            source_right_identity="canonical:sha256:" + "b" * 64,
        )
        report_b = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "c" * 64,
            source_right_identity="canonical:sha256:" + "d" * 64,
        )

        s_a = structural_bytes(report_a.report)
        s_b = structural_bytes(report_b.report)
        assert s_a == s_b

    def test_provenance_excluded_from_report_id_preimage(self) -> None:
        kwargs = _default_report_kwargs()

        report_with = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "a" * 64,
            source_right_identity="canonical:sha256:" + "b" * 64,
        )
        report_without = _build_report(
            **kwargs,
            source_left_identity=None,
            source_right_identity=None,
        )

        assert report_with.report_id == report_without.report_id


class TestVe014CompleteReportBytes:
    """ve_014 proves different complete bytes with same structural bytes."""

    def test_different_provenance_different_complete_bytes(self) -> None:
        kwargs = _default_report_kwargs()

        report_a = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "a" * 64,
            source_right_identity="canonical:sha256:" + "b" * 64,
        )
        report_b = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "c" * 64,
            source_right_identity="canonical:sha256:" + "d" * 64,
        )

        assert report_a.structural_bytes == report_b.structural_bytes
        assert report_a.report_id == report_b.report_id
        assert report_a.report_bytes != report_b.report_bytes

    def test_ve_014_wrapped_reports_compare_equal(self) -> None:
        kwargs = _default_report_kwargs()

        a = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "a" * 64,
            source_right_identity="canonical:sha256:" + "b" * 64,
        )
        b = _build_report(
            **kwargs,
            source_left_identity="canonical:sha256:" + "c" * 64,
            source_right_identity="canonical:sha256:" + "d" * 64,
        )

        assert a == b
        assert a.report_bytes != b.report_bytes


class TestVe037ReportEncodingFailureRaises:
    """ve_037: injected deterministic report-encoder failure raises
    validation_equivalence.encoding."""

    def test_encoding_failure_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _failing_structural(obj: object, encoder: object = None) -> bytes:
            raise ValidationEquivalenceEncodingError("injected failure")

        import derivatrace.validation_equivalence._report as report_mod

        monkeypatch.setattr(report_mod, "structural_bytes", _failing_structural)
        with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
            _build_report(**_default_report_kwargs())
        assert "injected failure" not in str(exc_info.value)
        assert "failed to encode structural projection" in str(exc_info.value)

    def test_structural_bytes_encoding_failure_raises(self) -> None:
        def _failing_encoder(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("injected failure")

        report = _build_report(**_default_report_kwargs())
        with pytest.raises(ValidationEquivalenceEncodingError):
            structural_bytes(report.report, _failing_encoder)


class TestReportCollision:
    """Collision defence without global state."""

    def test_same_report_id_same_bytes_equal(self) -> None:
        kwargs = _default_report_kwargs()
        report = _build_report(**kwargs)

        a = ValidationEquivalenceReport(
            report.report, report.structural_bytes, report.report_bytes
        )
        b = ValidationEquivalenceReport(
            report.report, report.structural_bytes, report.report_bytes
        )
        assert a == b

    def test_same_report_id_different_bytes_raises(self) -> None:
        kwargs = _default_report_kwargs()
        report = _build_report(**kwargs)

        fake_bytes = b"different structural bytes"

        with pytest.raises(ValidationEquivalenceEncodingError):
            ValidationEquivalenceReport(report.report, fake_bytes, report.report_bytes)

    def test_forced_collision_same_report_id_different_bytes(self) -> None:
        """Forced collision: two internally-consistent reports that hash to the
        same report_id but carry different structural bytes raise the collision
        error on equality (only constructible via the monkeypatched digest seam).
        """
        kwargs = _default_report_kwargs()

        original = _digest

        def _fake_digest(domain: str, version: str, payload: bytes) -> str:
            return "f" * 64

        import derivatrace.validation_equivalence._identity as id_mod

        id_mod._digest = _fake_digest
        try:
            report_a = _build_report(**kwargs)
            kwargs_b = _default_report_kwargs()
            kwargs_b["canonical_comparison_status"] = ComparisonStatus.DIFFERENT
            report_b = _build_report(**kwargs_b)

            assert report_a.report_id == report_b.report_id
            assert report_a.structural_bytes != report_b.structural_bytes

            a = ValidationEquivalenceReport(
                report_a.report, report_a.structural_bytes, report_a.report_bytes
            )
            b = ValidationEquivalenceReport(
                report_b.report, report_b.structural_bytes, report_b.report_bytes
            )
        finally:
            id_mod._digest = original

        with pytest.raises(ValidationEquivalenceReportCollisionError):
            _ = a == b

    def test_different_report_id_not_equal(self) -> None:
        kwargs1 = _default_report_kwargs()
        report1 = _build_report(**kwargs1)

        kwargs2 = _default_report_kwargs()
        kwargs2["canonical_comparison_status"] = ComparisonStatus.DIFFERENT
        report2 = _build_report(**kwargs2)

        a = ValidationEquivalenceReport(
            report1.report, report1.structural_bytes, report1.report_bytes
        )
        b = ValidationEquivalenceReport(
            report2.report, report2.structural_bytes, report2.report_bytes
        )
        assert a != b
        assert a != "not a report"

    def test_hash_based_on_report_id(self) -> None:
        kwargs = _default_report_kwargs()
        report = _build_report(**kwargs)

        a = ValidationEquivalenceReport(
            report.report, report.structural_bytes, report.report_bytes
        )
        b = ValidationEquivalenceReport(
            report.report, report.structural_bytes, report.report_bytes
        )
        assert hash(a) == hash(b)
        assert hash(a) == hash(report.report_id)

    def test_digest_seam_monkeypatchable(self) -> None:
        """The private digest seam may be monkeypatched in tests."""
        original = _digest

        def _fake_digest(domain: str, version: str, payload: bytes) -> str:
            return "a" * 64

        import derivatrace.validation_equivalence._identity as id_mod

        id_mod._digest = _fake_digest
        try:
            rid = report_identity(b"test")
            assert rid == "validation-equivalence:sha256:" + "a" * 64
        finally:
            id_mod._digest = original


class TestReportConstruction:
    """Test basic report construction and encoding."""

    def test_report_id_non_null(self) -> None:
        report = _build_report(**_default_report_kwargs())
        assert report.report_id
        assert report.report_id.startswith("validation-equivalence:sha256:")

    def test_report_id_is_64_hex(self) -> None:
        report = _build_report(**_default_report_kwargs())
        hex_part = report.report_id.split("validation-equivalence:sha256:")[1]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_report_encoding_roundtrip(self) -> None:
        report = _build_report(**_default_report_kwargs())
        encoded = encode_report(report.report)
        assert isinstance(encoded, bytes)
        assert b"derivatrace.validation-equivalence.report" in encoded

    def test_wrapped_report(self) -> None:
        wrapped = _build_report(**_default_report_kwargs())
        assert isinstance(wrapped, ValidationEquivalenceReport)
        assert wrapped.report_id.startswith("validation-equivalence:sha256:")

    def test_diff_none_empty_entries(self) -> None:
        report = _build_report(**_default_report_kwargs())
        assert report.report.diff_representation is DiffSelection.NONE
        assert report.report.diff_summary.entries == ()
        assert report.report.diff_summary.truncated is False
        assert report.report.diff_summary.truncation_reason is None
        assert report.report.diff_summary.unavailable_reason is None

    def test_report_equality_semantics(self) -> None:
        kwargs = _default_report_kwargs()
        a = _build_report(**kwargs)
        b = _build_report(**kwargs)
        assert a == b
        assert hash(a) == hash(b)

    def test_report_repr(self) -> None:
        report = _build_report(**_default_report_kwargs())
        r = repr(report)
        assert "ValidationEquivalenceReport" in r
        assert "validation-equivalence:sha256:" in r


class TestNestedLimitsUsed:
    """limits_used serializes as exact nested JSON tree."""

    def test_limits_used_nested_structure(self) -> None:
        report = _build_report(**_default_report_kwargs())
        d = report.report.limits_used
        assert isinstance(d.validation.max_depth, int)
        assert d.validation.max_depth == 64
        assert d.validation.max_unique_nodes == 4096
        assert d.canonicalization.max_canonical_nodes == 16384
        assert d.canonicalization.max_canonical_bytes == 8_000_000
        assert d.payoff.max_payoff_nodes == 4096
        assert d.payoff.max_document_bytes == 4_194_304
        assert d.payoff.max_structural_bytes == 2_097_152
        assert d.diff.max_compared_bytes == 2_097_152
        assert d.diff.max_compared_nodes == 4096
        assert d.diff.max_entries == 1024
        assert d.diff.max_report_bytes == 8_388_608
        assert d.diff.max_path_length == 256

    def test_limits_used_json_roundtrip(self) -> None:
        report = _build_report(**_default_report_kwargs())
        s_bytes = report.structural_bytes
        import json

        parsed = json.loads(s_bytes)
        lu = parsed["limits_used"]
        assert "validation" in lu
        assert "canonicalization" in lu
        assert "payoff" in lu
        assert "diff" in lu
        assert lu["validation"]["max_depth"] == 64
        assert lu["canonicalization"]["max_canonical_bytes"] == 8_000_000
        assert lu["payoff"]["max_structural_bytes"] == 2_097_152
        assert lu["diff"]["max_entries"] == 1024


class TestNestedSchemaMetadata:
    """schema_metadata serializes as exact nested JSON tree."""

    def test_schema_metadata_nested_structure(self) -> None:
        report = _build_report(**_default_report_kwargs())
        sm = report.report.schema_metadata
        assert sm.canonical.schema_name == "derivatrace.contract.canonical"
        assert sm.canonical.schema_version == "1.0.0"
        assert sm.canonical.node_identity_domain == "derivatrace.canonical.node"
        assert sm.canonical.representation_identity_domain == (
            "derivatrace.canonical.contract"
        )
        assert sm.payoff.schema_name == "derivatrace.payoffgraph"
        assert sm.payoff.schema_version == "1.0.0"
        assert sm.payoff.node_identity_domain == "derivatrace.payoffgraph.node"
        assert sm.payoff.representation_identity_domain == (
            "derivatrace.payoffgraph.graph"
        )

    def test_schema_metadata_json_roundtrip(self) -> None:
        report = _build_report(**_default_report_kwargs())
        s_bytes = report.structural_bytes
        import json

        parsed = json.loads(s_bytes)
        sm = parsed["schema_metadata"]
        assert "canonical" in sm
        assert "payoff" in sm
        assert sm["canonical"]["schema_name"] == "derivatrace.contract.canonical"
        assert sm["payoff"]["representation_identity_domain"] == (
            "derivatrace.payoffgraph.graph"
        )


class TestFactoryIdentityVerification:
    """Factory recomputes and verifies identity."""

    def test_constructor_recomputes_identity(self) -> None:
        wrapped = _build_report(**_default_report_kwargs())
        assert wrapped.report_id.startswith("validation-equivalence:sha256:")

    def test_structural_bytes_retained(self) -> None:
        wrapped = _build_report(**_default_report_kwargs())
        assert isinstance(wrapped.structural_bytes, bytes)
        assert len(wrapped.structural_bytes) > 0

    def test_complete_report_bytes_retained(self) -> None:
        wrapped = _build_report(**_default_report_kwargs())
        assert isinstance(wrapped.report_bytes, bytes)
        assert len(wrapped.report_bytes) > 0

    def test_forged_report_id_rejected(self) -> None:
        report = _build_report(**_default_report_kwargs())
        with pytest.raises(ValidationEquivalenceReportCollisionError):
            CompleteReport(
                report_id="validation-equivalence:sha256:" + "f" * 64,
                schema_name=report.report.schema_name,
                schema_version=report.report.schema_version,
                requested_level=report.report.requested_level,
                canonical_schema_version=report.report.canonical_schema_version,
                payoff_schema_version=report.report.payoff_schema_version,
                left_validation_outcome=report.report.left_validation_outcome,
                right_validation_outcome=report.report.right_validation_outcome,
                canonical_comparison_status=report.report.canonical_comparison_status,
                canonical_comparison_reason=report.report.canonical_comparison_reason,
                payoff_comparison_status=report.report.payoff_comparison_status,
                payoff_comparison_reason=report.report.payoff_comparison_reason,
                left=report.report.left,
                right=report.report.right,
                diff_representation=report.report.diff_representation,
                diff_summary=report.report.diff_summary,
                limits_used=report.report.limits_used,
                schema_metadata=report.report.schema_metadata,
                provenance=report.report.provenance,
            )

    def test_mismatched_structural_bytes_rejected(self) -> None:
        report = _build_report(**_default_report_kwargs())
        with pytest.raises(ValidationEquivalenceEncodingError):
            ValidationEquivalenceReport(
                report.report, b"different", report.report_bytes
            )

    def test_mismatched_complete_report_bytes_rejected(self) -> None:
        report = _build_report(**_default_report_kwargs())
        with pytest.raises(ValidationEquivalenceEncodingError):
            ValidationEquivalenceReport(
                report.report, report.structural_bytes, b"different"
            )


class TestR1ARejectsNonNoneDiffState:
    """R1A rejects every non-none diff state."""

    def test_rejects_canonical_diff(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["diff_representation"] = DiffSelection.CANONICAL
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_rejects_payoff_diff(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["diff_representation"] = DiffSelection.PAYOFF
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_rejects_non_empty_entries(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["diff_summary"] = DiffSummary(
            entries=(DiffEntry(path="/root", op=DiffOperation.CHANGE),),
            truncated=False,
            truncation_reason=None,
            unavailable_reason=None,
        )
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_rejects_truncated_true(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["diff_summary"] = DiffSummary(
            entries=(),
            truncated=True,
            truncation_reason=None,
            unavailable_reason=None,
        )
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_rejects_truncation_reason(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["diff_summary"] = DiffSummary(
            entries=(),
            truncated=False,
            truncation_reason=TruncationReason.ENTRY_LIMIT,
            unavailable_reason=None,
        )
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_rejects_unavailable_reason(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["diff_summary"] = DiffSummary(
            entries=(),
            truncated=False,
            truncation_reason=None,
            unavailable_reason=UnavailableReason.COMPARISON_LIMIT_EXCEEDED,
        )
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)


class TestClosedEnumsRejectRawStrings:
    """All closed enum types reject raw strings."""

    def test_validation_level_rejects_string(self) -> None:
        with pytest.raises(ValidationEquivalenceUnsupportedLevelError):
            _build_report(
                **{**_default_report_kwargs(), "requested_level": "canonical"}
            )

    def test_diff_selection_rejects_string(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(
                **{
                    **_default_report_kwargs(),
                    "diff_representation": "none",
                }
            )

    def test_validation_outcome_rejects_string(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["left_validation_outcome"] = "valid"
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)


class TestCapturedFailureValidation:
    """CapturedFailure uses exact enum types."""

    def test_exact_enum_types(self) -> None:
        f = CapturedFailure(
            stage=FailureStage.STRUCTURAL,
            code="contract.input",
            classification=CapturedFailureClassification.VALIDATION_FAILURE,
        )
        assert type(f.stage) is FailureStage
        assert type(f.classification) is CapturedFailureClassification

    def test_rejects_string_stage(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage="structural",  # type: ignore[arg-type]
                code="contract.input",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_rejects_string_classification(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="contract.input",
                classification="validation_failure",  # type: ignore[arg-type]
            )

    def test_rejects_empty_code(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            CapturedFailure(
                stage=FailureStage.STRUCTURAL,
                code="",
                classification=CapturedFailureClassification.VALIDATION_FAILURE,
            )

    def test_duplicate_failures_rejected(self) -> None:
        with pytest.raises(ValidationEquivalenceInputError):
            ReportSide(
                contract_identity="canonical:sha256:" + "a" * 64,
                failures=(
                    CapturedFailure(
                        stage=FailureStage.STRUCTURAL,
                        code="contract.input",
                        classification=CapturedFailureClassification.VALIDATION_FAILURE,
                    ),
                    CapturedFailure(
                        stage=FailureStage.STRUCTURAL,
                        code="contract.input",
                        classification=CapturedFailureClassification.VALIDATION_FAILURE,
                    ),
                ),
            )


class TestStatusReasonCoherence:
    """Invalid status/reason combinations are rejected."""

    def test_equivalent_with_reason_rejected(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["canonical_comparison_status"] = ComparisonStatus.EQUIVALENT
        kwargs["canonical_comparison_reason"] = (
            ComparisonReason.SHALLOWER_LEVEL_REQUESTED
        )
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_different_with_reason_rejected(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["canonical_comparison_status"] = ComparisonStatus.DIFFERENT
        kwargs["canonical_comparison_reason"] = (
            ComparisonReason.SHALLOWER_LEVEL_REQUESTED
        )
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_not_comparable_without_reason_rejected(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["canonical_comparison_status"] = ComparisonStatus.NOT_COMPARABLE
        kwargs["canonical_comparison_reason"] = None
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_not_evaluated_without_shallower_rejected(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["payoff_comparison_status"] = ComparisonStatus.NOT_EVALUATED
        kwargs["payoff_comparison_reason"] = ComparisonReason.UPSTREAM_STAGE_FAILURE
        with pytest.raises(ValidationEquivalenceInputError):
            _build_report(**kwargs)

    def test_not_evaluated_with_shallower_succeeds(self) -> None:
        kwargs = _default_report_kwargs()
        kwargs["payoff_comparison_status"] = ComparisonStatus.NOT_EVALUATED
        kwargs["payoff_comparison_reason"] = ComparisonReason.SHALLOWER_LEVEL_REQUESTED
        report = _build_report(**kwargs)
        assert report.report.payoff_comparison_status is ComparisonStatus.NOT_EVALUATED
        assert report.report.payoff_comparison_reason is (
            ComparisonReason.SHALLOWER_LEVEL_REQUESTED
        )
        assert report.report.payoff_comparison_status.value == "not_evaluated"
        assert (
            report.report.payoff_comparison_reason.value == "shallower_level_requested"
        )


class TestNoMutableCollectionLeakage:
    """No mutable collection leakage."""

    def test_failures_is_tuple(self) -> None:
        side = ReportSide(
            contract_identity="canonical:sha256:" + "a" * 64,
            failures=(),
        )
        assert type(side.failures) is tuple

    def test_diff_entries_is_tuple(self) -> None:
        ds = DiffSummary(entries=(), truncated=False)
        assert type(ds.entries) is tuple


class TestSafeReportIdentityInputTypes:
    """_safe_report_identity rejects None, bytes subclasses, str, int."""

    def test_none_rejected(self) -> None:
        from derivatrace.validation_equivalence._identity import _safe_report_identity

        with pytest.raises(ValidationEquivalenceReportCollisionError):
            _safe_report_identity(None)  # type: ignore[arg-type]

    def test_bytes_input_accepted(self) -> None:
        from derivatrace.validation_equivalence._identity import _safe_report_identity

        result = _safe_report_identity(b"\x00")
        assert result.startswith("validation-equivalence:sha256:")

    def test_int_rejected(self) -> None:
        from derivatrace.validation_equivalence._identity import _safe_report_identity

        with pytest.raises(ValidationEquivalenceReportCollisionError):
            _safe_report_identity(42)  # type: ignore[arg-type]

    def test_str_subclass_output_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression: a valid-looking str subclass must never be returned."""

        class IdentityString(str):
            pass

        from derivatrace.validation_equivalence import _identity as id_mod

        def _fake_report_identity(data: bytes) -> IdentityString:
            return IdentityString("validation-equivalence:sha256:" + "a" * 64)

        monkeypatch.setattr(id_mod, "report_identity", _fake_report_identity)
        with pytest.raises(ValidationEquivalenceReportCollisionError) as exc_info:
            id_mod._safe_report_identity(b"\x00")
        assert str(exc_info.value).endswith("failed to produce report identity")
        assert exc_info.value.__cause__ is None
