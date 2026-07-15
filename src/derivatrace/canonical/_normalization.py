from __future__ import annotations

from collections.abc import Callable
from typing import Any

from derivatrace.contracts import (
    Add,
    AllOf,
    AnyOf,
    BooleanConstant,
    Both,
    Comparison,
    ConditionalContract,
    ConditionalValue,
    Contract,
    ContractCycleError,
    ContractError,
    Divide,
    Maximum,
    Minimum,
    Multiply,
    Negate,
    Not,
    Number,
    Observable,
    Payment,
    Scale,
    Subtract,
    ValidationLimits,
    Zero,
    validate_contract,
)
from derivatrace.contracts import (
    ContractComplexityError as StageContractComplexityError,
)

from ._encoding import (
    _apply_comparison_operator,
    _decode_value_dict,
    _encode_operator_symbol,
    _exact_add,
    _exact_cmp,
    _exact_mul,
    _exact_neg,
    _exact_sub,
    _fold_number_payload,
    _unwrap_folded_number,
    canonical_json,
    encode_currency,
    encode_exact_number,
    encode_observable_id,
    encode_timestamp,
    encode_unit,
)
from ._errors import (
    CanonicalizationCollisionError,
    CanonicalizationComplexityError,
    CanonicalizationCycleError,
    CanonicalizationError,
    CanonicalizationInputError,
    CanonicalizationNotValidatedError,
)
from ._identity import contract_identity, node_identity
from ._nodes import CanonicalContract, _CanonicalNode
from ._schema import CanonicalizationLimits, CanonicalSchemaVersion

_ChildLookup = Callable[[object], tuple[str, dict[str, Any]]]


def _iter_children(node: object) -> list[tuple[tuple[str | int, ...], Any]]:
    """Yield ``(path_segments, child)`` for every child graph node.

    Mirrors the Stage 1A structural child mapping exactly so the canonical
    traversal visits the same edges.
    """
    children: list[tuple[tuple[str | int, ...], Any]] = []
    if isinstance(node, (Add, Maximum, Minimum)):
        for index, sop in enumerate(node.operands):
            children.append((("operands", index), sop))
    elif isinstance(node, Subtract):
        children.append((("minuend",), node.minuend))
        children.append((("subtrahend",), node.subtrahend))
    elif isinstance(node, Multiply):
        children.append((("left",), node.left))
        children.append((("right",), node.right))
    elif isinstance(node, Divide):
        children.append((("numerator",), node.numerator))
        children.append((("denominator",), node.denominator))
    elif isinstance(node, Negate):
        children.append((("operand",), node.operand))
    elif isinstance(node, ConditionalValue):
        children.append((("condition",), node.condition))
        children.append((("true_value",), node.true_value))
        children.append((("false_value",), node.false_value))
    elif isinstance(node, Comparison):
        children.append((("left",), node.left))
        children.append((("right",), node.right))
    elif isinstance(node, (AllOf, AnyOf)):
        for index, bop in enumerate(node.operands):
            children.append((("operands", index), bop))
    elif isinstance(node, Not):
        children.append((("operand",), node.operand))
    elif isinstance(node, Payment):
        children.append((("amount",), node.amount))
    elif isinstance(node, Both):
        for index, cop in enumerate(node.operands):
            children.append((("operands", index), cop))
    elif isinstance(node, Scale):
        children.append((("factor",), node.factor))
        children.append((("contract",), node.contract))
    elif isinstance(node, ConditionalContract):
        children.append((("condition",), node.condition))
        children.append((("true_contract",), node.true_contract))
        children.append((("false_contract",), node.false_contract))
    return children


