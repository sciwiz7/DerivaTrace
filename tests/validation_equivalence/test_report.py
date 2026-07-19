from __future__ import annotations

from typing import Any

import pytest

from derivatrace.validation_equivalence._encoding import (
    encode_report,
    structural_bytes,
)
from derivatrace.validation_equivalence._errors import (
    ValidationEquivalenceEncodingError,
)
from derivatrace.validation_equivalence._identity import _digest, report_identity
from derivatrace.validation_equivalence._records import (
    DiffSummary,
    LimitsUsed,
    ReportSide,
    SchemaMetadataRecord,
)
from derivatrace.validation_equivalence._report import (
    ValidationEquivalenceReport,
    build_report,
    build_wrapped_report,
)
from derivatrace.validation_equivalence._schema import (
    DiffSelection,
    ValidationLevel,
)


def _default_report_kwargs() -> dict[str, Any]:
    """Return default kwargs for build_report."""
    return {
        "requested_level": ValidationLevel.CANONICAL,
        "canonical_schema_version": "1.0.0",
        "payoff_schema_version": "1.0.0",
        "left_validation_outcome": "valid",
        "right_validation_outcome": "valid",
        "canonical_comparison_status": "equivalent",
        "canonical_comparison_reason": None,
        "payoff_comparison_status": "not_evaluated",
        "payoff_comparison_reason": "shallower_level_requested",
        "left": ReportSide(
            contract_identity="canonical:sha256:aaaa",
            payoff_graph_identity=None,
            failures=(),
        ),
        "right": ReportSide(
            contract_identity="canonical:sha256:aaaa",
            payoff_graph_identity=None,
            failures=(),
        ),
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


class TestVe014ProvenanceOnlyDiff:
    """ve_014: equal structural projection, different excluded provenance,
    identical report_id."""

    def test_identical_report_id_despite_provenance_difference(self) -> None:
        kwargs = _default_report_kwargs()

        report_a = build_report(
            **kwargs,
            source_left_identity="canonical:sha256:aaaa",
            source_right_identity="canonical:sha256:bbbb",
        )
        report_b = build_report(
            **kwargs,
            source_left_identity="canonical:sha256:cccc",
            source_right_identity="canonical:sha256:dddd",
        )

        assert report_a.report_id == report_b.report_id

    def test_structural_bytes_identical_despite_provenance(self) -> None:
        kwargs = _default_report_kwargs()

        report_a = build_report(
            **kwargs,
            source_left_identity="canonical:sha256:aaaa",
            source_right_identity="canonical:sha256:bbbb",
        )
        report_b = build_report(
            **kwargs,
            source_left_identity="canonical:sha256:cccc",
            source_right_identity="canonical:sha256:dddd",
        )

        s_a = structural_bytes(report_a)
        s_b = structural_bytes(report_b)
        assert s_a == s_b

    def test_provenance_excluded_from_report_id_preimage(self) -> None:
        kwargs = _default_report_kwargs()

        report_with = build_report(
            **kwargs,
            source_left_identity="canonical:sha256:aaaa",
            source_right_identity="canonical:sha256:bbbb",
        )
        report_without = build_report(
            **kwargs,
            source_left_identity=None,
            source_right_identity=None,
        )

        assert report_with.report_id == report_without.report_id


class TestVe037ReportEncodingFailureRaises:
    """ve_037: injected deterministic report-encoder failure raises
    validation_equivalence.encoding."""

    def test_encoding_failure_raises(self) -> None:
        def _failing_canonical(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("injected failure")

        import derivatrace.validation_equivalence._report as report_mod

        original = report_mod.structural_bytes

        def _patched_structural(report: object, encoder: object = None) -> bytes:
            return _failing_canonical(report)

        report_mod.structural_bytes = _patched_structural  # type: ignore[assignment]
        try:
            with pytest.raises(ValidationEquivalenceEncodingError):
                build_report(**_default_report_kwargs())
        finally:
            report_mod.structural_bytes = original

    def test_structural_bytes_encoding_failure_raises(self) -> None:
        def _failing_encoder(obj: object) -> bytes:
            raise ValidationEquivalenceEncodingError("injected failure")

        report = build_report(**_default_report_kwargs())
        with pytest.raises(ValidationEquivalenceEncodingError):
            structural_bytes(report, _failing_encoder)


class TestReportCollision:
    """Collision defence without global state."""

    def test_same_report_id_same_bytes_equal(self) -> None:
        kwargs = _default_report_kwargs()
        report = build_report(**kwargs)
        s_bytes = structural_bytes(report)

        a = ValidationEquivalenceReport(report, s_bytes)
        b = ValidationEquivalenceReport(report, s_bytes)
        assert a == b

    def test_same_report_id_different_bytes_raises(self) -> None:
        from derivatrace.validation_equivalence._errors import (
            ValidationEquivalenceReportCollisionError,
        )

        kwargs = _default_report_kwargs()
        report = build_report(**kwargs)
        s_bytes = structural_bytes(report)
        fake_bytes = b"different structural bytes"

        a = ValidationEquivalenceReport(report, s_bytes)
        b = ValidationEquivalenceReport(report, fake_bytes)

        with pytest.raises(ValidationEquivalenceReportCollisionError):
            _ = a == b

    def test_different_report_id_not_equal(self) -> None:
        kwargs1 = _default_report_kwargs()
        report1 = build_report(**kwargs1)
        s_bytes1 = structural_bytes(report1)

        kwargs2 = _default_report_kwargs()
        kwargs2["canonical_comparison_status"] = "different"
        report2 = build_report(**kwargs2)
        s_bytes2 = structural_bytes(report2)

        a = ValidationEquivalenceReport(report1, s_bytes1)
        b = ValidationEquivalenceReport(report2, s_bytes2)
        assert a != b
        assert a != "not a report"

    def test_hash_based_on_report_id(self) -> None:
        kwargs = _default_report_kwargs()
        report = build_report(**kwargs)
        s_bytes = structural_bytes(report)

        a = ValidationEquivalenceReport(report, s_bytes)
        b = ValidationEquivalenceReport(report, s_bytes)
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
        report = build_report(**_default_report_kwargs())
        assert report.report_id
        assert report.report_id.startswith("validation-equivalence:sha256:")

    def test_report_id_is_64_hex(self) -> None:
        report = build_report(**_default_report_kwargs())
        hex_part = report.report_id.split("validation-equivalence:sha256:")[1]
        assert len(hex_part) == 64
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_report_encoding_roundtrip(self) -> None:
        report = build_report(**_default_report_kwargs())
        encoded = encode_report(report)
        assert isinstance(encoded, bytes)
        assert b"derivatrace.validation-equivalence.report" in encoded

    def test_wrapped_report(self) -> None:
        wrapped = build_wrapped_report(**_default_report_kwargs())
        assert isinstance(wrapped, ValidationEquivalenceReport)
        assert wrapped.report_id.startswith("validation-equivalence:sha256:")

    def test_diff_none_empty_entries(self) -> None:
        report = build_report(**_default_report_kwargs())
        assert report.diff_representation == "none"
        assert report.diff_summary.entries == ()
        assert report.diff_summary.truncated is False
        assert report.diff_summary.truncation_reason is None
        assert report.diff_summary.unavailable_reason is None

    def test_report_equality_semantics(self) -> None:
        kwargs = _default_report_kwargs()
        a = build_wrapped_report(**kwargs)
        b = build_wrapped_report(**kwargs)
        assert a == b
        assert hash(a) == hash(b)

    def test_report_repr(self) -> None:
        report = build_report(**_default_report_kwargs())
        s_bytes = structural_bytes(report)
        wrapped = ValidationEquivalenceReport(report, s_bytes)
        r = repr(wrapped)
        assert "ValidationEquivalenceReport" in r
        assert "validation-equivalence:sha256:" in r
