from __future__ import annotations

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
from derivatrace.validation_equivalence._records import (
    CapturedFailure,
    CompleteReport,
    DiffSummary,
    LimitsUsed,
    ProvenanceRecord,
    ReportSide,
    SchemaMetadataRecord,
)


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
        with pytest.raises(ValidationEquivalenceEncodingError):
            encode_report(report, _failing_encoder)

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
            contract_identity="canonical:sha256:aaaa",
            failures=(
                CapturedFailure("structural", "validation.input", "validation_failure"),
            ),
        )
        d = report_to_jsonable(side)
        assert isinstance(d["failures"], list)


def _make_test_report() -> CompleteReport:
    return CompleteReport(
        report_id="validation-equivalence:sha256:" + "a" * 64,
        schema_name="derivatrace.validation-equivalence.report",
        schema_version="1.0.0",
        requested_level="canonical",
        canonical_schema_version="1.0.0",
        payoff_schema_version="1.0.0",
        left_validation_outcome="valid",
        right_validation_outcome="valid",
        canonical_comparison_status="equivalent",
        canonical_comparison_reason=None,
        payoff_comparison_status="not_evaluated",
        payoff_comparison_reason="shallower_level_requested",
        left=ReportSide(
            contract_identity="canonical:sha256:aaaa",
            payoff_graph_identity=None,
            failures=(),
        ),
        right=ReportSide(
            contract_identity="canonical:sha256:aaaa",
            payoff_graph_identity=None,
            failures=(),
        ),
        diff_representation="none",
        diff_summary=DiffSummary(
            entries=(),
            truncated=False,
            truncation_reason=None,
            unavailable_reason=None,
        ),
        limits_used=LimitsUsed(),
        schema_metadata=SchemaMetadataRecord(),
        provenance=ProvenanceRecord(
            source_left_identity="canonical:sha256:xxxx",
            source_right_identity="canonical:sha256:yyyy",
        ),
    )