def _build_payload(
    node: object,
    lookup: _ChildLookup,
    canon_nodes: dict[str, _CanonicalNode],
    path: tuple[str | int, ...],
) -> dict[str, Any]:
    """Compute the canonical payload for a single supported node.

    ``lookup`` resolves a child graph node to its ``(canonical_id,
    canonical_payload)`` pair, so this function never re-traverses the graph.
    The function is total over the supported ``derivatrace.contracts`` node
    types; an unsupported node type is a deterministic, traceable error (it can
    only arise from an internal dispatch mistake, since ``canonicalize_contract``
    only ever visits validated ``Contract``/expression nodes).
    """
    if isinstance(node, Number):
        return {
            "type": "Number",
            "unit": encode_unit(node.unit),
            "value": encode_exact_number(node.value),
        }
    if isinstance(node, BooleanConstant):
        return {"type": "BooleanConstant", "value": bool(node.value)}
    if isinstance(node, Observable):
        return {
            "type": "Observable",
            "observable_id": encode_observable_id(node.observable_id),
            "observation_time": encode_timestamp(node.observation_time),
            "unit": encode_unit(node.unit),
        }
    if isinstance(node, Zero):
        return {"type": "Zero"}
    if isinstance(node, Negate):
        cid, cpayload = lookup(node.operand)
        if cpayload.get("type") == "Number":
            # The operand is a validated Number, so its negation is always within
            # canonical numeric bounds; folding is total.
            return _unwrap_folded_number(
                _exact_neg(_decode_value_dict(cpayload["value"])),
                encode_unit(node.unit),
            )
        return {"type": "Negate", "operand": cid}
    if isinstance(node, Subtract):
        lcid, lpayload = lookup(node.minuend)
        rcid, rpayload = lookup(node.subtrahend)
        if lpayload.get("type") == "Number" and rpayload.get("type") == "Number":
            folded = _fold_number_payload(
                _exact_sub(
                    _decode_value_dict(lpayload["value"]),
                    _decode_value_dict(rpayload["value"]),
                ),
                encode_unit(node.unit),
            )
            if folded is not None:
                return folded
        return {"type": "Subtract", "minuend": lcid, "subtrahend": rcid}
    if isinstance(node, Multiply):
        lcid, lpayload = lookup(node.left)
        rcid, rpayload = lookup(node.right)
        if lpayload.get("type") == "Number" and rpayload.get("type") == "Number":
            folded = _fold_number_payload(
                _exact_mul(
                    _decode_value_dict(lpayload["value"]),
                    _decode_value_dict(rpayload["value"]),
                ),
                encode_unit(node.unit),
            )
            if folded is not None:
                return folded
        left_first = (lcid, canonical_json(lpayload)) <= (
            rcid,
            canonical_json(rpayload),
        )
        if left_first:
            return {"type": "Multiply", "left": lcid, "right": rcid}
        return {"type": "Multiply", "left": rcid, "right": lcid}
    if isinstance(node, Divide):
        ncid, _ = lookup(node.numerator)
        dcid, _ = lookup(node.denominator)
        return {"type": "Divide", "numerator": ncid, "denominator": dcid}
    if isinstance(node, (Add, Maximum, Minimum)):
        return _build_collection(node, lookup, canon_nodes, path)
    if isinstance(node, ConditionalValue):
        ccid, cpayload = lookup(node.condition)
        tvcid, tvpayload = lookup(node.true_value)
        fvcid, fvpayload = lookup(node.false_value)
        if cpayload.get("type") == "BooleanConstant":
            return tvpayload if cpayload["value"] else fvpayload
        return {
            "type": "ConditionalValue",
            "condition": ccid,
            "true_value": tvcid,
            "false_value": fvcid,
        }
    if isinstance(node, Comparison):
        lcid, lpayload = lookup(node.left)
        rcid, rpayload = lookup(node.right)
        if lpayload.get("type") == "Number" and rpayload.get("type") == "Number":
            result = _apply_comparison_operator(
                _encode_operator_symbol(node.operator),
                _decode_value_dict(lpayload["value"]),
                _decode_value_dict(rpayload["value"]),
            )
            return {"type": "BooleanConstant", "value": result}
        return {
            "type": "Comparison",
            "left": lcid,
            "right": rcid,
            "operator": _encode_operator_symbol(node.operator),
        }
    if isinstance(node, (AllOf, AnyOf)):
        return _build_bool_collection(node, lookup, canon_nodes, path)
    if isinstance(node, Not):
        cid, cpayload = lookup(node.operand)
        if cpayload.get("type") == "BooleanConstant":
            return {"type": "BooleanConstant", "value": not cpayload["value"]}
        return {"type": "Not", "operand": cid}
    if isinstance(node, Payment):
        acid, _ = lookup(node.amount)
        return {
            "type": "Payment",
            "amount": acid,
            "currency": encode_currency(node.currency),
            "settlement_time": encode_timestamp(node.settlement_time),
        }
    if isinstance(node, Both):
        ids = [lookup(o)[0] for o in node.operands]
        return {"type": "Both", "operands": ids}
    if isinstance(node, Scale):
        fcid, _ = lookup(node.factor)
        ccid, _ = lookup(node.contract)
        return {"type": "Scale", "factor": fcid, "contract": ccid}
    if isinstance(node, ConditionalContract):
        ccid, cpayload = lookup(node.condition)
        tcid, tpayload = lookup(node.true_contract)
        fcid, fpayload = lookup(node.false_contract)
        if cpayload.get("type") == "BooleanConstant":
            return tpayload if cpayload["value"] else fpayload
        return {
            "type": "ConditionalContract",
            "condition": ccid,
            "true_contract": tcid,
            "false_contract": fcid,
        }
    raise CanonicalizationError(
        f"unsupported node type: {type(node).__name__}", path=path
    )


