from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ._contracts import (
    Both,
    ConditionalContract,
    Contract,
    Payment,
    Scale,
    Zero,
)
from ._errors import (
    ContractComplexityError,
    ContractCycleError,
    ContractTypeMismatchError,
    ContractValidationError,
)
from ._expressions import (
    Add,
    AllOf,
    AnyOf,
    BooleanConstant,
    BooleanExpression,
    Comparison,
    ComparisonOperator,
    ConditionalValue,
    Divide,
    Maximum,
    Minimum,
    Multiply,
    Negate,
    Not,
    Number,
    Observable,
    ScalarExpression,
    Subtract,
)
from ._values import (
    _CURRENCY_RE,
    _IDENTIFIER_RE,
    _SLUG_RE,
    FIELD_MAX_LEN,
    IDENTIFIER_MAX_LEN,
    MAX_ABS_EXPONENT,
    MAX_SIGNIFICANT_DIGITS,
    NAMESPACE_MAX_LEN,
    ContractMetrics,
    Currency,
    ExactNumber,
    ObservableId,
    ObservationTime,
    SettlementTime,
    Unit,
    UnitKind,
    ValidationLimits,
)

# Closed, exact supported-concrete-node policy.
#
# Only these exact concrete types are admitted into the deterministic core. A
# subclass of an approved node is NOT automatically approved: it could override
# field access or other behaviour, so the exact type must be one of the reviewed
# classes below. The registry is the single source of truth for the policy.
_SUPPORTED_SCALAR_TYPES: frozenset[type[ScalarExpression]] = frozenset(
    {
        Number,
        Observable,
        Add,
        Subtract,
        Multiply,
        Divide,
        Negate,
        Maximum,
        Minimum,
        ConditionalValue,
    }
)

_SUPPORTED_BOOLEAN_TYPES: frozenset[type[BooleanExpression]] = frozenset(
    {
        BooleanConstant,
        Comparison,
        AllOf,
        AnyOf,
        Not,
    }
)

_SUPPORTED_CONTRACT_TYPES: frozenset[type[Contract]] = frozenset(
    {
        Zero,
        Payment,
        Both,
        Scale,
        ConditionalContract,
    }
)

_SUPPORTED_NODE_TYPES = (
    _SUPPORTED_SCALAR_TYPES | _SUPPORTED_BOOLEAN_TYPES | _SUPPORTED_CONTRACT_TYPES
)


def _ensure_supported_node_type(
    node: object,
    path: tuple[str | int, ...],
) -> None:
    if type(node) not in _SUPPORTED_NODE_TYPES:
        raise ContractValidationError(
            f"unsupported node type: {type(node).__name__}", path=path
        )


def _expect_type(
    value: object,
    expected: type,
    name: str,
    path: tuple[str | int, ...],
) -> None:
    if not isinstance(value, expected):
        raise ContractValidationError(f"{name} must be {expected.__name__}", path=path)


def _expect_scalar_collection(
    operands: object, name: str, path: tuple[str | int, ...]
) -> None:
    if not isinstance(operands, tuple):
        raise ContractTypeMismatchError(f"{name} must be a tuple", path=path)
    if len(operands) < 2:
        raise ContractValidationError(
            f"{name} requires at least two operands", path=path
        )
    first_unit: Unit | None = None
    for index, operand in enumerate(operands):
        if not isinstance(operand, ScalarExpression):
            raise ContractTypeMismatchError(
                f"{name}[{index}] must be a ScalarExpression", path=path
            )
        if first_unit is None:
            first_unit = operand.unit
        elif operand.unit != first_unit:
            raise ContractValidationError(f"{name}[{index}] unit mismatch", path=path)


def _expect_boolean_collection(
    operands: object, name: str, path: tuple[str | int, ...]
) -> None:
    if not isinstance(operands, tuple):
        raise ContractTypeMismatchError(f"{name} must be a tuple", path=path)
    if len(operands) < 2:
        raise ContractValidationError(
            f"{name} requires at least two operands", path=path
        )
    for index, operand in enumerate(operands):
        if not isinstance(operand, BooleanExpression):
            raise ContractTypeMismatchError(
                f"{name}[{index}] must be a BooleanExpression", path=path
            )


def _multiply_unit(a: Unit, b: Unit) -> Unit:
    if a.kind == UnitKind.MONEY and b.kind == UnitKind.MONEY:
        raise ContractValidationError("money x money is rejected")
    if a.kind == UnitKind.MONEY:
        return a
    if b.kind == UnitKind.MONEY:
        return b
    return Unit.scalar()


