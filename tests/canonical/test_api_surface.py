from __future__ import annotations

import os
from datetime import UTC, datetime

import derivatrace.canonical as canonical_pkg
from derivatrace.canonical import (
    CanonicalContract,
    canonical_contract_bytes,
    canonical_contract_identity,
    canonicalize_contract,
)
from derivatrace.contracts import (
    Currency,
    ExactNumber,
    Number,
    Observable,
    ObservableId,
    ObservationTime,
    Payment,
    SettlementTime,
    Unit,
)

usd = Currency.from_code("USD")
T0 = SettlementTime.from_datetime(datetime(2030, 6, 1, tzinfo=UTC))
OT0 = ObservationTime.from_datetime(datetime(2030, 6, 1, tzinfo=UTC))


def _obs(nsp: str, ident: str) -> Observable:
    return Observable(
        ObservableId.from_parts(nsp, ident, "close"), OT0, Unit.money(usd)
    )


def _payment() -> Payment:
    return Payment(Number(ExactNumber.from_string("1"), Unit.money(usd)), usd, T0)


def test_public_exports_present() -> None:
    for name in [
        "canonicalize_contract",
        "canonical_contract_bytes",
        "canonical_contract_identity",
        "structurally_equivalent",
        "CanonicalContract",
        "CanonicalSchemaVersion",
        "CanonicalizationLimits",
        "CanonicalizationError",
        "CanonicalizationInputError",
        "CanonicalizationNotValidatedError",
        "CanonicalizationCycleError",
        "CanonicalizationComplexityError",
        "CanonicalizationEncodingError",
        "CanonicalizationCollisionError",
    ]:
        assert hasattr(canonical_pkg, name), name


def test_all_is_locked_and_complete() -> None:
    # Every public symbol is enumerated in __all__ (no accidental exports).
    public = {
        n
        for n in dir(canonical_pkg)
        if not n.startswith("_") and n not in ("annotations",)
    }
    exported = set(canonical_pkg.__all__)
    assert exported <= public
    # No non-underscore name left unexported.
    assert public == exported


def test_canonical_contract_attributes() -> None:
    result = canonicalize_contract(_payment())
    assert isinstance(result, CanonicalContract)
    assert result.identity.startswith("canonical:sha256:")
    assert result.canonical_bytes.startswith(b"{")
    assert result.node_count >= 1
    assert result.root_node_id
    # The typed schema identity object:
    assert result.schema_version.name == "derivatrace.contract.canonical"
    assert result.schema_version.version == "1.0.0"
    # The serialized document carries the schema name/version as JSON keys:
    import json

    doc = json.loads(result.canonical_bytes.decode("utf-8"))
    assert doc["schema_name"] == "derivatrace.contract.canonical"
    assert doc["schema_version"] == "1.0.0"


def test_bytes_and_identity_helpers_equal_canonicalize() -> None:
    contract = _payment()
    c = canonicalize_contract(contract)
    assert canonical_contract_bytes(contract) == c.canonical_bytes
    assert canonical_contract_identity(contract) == c.identity
    assert canonical_contract_identity(contract) == c.identity


def test_py_typed_marker() -> None:
    marker = os.path.join(os.path.dirname(canonical_pkg.__file__), "py.typed")
    assert os.path.isfile(marker)


def test_root_re_exports_only_specific_symbols() -> None:
    # The top-level package must not surface the canonical API as if it were
    # core. This guards against accidental `from derivatrace import canonical`
    # re-exports leaking the R1 API at the wrong level.
    import derivatrace

    assert not hasattr(derivatrace, "canonicalize_contract")
    assert not hasattr(derivatrace, "structurally_equivalent")
