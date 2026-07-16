# Canonical test vectors (Stage 1B-R1 + Stage 1B-R2)

- **Status:** Implemented. Values below are **regenerated from the byte-exact
  Stage 1B-R1 canonical runtime** and the **Stage 1B-R2 payoff-graph runtime**,
  and are directly **constructible and valid through the public Stage 1A API**
  (`validate_contract` succeeds on every source contract).
- **Stage:** 1B (R1 canonical runtime + R2 payoff-graph runtime).
- **Companion docs:** `canonicalization-spec.md`, `payoff-graph-spec.md`, `adr/0007-canonical-contract-identity-and-payoff-graph.md`.

This document defines **normative** canonicalization and payoff-graph test
vectors, under the conservative, enumerated-law approach (no claim of complete
mathematical or economic equivalence). Every `expected_canonical_identity` below
is a **real, computed**
SHA-256 value, cross-checked for the properties the spec requires (reorder
invariance, flattening, duplicate preservation, distinctness under author-order
change, content-addressed sharing, timestamp precision, and a payoff-graph
compilation). No vector contains a placeholder, `TBD`, `example-hash`, or
all-zero identity.

> The R1 canonical vectors (CV-001–CV-010) are **executed by the Stage 1B-R1
> canonical runtime**. Every source contract is constructed through the public
> Stage 1A API and `validate_contract` succeeds; the canonical bytes, node
> identities, and contract identities are produced by the runtime and reproduced
> byte-for-byte in the accompanying test suite (`tests/canonical/test_vectors.py`).
>
> **CV-011 is a normative Stage 1B-R2 payoff-graph vector.** Its exact canonical
> payload bytes, node ids, structural bytes, document bytes, and graph identity
> were computed with a small, isolated **standard-library-only** verification
> script (not shipped in the repository) using the byte-exact rules of
> `canonicalization-spec.md` §3 and the payoff-graph identity preimage of
> `payoff-graph-spec.md` §9. The script cross-checks every hash preimage
> independently; no placeholder or deferred hash is used. The CV-011 source
> contract is the same canonical contract already verified by R1 (its canonical
> contract identity must agree with R1), and its payoff-graph identity is
> reproduced byte-for-byte by the Stage 1B-R2 runtime in
> `tests/payoffgraph/test_compiler.py`.

## 1. Conventions

- **Canonical bytes** = `json.dumps(obj, ensure_ascii=True, sort_keys=True,
  separators=(",", ":"))` encoded as UTF-8, **no BOM, no trailing newline**
  (`canonicalization-spec.md` §3).
- **Node identity** = `SHA-256("derivatrace.canonical.node" + "\x00" + "1.0.0"
  + "\x00" + canonical_payload_bytes)`, shown as **bare 64-hex**.
- **Contract identity** = `SHA-256("derivatrace.canonical.contract" + "\x00"
  + "1.0.0" + "\x00" + canonical_document_bytes)`, shown as
  `canonical:sha256:<hex>`.
- **Payoff-node identity** = `SHA-256("derivatrace.payoffgraph.node" + "\x00"
  + "1.0.0" + "\x00" + canonical_pg_payload_bytes)`, **bare 64-hex**.
- **Payoff-graph identity** = `SHA-256("derivatrace.payoffgraph.graph" + "\x00"
  + "1.0.0" + "\x00" + canonical_structural_document_bytes)` (the structural
  projection **excluding** `provenance`), shown as `payoffgraph:sha256:<hex>`.
- All inputs use observables
  `ObservableId(field="close", identifier=AAA|BBB|XXX, namespace="equity")`
  with `ObservationTime = 2030-01-01T00:00:00.000000Z` and `Unit = money(USD)`.
  Every `Payment` amount is a money-denominated `Number` (`Unit.money(Currency("USD"))`)
  matching `Payment.currency`, as required by the public Stage 1A API
  (`Payment` rejects a scalar-denominated amount). A **scalar** `Number`
  (`Unit.scalar()`) appears only where it is structurally dimensionless: the
  `Scale` factor and the `Multiply`/`Add`/`Subtract`/`Maximum`/`Minimum` operand
  paired with a money observable (e.g. CV-005, CV-008). `Payment` settlement
  time is `2030-01-01T00:00:00.000000Z` unless stated. Let `T0` denote
  `2030-01-01T00:00:00.000000Z`. Two **scalar** observables `scalar_A` and
  `scalar_B` are defined as
  `Observable(ObservableId(field="level", identifier="SCALARA"|"SCALARB",
  namespace="macro"), ObservationTime=T0, Unit=scalar())` and are used wherever a
  dimensionless observable is required (for example the `PGDivide` scalar-division
  vector).

## 2. Normative vectors

### CV-001 — `Number` spelling equivalence (`1` ≡ `1.0` ≡ `1.00`)

- **Input:** `Payment(amount=Number("1", Unit.money(USD)), currency=USD, T0)`, `Payment(amount=Number("1.0", …), …)`, `Payment(amount=Number("1.00", …), …)`.
- **Applied rules:** `decimal:normalize`, `value:coerce`.
- **Forbidden rules:** `fold`, `dedup`.
- **Normalized Number payload** (identical for all three):
  `{"type":"Number","unit":{"currency":"USD","kind":"money"},"value":{"digits":"1","exponent":0,"sign":0}}`