def _build_collection(
    node: Add | Maximum | Minimum,
    lookup: _ChildLookup,
    canon_nodes: dict[str, _CanonicalNode],
    path: tuple[str | int, ...],
) -> dict[str, Any]:
    coll_type = {Add: "Add", Maximum: "Maximum", Minimum: "Minimum"}[type(node)]
    unit_dict = encode_unit(node.unit)
    operand_ids: list[str] = []
    for child in node.operands:
        cid, cpayload = lookup(child)
        if cpayload.get("type") == coll_type:
            operand_ids.extend(cpayload["operands"])
        else:
            operand_ids.append(cid)
    operand_ids.sort(key=lambda cid: (cid, canon_nodes[cid].payload_bytes))
    all_numbers = all(
        canon_nodes[cid].payload.get("type") == "Number" for cid in operand_ids
    )
    if coll_type == "Add" and all_numbers:
        acc = (0, 0, 0)
        for cid in operand_ids:
            acc = _exact_add(acc, _decode_value_dict(canon_nodes[cid].payload["value"]))
        folded = _fold_number_payload(acc, unit_dict)
        if folded is not None:
            return folded
    if coll_type in ("Maximum", "Minimum") and all_numbers:
        # Seed ``best`` from the first validated operand and iterate the
        # remainder; no Optional sentinel is needed because ``operand_ids`` is
        # non-empty (collections require at least two operands).
        values = [
            _decode_value_dict(canon_nodes[cid].payload["value"]) for cid in operand_ids
        ]
        best = values[0]
        for value in values[1:]:
            if (
                _exact_cmp(value, best) > 0
                if coll_type == "Maximum"
                else _exact_cmp(value, best) < 0
            ):
                best = value
        # ``best`` is exactly one of the (already constructible) operand values,
        # so it is always within canonical numeric bounds. Folding is total.
        return _unwrap_folded_number(best, unit_dict)
    return {"type": coll_type, "operands": operand_ids}


