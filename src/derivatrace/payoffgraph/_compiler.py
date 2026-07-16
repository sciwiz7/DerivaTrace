from __future__ import annotations

import json as _json
from typing import Any

from derivatrace.canonical import (
    CanonicalizationLimits,
    CanonicalSchemaVersion,
    canonicalize_contract,
)
from derivatrace.canonical._encoding import canonical_json
from derivatrace.canonical._schema import (
    _validate_canonical_schema_version,
    _validate_canonicalization_limits,
)
from derivatrace.contracts import Contract, ValidationLimits

from ._encoding import payoff_document_json
from ._errors import (
    PayoffGraphCollisionError,
    PayoffGraphCompilationError,
    PayoffGraphComplexityError,
    PayoffGraphInputError,
)
from ._identity import payoff_graph_identity, payoff_node_identity
from ._result import PayoffGraph
from ._schema import (
    COMPILER_TAG,
    PROVENANCE_KEY_COMPILER,
    PROVENANCE_KEY_SOURCE,
    SUPPORTED_SCHEMA_NAME,
    PayoffGraphLimits,
    PayoffGraphSchemaVersion,
    _validate_payoff_graph_limits,
    _validate_payoff_schema_version,
)

# Reference-field maps for traversal of the trusted R1 canonical node graph.
# These mirror the canonical runtime's per-type schema and are used only to walk
# the canonical payloads produced inside the same call.
_CANON_SINGLE_REF: dict[str, tuple[str, ...]] = {
    "Negate": ("operand",),
    "Subtract": ("minuend", "subtrahend"),
    "Multiply": ("left", "right"),
    "Divide": ("numerator", "denominator"),
    "ConditionalValue": ("condition", "true_value", "false_value"),
    "Comparison": ("left", "right"),
    "Not": ("operand",),
    "Payment": ("amount",),
    "Scale": ("factor", "contract"),
    "ConditionalContract": ("condition", "true_contract", "false_contract"),
}
_CANON_LIST_REF: dict[str, tuple[str, ...]] = {
    "Add": ("operands",),
    "Maximum": ("operands",),
    "Minimum": ("operands",),
    "AllOf": ("operands",),
    "AnyOf": ("operands",),
    "Both": ("operands",),
}

# Reference-field maps for traversal of the compiled payoff-graph node graph.
_PG_SINGLE_REF: dict[str, tuple[str, ...]] = {
    "PGSubtract": ("minuend", "subtrahend"),
    "PGMultiply": ("left", "right"),
    "PGDivide": ("numerator", "denominator"),
    "PGNegate": ("operand",),
    "PGConditionalValue": ("condition", "true_payoff", "false_payoff"),
    "PGComparison": ("left", "right"),
    "PGNot": ("operand",),
    "PGPayment": ("amount",),
    "PGScale": ("factor", "payoff"),
    "PGConditionalContract": ("condition", "true_payoff", "false_payoff"),
}
_PG_LIST_REF: dict[str, tuple[str, ...]] = {
    "PGAdd": ("operands",),
    "PGMaximum": ("operands",),
    "PGMinimum": ("operands",),
    "PGAllOf": ("operands",),
    "PGAnyOf": ("operands",),
    "PGCombine": ("operands",),
}

# Payoff-node reference categories (§3.5 / §9 of payoff-graph-spec.md).
VALUE_CATEGORY: frozenset[str] = frozenset(
    {
        "PGConstant",
        "PGObservable",
        "PGAdd",
        "PGSubtract",
        "PGMultiply",
        "PGDivide",
        "PGNegate",
        "PGMaximum",
        "PGMinimum",
        "PGConditionalValue",
    }
)
BOOLEAN_CATEGORY: frozenset[str] = frozenset(
    {
        "PGBooleanConstant",
        "PGComparison",
        "PGAllOf",
        "PGAnyOf",
        "PGNot",
    }
)
CONTRACT_CATEGORY: frozenset[str] = frozenset(
    {
        "PGPayment",
        "PGCombine",
        "PGScale",
        "PGConditionalContract",
    }
)