# ---------------------------------------------------------------------------
# Value-object invariant revalidation
# ---------------------------------------------------------------------------
#
# Construction validates inputs immediately, but a frozen object can be mutated
# after the fact via ``object.__setattr__``. Graph validation must therefore
# re-check the *stored* internal state of every value object rather than trust
# its attributes or re-run the public constructor (which would silently
# normalize forged-but-valid state). Each validator below inspects the raw
# private fields and re-derives the original construction invariants.
#
# Exact-type policy: deterministic value objects require the *exact* approved
# type. A subclass of e.g. ``Currency`` could override ``__eq__`` or other
# behaviour, so ``isinstance`` is not sufficient; we require ``type(x) is T``.


def _validate_exact_number_invariants(
    obj: ExactNumber, path: tuple[str | int, ...]
) -> None:
    if type(obj) is not ExactNumber:
        raise ContractValidationError(
            "ExactNumber must be exactly the approved type", path=path
        )
    value = obj._value
    if not isinstance(value, Decimal):
        raise ContractValidationError("ExactNumber._value must be a Decimal", path=path)
    if not value.is_finite():
        raise ContractValidationError(
            "ExactNumber must be finite (NaN/Infinity rejected)", path=path
        )
    digits = value.as_tuple().digits
    if len(digits) > MAX_SIGNIFICANT_DIGITS:
        raise ContractValidationError(
            "ExactNumber has too many significant digits", path=path
        )
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and abs(exponent) > MAX_ABS_EXPONENT:
        raise ContractValidationError(
            "ExactNumber exponent magnitude exceeds limit", path=path
        )


def _validate_currency_invariants(obj: Currency, path: tuple[str | int, ...]) -> None:
    if type(obj) is not Currency:
        raise ContractValidationError(
            "Currency must be exactly the approved type", path=path
        )
    code = obj._code
    if not isinstance(code, str):
        raise ContractValidationError("Currency._code must be a str", path=path)
    if not _CURRENCY_RE.match(code):
        raise ContractValidationError(
            "Currency must be exactly three uppercase ASCII letters", path=path
        )


def _validate_unit_invariants(obj: Unit, path: tuple[str | int, ...]) -> None:
    if type(obj) is not Unit:
        raise ContractValidationError(
            "Unit must be exactly the approved type", path=path
        )
    kind = obj.kind
    if not isinstance(kind, UnitKind):
        raise ContractValidationError("Unit.kind must be exactly a UnitKind", path=path)
    currency = obj.currency
    if kind is UnitKind.SCALAR:
        if currency is not None:
            raise ContractValidationError(
                "scalar unit cannot carry a currency", path=path
            )
        return
    # ``UnitKind`` is a closed enum, so any other member is ``MONEY``.
    if type(currency) is not Currency:
        raise ContractValidationError("money unit requires a Currency", path=path)


def _validate_observable_id_invariants(
    obj: ObservableId, path: tuple[str | int, ...]
) -> None:
    if type(obj) is not ObservableId:
        raise ContractValidationError(
            "ObservableId must be exactly the approved type", path=path
        )
    namespace = obj.namespace
    identifier = obj.identifier
    field = obj.field
    if not isinstance(namespace, str) or not namespace:
        raise ContractValidationError("namespace must be a non-empty str", path=path)
    if len(namespace) > NAMESPACE_MAX_LEN:
        raise ContractValidationError(
            f"namespace exceeds maximum length {NAMESPACE_MAX_LEN}", path=path
        )
    if not _SLUG_RE.match(namespace):
        raise ContractValidationError(
            "namespace must be a lowercase ASCII slug", path=path
        )
    if not isinstance(field, str) or not field:
        raise ContractValidationError("field must be a non-empty str", path=path)
    if len(field) > FIELD_MAX_LEN:
        raise ContractValidationError(
            f"field exceeds maximum length {FIELD_MAX_LEN}", path=path
        )
    if not _SLUG_RE.match(field):
        raise ContractValidationError("field must be a lowercase ASCII slug", path=path)
    if not isinstance(identifier, str) or not identifier:
        raise ContractValidationError("identifier must be a non-empty str", path=path)
    if len(identifier) > IDENTIFIER_MAX_LEN:
        raise ContractValidationError(
            f"identifier exceeds maximum length {IDENTIFIER_MAX_LEN}", path=path
        )
    if not _IDENTIFIER_RE.match(identifier):
        raise ContractValidationError(
            "identifier must be conservative ASCII", path=path
        )


