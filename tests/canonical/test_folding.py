from __future__ import annotations

from datetime import UTC, datetime

from derivatrace.canonical import canonicalize_contract
from derivatrace.contracts import (
    Add,
    AllOf,
    AnyOf,
    BooleanConstant,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    Currency,
    ExactNumber,
    Maximum,
    Minimum,
    Multiply,
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
)

usd = Currency.from_code("USD")
T0 = SettlementTime.from_datetime(datetime(2030, 1, 1, tzinfo=UTC))
OT0 = ObservationTime.from_datetime(datetime(2030, 1, 1, tzinfo=UTC))


def _obs(namespace: str, identifier: str, field: str) -> Observable:
    return Observable(
        ObservableId.from_parts(namespace, identifier, field), OT0, Unit.money(usd)
    )


def _scalar_obs() -> Observable:
    return Observable(
        ObservableId.from_parts("scalar", "factor", "value"), OT0, Unit.scalar()
    )


obs_A = _obs("equity", "AAA", "close")
obs_B = _obs("equity", "BBB", "close")
shared = Payment(Add((obs_A, obs_B)), usd, T0)


def num(s: str) -> Number:
    return Number(ExactNumber.from_string(s), Unit.scalar())


def test_multiply_of_literals_folds_to_number_node() -> None:
    folded = Scale(Multiply(num("2"), num("3")), shared)
    result = canonicalize_contract(folded)
    # The Multiply operator node is replaced by a literal Number("6") ...
    assert b"Multiply" not in result.canonical_bytes
    assert b'"digits":"6"' in result.canonical_bytes
    # ... and commutation yields the identical canonical contract (folded
    # literal operands are pruned by the reachable-only policy).
    commuted = Scale(Multiply(num("3"), num("2")), shared)
    assert canonicalize_contract(commuted) == result


def test_add_of_literals_folds_to_number_node() -> None:
    # Use a Payment (not the `shared` Add) as the contract so the only Add
    # operator is the one being folded, keeping the assertion unambiguous.
    folded = Scale(Add((num("1"), num("2"))), Payment(obs_A, usd, T0))
    result = canonicalize_contract(folded)
    assert b"Add" not in result.canonical_bytes
    assert b'"digits":"3"' in result.canonical_bytes
    assert (
        canonicalize_contract(Scale(Add((num("2"), num("1"))), Payment(obs_A, usd, T0)))
        == result
    )


def test_subtract_of_literals_folds_to_number_node() -> None:
    folded = Scale(Subtract(num("5"), num("2")), shared)
    result = canonicalize_contract(folded)
    assert b"Subtract" not in result.canonical_bytes
    assert b'"digits":"3"' in result.canonical_bytes


def test_maximum_of_literals_folds_to_number_node() -> None:
    folded = Scale(Maximum((num("1"), num("5"), num("3"))), shared)
    result = canonicalize_contract(folded)
    assert b"Maximum" not in result.canonical_bytes
    assert b'"digits":"5"' in result.canonical_bytes


def test_minimum_of_literals_folds_to_number_node() -> None:
    folded = Scale(Minimum((num("5"), num("2"), num("3"))), shared)
    result = canonicalize_contract(folded)
    assert b"Minimum" not in result.canonical_bytes
    assert b'"digits":"2"' in result.canonical_bytes


def test_conditional_contract_constant_true_selects_true_branch() -> None:
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    result = canonicalize_contract(ConditionalContract(BooleanConstant(True), pa, pb))
    # The conditional collapses to the true branch; the constant condition and
    # false branch are pruned. The canonical document is identical to the
    # true branch alone.
    assert result == canonicalize_contract(pa)


def test_conditional_contract_constant_false_selects_false_branch() -> None:
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    result = canonicalize_contract(ConditionalContract(BooleanConstant(False), pa, pb))
    assert result.root_node_id == canonicalize_contract(pb).root_node_id


def test_not_of_constant_collapses() -> None:
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    result = canonicalize_contract(
        ConditionalContract(Not(BooleanConstant(True)), pa, pb)
    )
    assert result.root_node_id == canonicalize_contract(pb).root_node_id


def test_allof_anyof_of_constants_collapse() -> None:
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    true_branch = canonicalize_contract(pa).root_node_id
    assert (
        canonicalize_contract(
            ConditionalContract(
                AllOf((BooleanConstant(True), BooleanConstant(True))), pa, pb
            )
        ).root_node_id
        == true_branch
    )
    assert (
        canonicalize_contract(
            ConditionalContract(
                AnyOf((BooleanConstant(False), BooleanConstant(True))), pa, pb
            )
        ).root_node_id
        == true_branch
    )