def _parse_payoff_unit(unit: object) -> tuple[str, ...]:
    """Internal value-unit descriptor.

    Returns ``("scalar",)`` for a dimensionless value or ``("money", currency)``
    for a denominated value. This descriptor is used only for unit-consistency
    checks during compilation; it is never serialized into the graph.
    """
    if not isinstance(unit, dict):
        raise PayoffGraphCompilationError("internal canonical unit is malformed")
    kind = unit.get("kind")
    if kind == "scalar":
        return ("scalar",)
    if kind == "money":
        currency = unit.get("currency")
        if not isinstance(currency, str):
            raise PayoffGraphCompilationError("internal canonical unit is malformed")
        return ("money", currency)
    raise PayoffGraphCompilationError("internal canonical unit is malformed")


def _assert_same_payoff_units(units: list[tuple[str, ...]], ctx: str) -> None:
    ref = units[0]
    for other in units[1:]:
        if other != ref:
            raise PayoffGraphInputError(
                "a payoff node produces a unit-inconsistent graph"
            )


def _multiply_payoff_units(
    left: tuple[str, ...], right: tuple[str, ...]
) -> tuple[str, ...]:
    lk, rk = left[0], right[0]
    if lk == "scalar" and rk == "scalar":
        return ("scalar",)
    if lk == "scalar":
        return right
    if rk == "scalar":
        return left
    raise PayoffGraphInputError("money cannot be multiplied by money")


def _divide_payoff_units(num: tuple[str, ...], den: tuple[str, ...]) -> tuple[str, ...]:
    if den[0] != "scalar":
        raise PayoffGraphInputError("a payoff divisor must be a scalar")
    return num


def _require_canonical_payload(
    nodes: dict[str, Any], cid: str
) -> tuple[str, dict[str, Any]]:
    node = nodes.get(cid)
    if not isinstance(node, dict):
        raise PayoffGraphCompilationError("internal canonical node record is malformed")
    payload = node.get("payload")
    if not isinstance(payload, dict):
        raise PayoffGraphCompilationError("internal canonical node payload is missing")
    ctype = payload.get("type")
    if not isinstance(ctype, str):
        raise PayoffGraphCompilationError("internal canonical node type is missing")
    return ctype, payload