def _validate_aware_datetime_invariants(
    obj: object,
    raw: datetime,
    name: str,
    path: tuple[str | int, ...],
) -> None:
    if not isinstance(raw, datetime):
        raise ContractValidationError(f"{name}._value must be a datetime", path=path)
    if raw.tzinfo is None:
        raise ContractValidationError(f"{name} must be timezone-aware", path=path)
    try:
        offset = raw.utcoffset()
    except Exception as exc:
        raise ContractValidationError(
            f"{name} has an invalid timezone offset", path=path
        ) from exc
    if offset is None:
        raise ContractValidationError(
            f"{name} requires a concrete UTC offset", path=path
        )


def _validate_observation_time_invariants(
    obj: ObservationTime, path: tuple[str | int, ...]
) -> None:
    if type(obj) is not ObservationTime:
        raise ContractValidationError(
            "ObservationTime must be exactly the approved type", path=path
        )
    _validate_aware_datetime_invariants(obj, obj._value, "ObservationTime", path)


def _validate_settlement_time_invariants(
    obj: SettlementTime, path: tuple[str | int, ...]
) -> None:
    if type(obj) is not SettlementTime:
        raise ContractValidationError(
            "SettlementTime must be exactly the approved type", path=path
        )
    _validate_aware_datetime_invariants(obj, obj._value, "SettlementTime", path)


def _validate_validation_limits_invariants(
    obj: ValidationLimits, path: tuple[str | int, ...]
) -> None:
    if type(obj) is not ValidationLimits:
        raise ContractValidationError(
            "ValidationLimits must be exactly the approved type", path=path
        )
    depth = obj.max_depth
    nodes = obj.max_unique_nodes
    if isinstance(depth, bool) or not isinstance(depth, int) or depth <= 0:
        raise ContractValidationError(
            "ValidationLimits.max_depth must be an int greater than zero", path=path
        )
    if isinstance(nodes, bool) or not isinstance(nodes, int) or nodes <= 0:
        raise ContractValidationError(
            "ValidationLimits.max_unique_nodes must be an int greater than zero",
            path=path,
        )


def _validate_scalar_node(node: ScalarExpression, path: tuple[str | int, ...]) -> None:
    # Every scalar expression carries a Unit; revalidate its stored invariants
    # before trusting it (e.g. in unit-arithmetic and mismatch checks below).
    _validate_unit_invariants(node.unit, path)
    if isinstance(node, Number):
        _validate_exact_number_invariants(node.value, path)
        _expect_type(node.value, ExactNumber, "Number.value", path)
        return
    if isinstance(node, Observable):
        _validate_observable_id_invariants(node.observable_id, path)
        _validate_observation_time_invariants(node.observation_time, path)
        _expect_type(node.observable_id, ObservableId, "Observable.observable_id", path)
        _expect_type(
            node.observation_time,
            ObservationTime,
            "Observable.observation_time",
            path,
        )
        return
    if isinstance(node, Add):
        _expect_scalar_collection(node.operands, "Add.operands", path)
        _expect_type(node.unit, Unit, "Add.unit", path)
        if node.operands[0].unit != node.unit:
            raise ContractValidationError("Add unit mismatch", path=path)
        return
    if isinstance(node, Subtract):
        _expect_type(node.minuend, ScalarExpression, "Subtract.minuend", path)
        _expect_type(node.subtrahend, ScalarExpression, "Subtract.subtrahend", path)
        if node.minuend.unit != node.subtrahend.unit:
            raise ContractValidationError("Subtract unit mismatch", path=path)
        if node.minuend.unit != node.unit:
            raise ContractValidationError("Subtract unit mismatch", path=path)
        return
    if isinstance(node, Multiply):
        _expect_type(node.left, ScalarExpression, "Multiply.left", path)
        _expect_type(node.right, ScalarExpression, "Multiply.right", path)
        expected = _multiply_unit(node.left.unit, node.right.unit)
        if expected != node.unit:
            raise ContractValidationError("Multiply unit mismatch", path=path)
        return
    if isinstance(node, Divide):
        _expect_type(node.numerator, ScalarExpression, "Divide.numerator", path)
        _expect_type(node.denominator, ScalarExpression, "Divide.denominator", path)
        if node.denominator.unit.kind != UnitKind.SCALAR:
            raise ContractValidationError(
                "Divide denominator must be dimensionless", path=path
            )
        if isinstance(node.denominator, Number) and node.denominator.value.value == 0:
            raise ContractValidationError(
                "Divide rejects a literal zero denominator", path=path
            )
        if node.numerator.unit != node.unit:
            raise ContractValidationError("Divide unit mismatch", path=path)
        return
    if isinstance(node, Negate):
        _expect_type(node.operand, ScalarExpression, "Negate.operand", path)
        if node.operand.unit != node.unit:
            raise ContractValidationError("Negate unit mismatch", path=path)
        return
    if isinstance(node, (Maximum, Minimum)):
        label = type(node).__name__
        _expect_scalar_collection(node.operands, f"{label}.operands", path)
        _expect_type(node.unit, Unit, f"{label}.unit", path)
        if node.operands[0].unit != node.unit:
            raise ContractValidationError(f"{label} unit mismatch", path=path)
        return
    if isinstance(node, ConditionalValue):
        _expect_type(
            node.condition, BooleanExpression, "ConditionalValue.condition", path
        )
        _expect_type(
            node.true_value, ScalarExpression, "ConditionalValue.true_value", path
        )
        _expect_type(
            node.false_value,
            ScalarExpression,
            "ConditionalValue.false_value",
            path,
        )
        if node.true_value.unit != node.false_value.unit:
            raise ContractValidationError(
                "ConditionalValue branch unit mismatch", path=path
            )
        if node.true_value.unit != node.unit:
            raise ContractValidationError("ConditionalValue unit mismatch", path=path)
        return
    raise ContractValidationError(
        f"unsupported scalar node type: {type(node).__name__}", path=path
    )


