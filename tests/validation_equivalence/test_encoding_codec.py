from __future__ import annotations

from typing import Any

import pytest

from derivatrace.validation_equivalence._encoding import (
    canonical_json,
    encode_report,
    report_to_jsonable,
    structural_bytes,
)
from derivatrace.validation_equivalence._errors import (
    ValidationEquivalenceEncodingError,
)
from derivatrace.validation_equivalence._identity import _safe_report_identity
from derivatrace.validation_equivalence._records import (
    CapturedFailure,
    CompleteReport,
    DiffSummary,
    LimitsUsed,
    ProvenanceRecord,
    ReportSide,
    SchemaMetadataRecord,
    _StructuralPayload,
)
from derivatrace.validation_equivalence._schema import (
    CapturedFailureClassification,
    ComparisonReason,
    ComparisonStatus,
    DiffSelection,
    FailureStage,
    ValidationLevel,
    ValidationOutcome,
)


def _valid_side() -> ReportSide:
    return ReportSide(
        contract_identity="canonical:sha256:" + "a" * 64,
        payoff_graph_identity=None,
        failures=(),
    )


def _make_test_report() -> CompleteReport:
    payload = _StructuralPayload(
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
        left=_valid_side(),
        right=_valid_side(),
        diff_representation=DiffSelection.NONE,
        diff_summary=DiffSummary(),
        limits_used=LimitsUsed(),
        schema_metadata=SchemaMetadataRecord(),
    )
    s_bytes = structural_bytes(payload)
    rid = _safe_report_identity(s_bytes)
    return CompleteReport(
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
        provenance=ProvenanceRecord(
            source_left_identity="canonical:sha256:" + "a" * 64,
            source_right_identity="canonical:sha256:" + "b" * 64,
        ),
    )


def _failing_report_to_jsonable(report: object) -> dict[str, Any]:
    raise RuntimeError("secret conversion detail")


class TestCanonicalJson:
    def test_sorted_keys(self) -> None:
        result = canonical_json({"z": 1, "a": 2})
        assert result == b'{"a":2,"z":1}'

    def test_ascii_escaped(self) -> None:
        result = canonical_json({"key": "value"})
        assert isinstance(result, bytes)

    def test_no_trailing_newline(self) -> None:
        result = canonical_json({"key": "value"})
        assert not result.endswith(b"\n")

    def test_utf8_no_bom(self) -> None:
        result = canonical_json({"key": "value"})
        assert result[:3] != b"\xef\xbb\xbf"

    def test_compact_separators(self) -> None:
        result = canonical_json({"a": 1})
        assert b": " not in result
        assert b", " not in result

    def test_rejects_nan(self) -> None:
        with pytest.raises(ValueError):
            canonical_json({"key": float("nan")})

    def test_rejects_positive_inf(self) -> None:
        with pytest.raises(ValueError):
            canonical_json({"key": float("inf")})

    def test_rejects_negative_inf(self) -> None:
        with pytest.raises(ValueError):
            canonical_json({"key": float("-inf")})