def _traverse_payoff_graph(
    root_pg_id: str,
    pg_type_by_pgid: dict[str, str],
    pg_payload_by_pgid: dict[str, dict[str, Any]],
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    _UNSEEN = 0
    _VISITING = 1
    _VISITED = 2
    state: dict[str, int] = {}
    reachable: set[str] = set()
    node_records: dict[str, dict[str, Any]] = {}
    stack: list[tuple[str, bool]] = [(root_pg_id, False)]
    while stack:
        pid, leaving = stack.pop()
        if leaving:
            state[pid] = _VISITED
            reachable.add(pid)
            node_records[pid] = {
                "id": pid,
                "payload": pg_payload_by_pgid[pid],
            }
            continue
        cur = state.get(pid, _UNSEEN)
        if cur == _VISITING:
            raise PayoffGraphCompilationError("payoff graph contains a cycle")
        if cur == _VISITED:
            continue
        if pid not in pg_type_by_pgid:
            raise PayoffGraphCompilationError("payoff reference does not resolve")
        state[pid] = _VISITING
        stack.append((pid, True))
        payload = pg_payload_by_pgid[pid]
        ptype = pg_type_by_pgid[pid]
        if ptype in _PG_SINGLE_REF:
            for field in _PG_SINGLE_REF[ptype]:
                ref = payload[field]
                if not isinstance(ref, str):
                    raise PayoffGraphCompilationError("payoff reference is malformed")
                stack.append((ref, False))
        elif ptype in _PG_LIST_REF:
            for field in _PG_LIST_REF[ptype]:
                for ref in payload[field]:
                    if not isinstance(ref, str):
                        raise PayoffGraphCompilationError(
                            "payoff reference is malformed"
                        )
                    stack.append((ref, False))
    return reachable, node_records


def _canonical_multiply_order(
    left: str,
    left_bytes: bytes,
    right: str,
    right_bytes: bytes,
) -> tuple[str, str]:
    if (left, left_bytes) <= (right, right_bytes):
        return left, right
    return right, left


def compile_payoff_graph(
    contract: Contract,
    *,
    canonical_schema: CanonicalSchemaVersion | None = None,
    payoff_schema: PayoffGraphSchemaVersion | None = None,
    canonicalization_limits: CanonicalizationLimits | None = None,
    payoff_limits: PayoffGraphLimits | None = None,
    validation_limits: ValidationLimits | None = None,
) -> PayoffGraph:
    """Compile a validated Stage 1A contract into an immutable ``PayoffGraph``.

    The flow is: validate and canonicalize the contract through the
    authoritative R1 runtime, then compile from the resulting trusted
    ``CanonicalContract`` document (never from the author AST or from any
    user-supplied canonical JSON/bytes). The compiled graph is a deterministic,
    reachable-only payoff DAG with deterministic provenance.

    R1 failures (validation, cycle, complexity, encoding, collision) propagate
    unchanged. Only failures owned by the R2 boundary use ``payoff_graph.*``
    codes.
    """
    if payoff_schema is None:
        payoff_schema = PayoffGraphSchemaVersion()
    _validate_payoff_schema_version(payoff_schema)
    if payoff_limits is None:
        payoff_limits = PayoffGraphLimits.default()
    _validate_payoff_graph_limits(payoff_limits)
    if canonical_schema is None:
        canonical_schema = CanonicalSchemaVersion()
    _validate_canonical_schema_version(canonical_schema)
    if canonicalization_limits is None:
        canonicalization_limits = CanonicalizationLimits.default()
    _validate_canonicalization_limits(canonicalization_limits)
    if not isinstance(contract, Contract):
        raise PayoffGraphInputError(
            "compile_payoff_graph requires an exact supported Contract root"
        )

    canonical = canonicalize_contract(
        contract,
        schema=canonical_schema,
        limits=canonicalization_limits,
        validation_limits=validation_limits,
    )

    try:
        doc = _json.loads(canonical.canonical_bytes.decode("utf-8"))
    except (_json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PayoffGraphCompilationError(
            "internal canonical document is not decodable"
        ) from exc
    if not isinstance(doc, dict):
        raise PayoffGraphCompilationError("internal canonical document is malformed")
    nodes = doc.get("nodes")
    if not isinstance(nodes, dict):
        raise PayoffGraphCompilationError(
            "internal canonical document is missing the node table"
        )
    root_canon_id = doc.get("root")
    if not isinstance(root_canon_id, str):
        raise PayoffGraphCompilationError(
            "internal canonical document is missing the root id"
        )

    version = payoff_schema.version

    pg_id_by_canon: dict[str, str] = {}
    pg_bytes_by_canon: dict[str, bytes] = {}
    pg_payload_by_pgid: dict[str, dict[str, Any]] = {}
    pg_type_by_pgid: dict[str, str] = {}
    pg_unit_by_canon: dict[str, tuple[str, ...]] = {}
    pg_id_seen: dict[str, bytes] = {}

    def require_category(pgid: str, category: frozenset[str], ctx: str) -> None:
        ptype = pg_type_by_pgid.get(pgid)
        if ptype is None or ptype not in category:
            raise PayoffGraphInputError(
                "a payoff reference violates a category restriction"
            )

    def map_collection(
        pg_type: str, canon_operands: list[str], category: frozenset[str]
    ) -> tuple[dict[str, Any], Any]:
        items: list[tuple[str, bytes]] = []
        for child in canon_operands:
            pid = pg_id_by_canon[child]
            items.append((pid, pg_bytes_by_canon[child]))
        items.sort(key=lambda pair: (pair[0], pair[1]))
        ids = [pair[0] for pair in items]
        for pid in ids:
            require_category(pid, category, pg_type)
        if category is VALUE_CATEGORY:
            units = [pg_unit_by_canon[child] for child in canon_operands]
            _assert_same_payoff_units(units, pg_type)
            unit: Any = units[0]
        else:
            unit = None
        return {"type": pg_type, "operands": ids}, unit

    def map_node(ctype: str, cpayload: dict[str, Any]) -> tuple[dict[str, Any], Any]:
        if ctype == "Number":
            return (
                {
                    "type": "PGConstant",
                    "amount": cpayload["value"],
                    "unit": cpayload["unit"],
                },
                _parse_payoff_unit(cpayload["unit"]),
            )
        if ctype == "Observable":
            return (
                {
                    "type": "PGObservable",
                    "observable_id": cpayload["observable_id"],
                    "observation_time": cpayload["observation_time"],
                    "unit": cpayload["unit"],
                },
                _parse_payoff_unit(cpayload["unit"]),
            )
        if ctype == "BooleanConstant":
            return (
                {"type": "PGBooleanConstant", "value": bool(cpayload["value"])},
                None,
            )
        if ctype == "Zero":
            return ({"type": "PGCombine", "operands": []}, None)
        if ctype == "Add":
            return map_collection("PGAdd", cpayload["operands"], VALUE_CATEGORY)
        if ctype == "Maximum":
            return map_collection("PGMaximum", cpayload["operands"], VALUE_CATEGORY)
        if ctype == "Minimum":
            return map_collection("PGMinimum", cpayload["operands"], VALUE_CATEGORY)
        if ctype == "AllOf":
            return map_collection("PGAllOf", cpayload["operands"], BOOLEAN_CATEGORY)
        if ctype == "AnyOf":
            return map_collection("PGAnyOf", cpayload["operands"], BOOLEAN_CATEGORY)
        if ctype == "Both":
            ids = [pg_id_by_canon[child] for child in cpayload["operands"]]
            for pid in ids:
                require_category(pid, CONTRACT_CATEGORY, "PGCombine")
            return ({"type": "PGCombine", "operands": ids}, None)
        if ctype == "Subtract":
            minu = pg_id_by_canon[cpayload["minuend"]]
            sub = pg_id_by_canon[cpayload["subtrahend"]]
            require_category(minu, VALUE_CATEGORY, "PGSubtract.minuend")
            require_category(sub, VALUE_CATEGORY, "PGSubtract.subtrahend")
            minu_unit = pg_unit_by_canon[cpayload["minuend"]]
            sub_unit = pg_unit_by_canon[cpayload["subtrahend"]]
            if minu_unit != sub_unit:
                raise PayoffGraphInputError(
                    "a payoff subtraction requires matching units"
                )
            return (
                {"type": "PGSubtract", "minuend": minu, "subtrahend": sub},
                minu_unit,
            )
        if ctype == "Multiply":
            left = pg_id_by_canon[cpayload["left"]]
            right = pg_id_by_canon[cpayload["right"]]
            require_category(left, VALUE_CATEGORY, "PGMultiply.left")
            require_category(right, VALUE_CATEGORY, "PGMultiply.right")
            left_bytes = pg_bytes_by_canon[cpayload["left"]]
            right_bytes = pg_bytes_by_canon[cpayload["right"]]
            lid, rid = _canonical_multiply_order(left, left_bytes, right, right_bytes)
            unit = _multiply_payoff_units(
                pg_unit_by_canon[cpayload["left"]],
                pg_unit_by_canon[cpayload["right"]],
            )
            return ({"type": "PGMultiply", "left": lid, "right": rid}, unit)
        if ctype == "Divide":
            num = pg_id_by_canon[cpayload["numerator"]]
            den = pg_id_by_canon[cpayload["denominator"]]
            require_category(num, VALUE_CATEGORY, "PGDivide.numerator")
            require_category(den, VALUE_CATEGORY, "PGDivide.denominator")
            unit = _divide_payoff_units(
                pg_unit_by_canon[cpayload["numerator"]],
                pg_unit_by_canon[cpayload["denominator"]],
            )
            return (
                {
                    "type": "PGDivide",
                    "numerator": num,
                    "denominator": den,
                },
                unit,
            )
        if ctype == "Negate":
            operand = pg_id_by_canon[cpayload["operand"]]
            require_category(operand, VALUE_CATEGORY, "PGNegate.operand")
            return (
                {"type": "PGNegate", "operand": operand},
                pg_unit_by_canon[cpayload["operand"]],
            )
        if ctype == "Comparison":
            left = pg_id_by_canon[cpayload["left"]]
            right = pg_id_by_canon[cpayload["right"]]
            require_category(left, VALUE_CATEGORY, "PGComparison.left")
            require_category(right, VALUE_CATEGORY, "PGComparison.right")
            return (
                {
                    "type": "PGComparison",
                    "left": left,
                    "right": right,
                    "operator": cpayload["operator"],
                },
                None,
            )
        if ctype == "Not":
            operand = pg_id_by_canon[cpayload["operand"]]
            require_category(operand, BOOLEAN_CATEGORY, "PGNot.operand")
            return ({"type": "PGNot", "operand": operand}, None)
        if ctype == "Payment":
            amount = pg_id_by_canon[cpayload["amount"]]
            require_category(amount, VALUE_CATEGORY, "PGPayment.amount")
            amount_unit = pg_unit_by_canon[cpayload["amount"]]
            if amount_unit[0] != "money":
                raise PayoffGraphInputError(
                    "a payoff payment amount must be a money value"
                )
            currency = cpayload["currency"]
            if not isinstance(currency, str) or amount_unit[1] != currency:
                raise PayoffGraphInputError(
                    "a payoff payment currency must match its amount"
                )
            return (
                {
                    "type": "PGPayment",
                    "amount": amount,
                    "currency": currency,
                    "settlement_time": cpayload["settlement_time"],
                },
                None,
            )
        if ctype == "Scale":
            factor = pg_id_by_canon[cpayload["factor"]]
            require_category(factor, VALUE_CATEGORY, "PGScale.factor")
            factor_unit = pg_unit_by_canon[cpayload["factor"]]
            if factor_unit[0] != "scalar":
                raise PayoffGraphInputError("a payoff scale factor must be a scalar")
            payoff = pg_id_by_canon[cpayload["contract"]]
            require_category(payoff, CONTRACT_CATEGORY, "PGScale.payoff")
            return ({"type": "PGScale", "factor": factor, "payoff": payoff}, None)
        if ctype == "ConditionalValue":
            condition = pg_id_by_canon[cpayload["condition"]]
            require_category(
                condition, BOOLEAN_CATEGORY, "PGConditionalValue.condition"
            )
            true_payoff = pg_id_by_canon[cpayload["true_value"]]
            require_category(
                true_payoff, VALUE_CATEGORY, "PGConditionalValue.true_payoff"
            )
            false_payoff = pg_id_by_canon[cpayload["false_value"]]
            require_category(
                false_payoff, VALUE_CATEGORY, "PGConditionalValue.false_payoff"
            )
            true_unit = pg_unit_by_canon[cpayload["true_value"]]
            false_unit = pg_unit_by_canon[cpayload["false_value"]]
            if true_unit != false_unit:
                raise PayoffGraphInputError(
                    "a payoff conditional value branches must share a unit"
                )
            return (
                {
                    "type": "PGConditionalValue",
                    "condition": condition,
                    "true_payoff": true_payoff,
                    "false_payoff": false_payoff,
                },
                true_unit,
            )
        if ctype == "ConditionalContract":
            condition = pg_id_by_canon[cpayload["condition"]]
            require_category(
                condition, BOOLEAN_CATEGORY, "PGConditionalContract.condition"
            )
            true_payoff = pg_id_by_canon[cpayload["true_contract"]]
            require_category(
                true_payoff, CONTRACT_CATEGORY, "PGConditionalContract.true_payoff"
            )
            false_payoff = pg_id_by_canon[cpayload["false_contract"]]
            require_category(
                false_payoff, CONTRACT_CATEGORY, "PGConditionalContract.false_payoff"
            )
            return (
                {
                    "type": "PGConditionalContract",
                    "condition": condition,
                    "true_payoff": true_payoff,
                    "false_payoff": false_payoff,
                },
                None,
            )
        raise PayoffGraphCompilationError("unknown canonical node type encountered")

    # Iterative, recursion-free post-order compilation from the canonical root.
    stack: list[tuple[str, bool]] = [(root_canon_id, False)]
    while stack:
        cid, leaving = stack.pop()
        if cid in pg_id_by_canon:
            continue
        if leaving:
            ctype, cpayload = _require_canonical_payload(nodes, cid)
            payload, unit = map_node(ctype, cpayload)
            payload_bytes = canonical_json(payload)
            nid = payoff_node_identity(payload_bytes, version)
            seen = pg_id_seen.get(nid)
            if seen is not None and seen != payload_bytes:
                raise PayoffGraphCollisionError(
                    "distinct payoff payloads share a node id"
                )
            pg_id_seen[nid] = payload_bytes
            pg_id_by_canon[cid] = nid
            pg_bytes_by_canon[cid] = payload_bytes
            pg_payload_by_pgid[nid] = payload
            pg_type_by_pgid[nid] = payload["type"]
            pg_unit_by_canon[cid] = unit
            continue
        stack.append((cid, True))
        ctype, cpayload = _require_canonical_payload(nodes, cid)
        if ctype in _CANON_SINGLE_REF:
            for field in _CANON_SINGLE_REF[ctype]:
                child = cpayload.get(field)
                if not isinstance(child, str):
                    raise PayoffGraphCompilationError(
                        "internal canonical reference is malformed"
                    )
                stack.append((child, False))
        elif ctype in _CANON_LIST_REF:
            for field in _CANON_LIST_REF[ctype]:
                refs = cpayload.get(field)
                if not isinstance(refs, list):
                    raise PayoffGraphCompilationError(
                        "internal canonical reference is malformed"
                    )
                for child in refs:
                    if not isinstance(child, str):
                        raise PayoffGraphCompilationError(
                            "internal canonical reference is malformed"
                        )
                    stack.append((child, False))

    root_pg_id = pg_id_by_canon[root_canon_id]

    reachable, node_records = _traverse_payoff_graph(
        root_pg_id, pg_type_by_pgid, pg_payload_by_pgid
    )

    node_count = len(reachable)
    if node_count > payoff_limits.max_payoff_nodes:
        raise PayoffGraphComplexityError("payoff node count exceeds the limit")

    structural_doc: dict[str, Any] = {
        "nodes": node_records,
        "root": root_pg_id,
        "schema_name": SUPPORTED_SCHEMA_NAME,
        "schema_version": version,
    }
    structural_bytes = canonical_json(structural_doc)
    if len(structural_bytes) > payoff_limits.max_structural_bytes:
        raise PayoffGraphComplexityError("payoff structural bytes exceed the limit")

    identity = payoff_graph_identity(structural_bytes, version)

    provenance: dict[str, str] = {
        PROVENANCE_KEY_COMPILER: COMPILER_TAG,
        PROVENANCE_KEY_SOURCE: canonical.identity,
    }

    document_doc: dict[str, Any] = {**structural_doc, "provenance": provenance}
    document_bytes = payoff_document_json(document_doc)
    if len(document_bytes) > payoff_limits.max_document_bytes:
        raise PayoffGraphComplexityError("payoff document bytes exceed the limit")

    return PayoffGraph(
        schema_version=version,
        document_bytes=document_bytes,
        structural_bytes=structural_bytes,
        identity=identity,
        root_node_id=root_pg_id,
        node_count=node_count,
        source_contract_identity=canonical.identity,
    )


__all__: list[str] = ["compile_payoff_graph"]