def _validate_boolean_node(
    node: BooleanExpression, path: tuple[str | int, ...]
) -> None:
    if isinstance(node, BooleanConstant):
        _expect_type(node.value, bool, "BooleanConstant.value", path)
        return
    if isinstance(node, Comparison):
        _expect_type(node.left, ScalarExpression, "Comparison.left", path)
        _expect_type(node.right, ScalarExpression, "Comparison.right", path)
        _expect_type(node.operator, ComparisonOperator, "Comparison.operator", path)
        if node.left.unit != node.right.unit:
            raise ContractValidationError("Comparison unit mismatch", path=path)
        return
    if isinstance(node, (AllOf, AnyOf)):
        label = type(node).__name__
        _expect_boolean_collection(node.operands, f"{label}.operands", path)
        return
    if isinstance(node, Not):
        _expect_type(node.operand, BooleanExpression, "Not.operand", path)
        return
    raise ContractValidationError(
        f"unsupported boolean node type: {type(node).__name__}", path=path
    )


def _validate_contract_node(node: Contract, path: tuple[str | int, ...]) -> None:
    if isinstance(node, Zero):
        return
    if isinstance(node, Payment):
        _expect_type(node.amount, ScalarExpression, "Payment.amount", path)
        _validate_unit_invariants(node.amount.unit, path)
        _validate_currency_invariants(node.currency, path)
        _validate_settlement_time_invariants(node.settlement_time, path)
        _expect_type(node.currency, Currency, "Payment.currency", path)
        _expect_type(
            node.settlement_time, SettlementTime, "Payment.settlement_time", path
        )
        if node.amount.unit.kind != UnitKind.MONEY:
            raise ContractValidationError(
                "Payment amount must be money-denominated", path=path
            )
        if (
            node.amount.unit.currency is None
            or node.amount.unit.currency != node.currency
        ):
            raise ContractValidationError("Payment currency mismatch", path=path)
        return
    if isinstance(node, Both):
        if not isinstance(node.operands, tuple):
            raise ContractTypeMismatchError("Both.operands must be a tuple", path=path)
        if len(node.operands) < 2:
            raise ContractValidationError(
                "Both requires at least two contracts", path=path
            )
        for index, operand in enumerate(node.operands):
            if not isinstance(operand, Contract):
                raise ContractTypeMismatchError(
                    f"Both.operands[{index}] must be a Contract", path=path
                )
        return
    if isinstance(node, Scale):
        _expect_type(node.factor, ScalarExpression, "Scale.factor", path)
        _expect_type(node.contract, Contract, "Scale.contract", path)
        if node.factor.unit.kind != UnitKind.SCALAR:
            raise ContractValidationError(
                "Scale factor must be dimensionless", path=path
            )
        return
    if isinstance(node, ConditionalContract):
        _expect_type(
            node.condition, BooleanExpression, "ConditionalContract.condition", path
        )
        _expect_type(
            node.true_contract, Contract, "ConditionalContract.true_contract", path
        )
        _expect_type(
            node.false_contract,
            Contract,
            "ConditionalContract.false_contract",
            path,
        )
        return
    raise ContractValidationError(
        f"unsupported contract node type: {type(node).__name__}", path=path
    )


def _validate_node_invariants(node: object, path: tuple[str | int, ...]) -> None:
    if isinstance(node, ScalarExpression):
        _validate_scalar_node(node, path)
    elif isinstance(node, BooleanExpression):
        _validate_boolean_node(node, path)
    elif isinstance(node, Contract):
        _validate_contract_node(node, path)
    else:
        raise ContractValidationError(
            f"unsupported node type: {type(node).__name__}", path=path
        )