def test_comparison_of_literals_folds_to_constant() -> None:
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    # 2 < 1 is False, so the conditional selects the false branch.
    result = canonicalize_contract(
        ConditionalContract(
            Comparison(num("2"), num("1"), ComparisonOperator.LESS_THAN), pa, pb
        )
    )
    assert result.root_node_id == canonicalize_contract(pb).root_node_id


def test_add_nested_vs_flat_identical() -> None:
    # Nested Add and flat Add canonicalize identically (associative flattening).
    # The inner Add is pruned; no orphan nodes remain.
    nested = Payment(Add((obs_A, Add((obs_B, obs_A)))), usd, T0)
    flat = Payment(Add((obs_A, obs_B, obs_A)), usd, T0)
    rn = canonicalize_contract(nested)
    rf = canonicalize_contract(flat)
    assert rn == rf
    # Both have the same node count (no orphan inner Add).
    assert rn.node_count == rf.node_count


def test_multiply_is_not_flattened() -> None:
    # A money Multiply lives in the Payment amount (Scale factor must stay
    # dimensionless), exercising the binary, non-flattened operator directly.
    a = Payment(Multiply(obs_A, num("2")), usd, T0)
    b = Payment(Multiply(num("2"), obs_A), usd, T0)
    # Commutative reordering makes them identical ...
    assert canonicalize_contract(a) == canonicalize_contract(b)
    # ... and Multiply is never flattened (always binary).
    assert b"Multiply" in canonicalize_contract(a).canonical_bytes


def test_maximum_nested_vs_flat_identical() -> None:
    # Nested Maximum and flat Maximum canonicalize identically (associative flattening).
    # The inner Maximum is pruned; no orphan nodes remain.
    nested = Scale(Maximum((num("1"), Maximum((num("2"), num("3"))))), shared)
    flat = Scale(Maximum((num("1"), num("2"), num("3"))), shared)
    rn = canonicalize_contract(nested)
    rf = canonicalize_contract(flat)
    assert rn == rf
    assert rn.node_count == rf.node_count


def test_minimum_nested_vs_flat_identical() -> None:
    # Nested Minimum and flat Minimum canonicalize identically (associative flattening).
    # The inner Minimum is pruned; no orphan nodes remain.
    nested = Scale(Minimum((num("5"), Minimum((num("2"), num("3"))))), shared)
    flat = Scale(Minimum((num("5"), num("2"), num("3"))), shared)
    rn = canonicalize_contract(nested)
    rf = canonicalize_contract(flat)
    assert rn == rf
    assert rn.node_count == rf.node_count


def test_allof_nested_vs_flat_identical() -> None:
    # Nested AllOf and flat AllOf canonicalize identically (associative flattening)
    # when not fully literal-folded. The inner AllOf is pruned.
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    nested = ConditionalContract(
        AllOf(
            (
                BooleanConstant(True),
                AllOf((BooleanConstant(True), BooleanConstant(False))),
            )
        ),
        pa,
        pb,
    )
    flat = ConditionalContract(
        AllOf((BooleanConstant(True), BooleanConstant(True), BooleanConstant(False))),
        pa,
        pb,
    )
    rn = canonicalize_contract(nested)
    rf = canonicalize_contract(flat)
    assert rn == rf
    assert rn.node_count == rf.node_count


def test_anyof_nested_vs_flat_identical() -> None:
    # Nested AnyOf and flat AnyOf canonicalize identically (associative flattening)
    # when not fully literal-folded. The inner AnyOf is pruned.
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    nested = ConditionalContract(
        AnyOf(
            (
                BooleanConstant(False),
                AnyOf((BooleanConstant(True), BooleanConstant(False))),
            )
        ),
        pa,
        pb,
    )
    flat = ConditionalContract(
        AnyOf((BooleanConstant(False), BooleanConstant(True), BooleanConstant(False))),
        pa,
        pb,
    )
    rn = canonicalize_contract(nested)
    rf = canonicalize_contract(flat)
    assert rn == rf
    assert rn.node_count == rf.node_count


# ---------------------------------------------------------------------------
# BLOCKER 2: Nonliteral AllOf/AnyOf associative flattening tests
# ---------------------------------------------------------------------------


def _obs_cmp(lhs: Observable, rhs: Observable) -> Comparison:
    """Create a non-constant Comparison between two observables."""
    return Comparison(lhs, rhs, ComparisonOperator.LESS_THAN)