- **Number node identity (bare 64-hex):** `b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67`
- **Payment node identity (bare 64-hex):** `245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a`
- **Complete canonical JSON bytes** (identical for all three):
  `{"nodes":{"245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a":{"id":"245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a","payload":{"amount":"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}},"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67":{"id":"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67","payload":{"type":"Number","unit":{"currency":"USD","kind":"money"},"value":{"digits":"1","exponent":0,"sign":0}}}},"root":"245f56804c0f4df293c96845228b11540e7f06a606c73188115c754b13e0aa5a","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `723`
- **Canonical contract identity (all three identical):** `canonical:sha256:64a97aca38a8de396b059465d696ba6e8d84c8a6c7c5c2e7e687ab1b4724b4a5`
- **Expected structural equivalence:** the three contracts are **canonically identical** (spelling-independent value normalization).

### CV-002 — Canonical zero

- **Input:** `Payment(amount=Number("0", Unit.money(USD)), currency=USD, T0)`.
- **Applied rules:** `decimal:zero` (forced `{"digits":"0","exponent":0,"sign":0}`).
- **Forbidden rules:** negative-zero passthrough.
- **Normalized Number payload:** `{"type":"Number","unit":{"currency":"USD","kind":"money"},"value":{"digits":"0","exponent":0,"sign":0}}`
- **Zero Number node identity (bare 64-hex):** `53c1bb4970008789392a86f3278eb9031e1c106dff5504c8b461211f6ea3c29e`
- **Payment node identity (bare 64-hex):** `92e9d00e664604b0454cebd3d49ccff0c58f6f5f8d5bbf40c8a4523aea267350`
- **Complete canonical JSON bytes:** `{"nodes":{"53c1bb4970008789392a86f3278eb9031e1c106dff5504c8b461211f6ea3c29e":{"id":"53c1bb4970008789392a86f3278eb9031e1c106dff5504c8b461211f6ea3c29e","payload":{"type":"Number","unit":{"currency":"USD","kind":"money"},"value":{"digits":"0","exponent":0,"sign":0}}},"92e9d00e664604b0454cebd3d49ccff0c58f6f5f8d5bbf40c8a4523aea267350":{"id":"92e9d00e664604b0454cebd3d49ccff0c58f6f5f8d5bbf40c8a4523aea267350","payload":{"amount":"53c1bb4970008789392a86f3278eb9031e1c106dff5504c8b461211f6ea3c29e","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}}},"root":"92e9d00e664604b0454cebd3d49ccff0c58f6f5f8d5bbf40c8a4523aea267350","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `723`
- **Canonical contract identity:** `canonical:sha256:7d028d937117e85e0b8e55e9cd9193fa72767182735fe61bab917e87ea737721`
- **Expected structural equivalence:** distinct from every non-zero-amount contract.

### CV-003 — `Add` operand reordering is not identity-significant

- **Input:** `Payment(amount=Add(obs_A, obs_B), …)` vs `Payment(amount=Add(obs_B, obs_A), …)`.
- **Applied rules:** `commute:Add` (operands sorted by canonical node id, tie-broken by canonical payload bytes).
- **Forbidden rules:** `flatten:Add` (no nesting here), `dedup`, `reorder:Both`.
- **Normalized Add payload** (identical for both inputs): `{"operands":["2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9"],"type":"Add"}`
- **Add node identity (bare 64-hex):** `ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1`
- **Complete canonical JSON bytes** (identical for both inputs): `{"nodes":{"0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6":{"id":"0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6","payload":{"amount":"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}},"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb":{"id":"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","payload":{"observable_id":{"field":"close","identifier":"BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9":{"id":"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","payload":{"observable_id":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1":{"id":"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1","payload":{"operands":["2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9"],"type":"Add"}}},"root":"0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `1455`
- **Canonical contract identity (both inputs identical):** `canonical:sha256:259ab84dcede671196db17812e1efd629dd287c0d57f77d054e876568d6eb1ce`
- **Expected structural equivalence:** the two inputs are **canonically identical**.

### CV-004 — Nested `Add` associative flattening

- **Input:** `Payment(amount=Add(obs_A, Add(obs_B, obs_X)), …)`.
- **Applied rules:** `commute:Add`, `flatten:Add` (nested `Add` merged), `decimal:normalize`.
- **Forbidden rules:** `dedup`, `reorder:Both`.
- **Normalized (flattened) Add payload:** `{"operands":["2245a0746c4c11dfc358496557045f16eac26ba666247dd3cfd5b94099954f52","2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9"],"type":"Add"}`
- **Flattened Add node identity (bare 64-hex):** `92b23cdc56b0486005e5c3df9a2345a31dd10bc5a888a586af0ebbd3fd791a39`
- **Complete canonical JSON bytes:** `{"nodes":{"2245a0746c4c11dfc358496557045f16eac26ba666247dd3cfd5b94099954f52":{"id":"2245a0746c4c11dfc358496557045f16eac26ba666247dd3cfd5b94099954f52","payload":{"observable_id":{"field":"close","identifier":"XXX","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb":{"id":"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","payload":{"observable_id":{"field":"close","identifier":"BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"4e79af6151636208232491451ec1c36b8243b06371998cbdbd14183ba964d002":{"id":"4e79af6151636208232491451ec1c36b8243b06371998cbdbd14183ba964d002","payload":{"amount":"92b23cdc56b0486005e5c3df9a2345a31dd10bc5a888a586af0ebbd3fd791a39","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}},"92b23cdc56b0486005e5c3df9a2345a31dd10bc5a888a586af0ebbd3fd791a39":{"id":"92b23cdc56b0486005e5c3df9a2345a31dd10bc5a888a586af0ebbd3fd791a39","payload":{"operands":["2245a0746c4c11dfc358496557045f16eac26ba666247dd3cfd5b94099954f52","2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9"],"type":"Add"}},"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9":{"id":"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","payload":{"observable_id":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}}},"root":"4e79af6151636208232491451ec1c36b8243b06371998cbdbd14183ba964d002","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `1824`
- **Canonical contract identity:** `canonical:sha256:69c59d89f9a932a8a4e3bdfe14f19c265bc9fe547aeb52e3a528252d6966b953`
- **Expected structural equivalence:** the nested `Add` is flattened into a single n-ary `Add`; the inner `Add` node is not present in the canonical document; distinct from the un-flattened author form.

### CV-005 — Binary `Multiply` reorders but is NOT flattened

- **Input:** `Payment(amount=Multiply(obs_money, Number("2")), …)` vs `Payment(amount=Multiply(Number("2"), obs_money), …)`.
  (`Number("2")` is a dimensionless scalar; `obs_money` is `money(USD)`.)
- **Applied rules:** `commute:Multiply` (two operands ordered by canonical node id, tie-broken by payload bytes).
- **Forbidden rules:** `flatten:Multiply` (always binary).
- **Normalized Multiply payload** (identical for both inputs): `{"left":"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175","right":"c3649b98d29cf3a2b621b42f9da022892fccb53581ee97d7976502c07a44e32a","type":"Multiply"}`
- **Multiply node identity (bare 64-hex):** `07d3f45119060554989abc13645921ccfac1fe9ff4d4a72cbdae9a2f9c3949c2`
- **Complete canonical JSON bytes** (identical for both inputs): `{"nodes":{"07d3f45119060554989abc13645921ccfac1fe9ff4d4a72cbdae9a2f9c3949c2":{"id":"07d3f45119060554989abc13645921ccfac1fe9ff4d4a72cbdae9a2f9c3949c2","payload":{"left":"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175","right":"c3649b98d29cf3a2b621b42f9da022892fccb53581ee97d7976502c07a44e32a","type":"Multiply"}},"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175":{"id":"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175","payload":{"type":"Number","unit":{"kind":"scalar"},"value":{"digits":"2","exponent":0,"sign":0}}},"c3649b98d29cf3a2b621b42f9da022892fccb53581ee97d7976502c07a44e32a":{"id":"c3649b98d29cf3a2b621b42f9da022892fccb53581ee97d7976502c07a44e32a","payload":{"observable_id":{"field":"fx","identifier":"USDJPY","namespace":"macro"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"f5398dec03b9f70be48278aa2694e541c5cf15b2adce25c2279a265110784f58":{"id":"f5398dec03b9f70be48278aa2694e541c5cf15b2adce25c2279a265110784f58","payload":{"amount":"07d3f45119060554989abc13645921ccfac1fe9ff4d4a72cbdae9a2f9c3949c2","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}}},"root":"f5398dec03b9f70be48278aa2694e541c5cf15b2adce25c2279a265110784f58","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `1363`
- **Canonical contract identity (both inputs identical):** `canonical:sha256:dce9a43b3d8687b8f7ba9e770096a5d1ce04e0365fa1a1d83a04f7f2d8e95168`
- **Expected structural equivalence:** the two inputs are **canonically identical**; `Multiply` stays binary.

### CV-006 — `Both` order is preserved (NOT commutative)

- **Input:** `Both(Payment(obs_A), Payment(obs_B))` vs `Both(Payment(obs_B), Payment(obs_A))`.
- **Applied rules:** none (author order preserved).
- **Forbidden rules:** `reorder:Both`, `flatten:Both`.
- **`Both` payload A:** `{"operands":["6817593e93fc408ea51bc6b8f4d8c662c7430fe4367b4a74b33fbce93fae27c1","9791820c5de55950b386b57c141c53ab13e0814dd6ab5799b7010c37c543c40f"],"type":"Both"}`
- **`Both` payload B:** `{"operands":["9791820c5de55950b386b57c141c53ab13e0814dd6ab5799b7010c37c543c40f","6817593e93fc408ea51bc6b8f4d8c662c7430fe4367b4a74b33fbce93fae27c1"],"type":"Both"}`
- **`Both` node identities (bare 64-hex):** A = `fd6c6563c26d11896882c44693cc48cdb3513c78872f2b73e1d46ed8f77ad884`; B = `9db00c117e19bd4884cbddacb0e7b64610cc6d615e551b106c88d8279b53146e`
- **Canonical contract identity A:** `canonical:sha256:1500030155fd355074278431d58d7b8aabbab87a4b5e3c10ab2ff1a5acc05440`
- **Canonical contract identity B:** `canonical:sha256:0ad1293ffc073b92664b0b300a4c277a2f3dc6608ee8a7ed7aa1fbd5910038ee`
- **UTF-8 byte length:** `1767` (both).
- **Expected structural equivalence:** the two contracts are **NOT canonically equal** (distinct identities) — author order is load-bearing.

### CV-007 — Duplicate operands preserved

- **Input:** `Payment(amount=Add(obs_A, obs_A), …)`.
- **Applied rules:** `commute:Add`.
- **Forbidden rules:** `dedup`.
- **Normalized Add payload:** `{"operands":["f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9"],"type":"Add"}`
- **Add node identity (bare 64-hex):** `8b2968aedc6a0975a6c57a18db21bf85fa71288690f64d8299602c7b3f095ce0`
- **Complete canonical JSON bytes:** `{"nodes":{"8b2968aedc6a0975a6c57a18db21bf85fa71288690f64d8299602c7b3f095ce0":{"id":"8b2968aedc6a0975a6c57a18db21bf85fa71288690f64d8299602c7b3f095ce0","payload":{"operands":["f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9"],"type":"Add"}},"deb86822240312e15e6b894581da1a55efb8f44ca7ae554a2788a6d1f606b8ad":{"id":"deb86822240312e15e6b894581da1a55efb8f44ca7ae554a2788a6d1f606b8ad","payload":{"amount":"8b2968aedc6a0975a6c57a18db21bf85fa71288690f64d8299602c7b3f095ce0","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}},"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9":{"id":"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","payload":{"observable_id":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}}},"root":"deb86822240312e15e6b894581da1a55efb8f44ca7ae554a2788a6d1f606b8ad","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `1118`
- **Canonical contract identity:** `canonical:sha256:6ab629fde98d8f84d9d6c749539acc02c5849f63b06b60a52e3cbeafdaefc5cd`
- **Expected structural equivalence:** the duplicate `obs_A` appears **twice**; no dedup.

### CV-008 — Shared subtree vs separately allocated equal subtree

- **Input:** `Both(Scale(Number("2"), shared), Payment(shared))` vs `Both(Scale(Number("2"), copy), Payment(copy))`, where `shared = copy = Add(obs_A, obs_B)`.
- **Applied rules:** `dag:share` (content-addressed, independent of Python object identity).
- **Forbidden rules:** `reorder:Both`.
- **Complete canonical JSON bytes (shared):** `{"nodes":{"0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6":{"id":"0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6","payload":{"amount":"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}},"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175":{"id":"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175","payload":{"type":"Number","unit":{"kind":"scalar"},"value":{"digits":"2","exponent":0,"sign":0}}},"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb":{"id":"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","payload":{"observable_id":{"field":"close","identifier":"BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"990b861ef78c58d8bc50258184084d4cafd85e9504cbbfad1b448a1721149a46":{"id":"990b861ef78c58d8bc50258184084d4cafd85e9504cbbfad1b448a1721149a46","payload":{"operands":["ffcf7fc0e2b7acdca5cebd35fd90461501e12ed44748684da2bd2115a893ae65","0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6"],"type":"Both"}},"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9":{"id":"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","payload":{"observable_id":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1":{"id":"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1","payload":{"operands":["2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9"],"type":"Add"}},"ffcf7fc0e2b7acdca5cebd35fd90461501e12ed44748684da2bd2115a893ae65":{"id":"ffcf7fc0e2b7acdca5cebd35fd90461501e12ed44748684da2bd2115a893ae65","payload":{"contract":"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1","factor":"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175","type":"Scale"}}},"root":"990b861ef78c58d8bc50258184084d4cafd85e9504cbbfad1b448a1721149a46","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **Complete canonical JSON bytes (copy):** `{"nodes":{"0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6":{"id":"0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6","payload":{"amount":"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"Payment"}},"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175":{"id":"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175","payload":{"type":"Number","unit":{"kind":"scalar"},"value":{"digits":"2","exponent":0,"sign":0}}},"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb":{"id":"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","payload":{"observable_id":{"field":"close","identifier":"BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"990b861ef78c58d8bc50258184084d4cafd85e9504cbbfad1b448a1721149a46":{"id":"990b861ef78c58d8bc50258184084d4cafd85e9504cbbfad1b448a1721149a46","payload":{"operands":["ffcf7fc0e2b7acdca5cebd35fd90461501e12ed44748684da2bd2115a893ae65","0a9ceb076d2c84082d7ce42d44d651b582332a641b1de84804d6ab0effdb32d6"],"type":"Both"}},"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9":{"id":"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","payload":{"observable_id":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"Observable","unit":{"currency":"USD","kind":"money"}}},"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1":{"id":"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1","payload":{"operands":["2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9"],"type":"Add"}},"ffcf7fc0e2b7acdca5cebd35fd90461501e12ed44748684da2bd2115a893ae65":{"id":"ffcf7fc0e2b7acdca5cebd35fd90461501e12ed44748684da2bd2115a893ae65","payload":{"contract":"ff90f90d58c9197c0f65f11af7938c0571e03d9716bbbd7f623483b7f2e4c6f1","factor":"1edd078414ef94965fc293a5ddf0bc8a23d03fb7d4386210a1ff432e82587175","type":"Scale"}}},"root":"990b861ef78c58d8bc50258184084d4cafd85e9504cbbfad1b448a1721149a46","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `2330` (both).
- **Canonical contract identity (shared):** `canonical:sha256:e969a37667f2abb6a9aa81a6e00b0b167356a4ab139c570987af1e071440bfc1`
- **Canonical contract identity (copy):** `canonical:sha256:e969a37667f2abb6a9aa81a6e00b0b167356a4ab139c570987af1e071440bfc1`
- **Expected structural equivalence:** the two contracts are **canonically identical** — object identity is irrelevant.

### CV-009 — Non-commutative `Subtract` order

- **Input:** `Payment(amount=Subtract(obs_A, obs_B), …)` vs `Payment(amount=Subtract(obs_B, obs_A), …)`.
- **Applied rules:** none (author order preserved).
- **Forbidden rules:** `reorder:Subtract`, `flatten:Subtract`.
- **`Subtract` payload A:** `{"minuend":"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","subtrahend":"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","type":"Subtract"}`
- **`Subtract` payload B:** `{"minuend":"2983da37e2913b8f1a1fb097515abe28f131a67ac5269f94832de86f5c2235cb","subtrahend":"f0fa23010057002c04012039fbf91a42b241b9735abacbd80923be57fedc0bf9","type":"Subtract"}`
- **Canonical contract identity A:** `canonical:sha256:4980e10a017bb25d868029799bb73c5db859574f10c6264441779efd27c3349e`
- **Canonical contract identity B:** `canonical:sha256:7dc44bf7d9dd626adba790436a9cdbe305668bb28908b73301271778dc82bfbc`
- **UTF-8 byte length:** `1470` (both).
- **Expected structural equivalence:** the two contracts are **NOT canonically equal** (distinct identities).

### CV-010 — Timestamp UTC microsecond encoding

- **Input:** `Payment(amount=Number("1", Unit.money(USD)), currency=USD, settlement_time="2030-01-01T00:00:00.500000Z")`.
- **Applied rules:** `encode:timestamp-utc` (full microsecond precision).
- **Forbidden rules:** `truncate:timestamp`.
- **Number node identity (bare 64-hex):** `b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67`
- **Payment node identity (bare 64-hex):** `c336c691466be366a62cb3c257c243db741cff51647b745e86c206c3c2902777`
- **Complete canonical JSON bytes:** `{"nodes":{"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67":{"id":"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67","payload":{"type":"Number","unit":{"currency":"USD","kind":"money"},"value":{"digits":"1","exponent":0,"sign":0}}},"c336c691466be366a62cb3c257c243db741cff51647b745e86c206c3c2902777":{"id":"c336c691466be366a62cb3c257c243db741cff51647b745e86c206c3c2902777","payload":{"amount":"b97b700909b7daae2acd283df96645f4be6b4765995801a23897749a20e69a67","currency":"USD","settlement_time":"2030-01-01T00:00:00.500000Z","type":"Payment"}}},"root":"c336c691466be366a62cb3c257c243db741cff51647b745e86c206c3c2902777","schema_name":"derivatrace.contract.canonical","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `723`
- **Canonical contract identity:** `canonical:sha256:0271e7069e4b0ca82dcea2533c7737e15780b204762ddb7b1f90e99f0837d9b2`
- **Expected structural equivalence:** distinct from CV-001 (which used `...000000Z`) — microsecond precision participates in identity.

### CV-011 — Payoff-graph compilation (regenerated under the corrected schema)

- **Source contract:** `Payment(amount=Add(obs_A, obs_B), currency=USD, T0)` (canonical contract identity `canonical:sha256:259ab84dcede671196db17812e1efd629dd287c0d57f77d054e876568d6eb1ce`, identical to CV-003).
- **Applied rules (corrected):** `compile:payoff`, `commute:PGAdd`, `flatten:PGAdd`, `payment:amount` (field named `amount`, not `payoff_leaf`), `observable:no_settlement_time`, `payment:owns_settlement_time`.
- **Forbidden rules:** `payoff_leaf` field; `settlement_time` inside `PGObservable`/`PGConstant`; lowering `Subtract` to `PGAdd`+`PGNegate` (n/a here); reciprocal rewrite of `Divide` (n/a here); implementation-finalized mapping.
- **Expected structure:** two `PGObservable` nodes (no `settlement_time`), one `PGAdd` node, one `PGPayment` node using `amount`, with `settlement_time` present only in `PGPayment`.
- **`PGObservable` (obs_A / AAA) node identity (bare 64-hex):** `e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63`
- **`PGObservable` (obs_B / BBB) node identity (bare 64-hex):** `ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f4502e8f521fd0b5`
- **`PGAdd` node identity (bare 64-hex):** `2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b`
- **Root `PGPayment` node identity (bare 64-hex):** `5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c`
- **Complete payoff-graph structural bytes** (provenance **excluded**; this is the identity preimage): `{"nodes":{"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b":{"id":"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b","payload":{"operands":["ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f4502e8f521fd0b5","e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63"],"type":"PGAdd"}},"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c":{"id":"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c","payload":{"amount":"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"PGPayment"}},"ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f4502e8f521fd0b5":{"id":"ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f4502e8f521fd0b5","payload":{"observable_id":{"field":"close","identifier":"BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"PGObservable","unit":{"currency":"USD","kind":"money"}}},"e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63":{"id":"e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63","payload":{"observable_id":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"PGObservable","unit":{"currency":"USD","kind":"money"}}}},"root":"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c","schema_name":"derivatrace.payoffgraph","schema_version":"1.0.0"}`
- **Structural UTF-8 byte length:** `1456`
- **Complete payoff-graph document bytes** (provenance **included**): `{"nodes":{"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b":{"id":"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b","payload":{"operands":["ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f4502e8f521fd0b5","e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63"],"type":"PGAdd"}},"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c":{"id":"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c","payload":{"amount":"2f96aed4cfc2c7c6ab7923a3f57d6ce600367f168ae75997b084390175d0cf8b","currency":"USD","settlement_time":"2030-01-01T00:00:00.000000Z","type":"PGPayment"}},"ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f4502e8f521fd0b5":{"id":"ccb83e94063e4aca86182b91aee32dfd4b6a8c3d3f954b62f4502e8f521fd0b5","payload":{"observable_id":{"field":"close","identifier":"BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"PGObservable","unit":{"currency":"USD","kind":"money"}}},"e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63":{"id":"e173bb55806349d78a2bb783ea8a9df4ec1f4604f92b5ad2f2496a485dc6bc63","payload":{"observable_id":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","type":"PGObservable","unit":{"currency":"USD","kind":"money"}}}},"provenance":{"compiler":"derivatrace.payoffgraph.compiler/1.0.0","source_contract_identity":"canonical:sha256:259ab84dcede671196db17812e1efd629dd287c0d57f77d054e876568d6eb1ce"},"root":"5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c","schema_name":"derivatrace.payoffgraph","schema_version":"1.0.0"}`
- **Document UTF-8 byte length:** `1634`
- **Payoff-graph identity (over structural bytes; provenance excluded):** `payoffgraph:sha256:59fbb00dbb585755a799cd7e387e4ee51fd9b77ed3cc032758a825f2f8836e1a`
- **Payoff-graph identity if provenance were included (must differ, cross-check):** `payoffgraph:sha256:e256cbbf291ba3135213c2eea700b46e0658ddcff853f187cd654cbeb474e5b0`
- **Expected structural equivalence:** the compiled graph is deterministic and model-independent; recompiling the same contract yields the same graph identity. Provenance is excluded from the identity preimage, so changing the `compiler` tag or `source_contract_identity` would not change the graph identity (it only changes `document_bytes`).

### Stage 1B-R2 runtime conformance vectors

These vectors are **executed by the Stage 1B-R2 payoff-graph runtime**
(`derivatrace.payoffgraph.compile_payoff_graph`) and are directly **constructible
and valid through the public Stage 1A API** (`validate_contract` succeeds on every
source contract). Every `expected_payoff_graph_identity` below is a **real,
computed** SHA-256 value, cross-checked for the properties the spec requires
(reorder invariance, flattening, duplicate preservation, distinctness under
author-order change, content-addressed sharing, timestamp precision, and a
deterministic compilation). No vector contains a placeholder, `TBD`,
`example-hash`, or all-zero identity. All sources below use `currency=USD`,
`settlement_time=T0`, and the observables defined in §1.

- **PGConstant under PGPayment** — source
  `Payment(Number(ExactNumber("100"), Unit.money(USD)), USD, T0)`. Expect a
  `PGConstant` (no `settlement_time`) referenced by `PGPayment.amount`; graph
  distinct from any `PGObservable`-backed payment.
  **Payoff-graph identity:** `payoffgraph:sha256:858624784eed60272f1c73fb5b52d2547eec326dc2bd2862a3db3a42ecc07922`.
- **PGAdd commutation** — sources
  `Payment(Add((obs_A, obs_B)), USD, T0)` versus
  `Payment(Add((obs_B, obs_A)), USD, T0)`. Expect identical `PGAdd` operand array
  (sorted by id) and identical graph identity (commutative multiset). The identity
  equals CV-011.
  **Payoff-graph identity (both):** `payoffgraph:sha256:59fbb00dbb585755a799cd7e387e4ee51fd9b77ed3cc032758a825f2f8836e1a`.
- **PGSubtract order sensitivity** — sources
  `Payment(Subtract(obs_A, obs_B), USD, T0)` versus
  `Payment(Subtract(obs_B, obs_A), USD, T0)`. Expect distinct `PGSubtract`
  (`minuend`/`subtrahend` swapped) and **distinct** graph identities; **not**
  lowered to `PGAdd`+`PGNegate`.
  **Payoff-graph identities:** `payoffgraph:sha256:55ada2494e58231140c15e261b80ff294db26f88bb97e454576db82fe6d8c10a` (A−B) vs `payoffgraph:sha256:e0c7bba00c37d8305ee99a0ef0c5fa041ff3ab2164298a0e8584bcfbec1713f5` (B−A).
- **Nested PGAdd flattening** — compare
  `Payment(Add((obs_A, Add((obs_B, obs_X)))), USD, T0)` against
  `Payment(Add((obs_A, obs_B, obs_X)), USD, T0)`. Both sources canonicalize to the
  **identical** R1 canonical contract (associative flattening), so they compile to
  the **identical** payoff graph with exactly one reachable `PGAdd` and no inner
  `PGAdd`. Do not treat the nested-author form as a distinct graph.
  **Payoff-graph identity (both):** `payoffgraph:sha256:7e7690a487af6a85d03f0ffe3a310fb0747936f5b0ae4e6e61bd5b5443eafa69`.
- **Binary PGMultiply commutation without associativity** — use a dimensionless
  factor `Number(ExactNumber("2"), Unit.scalar())`. Within one grouping compare
  `Payment(Multiply(obs_A, Number(ExactNumber("2"), Unit.scalar())), USD, T0)`
  versus `Payment(Multiply(Number(ExactNumber("2"), Unit.scalar()), obs_A), USD,
  T0)`: expect identical binary `PGMultiply` (left/right reordered by id) and
  identical graph identity.
  **Payoff-graph identity (commuted pair):** `payoffgraph:sha256:189ad22220104a4f8f80f0e57d791365222dd435f395232857d2d09db605dae5`.
  Separately compare that grouping against a different valid binary grouping
  `Payment(Multiply(obs_A, Multiply(Number(ExactNumber("2"), Unit.scalar()),
  Number(ExactNumber("3"), Unit.scalar()))), USD, T0)` and its left-associated form
  `Payment(Multiply(Multiply(obs_A, Number(ExactNumber("2"), Unit.scalar())),
  Number(ExactNumber("3"), Unit.scalar())), USD, T0)`: the two distinct groupings
  remain **distinct** graph identities; `Multiply(Multiply(a,b),c)` must **not**
  flatten into a ternary node.
  **Payoff-graph identities:** `payoffgraph:sha256:7f2f3af0b53308827d1429f650c7997c043e39d3558f81005b5a71525bb71657` (right-associated) vs `payoffgraph:sha256:73c5bf6236ebf88f9cce9318d9f1624cb18beb9f72e2e90e53fe9fe1f4bb7563` (left-associated).
- **PGDivide order sensitivity** — use two distinct scalar observables
  `scalar_A` and `scalar_B`. Compare
  `Scale(Divide(scalar_A, scalar_B), Payment(obs_A, USD, T0))` versus
  `Scale(Divide(scalar_B, scalar_A), Payment(obs_A, USD, T0))`. Both sources
  validate (scalar ÷ scalar is dimensionless; the factor drives `Scale`). Expect
  distinct `PGDivide` (`numerator`/`denominator` swapped) and distinct graph
  identities; **no** reciprocal rewrite. (A money observable must **not** divide a
  money observable.)
  **Payoff-graph identities:** `payoffgraph:sha256:3859b48afb878ec09a881b8de7c13b19dcdfcb320ad39a2707119566038defac` (A÷B) vs `payoffgraph:sha256:b603b81912c92224c22fb66a9a101bdc9aeedce4370f9cb395d21f0ef011242a` (B÷A).
- **PGCombine author-order sensitivity** — sources
  `Both((Payment(obs_A, USD, T0), Payment(obs_B, USD, T0)))` versus
  `Both((Payment(obs_B, USD, T0), Payment(obs_A, USD, T0)))`. Expect distinct
  `PGCombine` operand order and distinct graph identities (author order
  preserved, not commutative).
  **Payoff-graph identities:** `payoffgraph:sha256:ea878884b83fea0dafbd1703e863cf356d59eaeaff410d50836a2d69d4535314` (A,B) vs `payoffgraph:sha256:ee2dfa4a1b99cc3f11be777668c120b593ec2464247e0320e7934270276fea05` (B,A).
- **Duplicate operand preservation (Add)** — compare
  `Payment(Add((obs_A, obs_A)), USD, T0)` against `Payment(obs_A, USD, T0)`. Expect
  `PGAdd.operands == [id_A, id_A]`; the duplicated graph is **distinct** from the
  single-observable payment (which has no `Add` wrapper).
  **Payoff-graph identities:** `payoffgraph:sha256:ac7653325470e272d3c32d96c027e3d4e93840f529b8be7e73b9376738b48742` (duplicate Add) vs `payoffgraph:sha256:07a5cf79d4942881810c8fce6158c27a623b1cf420819b7d1215f7c47c5cbaa2` (single observable).
- **Duplicate Multiply operand (shared scalar factor)** — source
  `Scale(Multiply(shared, shared), Payment(obs_A, USD, T0))` where
  `shared = Observable(ObservableId(field="level", identifier="SCALARA",
  namespace="macro"), ObservationTime=T0, Unit=scalar())`. Both `Multiply` operands
  reference the **same** scalar node, so `PGMultiply.left == PGMultiply.right` and
  the duplicate reference appears twice in the operand graph; the compiled graph is
  **distinct** from any non-duplicated Multiply grouping above.
  **Payoff-graph identity:** `payoffgraph:sha256:0025c2a2ed75cf9a442298ae2e78bfd6df0c8b5e19aacc47a53b2ee268c877db`.
- **Duplicate operand preservation (PGCombine)** — source
  `Both((shared, shared))` where `shared = Payment(obs_A, USD, T0)`. Expect
  `PGCombine.operands == [id_A, id_A]`; the duplicated graph is **distinct** from the
  single-observable payment.
  **Payoff-graph identity:** `payoffgraph:sha256:48ad96391a4202b61b5bf13a16e1cf2690266b0ee9566f655505fe241297df3d`.
- **Shared versus copied subgraphs** — use a **Contract** subtree (not an `Add`
  expression) as `Scale.contract`. Shared version: construct one
  `shared = Payment(Add((obs_A, obs_B)), USD, T0)` and reference that same object
  directly and inside `Scale`:
  `Both((shared, Scale(Number(ExactNumber("2"), Unit.scalar()), shared)))`. Copied
  version: construct two independently allocated but structurally identical
  subtrees `pay1 = Payment(Add((obs_A, obs_B)), USD, T0)` and
  `pay2 = Payment(Add((obs_A, obs_B)), USD, T0)`, then
  `Both((pay1, Scale(Number(ExactNumber("2"), Unit.scalar()), pay2)))`. Both
  complete contracts validate and produce identical canonical/payoff identities
  (content-addressed sharing, independent of Python object identity). The resulting
  graph is distinct from the duplicate PGCombine vector
  (`48ad96391a4202b61b5bf13a16e1cf2690266b0ee9566f655505fe241297df3d`) because it
  carries a `Scale` over the shared payment in addition to the shared payment itself.
  **Payoff-graph identity (both):** `payoffgraph:sha256:b5c987269d9b16f5605c4d49621aef2d93e4a65c0b083718e5e3d27e027cb04c`.
- **PGAllOf / PGAnyOf flattening** — provide separate nested-versus-flat pairs
  using non-literal `Comparison` conditions. For `AllOf` compare
  `Payment(ConditionalValue(AllOf((Comparison(obs_A, obs_B, GREATER_THAN),
  AllOf((Comparison(obs_B, obs_X, GREATER_THAN), Comparison(obs_A, obs_X,
  GREATER_THAN)))), obs_A, obs_B), USD, T0)` against
  `Payment(ConditionalValue(AllOf((Comparison(obs_A, obs_B, GREATER_THAN),
  Comparison(obs_B, obs_X, GREATER_THAN), Comparison(obs_A, obs_X,
  GREATER_THAN))), obs_A, obs_B), USD, T0)`. Both canonicalize to the identical R1
  contract (nested `AllOf` flattened) and compile to the identical payoff graph
  with a single `PGAllOf` and no inner `PGAllOf`.
  **Payoff-graph identity (AllOf both):** `payoffgraph:sha256:d2ecc0ce66d3bf79f741e4e5fd1593f3049ed75fa8eb5ea4ed444ce1c80c8e26`.
  The `AnyOf` pair uses the same structure with `AnyOf` and expects the same
  identical-graph relationship.
  **Payoff-graph identity (AnyOf both):** `payoffgraph:sha256:bfb09528718bbf825d4f34229d1591875e6d2ba3e17ddb7d7abba0916eeb6aba`.
- **PGConditionalValue** — source
  `Payment(ConditionalValue(Comparison(obs_A, obs_B, GREATER_THAN), obs_A,
  obs_B), USD, T0)`. Expect `PGConditionalValue` with `condition` (a `PGComparison`)
  /`true_payoff`/`false_payoff` author order preserved.
  **Payoff-graph identity:** `payoffgraph:sha256:719e567c5b7023469b5035156d1af63c0f8c70b6e4e911dc9849df01af786666`.
- **PGConditionalContract** — source
  `ConditionalContract(Comparison(obs_A, obs_B, GREATER_THAN),
  Payment(obs_A, USD, T0), Payment(obs_B, USD, T0))`. Expect
  `PGConditionalContract` with author order preserved; graph distinct from the
  swapped-branch contract.
  **Payoff-graph identity:** `payoffgraph:sha256:155177c729b3dd1673fc34d1521985bf187b2395b2300eab7cbd96c63075fa4d`.
- **Zero to empty PGCombine** — `Both((Zero(), Zero()))` (or a `Zero()` alone
  compiled to a payoff root). Each `Zero` compiles to a `PGCombine` with an empty
  `operands` array; node ids equal across distinct `Zero` sources
  (content-addressed).
  **Payoff-graph identity:** `payoffgraph:sha256:6cf223e52d6f1f016dd920568e48dcf9fd3576d374b1a073f46b768f6cdc9f67`.
- **Deterministic recompilation** — compiling the same source contract (e.g. CV-011)
  twice yields byte-identical `structural_bytes` and the same graph identity
  (`payoffgraph:sha256:59fbb00dbb585755a799cd7e387e4ee51fd9b77ed3cc032758a825f2f8836e1a`). Confirmed by `tests/payoffgraph/test_compiler.py`.
- **Provenance exclusion from identity** — this is an **internal serialization /
  identity test seam**, not a public API feature. The public `compile_payoff_graph`
  does **not** accept caller-supplied `compiler` or `source` provenance overrides.
  The test holds `structural_bytes` fixed, varies `provenance` only while
  constructing the full document, observes that `document_bytes` changes, and
  confirms the graph identity (which hashes `structural_bytes` only) remains
  unchanged. CV-011 demonstrates this explicitly via its two identity values
  above. Confirmed by `tests/payoffgraph/test_compiler.py`.
- **Timestamp microsecond precision** — sources
  `Payment(Number(ExactNumber("1"), Unit.money(USD)), USD,
  SettlementTime=2030-01-01T00:00:00.000000Z)` versus
  `Payment(Number(ExactNumber("1"), Unit.money(USD)), USD,
  SettlementTime=2030-01-01T00:00:00.500000Z)`. Expect `PGPayment.settlement_time`
  to carry full microsecond precision and participate in the graph identity;
  distinct from the `...000000Z` variant.
  **Payoff-graph identities:** `payoffgraph:sha256:d4e7c6f6d6e90b87c13155a71c54be3c872c04165eac9a7732fb345954e88719` (…000000Z) vs `payoffgraph:sha256:698aa543f12b6ce911885c73f5cef35a1723d3be492d8b00c86a6d1865209e30` (…500000Z).
- **Collision seam** — a constructed case where two distinct payoff payloads hash
  to the same payoff-node id must raise `payoff_graph.collision` (never silently
  merged); mirrors the R1 collision seam but uses the dedicated payoff-graph
  code. Exercised by `tests/payoffgraph/test_compiler.py`.

These vectors are promoted to normative status: the suite records the concrete
graph identities above and guarantees the coverage obligations below.

## 3. Coverage obligations

The suite must guarantee:

- **Injectivity:** every pair of vectors with distinct `expected structural equivalence` yields distinct identities (no canonicalization or payoff-graph collision).
- **Stability:** re-running compilation on the same input yields identical bytes and identity.
- **Forbidden-rule enforcement:** none of the `forbidden_rules` ever occurs.
- **Validation gate:** invalid / cyclic / oversized inputs are rejected before payoff output.
- **Schema participation:** changing the `payoff_graph` `schema_version` changes the identity.
- **Collision rule:** if the same payoff-node id maps to different payload bytes, `payoff_graph.collision` is raised. R1 canonicalization failures propagate to the caller according to the payoff-graph specification (§11) without silent reclassification, and are never remapped onto `payoff_graph.collision`.

> The R1 canonical vectors (CV-001–CV-010) are executed by the Stage 1B-R1
> canonical runtime (`derivatrace.canonical`) in `tests/canonical/test_vectors.py`.
> CV-011 is a normative Stage 1B-R2 payoff-graph vector, executed by the
> Stage 1B-R2 runtime (`derivatrace.payoffgraph`) in
> `tests/payoffgraph/test_compiler.py`. The Stage 1B-R2 runtime vectors (§2) are
> executed by `derivatrace.payoffgraph` in `tests/payoffgraph/test_compiler.py`.
