from __future__ import annotations

import json as _json
from datetime import UTC, datetime

from derivatrace.canonical import canonicalize_contract
from derivatrace.contracts import (
    Add,
    Both,
    Currency,
    ExactNumber,
    Multiply,
    Number,
    Observable,
    ObservableId,
    ObservationTime,
    Payment,
    Scale,
    SettlementTime,
    Subtract,
    Unit,
    validate_contract,
)

usd = Currency.from_code("USD")
T0 = SettlementTime.from_datetime(datetime(2030, 1, 1, tzinfo=UTC))
OT0 = ObservationTime.from_datetime(datetime(2030, 1, 1, tzinfo=UTC))


def _obs(namespace: str, identifier: str, field: str) -> Observable:
    return Observable(
        ObservableId.from_parts(namespace, identifier, field), OT0, Unit.money(usd)
    )


obs_A = _obs("equity", "AAA", "close")
obs_B = _obs("equity", "BBB", "close")
obs_X = _obs("equity", "XXX", "close")
obs_money = _obs("macro", "USDJPY", "fx")
num2 = Number(ExactNumber.from_string("2"), Unit.scalar())


# Expected canonical contract identities taken verbatim from
# docs/canonical-test-vectors.md (authoritative normative vectors CV-003..CV-009).
CV = {
    "CV-003": "canonical:sha256:259ab84dcede671196db17812e1efd629dd287c0d57f77d054e876568d6eb1ce",  # noqa: E501
    "CV-004": "canonical:sha256:69c59d89f9a932a8a4e3bdfe14f19c265bc9fe547aeb52e3a528252d6966b953",  # noqa: E501
    "CV-005": "canonical:sha256:dce9a43b3d8687b8f7ba9e770096a5d1ce04e0365fa1a1d83a04f7f2d8e95168",  # noqa: E501
    "CV-006a": "canonical:sha256:1500030155fd355074278431d58d7b8aabbab87a4b5e3c10ab2ff1a5acc05440",  # noqa: E501
    "CV-006b": "canonical:sha256:0ad1293ffc073b92664b0b300a4c277a2f3dc6608ee8a7ed7aa1fbd5910038ee",  # noqa: E501
    "CV-007": "canonical:sha256:6ab629fde98d8f84d9d6c749539acc02c5849f63b06b60a52e3cbeafdaefc5cd",  # noqa: E501
    "CV-008": "canonical:sha256:e969a37667f2abb6a9aa81a6e00b0b167356a4ab139c570987af1e071440bfc1",  # noqa: E501
    "CV-009a": "canonical:sha256:4980e10a017bb25d868029799bb73c5db859574f10c6264441779efd27c3349e",  # noqa: E501
    "CV-009b": "canonical:sha256:7dc44bf7d9dd626adba790436a9cdbe305668bb28908b73301271778dc82bfbc",  # noqa: E501
}


def test_cv003_add_commutes() -> None:
    a = Payment(Add((obs_A, obs_B)), usd, T0)
    b = Payment(Add((obs_B, obs_A)), usd, T0)
    ra = canonicalize_contract(a)
    rb = canonicalize_contract(b)
    assert ra.identity == CV["CV-003"]
    assert rb.identity == CV["CV-003"]
    assert ra == rb


def test_cv004_nested_add_flattens() -> None:
    contract = Payment(Add((obs_A, Add((obs_B, obs_X)))), usd, T0)
    result = canonicalize_contract(contract)
    assert result.identity == CV["CV-004"]


def test_cv005_multiply_reorders_not_flattened() -> None:
    a = Payment(Multiply(obs_money, num2), usd, T0)
    b = Payment(Multiply(num2, obs_money), usd, T0)
    ra = canonicalize_contract(a)
    rb = canonicalize_contract(b)
    assert ra.identity == CV["CV-005"]
    assert rb.identity == CV["CV-005"]


def test_cv006_both_order_preserved() -> None:
    a = Both((Payment(obs_A, usd, T0), Payment(obs_B, usd, T0)))
    b = Both((Payment(obs_B, usd, T0), Payment(obs_A, usd, T0)))
    ra = canonicalize_contract(a)
    rb = canonicalize_contract(b)
    assert ra.identity == CV["CV-006a"]
    assert rb.identity == CV["CV-006b"]
    assert ra != rb


