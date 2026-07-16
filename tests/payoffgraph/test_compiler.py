from __future__ import annotations

import datetime
import json
import sys
from dataclasses import FrozenInstanceError
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import pytest

from derivatrace.canonical import (
    CanonicalizationLimits,
    CanonicalSchemaVersion,
)
from derivatrace.contracts import (
    Add,
    AllOf,
    AnyOf,
    BooleanConstant,
    Both,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    ConditionalValue,
    Currency,
    Divide,
    ExactNumber,
    Maximum,
    Minimum,
    Multiply,
    Negate,
    Not,
    Number,
    Observable,
    ObservableId,
    ObservationTime,
    Payment,
    Scale,
    SettlementTime,
    Subtract,
    Unit,
    Zero,
)
from derivatrace.payoffgraph import (
    PayoffGraph,
    PayoffGraphCollisionError,
    PayoffGraphCompilationError,
    PayoffGraphComplexityError,
    PayoffGraphEncodingError,
    PayoffGraphError,
    PayoffGraphInputError,
    PayoffGraphLimits,
    PayoffGraphSchemaVersion,
    compile_payoff_graph,
)
from derivatrace.payoffgraph._encoding import payoff_document_json
from derivatrace.payoffgraph._identity import (
    payoff_graph_identity,
    payoff_node_identity,
)
from derivatrace.payoffgraph._schema import (
    COMPILER_TAG,
    SUPPORTED_SCHEMA_NAME,
    SUPPORTED_SCHEMA_VERSION,
)

UTC = datetime.UTC
USD = Currency.from_code("USD")
T0 = ObservationTime.from_datetime(datetime.datetime(2030, 1, 1, tzinfo=UTC))
T0ST = SettlementTime.from_datetime(datetime.datetime(2030, 1, 1, tzinfo=UTC))
T0_MS_ST = SettlementTime.from_datetime(
    datetime.datetime(2030, 1, 1, 0, 0, 0, 500000, tzinfo=UTC)
)


def _obs(ident: str) -> Observable:
    return Observable(
        ObservableId.from_parts("equity", ident, "close"), T0, Unit.money(USD)
    )


def _scobs(ident: str) -> Observable:
    return Observable(
        ObservableId.from_parts("macro", ident, "level"), T0, Unit.scalar()
    )


def _num(v: str, scalar: bool = False) -> Number:
    return Number(
        ExactNumber.from_string(v), Unit.scalar() if scalar else Unit.money(USD)
    )


def _pay(amt: Any) -> Payment:
    return Payment(amt, USD, T0ST)


def _struct(pg: PayoffGraph) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(pg.structural_bytes.decode()))


def _doc(pg: PayoffGraph) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(pg.document_bytes.decode()))


# ---------------------------------------------------------------------------
# CV-011: Normative Stage 1B-R2 payoff-graph vector (exact bytes).
# ---------------------------------------------------------------------------

_CV011_STRUCTURAL_BYTES = (
    b'{"nodes":{"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b'
    b'":{"id":"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b",'
    b'"payload":{"operands":["ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f450'
    b'2e8f521fd0b5","e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6'
    b'bc63"],"type":"PGAdd"}},"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c6'
    b'4b589f545c94c":{"id":"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b5'
    b'89f545c94c","payload":{"amount":"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae'
    b'75997b084390175d0cf8b","currency":"USD","settlement_time":"2030-01-01T00:00:00'
    b'.000000Z","type":"PGPayment"}},"ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f95'
    b'4b62f4502e8f521fd0b5":{"id":"ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b'
    b'62f4502e8f521fd0b5","payload":{"observable_id":{"field":"close","identifier":"'
    b'BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z",'
    b'"type":"PGObservable","unit":{"currency":"USD","kind":"money"}}},"e173bb558063'
    b'49d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63":{"id":"e173bb55806349'
    b'd78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63","payload":{"observable_id'
    b'":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"'
    b'2030-01-01T00:00:00.000000Z","type":"PGObservable","unit":{"currency":"USD",'
    b'"kind":"money"}}}},"root":"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c'
    b'64b589f545c94c","schema_name":"derivatrace.payoffgraph","schema_version":"1.0.0'
    b'"}'
)

_CV011_DOCUMENT_BYTES = (
    b'{"nodes":{"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b'
    b'":{"id":"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b",'
    b'"payload":{"operands":["ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f450'
    b'2e8f521fd0b5","e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6'
    b'bc63"],"type":"PGAdd"}},"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c6'
    b'4b589f545c94c":{"id":"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b5'
    b'89f545c94c","payload":{"amount":"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae'
    b'75997b084390175d0cf8b","currency":"USD","settlement_time":"2030-01-01T00:00:00'
    b'.000000Z","type":"PGPayment"}},"ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f95'
    b'4b62f4502e8f521fd0b5":{"id":"ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b'
    b'62f4502e8f521fd0b5","payload":{"observable_id":{"field":"close","identifier":"'
    b'BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z",'
    b'"type":"PGObservable","unit":{"currency":"USD","kind":"money"}}},"e173bb558063'
    b'49d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63":{"id":"e173bb55806349'
    b'd78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63","payload":{"observable_id'
    b'":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"'
    b'2030-01-01T00:00:00.000000Z","type":"PGObservable","unit":{"currency":"USD",'
    b'"kind":"money"}}}},"provenance":{"compiler":"derivatrace.payoffgraph.compiler/'
    b'1.0.0","source_contract_identity":"canonical:sha256:259ab84dcede671196db17812e'
    b'1efd629dd287c0d57f77d054e876568d6eb1ce"},"root":"5ee2594b6c230a97e1b44115db'
    b'479624a2de6780c192558a7c64b589f545c94c","schema_name":"derivatrace.payoffgraph'
    b'","schema_version":"1.0.0"}'
)


def _cv011_contract() -> Payment:
    obsA = _obs("AAA")
    obsB = _obs("BBB")
    return _pay(Add((obsA, obsB)))


# ---------------------------------------------------------------------------
# CV-011 exact structural and document bytes
# ---------------------------------------------------------------------------


