# Canonical test vectors (Stage 1B-R1)

- **Status:** Implemented. Values below are **regenerated from the byte-exact
  Stage 1B-R1 canonical runtime** and are directly **constructible and valid
  through the public Stage 1A API** (`validate_contract` succeeds on every
  source contract).
- **Stage:** 1B (R1 canonical runtime).
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

> These vectors are **executed by the Stage 1B-R1 canonical runtime**. Every
> source contract is constructed through the public Stage 1A API and
> `validate_contract` succeeds; the canonical bytes, node identities, and
> contract identities are produced by the runtime and reproduced byte-for-byte in
> the accompanying test suite (`tests/canonical/test_vectors.py`). Payoff-graph
> compilation (CV-011) remains deferred to Stage 1B-R2, but the CV-011 source
> contract is constructed, validated, and canonicalized here, and its canonical
> contract identity must agree with R1.

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
  time is `2030-01-01T00:00:00.000000Z` unless stated.

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

### CV-011 — Payoff-graph compilation

- **Source contract:** `Payment(amount=Add(obs_A, obs_B), currency=USD, T0)` (canonical contract identity `canonical:sha256:259ab84dcede671196db17812e1efd629dd287c0d57f77d054e876568d6eb1ce`, identical to CV-003).
- **Applied rules:** `compile:payoff`, `commute:PGAdd`, `flatten:PGAdd`.
- **Forbidden rules:** `implementation-finalized` mapping; reciprocal rewrite of `Divide` (n/a here).
- **Root payoff-node identity (bare 64-hex):** `e42ac8884412f81618967fbd8d92abf59a07f0b6204b06b00114e1f40357c2a8`
- **Complete payoff-graph JSON bytes** (the `provenance` field is shown but is **excluded** from the graph identity preimage):
  `{"nodes":{"14a7077a77fc751fdea28fc8685de67dd691fa5f3057d1f1e276d233bfa0a8ae":{"id":"14a7077a77fc751fdea28fc8685de67dd691fa5f3057d1f1e276d233bfa0a8ae","payload":{"observable_id":{"field":"close","identifier":"AAA","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","settlement_time":null,"type":"PGObservable","unit":{"currency":"USD","kind":"money"}}},"8f0818b65f5b8cc970b348c3f7b00051cd3b3705833e9862527187ac455e78d5":{"id":"8f0818b65f5b8cc970b348c3f7b00051cd3b3705833e9862527187ac455e78d5","payload":{"observable_id":{"field":"close","identifier":"BBB","namespace":"equity"},"observation_time":"2030-01-01T00:00:00.000000Z","settlement_time":null,"type":"PGObservable","unit":{"currency":"USD","kind":"money"}}},"b8c284535d888887c1c7fde19c44a4f5e59a56f2251b50ec7e05fb7800c62bc2":{"id":"b8c284535d888887c1c7fde19c44a4f5e59a56f2251b50ec7e05fb7800c62bc2","payload":{"operands":["8f0818b65f5b8cc970b348c3f7b00051cd3b3705833e9862527187ac455e78d5","14a7077a77fc751fdea28fc8685de67dd691fa5f3057d1f1e276d233bfa0a8ae"],"type":"PGAdd"}},"e42ac8884412f81618967fbd8d92abf59a07f0b6204b06b00114e1f40357c2a8":{"id":"e42ac8884412f81618967fbd8d92abf59a07f0b6204b06b00114e1f40357c2a8","payload":{"currency":"USD","payoff_leaf":"b8c284535d888887c1c7fde19c44a4f5e59a56f2251b50ec7e05fb7800c62bc2","settlement_time":"2030-01-01T00:00:00.000000Z","type":"PGPayment"}}},"provenance":{"compiler":"derivatrace.stage1b.baseline","source_contract_identity":"canonical:sha256:259ab84dcede671196db17812e1efd629dd287c0d57f77d054e876568d6eb1ce"},"root":"e42ac8884412f81618967fbd8d92abf59a07f0b6204b06b00114e1f40357c2a8","schema_name":"derivatrace.payoffgraph","schema_version":"1.0.0"}`
- **UTF-8 byte length:** `1605`
- **Payoff-graph identity:** `payoffgraph:sha256:21e03bda08044ba0a7c4558cdaab10eb75d2e21f6b764dae39446f5df996096d`
- **Expected structural equivalence:** the compiled graph is deterministic and model-independent; recompiling the same contract yields the same graph identity.

## 3. Coverage obligations (at implementation time)

When Stage 1B is implemented, the suite must additionally guarantee:

- **Injectivity:** every pair of vectors with distinct `expected structural equivalence` yields distinct identities (no canonicalization collision).
- **Stability:** re-running canonicalization on the same input yields identical bytes and identity.
- **Forbidden-rule enforcement:** none of the `forbidden_rules` ever occurs.
- **Validation gate:** unvalidated / cyclic / oversized graphs are rejected before canonicalization.
- **Schema participation:** changing `schema_version` changes the identity.
- **Collision rule:** if the same id maps to different payload bytes, `canonicalization.collision` is raised.

> These vectors are design commitments for the Stage 1B baseline. They are not
> executed by the current package, which contains no canonicalization code.