def _iter_children(
    node: object,
) -> list[tuple[tuple[str | int, ...], object]]:
    """Yield ``(path_segments, child)`` for every child graph node.

    Each child contributes a sequence of path labels (field names and/or integer
    indices) describing how to reach it from its parent.
    """
    children: list[tuple[tuple[str | int, ...], object]] = []
    if isinstance(node, (Add, Maximum, Minimum)):
        for index, scalar_operand in enumerate(node.operands):
            children.append((("operands", index), scalar_operand))
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
        for index, boolean_operand in enumerate(node.operands):
            children.append((("operands", index), boolean_operand))
    elif isinstance(node, Not):
        children.append((("operand",), node.operand))
    elif isinstance(node, Payment):
        children.append((("amount",), node.amount))
    elif isinstance(node, Both):
        for index, contract_operand in enumerate(node.operands):
            children.append((("operands", index), contract_operand))
    elif isinstance(node, Scale):
        children.append((("factor",), node.factor))
        children.append((("contract",), node.contract))
    elif isinstance(node, ConditionalContract):
        children.append((("condition",), node.condition))
        children.append((("true_contract",), node.true_contract))
        children.append((("false_contract",), node.false_contract))
    return children


def validate_contract(
    contract: Contract,
    *,
    limits: ValidationLimits | None = None,
) -> ContractMetrics:
    """Validate a complete contract graph and return deterministic metrics.

    The traversal is iterative (explicit stack), so it cannot be exhausted by
    deep structures. It re-checks every node's critical invariants so that
    objects forged or modified after construction (for example through
    ``object.__setattr__``) cannot bypass validation. Reference cycles are
    detected with a correct colouring algorithm, and safe DAG sharing is
    permitted.

    Depth definition: the root contract counts as depth 1. Node-count
    definition: the number of unique object nodes (by identity); shared
    subexpressions are counted once.

    The function never executes node content, never calls user-provided
    callbacks, and never uses the ``repr`` of untrusted nodes in its errors.
    """
    if limits is None:
        limits = ValidationLimits.default()
    if not isinstance(limits, ValidationLimits):
        raise ContractTypeMismatchError("limits must be ValidationLimits")
    # Revalidate the limits object itself so a forged ValidationLimits (for
    # example one whose max_depth was mutated to a bool or zero) cannot bypass
    # the invariants enforced here.
    _validate_validation_limits_invariants(limits, ())
    if not isinstance(contract, Contract):
        raise ContractValidationError(
            "validate_contract requires a Contract root", path=()
        )

    explored: set[int] = set()
    best_depth: dict[int, int] = {}
    ancestors: set[int] = set()
    counted: set[int] = set()
    node_count = 0
    max_depth = 0

    stack: list[tuple[object, int, tuple[str | int, ...], bool]] = [
        (contract, 1, (), False)
    ]

    while stack:
        node, depth, path, leaving = stack.pop()
        node_id = id(node)

        if leaving:
            explored.add(node_id)
            ancestors.discard(node_id)
            continue

        if node_id in ancestors:
            # The node is on the current traversal path: a reference cycle.
            raise ContractCycleError("cyclic contract graph detected", path=path)
        if node_id in explored and best_depth.get(node_id, -1) >= depth:
            # Already fully explored at an equal-or-greater depth; skip to avoid
            # exponential re-expansion of shared subexpressions (DAG sharing).
            continue

        ancestors.add(node_id)
        if node_id not in counted:
            counted.add(node_id)
            node_count += 1
        best_depth[node_id] = max(best_depth.get(node_id, -1), depth)
        if depth > max_depth:
            max_depth = depth

        if depth > limits.max_depth:
            raise ContractComplexityError(
                f"contract depth {depth} exceeds limit {limits.max_depth}",
                path=path,
            )
        if node_count > limits.max_unique_nodes:
            raise ContractComplexityError(
                f"unique node count {node_count} exceeds limit "
                f"{limits.max_unique_nodes}",
                path=path,
            )

        _ensure_supported_node_type(node, path)

        _validate_node_invariants(node, path)

        # Re-push as a post-order marker that records completion and clears the
        # node from the active ancestor set.
        stack.append((node, depth, path, True))
        for child_segments, child in reversed(_iter_children(node)):
            child_path = path + child_segments
            stack.append((child, depth + 1, child_path, False))

    return ContractMetrics(node_count=node_count, max_depth=max_depth)


__all__: list[str] = ["validate_contract"]