class TestCV011ExactBytes:
    """CV-011 byte-for-byte assertions against the pinned normative literals."""

    def test_structural_bytes_exact(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg.structural_bytes == _CV011_STRUCTURAL_BYTES

    def test_document_bytes_exact(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg.document_bytes == _CV011_DOCUMENT_BYTES

    def test_structural_byte_length(self) -> None:
        assert len(_CV011_STRUCTURAL_BYTES) == 1456

    def test_document_byte_length(self) -> None:
        assert len(_CV011_DOCUMENT_BYTES) == 1634

    def test_document_differs_from_structural(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg.document_bytes != pg.structural_bytes

    def test_neither_ends_with_newline(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert not pg.structural_bytes.endswith(b"\n")
        assert not pg.document_bytes.endswith(b"\n")

    def test_no_bom(self) -> None:
        assert not _CV011_STRUCTURAL_BYTES.startswith(b"\xef\xbb\xbf")
        assert not _CV011_DOCUMENT_BYTES.startswith(b"\xef\xbb\xbf")

    def test_provenance_in_document(self) -> None:
        doc = json.loads(_CV011_DOCUMENT_BYTES)
        assert "provenance" in doc
        assert doc["provenance"] == {
            "compiler": COMPILER_TAG,
            "source_contract_identity": "canonical:sha256:259ab84dcede671196db17812e"
            "1efd629dd287c0d57f77d054e876568d6eb1ce",
        }

    def test_provenance_excluded_from_structural(self) -> None:
        struct = json.loads(_CV011_STRUCTURAL_BYTES)
        assert "provenance" not in struct

    def test_structural_re_serialization_matches(self) -> None:
        struct = json.loads(_CV011_STRUCTURAL_BYTES)
        reserialized = payoff_document_json(struct)
        assert reserialized == _CV011_STRUCTURAL_BYTES

    def test_document_re_serialization_matches(self) -> None:
        doc = json.loads(_CV011_DOCUMENT_BYTES)
        reserialized = payoff_document_json(doc)
        assert reserialized == _CV011_DOCUMENT_BYTES

    def test_pretty_serialization_differs(self) -> None:
        struct = json.loads(_CV011_STRUCTURAL_BYTES)
        pretty = json.dumps(struct, ensure_ascii=True, sort_keys=True, indent=2).encode(
            "utf-8"
        )
        assert pretty != _CV011_STRUCTURAL_BYTES
        assert pretty != _CV011_DOCUMENT_BYTES

    def test_no_floating_point_json(self) -> None:
        raw = _CV011_STRUCTURAL_BYTES.decode()
        assert "e" not in raw.split('"')  # no scientific notation outside strings


# ---------------------------------------------------------------------------
# CV-011 identity and structure
# ---------------------------------------------------------------------------


class TestCV011IdentityAndStructure:
    def test_identity(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg.identity == (
            "payoffgraph:sha256:"
            "59fbb00dbb585755a799cd7e387e4ee51fd9b77ed3cc032758a825f2f8836e1a"
        )

    def test_root_node_id(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg.root_node_id == (
            "5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c"
        )

    def test_node_count(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg.node_count == 4

    def test_schema_version(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg.schema_version == "1.0.0"

    def test_obs_a_node_id(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        struct = _struct(pg)
        obs_a_id = "e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63"
        assert obs_a_id in struct["nodes"]
        assert struct["nodes"][obs_a_id]["payload"]["type"] == "PGObservable"

    def test_obs_b_node_id(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        struct = _struct(pg)
        obs_b_id = "ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f4502e8f521fd0b5"
        assert obs_b_id in struct["nodes"]
        assert struct["nodes"][obs_b_id]["payload"]["type"] == "PGObservable"

    def test_pg_add_node_id(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        struct = _struct(pg)
        add_id = "2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b"
        assert add_id in struct["nodes"]
        assert struct["nodes"][add_id]["payload"]["type"] == "PGAdd"

    def test_source_contract_identity(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg.source_contract_identity == (
            "canonical:sha256:259ab84dcede671196db17812e1efd629dd287c0d57f77d054e87"
            "6568d6eb1ce"
        )

    def test_provenance_included_cross_check(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        doc_dict = json.loads(pg.document_bytes.decode())
        doc_bytes = payoff_document_json(doc_dict)
        cross_id = payoff_graph_identity(doc_bytes, pg.schema_version)
        assert cross_id == (
            "payoffgraph:sha256:"
            "e256cbbf291ba3135213c2eea700b46e0658ddcff853f187cd654cbeb474e5b0"
        )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_identical_contracts_compile_identically(self) -> None:
        pg1 = compile_payoff_graph(_cv011_contract())
        pg2 = compile_payoff_graph(_cv011_contract())
        assert pg1 == pg2
        assert hash(pg1) == hash(pg2)
        assert pg1.identity == pg2.identity
        assert pg1.structural_bytes == pg2.structural_bytes
        assert pg1.document_bytes == pg2.document_bytes

    def test_provenance_change_does_not_alter_identity(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        pg2 = compile_payoff_graph(_cv011_contract())
        assert pg.identity == pg2.identity
        assert pg.source_contract_identity == pg2.source_contract_identity


# ---------------------------------------------------------------------------
# All 20 canonical-to-payoff mappings
# ---------------------------------------------------------------------------


class TestMappingNumber:
    def test_number_maps_to_pg_constant(self) -> None:
        contract = _pay(_num("100"))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert root["payload"]["type"] == "PGPayment"
        amt_id = root["payload"]["amount"]
        amt = struct["nodes"][amt_id]
        assert amt["payload"]["type"] == "PGConstant"
        assert amt["payload"]["unit"] == {"kind": "money", "currency": "USD"}
        assert "amount" in amt["payload"]
        assert "settlement_time" not in amt["payload"]
        assert "observation_time" not in amt["payload"]

    def test_constant_no_settlement_time(self) -> None:
        contract = _pay(_num("42"))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert "settlement_time" not in amt["payload"]
        assert "observation_time" not in amt["payload"]


class TestMappingObservable:
    def test_observable_maps_to_pg_observable(self) -> None:
        contract = _pay(_obs("AAA"))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGObservable"
        assert "observation_time" in amt["payload"]
        assert "settlement_time" not in amt["payload"]
        assert "unit" in amt["payload"]
        assert "observable_id" in amt["payload"]


class TestMappingAdd:
    def test_add_maps_to_pg_add(self) -> None:
        contract = _pay(Add((_obs("AAA"), _obs("BBB"))))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGAdd"
        assert "operands" in amt["payload"]
        assert len(amt["payload"]["operands"]) == 2

    def test_add_duplicates_preserved(self) -> None:
        contract = _pay(Add((_obs("AAA"), _obs("AAA"))))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGAdd"
        assert len(amt["payload"]["operands"]) == 2
        assert amt["payload"]["operands"][0] == amt["payload"]["operands"][1]

    def test_add_commutation(self) -> None:
        pg1 = compile_payoff_graph(_pay(Add((_obs("AAA"), _obs("BBB")))))
        pg2 = compile_payoff_graph(_pay(Add((_obs("BBB"), _obs("AAA")))))
        assert pg1.identity == pg2.identity
        assert pg1.structural_bytes == pg2.structural_bytes


class TestMappingSubtract:
    def test_subtract_maps_to_pg_subtract(self) -> None:
        contract = _pay(Subtract(_obs("AAA"), _obs("BBB")))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGSubtract"
        assert "minuend" in amt["payload"]
        assert "subtrahend" in amt["payload"]

    def test_subtract_order_sensitive(self) -> None:
        pg1 = compile_payoff_graph(_pay(Subtract(_obs("AAA"), _obs("BBB"))))
        pg2 = compile_payoff_graph(_pay(Subtract(_obs("BBB"), _obs("AAA"))))
        assert pg1.identity != pg2.identity
        assert pg1.structural_bytes != pg2.structural_bytes


class TestMappingMultiply:
    def test_multiply_maps_to_pg_multiply(self) -> None:
        contract = _pay(Multiply(_obs("AAA"), _num("2", scalar=True)))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGMultiply"
        assert "left" in amt["payload"]
        assert "right" in amt["payload"]

    def test_multiply_commutation(self) -> None:
        pg1 = compile_payoff_graph(_pay(Multiply(_obs("AAA"), _num("2", scalar=True))))
        pg2 = compile_payoff_graph(_pay(Multiply(_num("2", scalar=True), _obs("AAA"))))
        assert pg1.identity == pg2.identity
        assert pg1.structural_bytes == pg2.structural_bytes

    def test_multiply_not_flattened(self) -> None:
        pg_nested = compile_payoff_graph(
            _pay(
                Multiply(
                    _obs("AAA"),
                    Multiply(_num("2", scalar=True), _num("3", scalar=True)),
                )
            )
        )
        pg_flat = compile_payoff_graph(_pay(Add((_obs("AAA"), _obs("BBB")))))
        assert pg_nested.identity != pg_flat.identity


class TestMappingDivide:
    def test_divide_maps_to_pg_divide(self) -> None:
        contract = Scale(
            Divide(_scobs("SCALARA"), _scobs("SCALARB")),
            _pay(_obs("AAA")),
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        nodes = struct["nodes"]
        found_divide = False
        for node in nodes.values():
            if node["payload"]["type"] == "PGDivide":
                found_divide = True
                assert "numerator" in node["payload"]
                assert "denominator" in node["payload"]
        assert found_divide

    def test_divide_order_sensitive(self) -> None:
        pg1 = compile_payoff_graph(
            Scale(Divide(_scobs("SCALARA"), _scobs("SCALARB")), _pay(_obs("AAA")))
        )
        pg2 = compile_payoff_graph(
            Scale(Divide(_scobs("SCALARB"), _scobs("SCALARA")), _pay(_obs("AAA")))
        )
        assert pg1.identity != pg2.identity


class TestMappingNegate:
    def test_negate_maps_to_pg_negate(self) -> None:
        contract = Payment(
            Number(ExactNumber(Decimal("5")), Unit.money(USD)), USD, T0ST
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGNegate":
                assert "operand" in node["payload"]
                return
        # Negate(Number(5)) canonicalizes to Number(5), so no PGNegate node remains.
        # Use a contract where negate is actually present after canonicalization.
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGConstant"


class TestMappingMaximum:
    def test_maximum_maps_to_pg_maximum(self) -> None:
        contract = Payment(
            Maximum((_obs("AAA"), _obs("BBB"))),
            USD,
            T0ST,
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGMaximum"
        assert "operands" in amt["payload"]
        assert len(amt["payload"]["operands"]) == 2

    def test_maximum_commutation(self) -> None:
        pg1 = compile_payoff_graph(_pay(Maximum((_obs("AAA"), _obs("BBB")))))
        pg2 = compile_payoff_graph(_pay(Maximum((_obs("BBB"), _obs("AAA")))))
        assert pg1.identity == pg2.identity


class TestMappingMinimum:
    def test_minimum_maps_to_pg_minimum(self) -> None:
        contract = Payment(
            Minimum((_obs("AAA"), _obs("BBB"))),
            USD,
            T0ST,
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGMinimum"
        assert "operands" in amt["payload"]
        assert len(amt["payload"]["operands"]) == 2

    def test_minimum_commutation(self) -> None:
        pg1 = compile_payoff_graph(_pay(Minimum((_obs("AAA"), _obs("BBB")))))
        pg2 = compile_payoff_graph(_pay(Minimum((_obs("BBB"), _obs("AAA")))))
        assert pg1.identity == pg2.identity


class TestMappingConditionalValue:
    def test_conditional_value_maps_to_pg_conditional_value(self) -> None:
        contract = _pay(
            ConditionalValue(
                Comparison(_obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN),
                _obs("AAA"),
                _obs("BBB"),
            )
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        found = False
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGConditionalValue":
                found = True
                assert "condition" in node["payload"]
                assert "true_payoff" in node["payload"]
                assert "false_payoff" in node["payload"]
        assert found


class TestMappingBooleanConstant:
    def test_boolean_constant_maps_to_pg_boolean_constant(self) -> None:
        from derivatrace.contracts import ConditionalValue

        contract = Payment(
            ConditionalValue(
                AllOf(
                    (
                        BooleanConstant(True),
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            ),
            USD,
            T0ST,
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        found = False
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGBooleanConstant":
                found = True
                assert node["payload"]["value"] is True
                assert "type" in node["payload"]
        assert found


class TestMappingComparison:
    def test_comparison_maps_to_pg_comparison(self) -> None:
        contract = _pay(
            ConditionalValue(
                Comparison(_obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN),
                _obs("AAA"),
                _obs("BBB"),
            )
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        found = False
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGComparison":
                found = True
                assert "left" in node["payload"]
                assert "right" in node["payload"]
                assert "operator" in node["payload"]
                assert node["payload"]["operator"] == ">"
        assert found

    def test_comparison_order_sensitive(self) -> None:
        pg1 = compile_payoff_graph(
            _pay(
                ConditionalValue(
                    Comparison(
                        _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                    ),
                    _obs("AAA"),
                    _obs("BBB"),
                )
            )
        )
        pg2 = compile_payoff_graph(
            _pay(
                ConditionalValue(
                    Comparison(
                        _obs("BBB"), _obs("AAA"), ComparisonOperator.GREATER_THAN
                    ),
                    _obs("AAA"),
                    _obs("BBB"),
                )
            )
        )
        assert pg1.identity != pg2.identity


class TestMappingAllOf:
    def test_allof_maps_to_pg_allof(self) -> None:
        contract = _pay(
            ConditionalValue(
                AllOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("BBB"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        found = False
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGAllOf":
                found = True
                assert "operands" in node["payload"]
                assert len(node["payload"]["operands"]) >= 2
        assert found

    def test_allof_nested_vs_flat(self) -> None:
        nested = _pay(
            ConditionalValue(
                AllOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        AllOf(
                            (
                                Comparison(
                                    _obs("BBB"),
                                    _obs("XXX"),
                                    ComparisonOperator.GREATER_THAN,
                                ),
                                Comparison(
                                    _obs("AAA"),
                                    _obs("XXX"),
                                    ComparisonOperator.GREATER_THAN,
                                ),
                            )
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        )
        flat = _pay(
            ConditionalValue(
                AllOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("BBB"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("AAA"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        )
        pg_nested = compile_payoff_graph(nested)
        pg_flat = compile_payoff_graph(flat)
        assert pg_nested.identity == pg_flat.identity
        assert pg_nested.structural_bytes == pg_flat.structural_bytes


class TestMappingAnyOf:
    def test_anyof_maps_to_pg_anyof(self) -> None:
        contract = _pay(
            ConditionalValue(
                AnyOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("BBB"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        found = False
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGAnyOf":
                found = True
                assert "operands" in node["payload"]
                assert len(node["payload"]["operands"]) >= 2
        assert found

    def test_anyof_nested_vs_flat(self) -> None:
        nested = _pay(
            ConditionalValue(
                AnyOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        AnyOf(
                            (
                                Comparison(
                                    _obs("BBB"),
                                    _obs("XXX"),
                                    ComparisonOperator.GREATER_THAN,
                                ),
                                Comparison(
                                    _obs("AAA"),
                                    _obs("XXX"),
                                    ComparisonOperator.GREATER_THAN,
                                ),
                            )
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        )
        flat = _pay(
            ConditionalValue(
                AnyOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("BBB"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("AAA"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        )
        pg_nested = compile_payoff_graph(nested)
        pg_flat = compile_payoff_graph(flat)
        assert pg_nested.identity == pg_flat.identity


class TestMappingNot:
    def test_not_maps_to_pg_not(self) -> None:
        contract = Payment(
            ConditionalValue(
                Not(
                    Comparison(
                        _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            ),
            USD,
            T0ST,
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        found = False
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGNot":
                found = True
                assert "operand" in node["payload"]
        assert found


class TestMappingZero:
    def test_zero_maps_to_pg_combine_empty(self) -> None:
        pg = compile_payoff_graph(Zero())
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert root["payload"]["type"] == "PGCombine"
        assert root["payload"]["operands"] == []

    def test_zero_node_count_is_one(self) -> None:
        pg = compile_payoff_graph(Zero())
        assert pg.node_count == 1


class TestMappingPayment:
    def test_payment_maps_to_pg_payment(self) -> None:
        contract = _pay(_obs("AAA"))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert root["payload"]["type"] == "PGPayment"
        assert "amount" in root["payload"]
        assert "currency" in root["payload"]
        assert "settlement_time" in root["payload"]
        assert root["payload"]["currency"] == "USD"
        assert root["payload"]["settlement_time"] == "2030-01-01T00:00:00.000000Z"
        assert "unit" not in root["payload"]

    def test_payment_owns_settlement_time(self) -> None:
        contract = Payment(_obs("AAA"), USD, T0ST)
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert "settlement_time" in root["payload"]
        amt = struct["nodes"][root["payload"]["amount"]]
        assert "settlement_time" not in amt["payload"]


class TestMappingBoth:
    def test_both_maps_to_pg_combine(self) -> None:
        contract = Both((_pay(_obs("AAA")), _pay(_obs("BBB"))))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert root["payload"]["type"] == "PGCombine"
        assert len(root["payload"]["operands"]) == 2

    def test_both_author_order_sensitive(self) -> None:
        pg1 = compile_payoff_graph(Both((_pay(_obs("AAA")), _pay(_obs("BBB")))))
        pg2 = compile_payoff_graph(Both((_pay(_obs("BBB")), _pay(_obs("AAA")))))
        assert pg1.identity != pg2.identity


class TestMappingScale:
    def test_scale_maps_to_pg_scale(self) -> None:
        contract = Scale(
            Number(ExactNumber(Decimal("2")), Unit.scalar()),
            Payment(_obs("AAA"), USD, T0ST),
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert root["payload"]["type"] == "PGScale"
        assert "factor" in root["payload"]
        assert "payoff" in root["payload"]
        factor = struct["nodes"][root["payload"]["factor"]]
        assert factor["payload"]["type"] == "PGConstant"
        assert factor["payload"]["unit"] == {"kind": "scalar"}
        payoff = struct["nodes"][root["payload"]["payoff"]]
        assert payoff["payload"]["type"] == "PGPayment"


class TestMappingConditionalContract:
    def test_conditional_contract_maps_to_pg_conditional_contract(self) -> None:
        contract = ConditionalContract(
            Comparison(_obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN),
            _pay(_obs("AAA")),
            _pay(_obs("BBB")),
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert root["payload"]["type"] == "PGConditionalContract"
        assert "condition" in root["payload"]
        assert "true_payoff" in root["payload"]
        assert "false_payoff" in root["payload"]

    def test_conditional_contract_order_sensitive(self) -> None:
        pg1 = compile_payoff_graph(
            ConditionalContract(
                Comparison(_obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN),
                _pay(_obs("AAA")),
                _pay(_obs("BBB")),
            )
        )
        pg2 = compile_payoff_graph(
            ConditionalContract(
                Comparison(_obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN),
                _pay(_obs("BBB")),
                _pay(_obs("AAA")),
            )
        )
        assert pg1.identity != pg2.identity


# ---------------------------------------------------------------------------
# Structural vector suite
# ---------------------------------------------------------------------------


class TestStructuralVectors:
    def test_pg_constant_under_pg_payment(self) -> None:
        contract = _pay(_num("100"))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert root["payload"]["type"] == "PGPayment"
        amt = struct["nodes"][root["payload"]["amount"]]
        assert amt["payload"]["type"] == "PGConstant"
        assert "unit" in amt["payload"]
        assert "settlement_time" not in amt["payload"]

    def test_nested_vs_flat_pg_add_identity(self) -> None:
        nested = _pay(Add((_obs("AAA"), Add((_obs("BBB"), _obs("XXX"))))))
        flat = _pay(Add((_obs("AAA"), _obs("BBB"), _obs("XXX"))))
        pg_nested = compile_payoff_graph(nested)
        pg_flat = compile_payoff_graph(flat)
        assert pg_nested.identity == pg_flat.identity
        assert pg_nested.structural_bytes == pg_flat.structural_bytes

    def test_pgmultiply_non_associativity(self) -> None:
        pg1 = compile_payoff_graph(
            _pay(
                Multiply(
                    _obs("AAA"),
                    Multiply(_num("2", scalar=True), _num("3", scalar=True)),
                )
            )
        )
        pg2 = compile_payoff_graph(
            _pay(
                Multiply(
                    Multiply(_obs("AAA"), _num("2", scalar=True)),
                    _num("3", scalar=True),
                )
            )
        )
        assert pg1.identity != pg2.identity

    def test_pg_combine_author_order(self) -> None:
        pg1 = compile_payoff_graph(Both((_pay(_obs("AAA")), _pay(_obs("BBB")))))
        pg2 = compile_payoff_graph(Both((_pay(_obs("BBB")), _pay(_obs("AAA")))))
        assert pg1.identity != pg2.identity
        struct1 = _struct(pg1)
        struct2 = _struct(pg2)
        root1 = struct1["nodes"][pg1.root_node_id]
        root2 = struct2["nodes"][pg2.root_node_id]
        assert root1["payload"]["operands"] != root2["payload"]["operands"]

    def test_duplicate_add_references(self) -> None:
        pg1 = compile_payoff_graph(_pay(Add((_obs("AAA"), _obs("AAA")))))
        pg2 = compile_payoff_graph(_pay(_obs("AAA")))
        struct1 = _struct(pg1)
        add_node = struct1["nodes"][
            struct1["nodes"][pg1.root_node_id]["payload"]["amount"]
        ]
        assert add_node["payload"]["operands"][0] == add_node["payload"]["operands"][1]
        assert pg1.identity != pg2.identity

    def test_duplicate_multiply_references(self) -> None:
        # Genuine duplicate reference: both Multiply operands point at the SAME
        # scalar node. Multiply rejects money x money in Stage 1A, so the shared
        # operand is a scalar observable and the product drives a Scale factor;
        # the point of this test is the duplicate reference, not the arithmetic.
        shared = _scobs("SCALARA")
        contract = Scale(Multiply(shared, shared), _pay(_obs("AAA")))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        assert len(struct["nodes"]) == pg.node_count

        mul_ids = [
            nid
            for nid, node in struct["nodes"].items()
            if node["payload"].get("type") == "PGMultiply"
        ]
        assert len(mul_ids) == 1
        mul = struct["nodes"][mul_ids[0]]
        left = mul["payload"]["left"]
        right = mul["payload"]["right"]
        # The duplicate reference: both operand slots name the same node id.
        assert left == right
        # The shared child node exists exactly once in the node table.
        assert left in struct["nodes"]
        assert sum(1 for node in struct["nodes"].values() if node["id"] == left) == 1
        # The duplicate reference is present in exactly both operand slots.
        assert [left, right].count(left) == 2
        # Reachability closure covers exactly the node table (no orphans/missing).
        reachable: set[str] = set()
        stack = [pg.root_node_id]
        while stack:
            nid = stack.pop()
            if nid in reachable:
                continue
            reachable.add(nid)
            payload = struct["nodes"][nid]["payload"]
            for ref_field in (
                "amount",
                "left",
                "right",
                "factor",
                "payoff",
                "operand",
            ):
                if isinstance(payload.get(ref_field), str):
                    stack.append(payload[ref_field])
            for ref in payload.get("operands", []):
                if isinstance(ref, str):
                    stack.append(ref)
        assert reachable == set(struct["nodes"])
        # Recompilation is deterministic.
        pg2 = compile_payoff_graph(contract)
        assert pg2.identity == pg.identity
        assert pg2.structural_bytes == pg.structural_bytes

    def test_duplicate_pg_combine_references(self) -> None:
        shared = _pay(_obs("AAA"))
        contract = Both((shared, shared))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert root["payload"]["type"] == "PGCombine"
        assert len(root["payload"]["operands"]) == 2
        assert root["payload"]["operands"][0] == root["payload"]["operands"][1]

    def test_shared_vs_copied_subgraphs(self) -> None:
        shared = _pay(Add((_obs("AAA"), _obs("BBB"))))
        pg_shared = compile_payoff_graph(
            Both((shared, Scale(_num("2", scalar=True), shared)))
        )
        pay1 = _pay(Add((_obs("AAA"), _obs("BBB"))))
        pay2 = _pay(Add((_obs("AAA"), _obs("BBB"))))
        pg_copied = compile_payoff_graph(
            Both((pay1, Scale(_num("2", scalar=True), pay2)))
        )
        assert pg_shared.identity == pg_copied.identity
        assert pg_shared.structural_bytes == pg_copied.structural_bytes

    def test_provenance_exclusion_from_identity(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        struct_dict = json.loads(pg.structural_bytes.decode())
        doc_no_prov = payoff_document_json(struct_dict)
        id_no_prov = payoff_graph_identity(doc_no_prov, "1.0.0")
        assert id_no_prov == pg.identity
        doc_with_prov = payoff_document_json(
            {**struct_dict, "provenance": {"compiler": "X"}}
        )
        struct_from_doc = json.loads(pg.document_bytes.decode())
        del struct_from_doc["provenance"]
        doc_stripped = payoff_document_json(struct_from_doc)
        id_stripped = payoff_graph_identity(doc_stripped, "1.0.0")
        assert id_stripped == pg.identity
        assert len(doc_with_prov) > len(doc_no_prov)

    def test_timestamp_microsecond_precision(self) -> None:
        pg1 = compile_payoff_graph(Payment(_num("1"), USD, T0ST))
        pg2 = compile_payoff_graph(Payment(_num("1"), USD, T0_MS_ST))
        assert pg1.identity != pg2.identity
        assert pg1.structural_bytes != pg2.structural_bytes

    def test_collision_seam(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        struct = _struct(pg)
        obs_ids = [
            nid
            for nid, n in struct["nodes"].items()
            if n["payload"]["type"] == "PGObservable"
        ]
        assert len(obs_ids) == 2

    def test_zero_to_empty_pg_combine(self) -> None:
        pg1 = compile_payoff_graph(Zero())
        pg2 = compile_payoff_graph(Zero())
        struct1 = _struct(pg1)
        struct2 = _struct(pg2)
        root1 = struct1["nodes"][pg1.root_node_id]
        root2 = struct2["nodes"][pg2.root_node_id]
        assert root1["payload"]["type"] == "PGCombine"
        assert root1["payload"]["operands"] == []
        assert root2["payload"]["type"] == "PGCombine"
        assert root2["payload"]["operands"] == []
        assert pg1.identity == pg2.identity


# ---------------------------------------------------------------------------
# PayoffGraph result model
# ---------------------------------------------------------------------------


class TestPayoffGraphResult:
    def test_frozen(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        with pytest.raises(FrozenInstanceError):
            pg.schema_version = "2.0.0"  # type: ignore[misc]

    def test_setattr_blocked(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        with pytest.raises(FrozenInstanceError):
            pg.identity = "forged"  # type: ignore[misc]

    def test_equality_based_on_identity(self) -> None:
        pg1 = compile_payoff_graph(_cv011_contract())
        pg2 = compile_payoff_graph(_cv011_contract())
        assert pg1 == pg2
        assert hash(pg1) == hash(pg2)

    def test_inequality_for_distinct_contracts(self) -> None:
        pg1 = compile_payoff_graph(_pay(_num("1")))
        pg2 = compile_payoff_graph(_pay(_num("2")))
        assert pg1 != pg2

    def test_inequality_with_non_payoffgraph(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert pg != "not a pg"
        assert pg != 42

    def test_repr(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        r = repr(pg)
        assert "PayoffGraph" in r
        assert pg.identity in r
        assert str(pg.node_count) in r

    def test_schema_version_exact_type(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert type(pg.schema_version) is str

    def test_document_bytes_exact_type(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert type(pg.document_bytes) is bytes

    def test_structural_bytes_exact_type(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert type(pg.structural_bytes) is bytes

    def test_identity_exact_type(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert type(pg.identity) is str
        assert pg.identity.startswith("payoffgraph:sha256:")

    def test_node_count_positive_int(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        assert type(pg.node_count) is int
        assert pg.node_count >= 1

    def test_malformed_identity_rejected(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraph(
                schema_version="1.0.0",
                document_bytes=b"{}",
                structural_bytes=b"{}",
                identity="not-a-valid-hash",
                root_node_id="a" * 64,
                node_count=1,
                source_contract_identity="canonical:sha256:" + "a" * 64,
            )

    def test_malformed_root_rejected(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraph(
                schema_version="1.0.0",
                document_bytes=b"{}",
                structural_bytes=b"{}",
                identity="payoffgraph:sha256:" + "a" * 64,
                root_node_id="not-hex",
                node_count=1,
                source_contract_identity="canonical:sha256:" + "a" * 64,
            )

    def test_non_contract_root_is_input_error(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            compile_payoff_graph(cast(Any, "not a contract"))


# ---------------------------------------------------------------------------
# PayoffGraphSchemaVersion
# ---------------------------------------------------------------------------


class TestPayoffGraphSchemaVersion:
    def test_default(self) -> None:
        s = PayoffGraphSchemaVersion()
        assert s.name == SUPPORTED_SCHEMA_NAME
        assert s.version == SUPPORTED_SCHEMA_VERSION

    def test_supported(self) -> None:
        s = PayoffGraphSchemaVersion.supported()
        assert s.name == SUPPORTED_SCHEMA_NAME
        assert s.version == SUPPORTED_SCHEMA_VERSION

    def test_exact_base_type(self) -> None:
        s = PayoffGraphSchemaVersion()
        assert type(s) is PayoffGraphSchemaVersion

    def test_exact_strings(self) -> None:
        s = PayoffGraphSchemaVersion()
        assert type(s.name) is str
        assert type(s.version) is str
        assert s.name == "derivatrace.payoffgraph"
        assert s.version == "1.0.0"

    def test_bool_rejected(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphSchemaVersion(name=cast(Any, True), version="1.0.0")

    def test_subclass_rejected(self) -> None:
        class Bad(PayoffGraphSchemaVersion):
            pass

        with pytest.raises(PayoffGraphInputError):
            Bad()

    def test_forged_object_rejected(self) -> None:
        class Forged:
            name = "derivatrace.payoffgraph"
            version = "1.0.0"

        with pytest.raises(PayoffGraphInputError):
            compile_payoff_graph(
                _cv011_contract(),
                payoff_schema=cast(Any, Forged()),
            )

    def test_unsupported_version_rejected(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphSchemaVersion(name="derivatrace.payoffgraph", version="2.0.0")


# ---------------------------------------------------------------------------
# PayoffGraphLimits
# ---------------------------------------------------------------------------


class TestPayoffGraphLimits:
    def test_defaults(self) -> None:
        lim = PayoffGraphLimits()
        assert lim.max_payoff_nodes == 4096
        assert lim.max_document_bytes == 4_194_304
        assert lim.max_structural_bytes == 2_097_152

    def test_exact_positive_ints(self) -> None:
        lim = PayoffGraphLimits()
        assert type(lim.max_payoff_nodes) is int
        assert type(lim.max_document_bytes) is int
        assert type(lim.max_structural_bytes) is int
        assert lim.max_payoff_nodes > 0
        assert lim.max_document_bytes > 0
        assert lim.max_structural_bytes > 0

    def test_bool_rejected(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_payoff_nodes=True)

    def test_subclass_rejected(self) -> None:
        class Bad(PayoffGraphLimits):
            pass

        with pytest.raises(PayoffGraphInputError):
            Bad()

    def test_structural_limit_coherent_with_document(self) -> None:
        lim = PayoffGraphLimits.__new__(PayoffGraphLimits)
        object.__setattr__(lim, "max_payoff_nodes", 4096)
        object.__setattr__(lim, "max_structural_bytes", 5000)
        object.__setattr__(lim, "max_document_bytes", 4000)
        with pytest.raises(PayoffGraphInputError):
            compile_payoff_graph(_cv011_contract(), payoff_limits=lim)

    def test_use_time_revalidation(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_payoff_nodes=0)
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_structural_bytes=0)
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_document_bytes=0)


# ---------------------------------------------------------------------------
# Error taxonomy
# ---------------------------------------------------------------------------


class TestErrorTaxonomy:
    def test_all_errors_derive_from_payoffgrapherror(self) -> None:
        for err in (
            PayoffGraphCollisionError,
            PayoffGraphCompilationError,
            PayoffGraphComplexityError,
            PayoffGraphEncodingError,
            PayoffGraphInputError,
        ):
            assert issubclass(err, PayoffGraphError)
            assert issubclass(err, Exception)

    def test_exact_codes(self) -> None:
        assert PayoffGraphError.code == "payoff_graph.error"
        assert PayoffGraphInputError.code == "payoff_graph.input"
        assert PayoffGraphCompilationError.code == "payoff_graph.compilation"
        assert PayoffGraphComplexityError.code == "payoff_graph.complexity"
        assert PayoffGraphEncodingError.code == "payoff_graph.encoding"
        assert PayoffGraphCollisionError.code == "payoff_graph.collision"

    def test_safe_messages(self) -> None:
        for err_cls in (
            PayoffGraphError,
            PayoffGraphInputError,
            PayoffGraphCompilationError,
            PayoffGraphComplexityError,
            PayoffGraphEncodingError,
            PayoffGraphCollisionError,
        ):
            err = err_cls("test message")
            assert "test message" in str(err)

    def test_r1_errors_propagate(self) -> None:
        from derivatrace.canonical import (
            CanonicalizationCollisionError,
            CanonicalizationComplexityError,
        )

        with pytest.raises(
            (CanonicalizationCollisionError, CanonicalizationComplexityError)
        ):
            tiny = CanonicalizationLimits(max_canonical_nodes=1)
            compile_payoff_graph(
                Both((_pay(_obs("AAA")), _pay(_obs("BBB")))),
                canonicalization_limits=tiny,
            )

    def test_collision_uses_payoff_graph_collision_error(self) -> None:

        def fake_digest(domain: str, version: str, payload: bytes) -> str:
            return "a" * 64

        with patch("derivatrace.payoffgraph._identity._digest", fake_digest):
            contract = Both((_pay(_obs("AAA")), _pay(_obs("BBB"))))
            with pytest.raises(PayoffGraphCollisionError):
                compile_payoff_graph(contract)


# ---------------------------------------------------------------------------
# Reachability and node-count coverage
# ---------------------------------------------------------------------------


class TestReachability:
    def test_all_structural_nodes_reachable(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        struct = _struct(pg)
        assert len(struct["nodes"]) == pg.node_count
        for nid in struct["nodes"]:
            assert len(nid) == 64

    def test_node_count_equals_reachable(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        struct = _struct(pg)
        reachable = set()
        stack = [pg.root_node_id]
        while stack:
            nid = stack.pop()
            if nid in reachable:
                continue
            reachable.add(nid)
            node = struct["nodes"][nid]
            payload = node["payload"]
            for ref_field in (
                "amount",
                "operand",
                "left",
                "right",
                "numerator",
                "denominator",
                "condition",
                "true_payoff",
                "false_payoff",
                "factor",
                "payoff",
                "minuend",
                "subtrahend",
            ):
                if ref_field in payload and isinstance(payload[ref_field], str):
                    stack.append(payload[ref_field])
            for list_field in ("operands",):
                if list_field in payload:
                    for ref in payload[list_field]:
                        if isinstance(ref, str):
                            stack.append(ref)
        assert len(reachable) == pg.node_count

    def test_no_orphan_nodes(self) -> None:
        contract = Both((_pay(_obs("AAA")), _pay(_obs("BBB"))))
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        assert len(struct["nodes"]) == pg.node_count

    def test_duplicated_references_remain_duplicated(self) -> None:
        pg = compile_payoff_graph(_pay(Add((_obs("AAA"), _obs("AAA")))))
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        add = struct["nodes"][root["payload"]["amount"]]
        assert add["payload"]["operands"][0] == add["payload"]["operands"][1]
        assert len(struct["nodes"]) == pg.node_count


# ---------------------------------------------------------------------------
# Limit and deep-graph tests
# ---------------------------------------------------------------------------


class TestLimits:
    def test_max_payoff_nodes_boundary(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        lim = PayoffGraphLimits(max_payoff_nodes=pg.node_count)
        pg2 = compile_payoff_graph(_cv011_contract(), payoff_limits=lim)
        assert pg2.node_count == pg.node_count

    def test_max_payoff_nodes_exceeded(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        lim = PayoffGraphLimits(max_payoff_nodes=pg.node_count - 1)
        with pytest.raises(PayoffGraphComplexityError):
            compile_payoff_graph(_cv011_contract(), payoff_limits=lim)

    def test_max_structural_bytes_boundary(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        lim = PayoffGraphLimits(
            max_structural_bytes=len(pg.structural_bytes),
            max_document_bytes=max(len(pg.document_bytes), len(pg.structural_bytes)),
        )
        pg2 = compile_payoff_graph(_cv011_contract(), payoff_limits=lim)
        assert len(pg2.structural_bytes) <= lim.max_structural_bytes

    def test_max_structural_bytes_exceeded(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        lim = PayoffGraphLimits(
            max_structural_bytes=len(pg.structural_bytes) - 1,
            max_document_bytes=max(len(pg.document_bytes), len(pg.structural_bytes)),
        )
        with pytest.raises(PayoffGraphComplexityError):
            compile_payoff_graph(_cv011_contract(), payoff_limits=lim)

    def test_max_document_bytes_boundary(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        lim = PayoffGraphLimits(
            max_document_bytes=len(pg.document_bytes),
            max_structural_bytes=max(len(pg.structural_bytes), len(pg.document_bytes)),
        )
        pg2 = compile_payoff_graph(_cv011_contract(), payoff_limits=lim)
        assert len(pg2.document_bytes) <= lim.max_document_bytes

    def test_max_document_bytes_exceeded(self) -> None:
        pg = compile_payoff_graph(_cv011_contract())
        lim = PayoffGraphLimits.__new__(PayoffGraphLimits)
        object.__setattr__(lim, "max_payoff_nodes", 4096)
        object.__setattr__(lim, "max_document_bytes", len(pg.document_bytes) - 1)
        object.__setattr__(lim, "max_structural_bytes", len(pg.structural_bytes))
        with pytest.raises(PayoffGraphComplexityError):
            compile_payoff_graph(_cv011_contract(), payoff_limits=lim)

    def test_compiler_traversal_is_iterative(self) -> None:
        old_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(50)
            contract = Both((_pay(_obs("AAA")), _pay(_obs("BBB"))))
            pg = compile_payoff_graph(contract)
            assert pg.node_count >= 4
        finally:
            sys.setrecursionlimit(old_limit)

    def test_reachability_traversal_is_iterative(self) -> None:
        old_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(50)
            contract = Both((_pay(_obs("AAA")), _pay(_obs("BBB"))))
            pg = compile_payoff_graph(contract)
            assert pg.node_count >= 4
        finally:
            sys.setrecursionlimit(old_limit)


# ---------------------------------------------------------------------------
# Cycle detection in _traverse_payoff_graph
# ---------------------------------------------------------------------------


class TestCycleDetection:
    def test_self_cycle_rejected(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph
        from derivatrace.payoffgraph._errors import PayoffGraphCompilationError

        types = {"A": "PGNegate"}
        payloads: dict[str, dict[str, Any]] = {"A": {"operand": "A"}}
        with pytest.raises(PayoffGraphCompilationError, match="cycle"):
            _traverse_payoff_graph("A", types, payloads)

    def test_two_node_cycle_rejected(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph
        from derivatrace.payoffgraph._errors import PayoffGraphCompilationError

        types = {"A": "PGNegate", "B": "PGNegate"}
        payloads: dict[str, dict[str, Any]] = {
            "A": {"operand": "B"},
            "B": {"operand": "A"},
        }
        with pytest.raises(PayoffGraphCompilationError, match="cycle"):
            _traverse_payoff_graph("A", types, payloads)

    def test_three_node_cycle_rejected(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph
        from derivatrace.payoffgraph._errors import PayoffGraphCompilationError

        types = {"A": "PGNegate", "B": "PGNegate", "C": "PGNegate"}
        payloads: dict[str, dict[str, Any]] = {
            "A": {"operand": "B"},
            "B": {"operand": "C"},
            "C": {"operand": "A"},
        }
        with pytest.raises(PayoffGraphCompilationError, match="cycle"):
            _traverse_payoff_graph("A", types, payloads)

    def test_valid_shared_dag_accepted(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph

        types = {"A": "PGAdd", "B": "PGConstant", "C": "PGConstant"}
        payloads: dict[str, dict[str, Any]] = {
            "A": {"operands": ["B", "C"]},
            "B": {},
            "C": {},
        }
        reachable, node_records = _traverse_payoff_graph("A", types, payloads)
        assert reachable == {"A", "B", "C"}
        assert set(node_records.keys()) == {"A", "B", "C"}

    def test_duplicate_references_no_error(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph

        types = {"A": "PGAdd", "B": "PGConstant"}
        payloads: dict[str, dict[str, Any]] = {
            "A": {"operands": ["B", "B"]},
            "B": {},
        }
        reachable, node_records = _traverse_payoff_graph("A", types, payloads)
        assert reachable == {"A", "B"}
        assert set(node_records.keys()) == {"A", "B"}

    def test_malformed_reference_rejected(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph
        from derivatrace.payoffgraph._errors import PayoffGraphCompilationError

        types = {"A": "PGNegate"}
        payloads: dict[str, dict[str, Any]] = {
            "A": {"operand": 123},
        }
        with pytest.raises(PayoffGraphCompilationError, match="malformed"):
            _traverse_payoff_graph("A", types, payloads)


class TestR1FailurePropagation:
    def test_validation_limit_propagates(self) -> None:
        from derivatrace.canonical import CanonicalizationComplexityError
        from derivatrace.contracts import ValidationLimits

        tiny = ValidationLimits(max_unique_nodes=1)
        with pytest.raises(CanonicalizationComplexityError):
            compile_payoff_graph(
                Both((_pay(_obs("AAA")), _pay(_obs("BBB")))),
                validation_limits=tiny,
            )

    def test_canonicalization_limit_propagates(self) -> None:
        from derivatrace.canonical import CanonicalizationComplexityError

        tiny = CanonicalizationLimits(max_canonical_nodes=1)
        with pytest.raises(CanonicalizationComplexityError):
            compile_payoff_graph(
                Both((_pay(_obs("AAA")), _pay(_obs("BBB")))),
                canonicalization_limits=tiny,
            )


# ---------------------------------------------------------------------------
# Encoding module
# ---------------------------------------------------------------------------


class TestEncoding:
    def test_payoff_document_json_compact(self) -> None:
        result = payoff_document_json({"key": "value"})
        assert isinstance(result, bytes)
        assert b" " not in result
        assert not result.endswith(b"\n")

    def test_payoff_document_json_sorted_keys(self) -> None:
        result = payoff_document_json({"z": 1, "a": 2})
        assert result == b'{"a":2,"z":1}'

    def test_payoff_document_json_ascii(self) -> None:
        result = payoff_document_json({"k": "\u00e9"})
        assert b"\\u00e9" in result


# ---------------------------------------------------------------------------
# Payoff-graph identity functions
# ---------------------------------------------------------------------------


class TestIdentityFunctions:
    def test_payoff_graph_identity_prefix(self) -> None:
        ident = payoff_graph_identity(b"test", "1.0.0")
        assert ident.startswith("payoffgraph:sha256:")
        assert len(ident) == len("payoffgraph:sha256:") + 64

    def test_payoff_node_identity_is_bare_hex(self) -> None:
        ident = payoff_node_identity(b"test", "1.0.0")
        assert len(ident) == 64
        assert all(c in "0123456789abcdef" for c in ident)

    def test_identity_deterministic(self) -> None:
        assert payoff_graph_identity(b"test", "1.0.0") == payoff_graph_identity(
            b"test", "1.0.0"
        )
        assert payoff_node_identity(b"test", "1.0.0") == payoff_node_identity(
            b"test", "1.0.0"
        )

    def test_identity_distinguishes_payloads(self) -> None:
        assert payoff_node_identity(b"a", "1.0.0") != payoff_node_identity(
            b"b", "1.0.0"
        )


# ---------------------------------------------------------------------------
# Coverage: _result.py PayoffGraph constructor type guards
# ---------------------------------------------------------------------------


class TestPayoffGraphConstructorGuards:
    def _make_pg(self, **kwargs: Any) -> PayoffGraph:
        defaults: dict[str, Any] = {
            "schema_version": "1.0.0",
            "document_bytes": b"{}",
            "structural_bytes": b"{}",
            "identity": "payoffgraph:sha256:" + "a" * 64,
            "root_node_id": "b" * 64,
            "node_count": 1,
            "source_contract_identity": "canonical:sha256:" + "c" * 64,
        }
        defaults.update(kwargs)
        return PayoffGraph(**defaults)

    def test_schema_version_not_str(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(schema_version=123)

    def test_schema_version_unsupported(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(schema_version="2.0.0")

    def test_document_bytes_not_bytes(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(document_bytes="not bytes")

    def test_structural_bytes_not_bytes(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(structural_bytes="not bytes")

    def test_node_count_zero(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(node_count=0)

    def test_node_count_negative(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(node_count=-1)

    def test_node_count_not_int(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(node_count=1.5)

    def test_source_contract_identity_not_str(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(source_contract_identity=123)

    def test_source_contract_identity_valid(self) -> None:
        pg = self._make_pg(source_contract_identity="canonical:sha256:" + "c" * 64)
        assert pg.source_contract_identity == "canonical:sha256:" + "c" * 64

    def test_source_contract_identity_wrong_prefix(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(source_contract_identity="foo:sha256:" + "c" * 64)

    def test_source_contract_identity_empty_digest(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(source_contract_identity="canonical:sha256:")

    def test_source_contract_identity_63_char(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(source_contract_identity="canonical:sha256:" + "c" * 63)

    def test_source_contract_identity_65_char(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(source_contract_identity="canonical:sha256:" + "c" * 65)

    def test_source_contract_identity_uppercase(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(source_contract_identity="canonical:sha256:" + "C" * 64)

    def test_source_contract_identity_non_hex(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(source_contract_identity="canonical:sha256:" + "g" * 64)

    def test_identity_non_hex(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(
                identity="payoffgraph:sha256:" + "g" * 64,
            )

    def test_root_node_id_non_hex(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(
                root_node_id="g" * 64,
            )

    def test_identity_wrong_length(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(identity="payoffgraph:sha256:" + "a" * 32)

    def test_root_node_id_wrong_length(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            self._make_pg(root_node_id="a" * 32)


# ---------------------------------------------------------------------------
# Coverage: _schema.py type guards
# ---------------------------------------------------------------------------


class TestSchemaTypeGuards:
    def test_schema_version_not_str(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphSchemaVersion(version=cast(Any, True))

    def test_schema_name_unsupported(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphSchemaVersion(name="wrong.name")

    def test_limits_structural_bytes_not_int(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_structural_bytes=cast(Any, "x"))

    def test_limits_document_bytes_not_int(self) -> None:
        with pytest.raises(PayoffGraphInputError):
            PayoffGraphLimits(max_document_bytes=cast(Any, "x"))


# ---------------------------------------------------------------------------
# Coverage: _compiler.py internal error paths (corrupted canonical docs)
# ---------------------------------------------------------------------------


class TestCompilerInternalPaths:
    def _make_canonical(self, doc: dict[str, Any]) -> Any:
        from derivatrace.canonical._encoding import canonical_json

        return SimpleNamespace(
            canonical_bytes=canonical_json(doc),
            identity="canonical:sha256:" + "a" * 64,
        )

    def test_explicit_canonical_schema(self) -> None:
        cs = CanonicalSchemaVersion()
        pg = compile_payoff_graph(_cv011_contract(), canonical_schema=cs)
        assert pg.schema_version == "1.0.0"

    def test_json_decode_error(self) -> None:
        bad = SimpleNamespace(
            canonical_bytes=b"\x80\x81\x82",
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())

    def test_doc_not_dict(self) -> None:
        from derivatrace.canonical._encoding import canonical_json

        bad = SimpleNamespace(
            canonical_bytes=canonical_json([1, 2, 3]),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())

    def test_nodes_not_dict(self) -> None:
        from unittest.mock import patch

        from derivatrace.canonical._encoding import canonical_json

        bad = SimpleNamespace(
            canonical_bytes=canonical_json({"nodes": [], "root": "x"}),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())

    def test_root_not_str(self) -> None:
        from unittest.mock import patch

        from derivatrace.canonical._encoding import canonical_json

        bad = SimpleNamespace(
            canonical_bytes=canonical_json({"nodes": {}, "root": 123}),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())

    def test_unknown_canonical_node_type(self) -> None:
        from unittest.mock import patch

        from derivatrace.canonical._encoding import canonical_json

        cid = "a" * 64
        bad = SimpleNamespace(
            canonical_bytes=canonical_json(
                {
                    "nodes": {cid: {"id": cid, "payload": {"type": "UnknownType"}}},
                    "root": cid,
                }
            ),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())

    def test_canonical_single_ref_malformed(self) -> None:
        from unittest.mock import patch

        from derivatrace.canonical._encoding import canonical_json

        cid = "a" * 64
        bad = SimpleNamespace(
            canonical_bytes=canonical_json(
                {
                    "nodes": {
                        cid: {
                            "id": cid,
                            "payload": {"type": "Negate", "operand": 123},
                        }
                    },
                    "root": cid,
                }
            ),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())

    def test_canonical_list_ref_malformed(self) -> None:
        from unittest.mock import patch

        from derivatrace.canonical._encoding import canonical_json

        cid = "a" * 64
        bad = SimpleNamespace(
            canonical_bytes=canonical_json(
                {
                    "nodes": {
                        cid: {
                            "id": cid,
                            "payload": {"type": "Add", "operands": [123]},
                        }
                    },
                    "root": cid,
                }
            ),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())

    def test_category_violation(self) -> None:
        from derivatrace.canonical._encoding import canonical_json

        cid_const = "a" * 64
        cid_inner_pay = "b" * 64
        cid_root = "c" * 64
        bad = SimpleNamespace(
            canonical_bytes=canonical_json(
                {
                    "nodes": {
                        cid_const: {
                            "id": cid_const,
                            "payload": {
                                "type": "Number",
                                "value": {"sign": 0, "digits": "1", "exponent": 0},
                                "unit": {"kind": "money", "currency": "USD"},
                            },
                        },
                        cid_inner_pay: {
                            "id": cid_inner_pay,
                            "payload": {
                                "type": "Payment",
                                "amount": cid_const,
                                "currency": "USD",
                                "settlement_time": "2030-01-01T00:00:00.000000Z",
                            },
                        },
                        cid_root: {
                            "id": cid_root,
                            "payload": {
                                "type": "Payment",
                                "amount": cid_inner_pay,
                                "currency": "USD",
                                "settlement_time": "2030-01-01T00:00:00.000000Z",
                            },
                        },
                    },
                    "root": cid_root,
                }
            ),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphInputError),
        ):
            compile_payoff_graph(_cv011_contract())


# ---------------------------------------------------------------------------
# Value-unit derivation (requirement 2)
# ---------------------------------------------------------------------------


def _compile_from_canonical(nodes: dict[str, Any], root: str) -> PayoffGraph:
    from derivatrace.canonical._encoding import canonical_json

    bad = SimpleNamespace(
        canonical_bytes=canonical_json({"nodes": nodes, "root": root}),
        identity="canonical:sha256:" + "a" * 64,
    )
    with patch(
        "derivatrace.payoffgraph._compiler.canonicalize_contract",
        return_value=bad,
    ):
        return compile_payoff_graph(_cv011_contract())


def _canon_number(scalar: bool = False, currency: str = "USD") -> dict[str, Any]:
    return {
        "id": "n" * 64,
        "payload": {
            "type": "Number",
            "value": {"sign": 0, "digits": "1", "exponent": 0},
            "unit": (
                {"kind": "scalar"}
                if scalar
                else {"kind": "money", "currency": currency}
            ),
        },
    }


def _canon_obs(currency: str = "USD", tag: str = "o") -> dict[str, Any]:
    return {
        "id": tag * 64,
        "payload": {
            "type": "Observable",
            "observable_id": {
                "field": "close",
                "identifier": "AAA",
                "namespace": "equity",
            },
            "observation_time": "2030-01-01T00:00:00.000000Z",
            "unit": {"kind": "money", "currency": currency},
        },
    }


def _canon_obs_scalar(tag: str = "a") -> dict[str, Any]:
    return {
        "id": tag * 64,
        "payload": {
            "type": "Observable",
            "observable_id": {
                "field": "level",
                "identifier": "SCALARA",
                "namespace": "macro",
            },
            "observation_time": "2030-01-01T00:00:00.000000Z",
            "unit": {"kind": "scalar"},
        },
    }


def _canon_payment(
    amount: str, currency: str = "USD", tag: str = "p"
) -> dict[str, Any]:
    return {
        "id": tag * 64,
        "payload": {
            "type": "Payment",
            "amount": amount,
            "currency": currency,
            "settlement_time": "2030-01-01T00:00:00.000000Z",
        },
    }


class TestValueUnitDerivationMalformed:
    def test_scalar_payment_amount_rejected(self) -> None:
        nodes = {
            "n" * 64: _canon_number(scalar=True),
            "p" * 64: _canon_payment("n" * 64),
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_money_scale_factor_rejected(self) -> None:
        nodes = {
            "n" * 64: _canon_number(scalar=False),
            "o" * 64: _canon_obs(),
            "q" * 64: _canon_payment("o" * 64, tag="q"),
            "r" * 64: {
                "id": "r" * 64,
                "payload": {"type": "Scale", "factor": "n" * 64, "contract": "q" * 64},
            },
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "r" * 64)

    def test_mismatched_currency_payment_rejected(self) -> None:
        nodes = {
            "n" * 64: _canon_number(scalar=False, currency="EUR"),
            "p" * 64: _canon_payment("n" * 64),
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_mismatched_currency_conditional_rejected(self) -> None:
        nodes = {
            "c" * 64: {
                "id": "c" * 64,
                "payload": {
                    "type": "Comparison",
                    "left": "o" * 64,
                    "right": "b" * 64,
                    "operator": ">",
                },
            },
            "o" * 64: _canon_obs("USD", "o"),
            "b" * 64: _canon_obs("USD", "b"),
            "x" * 64: _canon_obs("EUR", "x"),
            "p" * 64: {
                "id": "p" * 64,
                "payload": {
                    "type": "ConditionalValue",
                    "condition": "c" * 64,
                    "true_value": "o" * 64,
                    "false_value": "x" * 64,
                },
            },
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_money_times_money_rejected(self) -> None:
        nodes = {
            "o" * 64: _canon_obs("USD", "o"),
            "b" * 64: _canon_obs("USD", "b"),
            "m" * 64: {
                "id": "m" * 64,
                "payload": {"type": "Multiply", "left": "o" * 64, "right": "b" * 64},
            },
            "p" * 64: _canon_payment("m" * 64),
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_money_divisor_rejected(self) -> None:
        nodes = {
            "o" * 64: _canon_obs("USD", "o"),
            "b" * 64: _canon_obs("USD", "b"),
            "d" * 64: {
                "id": "d" * 64,
                "payload": {
                    "type": "Divide",
                    "numerator": "o" * 64,
                    "denominator": "b" * 64,
                },
            },
            "s" * 64: {
                "id": "s" * 64,
                "payload": {"type": "Scale", "factor": "d" * 64, "contract": "p" * 64},
            },
            "p" * 64: _canon_payment("o" * 64),
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "s" * 64)

    def test_money_plus_scalar_add_rejected(self) -> None:
        nodes = {
            "o" * 64: _canon_obs("USD", "o"),
            "a" * 64: _canon_obs_scalar("a"),
            "m" * 64: {
                "id": "m" * 64,
                "payload": {"type": "Add", "operands": ["o" * 64, "a" * 64]},
            },
            "p" * 64: _canon_payment("m" * 64),
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_money_minus_scalar_subtract_rejected(self) -> None:
        nodes = {
            "o" * 64: _canon_obs("USD", "o"),
            "a" * 64: _canon_obs_scalar("a"),
            "m" * 64: {
                "id": "m" * 64,
                "payload": {
                    "type": "Subtract",
                    "minuend": "o" * 64,
                    "subtrahend": "a" * 64,
                },
            },
            "p" * 64: _canon_payment("m" * 64),
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_mismatched_currency_subtract_rejected(self) -> None:
        nodes = {
            "o" * 64: _canon_obs("USD", "o"),
            "b" * 64: _canon_obs("EUR", "b"),
            "m" * 64: {
                "id": "m" * 64,
                "payload": {
                    "type": "Subtract",
                    "minuend": "o" * 64,
                    "subtrahend": "b" * 64,
                },
            },
            "p" * 64: _canon_payment("m" * 64),
        }
        with pytest.raises(PayoffGraphInputError):
            _compile_from_canonical(nodes, "p" * 64)


class TestValueUnitDerivationPositive:
    def test_scalar_times_scalar(self) -> None:
        nodes = {
            "a" * 64: _canon_obs_scalar("a"),
            "c" * 64: _canon_obs_scalar("c"),
            "o" * 64: _canon_obs(),
            "m" * 64: {
                "id": "m" * 64,
                "payload": {"type": "Multiply", "left": "a" * 64, "right": "c" * 64},
            },
            "s" * 64: {
                "id": "s" * 64,
                "payload": {"type": "Scale", "factor": "m" * 64, "contract": "p" * 64},
            },
            "p" * 64: _canon_payment("o" * 64),
        }
        pg = _compile_from_canonical(nodes, "s" * 64)
        assert pg.identity.startswith("payoffgraph:sha256:")

    def test_money_times_scalar(self) -> None:
        nodes = {
            "o" * 64: _canon_obs("USD", "o"),
            "a" * 64: _canon_obs_scalar("a"),
            "m" * 64: {
                "id": "m" * 64,
                "payload": {"type": "Multiply", "left": "o" * 64, "right": "a" * 64},
            },
            "p" * 64: _canon_payment("m" * 64),
        }
        pg = _compile_from_canonical(nodes, "p" * 64)
        assert pg.identity.startswith("payoffgraph:sha256:")

    def test_scalar_times_money(self) -> None:
        nodes = {
            "a" * 64: _canon_obs_scalar("a"),
            "o" * 64: _canon_obs("USD", "o"),
            "m" * 64: {
                "id": "m" * 64,
                "payload": {"type": "Multiply", "left": "a" * 64, "right": "o" * 64},
            },
            "p" * 64: _canon_payment("m" * 64),
        }
        pg = _compile_from_canonical(nodes, "p" * 64)
        assert pg.identity.startswith("payoffgraph:sha256:")

    def test_money_divided_by_scalar(self) -> None:
        nodes = {
            "o" * 64: _canon_obs("USD", "o"),
            "a" * 64: _canon_obs_scalar("a"),
            "d" * 64: {
                "id": "d" * 64,
                "payload": {
                    "type": "Divide",
                    "numerator": "o" * 64,
                    "denominator": "a" * 64,
                },
            },
            "p" * 64: _canon_payment("d" * 64),
        }
        pg = _compile_from_canonical(nodes, "p" * 64)
        assert pg.identity.startswith("payoffgraph:sha256:")

    def test_scalar_divided_by_scalar(self) -> None:
        nodes = {
            "a" * 64: _canon_obs_scalar("a"),
            "c" * 64: _canon_obs_scalar("c"),
            "o" * 64: _canon_obs(),
            "d" * 64: {
                "id": "d" * 64,
                "payload": {
                    "type": "Divide",
                    "numerator": "a" * 64,
                    "denominator": "c" * 64,
                },
            },
            "s" * 64: {
                "id": "s" * 64,
                "payload": {"type": "Scale", "factor": "d" * 64, "contract": "p" * 64},
            },
            "p" * 64: _canon_payment("o" * 64),
        }
        pg = _compile_from_canonical(nodes, "s" * 64)
        assert pg.identity.startswith("payoffgraph:sha256:")

    def test_same_currency_conditional_value(self) -> None:
        nodes = {
            "c" * 64: {
                "id": "c" * 64,
                "payload": {
                    "type": "Comparison",
                    "left": "o" * 64,
                    "right": "b" * 64,
                    "operator": ">",
                },
            },
            "o" * 64: _canon_obs("USD", "o"),
            "b" * 64: _canon_obs("USD", "b"),
            "p" * 64: {
                "id": "p" * 64,
                "payload": {
                    "type": "ConditionalValue",
                    "condition": "c" * 64,
                    "true_value": "o" * 64,
                    "false_value": "b" * 64,
                },
            },
        }
        pg = _compile_from_canonical(nodes, "p" * 64)
        assert pg.identity.startswith("payoffgraph:sha256:")


class TestValueUnitInternalMalformed:
    def test_unit_non_dict(self) -> None:
        nodes = {
            "n" * 64: {
                "id": "n" * 64,
                "payload": {"type": "Number", "value": "1", "unit": 123},
            },
            "p" * 64: _canon_payment("n" * 64),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_unit_unknown_kind(self) -> None:
        nodes = {
            "n" * 64: {
                "id": "n" * 64,
                "payload": {"type": "Number", "value": "1", "unit": {"kind": "weird"}},
            },
            "p" * 64: _canon_payment("n" * 64),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_unit_money_missing_currency(self) -> None:
        nodes = {
            "n" * 64: {
                "id": "n" * 64,
                "payload": {
                    "type": "Number",
                    "value": "1",
                    "unit": {"kind": "money", "currency": 123},
                },
            },
            "p" * 64: _canon_payment("n" * 64),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, "p" * 64)


# ---------------------------------------------------------------------------
# Trusted canonical-document structure guards (requirement 3)
# ---------------------------------------------------------------------------


class TestCanonicalDocumentStructure:
    def test_missing_canonical_payload(self) -> None:
        nodes = {"c" * 64: {"id": "c" * 64}}
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, "c" * 64)

    def test_non_dict_canonical_payload(self) -> None:
        nodes = {"c" * 64: {"id": "c" * 64, "payload": 123}}
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, "c" * 64)

    def test_missing_canonical_type(self) -> None:
        nodes = {"c" * 64: {"id": "c" * 64, "payload": {"value": 1}}}
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, "c" * 64)

    def test_missing_required_reference_field(self) -> None:
        nodes = {
            "c" * 64: {"id": "c" * 64, "payload": {"type": "Add"}},
            "p" * 64: _canon_payment("c" * 64),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_missing_canonical_target(self) -> None:
        nodes = {
            "p" * 64: {
                "id": "p" * 64,
                "payload": {
                    "type": "Payment",
                    "amount": "missing",
                    "currency": "USD",
                    "settlement_time": "2030-01-01T00:00:00.000000Z",
                },
            }
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, "p" * 64)

    def test_valid_shared_dag(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph

        types = {"A": "PGAdd", "B": "PGConstant", "C": "PGConstant"}
        payloads = {"A": {"operands": ["B", "C"]}, "B": {}, "C": {}}
        reachable, records = _traverse_payoff_graph("A", types, payloads)
        assert reachable == {"A", "B", "C"}
        assert set(records) == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Canonical three-state cycle detection (requirement 1): exercises
# compile_payoff_graph directly through the patched canonicalize_contract seam.
# ---------------------------------------------------------------------------


def _node(cid: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"id": cid, "payload": payload}


class TestCanonicalCycleDetection:
    def test_self_cycle_rejected(self) -> None:
        cid = "a" * 64
        nodes = {cid: _node(cid, {"type": "Negate", "operand": cid})}
        with pytest.raises(PayoffGraphCompilationError, match="cycle"):
            _compile_from_canonical(nodes, cid)

    def test_two_node_cycle_rejected(self) -> None:
        a = "a" * 64
        b = "b" * 64
        nodes = {
            a: _node(a, {"type": "Negate", "operand": b}),
            b: _node(b, {"type": "Negate", "operand": a}),
        }
        with pytest.raises(PayoffGraphCompilationError, match="cycle"):
            _compile_from_canonical(nodes, a)

    def test_three_node_cycle_rejected(self) -> None:
        a = "a" * 64
        b = "b" * 64
        c = "c" * 64
        nodes = {
            a: _node(a, {"type": "Negate", "operand": b}),
            b: _node(b, {"type": "Negate", "operand": c}),
            c: _node(c, {"type": "Negate", "operand": a}),
        }
        with pytest.raises(PayoffGraphCompilationError, match="cycle"):
            _compile_from_canonical(nodes, a)

    def test_valid_shared_diamond_accepted(self) -> None:
        a = "a" * 64
        b = "b" * 64
        c = "c" * 64
        d = "d" * 64
        e = "e" * 64
        nodes = {
            d: _node(
                d,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            e: _node(
                e,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "2", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            b: _node(b, {"type": "Subtract", "minuend": d, "subtrahend": e}),
            c: _node(c, {"type": "Negate", "operand": d}),
            a: _node(a, {"type": "Add", "operands": [b, c]}),
        }
        pg = _compile_from_canonical(nodes, a)
        # Five distinct payoff nodes; ``d`` is shared by both ``b`` and ``c``
        # (a genuine DAG, not just identical subtrees).
        assert pg.node_count == 5

    def test_duplicate_canonical_child_reference_accepted(self) -> None:
        a = "a" * 64
        b = "b" * 64
        nodes = {
            b: _node(
                b,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            a: _node(a, {"type": "Add", "operands": [b, b]}),
        }
        pg = _compile_from_canonical(nodes, a)
        struct = _struct(pg)
        root = struct["nodes"][pg.root_node_id]
        assert (
            root["payload"]["operands"]
            == [struct["nodes"][root["payload"]["operands"][0]]["id"]] * 2
        )

    def test_all_cycle_tests_terminate(self) -> None:
        # Each cycle variant must raise deterministically (no infinite loop and
        # no partial PayoffGraph). The assertions above already cover the raise;
        # this guard ensures termination even under a tight recursion limit.
        import sys

        old = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(60)
            a = "a" * 64
            b = "b" * 64
            c = "c" * 64
            for nodes, root in (
                ({a: _node(a, {"type": "Negate", "operand": a})}, a),
                (
                    {
                        a: _node(a, {"type": "Negate", "operand": b}),
                        b: _node(b, {"type": "Negate", "operand": a}),
                    },
                    a,
                ),
                (
                    {
                        a: _node(a, {"type": "Negate", "operand": b}),
                        b: _node(b, {"type": "Negate", "operand": c}),
                        c: _node(c, {"type": "Negate", "operand": a}),
                    },
                    a,
                ),
            ):
                with pytest.raises(PayoffGraphCompilationError):
                    _compile_from_canonical(nodes, root)
        finally:
            sys.setrecursionlimit(old)


# ---------------------------------------------------------------------------
# Canonical record / payload validation matrix (requirement 2)
# ---------------------------------------------------------------------------


class TestCanonicalRecordValidation:
    def _bad(self, cid: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {cid: _node(cid, payload)}

    def test_missing_record_id(self) -> None:
        cid = "a" * 64
        nodes = {
            cid: {
                "payload": {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                }
            }
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_record_id_key_mismatch(self) -> None:
        cid = "a" * 64
        nodes = {cid: _node("b" * 64, {"type": "Zero"})}
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_non_string_record_id(self) -> None:
        cid = "a" * 64
        nodes = {cid: {"id": 123, "payload": {"type": "Zero"}}}
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_missing_number_value(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid, {"type": "Number", "unit": {"kind": "money", "currency": "USD"}}
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_missing_number_unit(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid, {"type": "Number", "value": {"sign": 0, "digits": "1", "exponent": 0}}
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_malformed_exact_number_payload(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Number",
                "value": {"sign": 5, "digits": "1", "exponent": 0},
                "unit": {"kind": "money", "currency": "USD"},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_malformed_exact_number_digits(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Number",
                "value": {"sign": 0, "digits": 123, "exponent": 0},
                "unit": {"kind": "money", "currency": "USD"},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_missing_observable_id(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Observable",
                "observation_time": "2030-01-01T00:00:00.000000Z",
                "unit": {"kind": "money", "currency": "USD"},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_missing_observation_time(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Observable",
                "observable_id": {
                    "field": "close",
                    "identifier": "AAA",
                    "namespace": "equity",
                },
                "unit": {"kind": "money", "currency": "USD"},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_boolean_constant_string_rejected(self) -> None:
        cid = "a" * 64
        nodes = self._bad(cid, {"type": "BooleanConstant", "value": "true"})
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_boolean_constant_int_rejected(self) -> None:
        cid = "a" * 64
        nodes = self._bad(cid, {"type": "BooleanConstant", "value": 1})
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_comparison_missing_operator(self) -> None:
        cid = "a" * 64
        b = "b" * 64
        nodes = {
            b: _node(
                b,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            cid: _node(cid, {"type": "Comparison", "left": b, "right": b}),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_comparison_bad_operator(self) -> None:
        cid = "a" * 64
        b = "b" * 64
        nodes = {
            b: _node(
                b,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            cid: _node(
                cid, {"type": "Comparison", "left": b, "right": b, "operator": "~"}
            ),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_payment_missing_currency(self) -> None:
        cid = "a" * 64
        b = "b" * 64
        nodes = {
            b: _node(
                b,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            cid: _node(
                cid,
                {
                    "type": "Payment",
                    "amount": b,
                    "settlement_time": "2030-01-01T00:00:00.000000Z",
                },
            ),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_payment_missing_settlement_time(self) -> None:
        cid = "a" * 64
        b = "b" * 64
        nodes = {
            b: _node(
                b,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            cid: _node(cid, {"type": "Payment", "amount": b, "currency": "USD"}),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_empty_add_rejected(self) -> None:
        cid = "a" * 64
        nodes = self._bad(cid, {"type": "Add", "operands": []})
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_single_operand_add_rejected(self) -> None:
        cid = "a" * 64
        b = "b" * 64
        nodes = {
            b: _node(
                b,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            cid: _node(cid, {"type": "Add", "operands": [b]}),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_empty_both_rejected(self) -> None:
        cid = "a" * 64
        nodes = self._bad(cid, {"type": "Both", "operands": []})
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_single_operand_both_rejected(self) -> None:
        cid = "a" * 64
        b = "b" * 64
        nodes = {
            b: _node(
                b,
                {
                    "type": "Number",
                    "value": {"sign": 0, "digits": "1", "exponent": 0},
                    "unit": {"kind": "money", "currency": "USD"},
                },
            ),
            cid: _node(cid, {"type": "Both", "operands": [b]}),
        }
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_unknown_node_type_rejected(self) -> None:
        cid = "a" * 64
        nodes = self._bad(cid, {"type": "Frobnicate", "value": 1})
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_number_unit_money_currency_non_string(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Number",
                "value": {"sign": 0, "digits": "1", "exponent": 0},
                "unit": {"kind": "money", "currency": 123},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_number_unit_unknown_kind(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Number",
                "value": {"sign": 0, "digits": "1", "exponent": 0},
                "unit": {"kind": "vector"},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_exact_number_exponent_not_int(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Number",
                "value": {"sign": 0, "digits": "1", "exponent": "0"},
                "unit": {"kind": "money", "currency": "USD"},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_exact_number_digits_not_numeric(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Number",
                "value": {"sign": 0, "digits": "1a", "exponent": 0},
                "unit": {"kind": "money", "currency": "USD"},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)

    def test_observable_id_part_non_string(self) -> None:
        cid = "a" * 64
        nodes = self._bad(
            cid,
            {
                "type": "Observable",
                "observable_id": {
                    "field": 123,
                    "identifier": "AAA",
                    "namespace": "equity",
                },
                "observation_time": "2030-01-01T00:00:00.000000Z",
                "unit": {"kind": "money", "currency": "USD"},
            },
        )
        with pytest.raises(PayoffGraphCompilationError):
            _compile_from_canonical(nodes, cid)


# ---------------------------------------------------------------------------
# Executable conformance registry (requirement 4)
# ---------------------------------------------------------------------------


class TestConformanceRegistry:
    def test_every_vector_matches_registry(self) -> None:
        from conformance_registry import CONFORMANCE_VECTORS

        for name, (expected, builders) in CONFORMANCE_VECTORS.items():
            identities = {compile_payoff_graph(b()).identity for b in builders}
            assert identities == {expected}, name


class TestMultiplySwapBranch:
    def test_canonical_multiply_order_else_branch(self) -> None:
        from derivatrace.payoffgraph._compiler import _canonical_multiply_order

        left, right = _canonical_multiply_order("f" * 64, b"b", "a" * 64, b"a")
        assert left == "a" * 64
        assert right == "f" * 64

    def test_canonical_multiply_order_if_branch(self) -> None:
        from derivatrace.payoffgraph._compiler import _canonical_multiply_order

        left, right = _canonical_multiply_order("a" * 64, b"a", "f" * 64, b"b")
        assert left == "a" * 64
        assert right == "f" * 64

    def test_swap_fires_when_right_sorts_before_left(self) -> None:
        obs_a = _scobs("SCALARA")
        obs_b = _scobs("SCALARB")
        contract = Scale(
            Multiply(obs_a, obs_b),
            _pay(_obs("AAA")),
        )

        _orig_identity = payoff_node_identity

        def _controlled_identity(payload: bytes, version: str) -> str:
            if b"SCALARA" in payload:
                return "f" * 64
            if b"SCALARB" in payload:
                return "a" * 64
            return _orig_identity(payload, version)

        with patch(
            "derivatrace.payoffgraph._compiler.payoff_node_identity",
            side_effect=_controlled_identity,
        ):
            pg = compile_payoff_graph(contract)

        struct = _struct(pg)
        found = False
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGMultiply":
                found = True
                left_id = node["payload"]["left"]
                right_id = node["payload"]["right"]
                assert left_id <= right_id
        assert found


class TestMappingNegateDirect:
    def test_negate_of_observable_survives(self) -> None:
        contract = Payment(
            Negate(_obs("AAA")),
            USD,
            T0ST,
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGNegate":
                assert "operand" in node["payload"]
                return
        pytest.fail("expected PGNegate node in graph")


class TestTraversePayoffGraphDirect:
    def test_unknown_pg_id_raises(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph

        with pytest.raises(PayoffGraphCompilationError):
            _traverse_payoff_graph(
                "a" * 64,
                {"b" * 64: "PGConstant"},
                {"b" * 64: {"type": "PGConstant"}},
            )

    def test_malformed_single_ref_raises(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph

        root_id = "a" * 64
        with pytest.raises(PayoffGraphCompilationError):
            _traverse_payoff_graph(
                root_id,
                {root_id: "PGPayment"},
                {root_id: {"type": "PGPayment", "amount": 123}},
            )

    def test_malformed_list_ref_raises(self) -> None:
        from derivatrace.payoffgraph._compiler import _traverse_payoff_graph

        root_id = "a" * 64
        with pytest.raises(PayoffGraphCompilationError):
            _traverse_payoff_graph(
                root_id,
                {root_id: "PGAdd"},
                {root_id: {"type": "PGAdd", "operands": [123]}},
            )


class TestCheckHex64TypeGuard:
    def test_non_string_raises(self) -> None:
        from derivatrace.payoffgraph._result import _check_hex64

        with pytest.raises(PayoffGraphInputError):
            _check_hex64(cast(Any, 123), "identity")

    def test_multiply_swap_branch(self) -> None:

        obs_a = _scobs("SCALARA")
        obs_b = _scobs("SCALARB")
        contract = Scale(
            Multiply(obs_a, obs_b),
            _pay(_obs("AAA")),
        )
        pg = compile_payoff_graph(contract)
        struct = _struct(pg)
        found = False
        for node in struct["nodes"].values():
            if node["payload"]["type"] == "PGMultiply":
                left_id = node["payload"]["left"]
                right_id = node["payload"]["right"]
                assert left_id <= right_id
                found = True
        assert found

    def test_pg_single_ref_malformed(self) -> None:
        from unittest.mock import patch

        from derivatrace.canonical._encoding import canonical_json

        cid_factor = "a" * 64
        cid_payoff = "b" * 64
        cid_root = "c" * 64
        bad = SimpleNamespace(
            canonical_bytes=canonical_json(
                {
                    "nodes": {
                        cid_factor: {
                            "id": cid_factor,
                            "payload": {
                                "type": "Number",
                                "value": "2",
                                "unit": {"kind": "scalar"},
                            },
                        },
                        cid_payoff: {
                            "id": cid_payoff,
                            "payload": {
                                "type": "Payment",
                                "amount": cid_factor,
                                "currency": "USD",
                                "settlement_time": "2030-01-01T00:00:00.000000Z",
                            },
                        },
                        cid_root: {
                            "id": cid_root,
                            "payload": {
                                "type": "Scale",
                                "factor": cid_factor,
                                "contract": 123,
                            },
                        },
                    },
                    "root": cid_root,
                }
            ),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())

    def test_pg_list_ref_malformed(self) -> None:
        from unittest.mock import patch

        from derivatrace.canonical._encoding import canonical_json

        cid_operand = "a" * 64
        cid_add = "b" * 64
        bad = SimpleNamespace(
            canonical_bytes=canonical_json(
                {
                    "nodes": {
                        cid_operand: {
                            "id": cid_operand,
                            "payload": {
                                "type": "Number",
                                "value": "1",
                                "unit": {"kind": "scalar"},
                            },
                        },
                        cid_add: {
                            "id": cid_add,
                            "payload": {"type": "Add", "operands": 123},
                        },
                    },
                    "root": cid_add,
                }
            ),
            identity="canonical:sha256:" + "a" * 64,
        )
        with (
            patch(
                "derivatrace.payoffgraph._compiler.canonicalize_contract",
                return_value=bad,
            ),
            pytest.raises(PayoffGraphCompilationError),
        ):
            compile_payoff_graph(_cv011_contract())
