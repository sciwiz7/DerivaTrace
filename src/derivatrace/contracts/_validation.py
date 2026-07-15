from __future__ import annotations

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


def _validate_scalar_node(node: ScalarExpression, path: tuple[str | int, ...]) -> None:
    if isinstance(node, Number):
        _expect_type(node.value, ExactNumber, "Number.value", path)
        _expect_type(node.unit, Unit, "Number.unit", path)
        return
    if isinstance(node, Observable):
        _expect_type(node.observable_id, ObservableId, "Observable.observable_id", path)
        _expect_type(
            node.observation_time,
            ObservationTime,
            "Observable.observation_time",
            path,
        )
        _expect_type(node.unit, Unit, "Observable.unit", path)
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