def _build_bool_collection(
    node: AllOf | AnyOf,
    lookup: _ChildLookup,
    canon_nodes: dict[str, _CanonicalNode],
    path: tuple[str | int, ...],
) -> dict[str, Any]:
    coll_type = "AllOf" if isinstance(node, AllOf) else "AnyOf"
    operand_ids: list[str] = []
    for child in node.operands:
        cid, cpayload = lookup(child)
        if cpayload.get("type") == coll_type:
            operand_ids.extend(cpayload["operands"])
        else:
            operand_ids.append(cid)
    operand_ids.sort(key=lambda cid: (cid, canon_nodes[cid].payload_bytes))
    if all(
        canon_nodes[cid].payload.get("type") == "BooleanConstant" for cid in operand_ids
    ):
        values = [canon_nodes[cid].payload["value"] for cid in operand_ids]
        result = all(values) if coll_type == "AllOf" else any(values)
        return {"type": "BooleanConstant", "value": result}
    return {"type": coll_type, "operands": operand_ids}


def _canonicalize_core(
    contract: Contract,
    schema: CanonicalSchemaVersion,
    limits: CanonicalizationLimits,
) -> CanonicalContract:
    """Iterative, content-addressed canonicalization of a validated contract.

    Assumes ``contract`` has already passed ``validate_contract``. Performs an
    explicit-stack post-order traversal (never recursion), canonicalizes children
    before parents, flattens and reorders commutative nodes, applies the
    approved literal-only simplifications, content-addresses nodes, detects
    SHA-256 collisions, and assembles the canonical document.

    Cycle safety is the responsibility of ``validate_contract`` (the
    authoritative cycle gate invoked by ``canonicalize_contract``); a validated
    graph is acyclic, so no in-core cycle guard is required here.

    After canonicalization, only nodes reachable from the final canonical root
    are retained in the document. Flattened-away, folded-away, and
    branch-discarded intermediate nodes are pruned before serialization.
    """
    version = schema.version
    canon_nodes: dict[str, _CanonicalNode] = {}
    memo: dict[int, str] = {}

    def lookup(child: object) -> tuple[str, dict[str, Any]]:
        cid = memo[id(child)]
        return cid, canon_nodes[cid].payload

    def register(payload: dict[str, Any], path: tuple[str | int, ...]) -> str:
        payload_bytes = canonical_json(payload)
        nid = node_identity(payload_bytes, version)
        existing = canon_nodes.get(nid)
        if existing is not None and existing.payload_bytes != payload_bytes:
            raise CanonicalizationCollisionError(
                "distinct canonical payloads share a node identity", path=path
            )
        if existing is None:
            canon_nodes[nid] = _CanonicalNode(
                payload=payload, payload_bytes=payload_bytes
            )
        return nid

    stack: list[tuple[object, int, tuple[str | int, ...], bool]] = [
        (contract, 1, (), False)
    ]
    while stack:
        node, _depth, path, leaving = stack.pop()
        if leaving:
            payload = _build_payload(node, lookup, canon_nodes, path)
            nid = register(payload, path)
            memo[id(node)] = nid
            continue
        # ``validate_contract`` already rejected any cycle before this core
        # traversal runs, so the graph is acyclic; a shared subtree is simply
        # visited again and produces the same content-addressed identity.
        if id(node) in memo:
            continue
        stack.append((node, _depth, path, True))
        for segments, child in reversed(_iter_children(node)):
            stack.append((child, _depth + 1, path + segments, False))

    root_id = memo[id(contract)]

    # Prune to reachable nodes only. Traverse the canonical payload graph
    # starting from root_id using the explicit per-type reference schema.
    # This removes flattened-away, folded-away, and branch-discarded nodes.
    _SINGLE_REF_FIELDS: dict[str, tuple[str, ...]] = {
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
    _LIST_REF_FIELDS: dict[str, tuple[str, ...]] = {
        "Add": ("operands",),
        "Maximum": ("operands",),
        "Minimum": ("operands",),
        "AllOf": ("operands",),
        "AnyOf": ("operands",),
        "Both": ("operands",),
    }

    reachable: set[str] = set()
    stack_ids: list[str] = [root_id]
    while stack_ids:
        nid = stack_ids.pop()
        if nid in reachable:
            continue
        if nid not in canon_nodes:
            raise CanonicalizationError(
                f"canonical node {nid} referenced but not produced", path=()
            )
        reachable.add(nid)
        node = canon_nodes[nid]
        ptype = node.payload.get("type")
        if ptype in _SINGLE_REF_FIELDS:
            for field in _SINGLE_REF_FIELDS[ptype]:
                ref = node.payload[field]
                stack_ids.append(ref)
        if ptype in _LIST_REF_FIELDS:
            for field in _LIST_REF_FIELDS[ptype]:
                for ref in node.payload[field]:
                    stack_ids.append(ref)

    # Validate that every reachable node's references exist in canon_nodes
    # (the traversal above already validated this during collection).

    reachable_nodes = {nid: cn for nid, cn in canon_nodes.items() if nid in reachable}

    if len(reachable_nodes) > limits.max_canonical_nodes:
        raise CanonicalizationComplexityError(
            f"canonical node count {len(reachable_nodes)} exceeds limit "
            f"{limits.max_canonical_nodes}"
        )

    # Deterministic ordering: sort by canonical id (bytes), tie-broken by
    # payload bytes (already canonical JSON).
    sorted_items = sorted(
        reachable_nodes.items(),
        key=lambda kv: (kv[0], kv[1].payload_bytes),
    )
    nodes_dict = {nid: {"id": nid, "payload": cn.payload} for nid, cn in sorted_items}
    document = {
        "nodes": nodes_dict,
        "root": root_id,
        "schema_name": schema.name,
        "schema_version": schema.version,
    }
    document_bytes = canonical_json(document)
    if len(document_bytes) > limits.max_canonical_bytes:
        raise CanonicalizationComplexityError(
            f"canonical byte length {len(document_bytes)} exceeds limit "
            f"{limits.max_canonical_bytes}"
        )
    identity = contract_identity(document_bytes, version)
    return CanonicalContract(
        schema_version=schema,
        canonical_bytes=document_bytes,
        identity=identity,
        root_node_id=root_id,
        node_count=len(reachable_nodes),
    )


def canonicalize_contract(
    contract: Contract,
    *,
    schema: CanonicalSchemaVersion | None = None,
    limits: CanonicalizationLimits | None = None,
    validation_limits: ValidationLimits | None = None,
) -> CanonicalContract:
    """Canonicalize a validated Stage 1A contract into a ``CanonicalContract``.

    The contract must be an exact supported ``Contract`` root. It is validated
    with ``validate_contract`` first; a graph that fails validation (including a
    cycle or an over-complex graph) is rejected with a documented, traceable
    canonicalization error that preserves the original cause. The canonical
    result is then produced iteratively without executing any node content.
    """
    if schema is None:
        schema = CanonicalSchemaVersion()
    if not isinstance(schema, CanonicalSchemaVersion):
        raise CanonicalizationInputError("schema must be a CanonicalSchemaVersion")
    if limits is None:
        limits = CanonicalizationLimits.default()
    if not isinstance(limits, CanonicalizationLimits):
        raise CanonicalizationInputError("limits must be a CanonicalizationLimits")
    if not isinstance(contract, Contract):
        raise CanonicalizationInputError(
            "canonicalization requires an exact supported Contract root", path=()
        )
    vlimits = (
        validation_limits
        if validation_limits is not None
        else ValidationLimits.default()
    )
    try:
        validate_contract(contract, limits=vlimits)
    except ContractCycleError as exc:
        raise CanonicalizationCycleError(
            "contract graph failed validation (cycle)", path=exc.path
        ) from exc
    except StageContractComplexityError as exc:
        raise CanonicalizationComplexityError(
            "contract graph failed validation (complexity)", path=exc.path
        ) from exc
    except ContractError as exc:
        raise CanonicalizationNotValidatedError(
            "contract graph did not pass validation", path=exc.path
        ) from exc
    return _canonicalize_core(contract, schema, limits)


__all__: list[str] = ["_build_payload", "_canonicalize_core", "canonicalize_contract"]