def test_cv007_add_duplicate_operands_retained() -> None:
    contract = Payment(Add((obs_A, obs_A)), usd, T0)
    result = canonicalize_contract(contract)
    assert result.identity == CV["CV-007"]


def test_cv008_shared_subtree_content_addressed() -> None:
    shared = Payment(Add((obs_A, obs_B)), usd, T0)
    a = Both((Scale(num2, shared), shared))
    b = Both(
        (
            Scale(num2, Payment(Add((obs_A, obs_B)), usd, T0)),
            Payment(Add((obs_A, obs_B)), usd, T0),
        )
    )
    ra = canonicalize_contract(a)
    rb = canonicalize_contract(b)
    assert ra.identity == CV["CV-008"]
    assert rb.identity == CV["CV-008"]
    assert ra == rb


def test_cv009_subtract_non_commutative() -> None:
    a = Payment(Subtract(obs_A, obs_B), usd, T0)
    b = Payment(Subtract(obs_B, obs_A), usd, T0)
    ra = canonicalize_contract(a)
    rb = canonicalize_contract(b)
    assert ra.identity == CV["CV-009a"]
    assert rb.identity == CV["CV-009b"]
    assert ra != rb


def test_document_is_byte_exact_and_deterministic() -> None:
    a = Payment(Add((obs_A, obs_B)), usd, T0)
    b = Payment(Add((obs_B, obs_A)), usd, T0)
    assert (
        canonicalize_contract(a).canonical_bytes
        == canonicalize_contract(b).canonical_bytes
    )
    assert canonicalize_contract(a).canonical_bytes.endswith(b"}")
    assert b"\n" not in canonicalize_contract(a).canonical_bytes


# ---------------------------------------------------------------------------
# Blocker 1: corrected CV-001 / CV-002 / CV-010 source contracts are
# constructible and valid through the public Stage 1A API, and their canonical
# bytes, node identities, and contract identities match the normative vectors
# (regenerated from the Stage 1B-R1 runtime). These corrected vectors use a
# money-denominated Number amount (Unit.money(USD)) matching Payment.currency,
# which is required by Stage 1A; the previously documented scalar amount was
# rejected by Payment and therefore not directly constructible.
# ---------------------------------------------------------------------------


def _node_id_by_type(canonical_bytes: bytes, node_type: str) -> str:
    doc = _json.loads(canonical_bytes.decode("utf-8"))
    for nid, rec in doc["nodes"].items():
        if rec["payload"].get("type") == node_type:
            assert isinstance(nid, str)
            return nid
    raise AssertionError(f"no node of type {node_type!r} in canonical document")


def _money_number(s: str) -> Number:
    return Number(ExactNumber.from_string(s), Unit.money(usd))


_CV001_BYTES = (
    '{"nodes":{"245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a"'
    ':{"id":"245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a",'
    '"payload":{"amount":"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67",'
    '"currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}},'
    '"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67":'
    '{"id":"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67",'
    '"payload":{"type":"Number","unit":{"currency":"USD","kind":"money"},'
    '"value":{"digits":"1","exponent":0,"sign":0}}}},"root":'
    '"245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a",'
    '"schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}'
)

_CV002_BYTES = (
    '{"nodes":{"53c1bb4970008789392a86f3278eb9031e1c106dff5504c8b461211f6ea3c29e":'
    '{"id":"53c1bb4970008789392a86f3278eb9031e1c106dff5504c8b461211f6ea3c29e",'
    '"payload":{"type":"Number","unit":{"currency":"USD","kind":"money"},'
    '"value":{"digits":"0","exponent":0,"sign":0}}},'
    '"92e9d00e664604b0454cebd3d49ccff0c58f6f5f8d5bbf40c8a4523aea267350":'
    '{"id":"92e9d00e664604b0454cebd3d49ccff0c58f6f5f8d5bbf40c8a4523aea267350",'
    '"payload":{"amount":"53c1bb4970008789392a86f3278eb9031e1c106dff5504c8b461211f6ea3c29e",'
    '"currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}}},'
    '"root":"92e9d00e664604b0454cebd3d49ccff0c58f6f5f8d5bbf40c8a4523aea267350",'
    '"schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}'
)