def test_allof_nonliteral_nested_vs_flat_identical() -> None:
    # Nested AllOf and flat AllOf with nonliteral (observable) Comparison
    # operands canonicalize identically. The inner AllOf is pruned.
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    comp_a = _obs_cmp(obs_A, obs_B)
    comp_b = _obs_cmp(obs_B, obs_A)

    nested = ConditionalContract(AllOf((comp_a, AllOf((comp_b, comp_a)))), pa, pb)
    flat = ConditionalContract(AllOf((comp_a, comp_b, comp_a)), pa, pb)
    rn = canonicalize_contract(nested)
    rf = canonicalize_contract(flat)
    assert rn.canonical_bytes == rf.canonical_bytes
    assert rn.identity == rf.identity
    assert rn.root_node_id == rf.root_node_id
    assert rn.node_count == rf.node_count
    # Exactly one reachable AllOf node, inner collection absent.
    doc = rn.canonical_bytes
    assert doc.count(b'"type":"AllOf"') == 1
    assert b"AllOf" not in rn.canonical_bytes.replace(b'"type":"AllOf"', b"", 1)
    # The condition does not fold to BooleanConstant.
    assert b'"type":"BooleanConstant"' not in rn.canonical_bytes


def test_anyof_nonliteral_nested_vs_flat_identical() -> None:
    # Nested AnyOf and flat AnyOf with nonliteral (observable) Comparison
    # operands canonicalize identically. The inner AnyOf is pruned.
    pa = Payment(obs_A, usd, T0)
    pb = Payment(obs_B, usd, T0)
    comp_a = _obs_cmp(obs_A, obs_B)
    comp_b = _obs_cmp(obs_B, obs_A)

    nested = ConditionalContract(AnyOf((comp_a, AnyOf((comp_b, comp_a)))), pa, pb)
    flat = ConditionalContract(AnyOf((comp_a, comp_b, comp_a)), pa, pb)
    rn = canonicalize_contract(nested)
    rf = canonicalize_contract(flat)
    assert rn.canonical_bytes == rf.canonical_bytes
    assert rn.identity == rf.identity
    assert rn.root_node_id == rf.root_node_id
    assert rn.node_count == rf.node_count
    # Exactly one reachable AnyOf node, inner collection absent.
    doc = rn.canonical_bytes
    assert doc.count(b'"type":"AnyOf"') == 1
    assert b"AnyOf" not in rn.canonical_bytes.replace(b'"type":"AnyOf"', b"", 1)
    # The condition does not fold to BooleanConstant.
    assert b'"type":"BooleanConstant"' not in rn.canonical_bytes


# ---------------------------------------------------------------------------
# BLOCKER 3: Nested Multiply non-flattening test
# ---------------------------------------------------------------------------


def _scalar_num(s: str) -> Number:
    return Number(ExactNumber.from_string(s), Unit.scalar())


def _money_obs() -> Observable:
    return Observable(
        ObservableId.from_parts("equity", "AAA", "close"), OT0, Unit.money(usd)
    )


def test_multiply_nested_not_flattened() -> None:
    # Multiply is binary and never flattened. Use nonliteral observables so
    # literal folding cannot erase the operator.
    money = _money_obs()
    scalar_a = _scalar_obs()
    scalar_b = _scalar_obs()

    # money * (scalar_a * scalar_b)
    inner_mul = Multiply(scalar_a, scalar_b)
    grouping1 = Payment(Multiply(money, inner_mul), usd, T0)

    # (money * scalar_a) * scalar_b
    left_mul = Multiply(money, scalar_a)
    grouping2 = Payment(Multiply(left_mul, scalar_b), usd, T0)

    r1 = canonicalize_contract(grouping1)
    r2 = canonicalize_contract(grouping2)

    # Each canonical document contains two reachable Multiply nodes.
    multiplies1 = r1.canonical_bytes.count(b'"type":"Multiply"')
    multiplies2 = r2.canonical_bytes.count(b'"type":"Multiply"')
    assert multiplies1 == 2
    assert multiplies2 == 2
    # Every Multiply payload has exactly left and right references (no operands array).
    doc1 = r1.canonical_bytes
    doc2 = r2.canonical_bytes
    assert b'"left"' in doc1 and b'"right"' in doc1
    assert b'"left"' in doc2 and b'"right"' in doc2
    assert b'"operands"' not in doc1 and b'"operands"' not in doc2

    # The two groupings have different canonical bytes and different identities.
    assert r1.canonical_bytes != r2.canonical_bytes
    assert r1.identity != r2.identity

    # Swapping left/right within the same binary grouping remains canonically
    # identical (commutativity without associativity).
    grouping1_commuted = Payment(Multiply(inner_mul, money), usd, T0)
    r1_commuted = canonicalize_contract(grouping1_commuted)
    assert r1_commuted.canonical_bytes == r1.canonical_bytes
    assert r1_commuted.identity == r1.identity