class TestReportEncoding:
    def test_encode_report_produces_bytes(self) -> None:
        report = _make_test_report()
        result = encode_report(report)
        assert isinstance(result, bytes)
        assert b"derivatrace.validation-equivalence.report" in result

    def test_encoder_failure_raises(self) -> None:
        def _failing_encoder(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("injected")

        report = _make_test_report()
        with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
            encode_report(report, _failing_encoder)
        assert type(exc_info.value) is ValidationEquivalenceEncodingError
        assert "failed to encode complete report" in str(exc_info.value)
        assert "injected" not in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ValidationEquivalenceEncodingError)

    def test_structural_bytes_excludes_provenance(self) -> None:
        report = _make_test_report()
        s_bytes = structural_bytes(report)
        assert b"excluded_from_identity" not in s_bytes
        assert b"validation-equivalence:sha256:" not in s_bytes

    def test_structural_bytes_includes_other_fields(self) -> None:
        report = _make_test_report()
        s_bytes = structural_bytes(report)
        assert b"derivatrace.validation-equivalence.report" in s_bytes
        assert b"1.0.0" in s_bytes

    def test_report_to_jsonable(self) -> None:
        report = _make_test_report()
        d = report_to_jsonable(report)
        assert isinstance(d, dict)
        assert d["schema_name"] == "derivatrace.validation-equivalence.report"

    def test_encoder_failure_on_structural_bytes(self) -> None:
        def _failing_encoder(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("injected")

        report = _make_test_report()
        with pytest.raises(ValidationEquivalenceEncodingError):
            structural_bytes(report, _failing_encoder)

    def test_structural_bytes_conversion_failure_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import derivatrace.validation_equivalence._encoding as enc_mod

        report = _make_test_report()
        monkeypatch.setattr(enc_mod, "report_to_jsonable", _failing_report_to_jsonable)
        with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
            structural_bytes(report)
        assert "failed to encode structural projection" in str(exc_info.value)
        assert "secret" not in str(exc_info.value)

    def test_structural_bytes_encoder_failure_message(self) -> None:
        def _exploding_encoder(obj: object) -> bytes:
            raise RuntimeError("secret encoder detail")

        with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
            structural_bytes(_make_test_report(), _exploding_encoder)
        assert "failed to encode structural projection" in str(exc_info.value)
        assert "secret" not in str(exc_info.value)

    def test_encode_report_conversion_failure_message(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import derivatrace.validation_equivalence._encoding as enc_mod

        report = _make_test_report()
        monkeypatch.setattr(enc_mod, "report_to_jsonable", _failing_report_to_jsonable)
        with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
            encode_report(report)
        assert "failed to encode complete report" in str(exc_info.value)
        assert "secret" not in str(exc_info.value)

    def test_encode_report_encoder_failure_message(self) -> None:
        def _exploding_encoder(obj: object) -> bytes:
            raise RuntimeError("secret encoder detail")

        with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
            encode_report(_make_test_report(), _exploding_encoder)
        assert "failed to encode complete report" in str(exc_info.value)
        assert "secret" not in str(exc_info.value)

    def test_underlying_secret_text_absent_from_messages(self) -> None:
        import derivatrace.validation_equivalence._encoding as enc_mod

        report = _make_test_report()
        original = enc_mod._to_jsonable
        enc_mod._to_jsonable = lambda obj: (_ for _ in ()).throw(
            RuntimeError("very_secret_implementation_detail")
        )
        try:
            with pytest.raises(ValidationEquivalenceEncodingError) as exc_info:
                structural_bytes(report)
            msg = str(exc_info.value)
            assert "very_secret_implementation_detail" not in msg
            assert "secret" not in msg
        finally:
            enc_mod._to_jsonable = original


class TestReportToJsonable:
    def test_nested_dataclass(self) -> None:
        report = _make_test_report()
        d = report_to_jsonable(report)
        assert isinstance(d["left"], dict)
        assert isinstance(d["diff_summary"], dict)

    def test_none_values(self) -> None:
        side = ReportSide(
            contract_identity=None,
            payoff_graph_identity=None,
            failures=(),
        )
        d = report_to_jsonable(side)
        assert d["contract_identity"] is None
        assert d["payoff_graph_identity"] is None
        assert d["failures"] == []

    def test_tuple_to_list(self) -> None:
        side = ReportSide(
            contract_identity="canonical:sha256:" + "a" * 64,
            failures=(
                CapturedFailure(
                    stage=FailureStage.STRUCTURAL,
                    code="contract.input",
                    classification=CapturedFailureClassification.VALIDATION_FAILURE,
                ),
            ),
        )
        d = report_to_jsonable(side)
        assert isinstance(d["failures"], list)


class TestNestedLimitsJson:
    """limits_used JSON tree is exact."""

    def test_nested_limits_json_keys(self) -> None:
        report = _make_test_report()
        d = report_to_jsonable(report)
        lu = d["limits_used"]
        assert "validation" in lu
        assert "canonicalization" in lu
        assert "payoff" in lu
        assert "diff" in lu
        assert lu["validation"]["max_depth"] == 64
        assert lu["canonicalization"]["max_canonical_bytes"] == 8_000_000
        assert lu["payoff"]["max_structural_bytes"] == 2_097_152
        assert lu["diff"]["max_entries"] == 1024


class TestNestedSchemaMetadataJson:
    """schema_metadata JSON tree is exact."""

    def test_nested_metadata_json_keys(self) -> None:
        report = _make_test_report()
        d = report_to_jsonable(report)
        sm = d["schema_metadata"]
        assert "canonical" in sm
        assert "payoff" in sm
        assert sm["canonical"]["schema_name"] == "derivatrace.contract.canonical"
        assert sm["payoff"]["representation_identity_domain"] == (
            "derivatrace.payoffgraph.graph"
        )
