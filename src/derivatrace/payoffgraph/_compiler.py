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
    pg_id_seen: dict[str, bytes] = {}

    def require_category(pgid: str, category: frozenset[str], ctx: str) -> None:
        ptype = pg_type_by_pgid.get(pgid)
        if ptype is None or ptype not in category:
            raise PayoffGraphInputError(
                "a payoff reference violates a category restriction"
            )

    def map_collection(
        pg_type: str, canon_operands: list[str], category: frozenset[str]
    ) -> dict[str, Any]:
        items: list[tuple[str, bytes]] = []
        for child in canon_operands:
            pid = pg_id_by_canon[child]
            items.append((pid, pg_bytes_by_canon[child]))
        items.sort(key=lambda pair: (pair[0], pair[1]))
        ids = [pair[0] for pair in items]
        for pid in ids:
            require_category(pid, category, pg_type)
        return {"type": pg_type, "operands": ids}

    def map_node(ctype: str, cpayload: dict[str, Any]) -> dict[str, Any]:
        if ctype == "Number":
            return {
                "type": "PGConstant",
                "amount": cpayload["value"],
                "unit": cpayload["unit"],
            }
        if ctype == "Observable":
            return {
                "type": "PGObservable",
                "observable_id": cpayload["observable_id"],
                "observation_time": cpayload["observation_time"],
                "unit": cpayload["unit"],
            }
        if ctype == "BooleanConstant":
            return {
                "type": "PGBooleanConstant",
                "value": bool(cpayload["value"]),
            }
        if ctype == "Zero":
            return {"type": "PGCombine", "operands": []}
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
            return {"type": "PGCombine", "operands": ids}
        if ctype == "Subtract":
            return {
                "type": "PGSubtract",
                "minuend": pg_id_by_canon[cpayload["minuend"]],
                "subtrahend": pg_id_by_canon[cpayload["subtrahend"]],
            }
        if ctype == "Multiply":
            left = pg_id_by_canon[cpayload["left"]]
            right = pg_id_by_canon[cpayload["right"]]
            left_bytes = pg_bytes_by_canon[cpayload["left"]]
            right_bytes = pg_bytes_by_canon[cpayload["right"]]
            lid, rid = _canonical_multiply_order(left, left_bytes, right, right_bytes)
            return {"type": "PGMultiply", "left": lid, "right": rid}
        if ctype == "Divide":
            return {
                "type": "PGDivide",
                "numerator": pg_id_by_canon[cpayload["numerator"]],
                "denominator": pg_id_by_canon[cpayload["denominator"]],
            }
        if ctype == "Negate":
            return {
                "type": "PGNegate",
                "operand": pg_id_by_canon[cpayload["operand"]],
            }
        if ctype == "Comparison":
            return {
                "type": "PGComparison",
                "left": pg_id_by_canon[cpayload["left"]],
                "right": pg_id_by_canon[cpayload["right"]],
                "operator": cpayload["operator"],
            }
        if ctype == "Not":
            return {
                "type": "PGNot",
                "operand": pg_id_by_canon[cpayload["operand"]],
            }
        if ctype == "Payment":
            amount = pg_id_by_canon[cpayload["amount"]]
            require_category(amount, VALUE_CATEGORY, "PGPayment.amount")
            return {
                "type": "PGPayment",
                "amount": amount,
                "currency": cpayload["currency"],
                "settlement_time": cpayload["settlement_time"],
            }
        if ctype == "Scale":
            factor = pg_id_by_canon[cpayload["factor"]]
            require_category(factor, VALUE_CATEGORY, "PGScale.factor")
            payoff = pg_id_by_canon[cpayload["contract"]]
            require_category(payoff, CONTRACT_CATEGORY, "PGScale.payoff")
            return {"type": "PGScale", "factor": factor, "payoff": payoff}
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
            return {
                "type": "PGConditionalValue",
                "condition": condition,
                "true_payoff": true_payoff,
                "false_payoff": false_payoff,
            }
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
            return {
                "type": "PGConditionalContract",
                "condition": condition,
                "true_payoff": true_payoff,
                "false_payoff": false_payoff,
            }
        raise PayoffGraphCompilationError("unknown canonical node type encountered")

    # Iterative, recursion-free post-order compilation from the canonical root.
    stack: list[tuple[str, bool]] = [(root_canon_id, False)]
    while stack:
        cid, leaving = stack.pop()
        if cid in pg_id_by_canon:
            continue
        if leaving:
            cpayload = nodes[cid]["payload"]
            ctype = cpayload["type"]
            payload = map_node(ctype, cpayload)
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
            continue
        stack.append((cid, True))
        cpayload = nodes[cid]["payload"]
        ctype = cpayload["type"]
        if ctype in _CANON_SINGLE_REF:
            for field in _CANON_SINGLE_REF[ctype]:
                child = cpayload[field]
                if not isinstance(child, str):
                    raise PayoffGraphCompilationError(
                        "internal canonical reference is malformed"
                    )
                stack.append((child, False))
        elif ctype in _CANON_LIST_REF:
            for field in _CANON_LIST_REF[ctype]:
                refs = cpayload[field]
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