_CV010_BYTES = (
    '{"nodes":{"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67":'
    '{"id":"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67",'
    '"payload":{"type":"Number","unit":{"currency":"USD","kind":"money"},'
    '"value":{"digits":"1","exponent":0,"sign":0}}},'
    '"c336c691466be366a62cb3c257c243db741cff51647b745e86c206c3c2902777":'
    '{"id":"c336c691466be366a62cb3c257c243db741cff51647b745e86c206c3c2902777",'
    '"payload":{"amount":"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67",'
    '"currency":"USD","settlement_time":"2030-01-01T00:00:00.500000Z","type":"Payment"}}},'
    '"root":"c336c691466be366a62cb3c257c243db741cff51647b745e86c206c3c2902777",'
    '"schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}'
)


def test_cv001_number_spelling_equivalence() -> None:
    expected_id = (
        "canonical:sha256:64a97aca38a8de396b059465d696ba6e"
        "8d84c8a6c7c5c2e7e687ab1b4724b4a5"
    )
    for spelling in ("1", "1.0", "1.00"):
        contract = Payment(_money_number(spelling), usd, T0)
        # The source contract is constructible and valid through the public API.
        validate_contract(contract)
        result = canonicalize_contract(contract)
        assert result.identity == expected_id
        assert result.canonical_bytes == _CV001_BYTES.encode("utf-8")
        assert result.root_node_id == (
            "245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a"
        )
        assert (
            _node_id_by_type(result.canonical_bytes, "Number")
            == "b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67"
        )
    # All three spellings canonicalize identically.
    a = canonicalize_contract(Payment(_money_number("1"), usd, T0))
    b = canonicalize_contract(Payment(_money_number("1.00"), usd, T0))
    assert a == b


def test_cv002_canonical_zero() -> None:
    contract = Payment(_money_number("0"), usd, T0)
    validate_contract(contract)
    result = canonicalize_contract(contract)
    assert (
        result.identity
        == "canonical:sha256:7d028d937117e85e0b8e55e9cd9193fa72767182735fe61bab9"
        "17e87ea737721"
    )
    assert result.canonical_bytes == _CV002_BYTES.encode("utf-8")
    assert result.root_node_id == (
        "92e9d00e664604b0454cebd3d49ccff0c58f6f5f8d5bbf40c8a4523aea267350"
    )
    assert (
        _node_id_by_type(result.canonical_bytes, "Number")
        == "53c1bb4970008789392a86f3278eb9031e1c106dff5504c8b461211f6ea3c29e"
    )


def test_cv010_timestamp_microsecond_precision() -> None:
    half = SettlementTime.from_datetime(
        datetime(2030, 1, 1, 0, 0, 0, 500000, tzinfo=UTC)
    )
    contract = Payment(_money_number("1"), usd, half)
    validate_contract(contract)
    result = canonicalize_contract(contract)
    assert (
        result.identity
        == "canonical:sha256:0271e7069e4b0ca82dcea2533c7737e15780b204762ddb7b1f90e"
        "99f0837d9b2"
    )
    assert result.canonical_bytes == _CV010_BYTES.encode("utf-8")
    assert result.root_node_id == (
        "c336c691466be366a62cb3c257c243db741cff51647b745e86c206c3c2902777"
    )
    # Distinct from CV-001 (microsecond precision participates in identity).
    cv001 = canonicalize_contract(Payment(_money_number("1"), usd, T0))
    assert cv001.identity != result.identity


def test_cv011_source_contract_constructible_and_matches_r1() -> None:
    # CV-011 (payoff-graph compilation) is deferred to R2 for runtime execution,
    # but its source Stage 1A contract must be constructible and valid, and its
    # canonical contract identity must agree with R1 (identical to CV-003).
    contract = Payment(Add((obs_A, obs_B)), usd, T0)
    validate_contract(contract)
    result = canonicalize_contract(contract)
    assert (
        result.identity
        == "canonical:sha256:259ab84dcede671196db17812e1efd629dd287c0d57f77d054e8765"
        "68d6eb1ce"
    )
    assert result.identity == CV["CV-003"]
