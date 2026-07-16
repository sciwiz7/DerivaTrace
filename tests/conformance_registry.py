"""Executable conformance registry for the Stage 1B-R2 payoff-graph runtime.

This module is the single source of truth for the documented R2 conformance
vectors. Every entry pairs the documented ``expected`` graph identity with one
or more source builders that must all compile to exactly that identity. The
builders use only the public Stage 1A API, so the vectors stay constructible
and valid through ``validate_contract``.

The test suite guarantees:

* ``compile_payoff_graph(builder()).identity == expected`` for every entry;
* for entries with more than one builder (reorder / flatten / copy invariance),
  every builder yields the same identity;
* the conformance section of ``docs/canonical-test-vectors.md`` documents exactly
  the identities recorded here (no documented identity is unused, and no runtime
  conformance vector is undocumented).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from derivatrace.contracts import (
    Add,
    AllOf,
    AnyOf,
    Both,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    ConditionalValue,
    Currency,
    Divide,
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
    Zero,
)

USD = Currency.from_code("USD")
T0 = ObservationTime.from_datetime(
    __import__("datetime").datetime(2030, 1, 1, tzinfo=__import__("datetime").UTC)
)
T0ST = SettlementTime.from_datetime(
    __import__("datetime").datetime(2030, 1, 1, tzinfo=__import__("datetime").UTC)
)
T0_MS_ST = SettlementTime.from_datetime(
    __import__("datetime").datetime(
        2030, 1, 1, 0, 0, 0, 500000, tzinfo=__import__("datetime").UTC
    )
)
GT = ComparisonOperator.GREATER_THAN


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


# --- Source builders (one or more per documented vector) -------------------


def _b_pgconstant() -> Payment:
    return _pay(_num("100"))


def _b_pgadd_ab() -> Payment:
    return _pay(Add((_obs("AAA"), _obs("BBB"))))


def _b_pgadd_ba() -> Payment:
    return _pay(Add((_obs("BBB"), _obs("AAA"))))


def _b_sub_ab() -> Payment:
    return _pay(Subtract(_obs("AAA"), _obs("BBB")))


def _b_sub_ba() -> Payment:
    return _pay(Subtract(_obs("BBB"), _obs("AAA")))


def _b_add_nest() -> Payment:
    return _pay(Add((_obs("AAA"), Add((_obs("BBB"), _obs("XXX"))))))


def _b_add_flat() -> Payment:
    return _pay(Add((_obs("AAA"), _obs("BBB"), _obs("XXX"))))


def _b_mul_comm_ab() -> Payment:
    return _pay(Multiply(_obs("AAA"), _num("2", scalar=True)))


def _b_mul_comm_ba() -> Payment:
    return _pay(Multiply(_num("2", scalar=True), _obs("AAA")))


def _b_mul_right() -> Payment:
    return _pay(
        Multiply(_obs("AAA"), Multiply(_num("2", scalar=True), _num("3", scalar=True)))
    )


def _b_mul_left() -> Payment:
    return _pay(
        Multiply(Multiply(_obs("AAA"), _num("2", scalar=True)), _num("3", scalar=True))
    )


def _b_div_ab() -> Any:
    return Scale(Divide(_scobs("SCALARA"), _scobs("SCALARB")), _pay(_obs("AAA")))


def _b_div_ba() -> Any:
    return Scale(Divide(_scobs("SCALARB"), _scobs("SCALARA")), _pay(_obs("AAA")))


def _b_comb_ab() -> Any:
    return Both((_pay(_obs("AAA")), _pay(_obs("BBB"))))


def _b_comb_ba() -> Any:
    return Both((_pay(_obs("BBB")), _pay(_obs("AAA"))))


def _b_dup_add() -> Payment:
    return _pay(Add((_obs("AAA"), _obs("AAA"))))


def _b_single_obs() -> Payment:
    return _pay(_obs("AAA"))


def _b_dup_mul() -> Any:
    shared = _scobs("SCALARA")
    return Scale(Multiply(shared, shared), _pay(_obs("AAA")))


def _b_dup_comb() -> Any:
    shared = _pay(_obs("AAA"))
    return Both((shared, shared))


def _b_shared() -> Any:
    shared = _pay(Add((_obs("AAA"), _obs("BBB"))))
    return Both((shared, Scale(_num("2", scalar=True), shared)))


def _b_cv() -> Payment:
    return _pay(
        ConditionalValue(
            Comparison(_obs("AAA"), _obs("BBB"), GT), _obs("AAA"), _obs("BBB")
        )
    )


def _b_cc() -> Any:
    return ConditionalContract(
        Comparison(_obs("AAA"), _obs("BBB"), GT), _pay(_obs("AAA")), _pay(_obs("BBB"))
    )


def _b_zero() -> Any:
    return Zero()


def _b_ts_000() -> Payment:
    return Payment(_num("1"), USD, T0ST)


def _b_ts_500() -> Payment:
    return Payment(_num("1"), USD, T0_MS_ST)


def _b_allof_nest() -> Payment:
    return _pay(
        ConditionalValue(
            AllOf(
                (
                    Comparison(_obs("AAA"), _obs("BBB"), GT),
                    AllOf(
                        (
                            Comparison(_obs("BBB"), _obs("XXX"), GT),
                            Comparison(_obs("AAA"), _obs("XXX"), GT),
                        )
                    ),
                )
            ),
            _obs("AAA"),
            _obs("BBB"),
        )
    )


def _b_allof_flat() -> Payment:
    return _pay(
        ConditionalValue(
            AllOf(
                (
                    Comparison(_obs("AAA"), _obs("BBB"), GT),
                    Comparison(_obs("BBB"), _obs("XXX"), GT),
                    Comparison(_obs("AAA"), _obs("XXX"), GT),
                )
            ),
            _obs("AAA"),
            _obs("BBB"),
        )
    )


def _b_anyof_nest() -> Payment:
    return _pay(
        ConditionalValue(
            AnyOf(
                (
                    Comparison(_obs("AAA"), _obs("BBB"), GT),
                    AnyOf(
                        (
                            Comparison(_obs("BBB"), _obs("XXX"), GT),
                            Comparison(_obs("AAA"), _obs("XXX"), GT),
                        )
                    ),
                )
            ),
            _obs("AAA"),
            _obs("BBB"),
        )
    )


def _b_anyof_flat() -> Payment:
    return _pay(
        ConditionalValue(
            AnyOf(
                (
                    Comparison(_obs("AAA"), _obs("BBB"), GT),
                    Comparison(_obs("BBB"), _obs("XXX"), GT),
                    Comparison(_obs("AAA"), _obs("XXX"), GT),
                )
            ),
            _obs("AAA"),
            _obs("BBB"),
        )
    )


# name -> (documented expected identity, [builders that must all match it])
CONFORMANCE_VECTORS: dict[str, tuple[str, list[Callable[[], Any]]]] = {
    "pg_constant": (
        "payoffgraph:sha256:858624784eed60272f1c73fb5b52d2547eec326dc2bd2862a3db3a42ecc07922",
        [_b_pgconstant],
    ),
    "pgadd_commutation": (
        "payoffgraph:sha256:59fbb00dbb585755a799cd7e387e4ee51fd9b77ed3cc032758a825f2f8836e1a",
        [_b_pgadd_ab, _b_pgadd_ba],
    ),
    "pg_subtract_ab": (
        "payoffgraph:sha256:55ada2494e58231140c15e261b80ff294db26f88bb97e454576db82fe6d8c10a",
        [_b_sub_ab],
    ),
    "pg_subtract_ba": (
        "payoffgraph:sha256:e0c7bba00c37d8305ee99a0ef0c5fa041ff3ab2164298a0e8584bcfbec1713f5",
        [_b_sub_ba],
    ),
    "pg_add_flattening": (
        "payoffgraph:sha256:7e7690a487af6a85d03f0ffe3a310fb0747936f5b0ae4e6e61bd5b5443eafa69",
        [_b_add_nest, _b_add_flat],
    ),
    "pg_multiply_commutation": (
        "payoffgraph:sha256:189ad22220104a4f8f80f0e57d791365222dd435f395232857d2d09db605dae5",
        [_b_mul_comm_ab, _b_mul_comm_ba],
    ),
    "pg_multiply_right_assoc": (
        "payoffgraph:sha256:7f2f3af0b53308827d1429f650c7997c043e39d3558f81005b5a71525bb71657",
        [_b_mul_right],
    ),
    "pg_multiply_left_assoc": (
        "payoffgraph:sha256:73c5bf6236ebf88f9cce9318d9f1624cb18beb9f72e2e90e53fe9fe1f4bb7563",
        [_b_mul_left],
    ),
    "pg_divide_ab": (
        "payoffgraph:sha256:3859b48afb878ec09a881b8de7c13b19dcdfcb320ad39a2707119566038defac",
        [_b_div_ab],
    ),
    "pg_divide_ba": (
        "payoffgraph:sha256:b603b81912c92224c22fb66a9a101bdc9aeedce4370f9cb395d21f0ef011242a",
        [_b_div_ba],
    ),
    "pg_combine_ab": (
        "payoffgraph:sha256:ea878884b83fea0dafbd1703e863cf356d59eaeaff410d50836a2d69d4535314",
        [_b_comb_ab],
    ),
    "pg_combine_ba": (
        "payoffgraph:sha256:ee2dfa4a1b99cc3f11be777668c120b593ec2464247e0320e7934270276fea05",
        [_b_comb_ba],
    ),
    "pg_duplicate_add": (
        "payoffgraph:sha256:ac7653325470e272d3c32d96c027e3d4e93840f529b8be7e73b9376738b48742",
        [_b_dup_add],
    ),
    "pg_single_observable": (
        "payoffgraph:sha256:07a5cf79d4942881810c8fce6158c27a623b1cf420819b7d1215f7c47c5cbaa2",
        [_b_single_obs],
    ),
    "pg_duplicate_multiply": (
        "payoffgraph:sha256:0025c2a2ed75cf9a442298ae2e78bfd6df0c8b5e19aacc47a53b2ee268c877db",
        [_b_dup_mul],
    ),
    "pg_duplicate_combine": (
        "payoffgraph:sha256:48ad96391a4202b61b5bf13a16e1cf2690266b0ee9566f655505fe241297df3d",
        [_b_dup_comb],
    ),
    "pg_shared_subgraph": (
        "payoffgraph:sha256:b5c987269d9b16f5605c4d49621aef2d93e4a65c0b083718e5e3d27e027cb04c",
        [_b_shared],
    ),
    "pg_conditional_value": (
        "payoffgraph:sha256:719e567c5b7023469b5035156d1af63c0f8c70b6e4e911dc9849df01af786666",
        [_b_cv],
    ),
    "pg_conditional_contract": (
        "payoffgraph:sha256:155177c729b3dd1673fc34d1521985bf187b2395b2300eab7cbd96c63075fa4d",
        [_b_cc],
    ),
    "pg_zero": (
        "payoffgraph:sha256:6cf223e52d6f1f016dd920568e48dcf9fd3576d374b1a073f46b768f6cdc9f67",
        [_b_zero],
    ),
    "pg_timestamp_000000": (
        "payoffgraph:sha256:d4e7c6f6d6e90b87c13155a71c54be3c872c04165eac9a7732fb345954e88719",
        [_b_ts_000],
    ),
    "pg_timestamp_500000": (
        "payoffgraph:sha256:698aa543f12b6ce911885c73f5cef35a1723d3be492d8b00c86a6d1865209e30",
        [_b_ts_500],
    ),
    "pg_allof_flattening": (
        "payoffgraph:sha256:d2ecc0ce66d3bf79f741e4e5fd1593f3049ed75fa8eb5ea4ed444ce1c80c8e26",
        [_b_allof_nest, _b_allof_flat],
    ),
    "pg_anyof_flattening": (
        "payoffgraph:sha256:bfb09528718bbf825d4f34229d1591875e6d2ba3e17ddb7d7abba0916eeb6aba",
        [_b_anyof_nest, _b_anyof_flat],
    ),
}


__all__: list[str] = ["CONFORMANCE_VECTORS"]
