from __future__ import annotations

import importlib
import re
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from derivatrace.contracts import (
    Add,
    AllOf,
    AnyOf,
    Both,
    Comparison,
    ComparisonOperator,
    ConditionalContract,
    ConditionalValue,
    Contract,
    ContractError,
    Currency,
    Divide,
    ExactNumber,
    Multiply,
    Number,
    Observable,
    ObservableId,
    ObservationTime,
    Payment,
    ScalarExpression,
    Scale,
    SettlementTime,
    Subtract,
    Unit,
    Zero,
    validate_contract,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"

INLINE_LINK_RE = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REF_DEF_RE = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)
REF_USE_RE = re.compile(r"\!?\[[^\]]+\]\[([^\]]+)\]")
REF_USE_EMPTY_RE = re.compile(r"\!?\[([^\]]+)\]\[\]")

ABS_PATH_RE = re.compile(r"(/Users/|/home/|/Documents/|[A-Za-z]:[\\/](?!/))")

FORBIDDEN_CLAIMS = [
    "first ever",
    "first-of-its-kind",
    "formally verified",
    "formally proven",
    "mathematically proven",
    "proven correct",
]

PYPI_CLAIMS = [
    "available on pypi",
    "published on pypi",
    "install derivatrace",
    "pip install derivatrace",
    "on pypi",
    "pypi package",
    "released on pypi",
]

PRICING_CLAIMS = [
    "can price",
    "can value",
    "calculates prices",
    "calculates price",
    "prices derivatives",
    "values derivatives",
    "perform pricing",
    "performs pricing",
    "provides pricing",
    "derivatrace prices",
    "derivatrace values",
    "derivatrace calculates",
]

NEGATIONS = [
    "not ",
    "never ",
    "no ",
    "without ",
    "cannot",
    "can't",
    "don't",
    "do not",
    "isn't",
    "aren't",
    "won't",
    "does not",
    "doesn't",
]

SECRET_RES = [
    re.compile(r"AKIA[0-9A-Z]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"-----BEGIN CERTIFICATE-----"),
    re.compile(r"ghp_[A-Za-z0-9]{16,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[0-9]{10,}"),
    re.compile(
        r"(?:api[_]?key|secret[_]?key|client[_]?secret|password|passwd|access[_]?token)\s*[:=]"
    ),
]

CONFIG_FILES = [
    REPO_ROOT / "pyproject.toml",
    REPO_ROOT / ".github" / "workflows" / "ci.yml",
    REPO_ROOT / ".pre-commit-config.yaml",
]


def markdown_files() -> list[Path]:
    files: list[Path] = [REPO_ROOT / "README.md"]
    files.extend(sorted(REPO_ROOT.glob("*.md")))
    files.extend(sorted(DOCS_DIR.glob("*.md")))
    files.extend(sorted((DOCS_DIR / "adr").glob("*.md")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in files:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def extract_local_targets(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    targets: list[str] = []
    for match in INLINE_LINK_RE.finditer(text):
        targets.append(match.group(1))
    definitions: dict[str, str] = {}
    for match in REF_DEF_RE.finditer(text):
        definitions[match.group(1).lower()] = match.group(2)
    for match in REF_USE_RE.finditer(text):
        label = match.group(1).lower()
        if label in definitions:
            targets.append(definitions[label])
    for match in REF_USE_EMPTY_RE.finditer(text):
        label = match.group(1).lower()
        if label in definitions:
            targets.append(definitions[label])
    return targets


def link_resolves(source: Path, target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return True
    path_part = target.split("#", 1)[0]
    if path_part == "":
        return True
    if target.startswith("/"):
        candidate = REPO_ROOT / path_part.lstrip("/")
    else:
        candidate = (source.parent / path_part).resolve()
    return candidate.exists()


def lines_without_negation(text: str, claim: str) -> list[str]:
    offending: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        index = lower.find(claim)
        while index != -1:
            before = lower[:index]
            if not any(negation in before for negation in NEGATIONS):
                offending.append(line)
            index = lower.find(claim, index + 1)
    return offending


def test_all_local_markdown_links_resolve() -> None:
    broken: list[tuple[str, str]] = []
    for markdown in markdown_files():
        for target in extract_local_targets(markdown):
            if not link_resolves(markdown, target):
                broken.append((str(markdown), target))
    assert not broken, f"Broken local links: {broken}"


def test_readme_states_prealpha_not_published() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "pre-alpha" in text
    assert "not published" in text


def test_readme_does_not_claim_pricing_exists() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    offending = []
    for claim in PRICING_CLAIMS:
        if lines_without_negation(text, claim):
            offending.append(claim)
    assert not offending, f"Pricing claims in README: {offending}"


def test_docs_do_not_claim_pypi_availability() -> None:
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for claim in PYPI_CLAIMS:
            offending = lines_without_negation(text, claim)
            assert not offending, f"{markdown}: PyPI claim '{claim}': {offending}"


def test_docs_do_not_make_forbidden_claims() -> None:
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for claim in FORBIDDEN_CLAIMS:
            offending = lines_without_negation(text, claim)
            assert not offending, f"{markdown}: forbidden claim '{claim}': {offending}"


def test_no_absolute_local_paths() -> None:
    files = markdown_files() + CONFIG_FILES
    hits: list[tuple[str, str]] = []
    for path in files:
        for match in ABS_PATH_RE.finditer(path.read_text(encoding="utf-8")):
            hits.append((str(path), match.group(0)))
    assert not hits, f"Absolute local paths: {hits}"


def test_no_secrets_or_credentials() -> None:
    files = markdown_files() + CONFIG_FILES
    hits: list[tuple[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_RES:
            match = pattern.search(text)
            if match is not None:
                hits.append((str(path), pattern.pattern))
    assert not hits, f"Possible secrets: {hits}"


def test_no_codex_context_file() -> None:
    assert not (REPO_ROOT / "CODEX_CONTEXT.md").exists()


def test_project_urls_point_to_intended_repo() -> None:
    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    urls = data["project"].get("urls", {})
    for name, url in urls.items():
        assert "github.com/sciwiz7/DerivaTrace" in url, (name, url)
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for match in re.finditer(r"github\.com/[A-Za-z0-9_./-]+", text):
            assert "sciwiz7/DerivaTrace" in match.group(0), (
                str(markdown),
                match.group(0),
            )


def test_ci_matrix_includes_311_to_314() -> None:
    text = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for version in ['"3.11"', '"3.12"', '"3.13"', '"3.14"']:
        assert version in text, version


def test_ci_has_no_publishing_or_oidc_permissions() -> None:
    text = (
        (REPO_ROOT / ".github" / "workflows" / "ci.yml")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "id-token" not in text
    assert "publish" not in text
    assert "write" not in text
    assert "secrets" not in text


def test_separation_of_concerns_referenced() -> None:
    architecture = (
        (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8").lower()
    )
    assert "separation of concerns" in architecture
    layers = [
        "contract semantics",
        "market data",
        "model",
        "numerical engine",
        "risk",
        "validation",
        "evidence certificate",
    ]
    for layer in layers:
        assert layer in architecture, layer
    for doc in [
        REPO_ROOT / "docs" / "index.md",
        REPO_ROOT / "docs" / "product-spec.md",
        REPO_ROOT / "docs" / "contract-semantics.md",
    ]:
        content = doc.read_text(encoding="utf-8").lower()
        assert "separation of concerns" in content, str(doc)


def _strip_emphasis(text: str) -> str:
    return re.sub(r"\*+", "", text)


def test_certificate_spec_denies_proof_and_signature() -> None:
    text = _strip_emphasis(
        (REPO_ROOT / "docs" / "certificate-spec.md").read_text(encoding="utf-8")
    ).lower()
    assert "not a mathematical proof" in text
    assert "not a digital signature" in text


def test_certificate_spec_hash_excludes_itself() -> None:
    text = (
        (REPO_ROOT / "docs" / "certificate-spec.md").read_text(encoding="utf-8").lower()
    )
    assert "certificate_hash" in text
    assert "omit" in text
    assert "reproducibility_hash" in text


def test_threat_model_covers_required_threats() -> None:
    text = (REPO_ROOT / "docs" / "threat-model.md").read_text(encoding="utf-8").lower()
    required = [
        "arbitrary-code execution",
        "untrusted deserialization",
        "schema confusion",
        "canonicalization collision",
        "hash confusion",
        "deeply nested",
        "cyclic graph",
        "path counts",
        "extreme numeric",
        "overflow",
        "infinity",
        "path traversal",
        "archive extraction",
        "denial of service",
        "plugin",
        "model or engine substitution",
        "dependency confusion",
        "release workflows",
        "certificate tampering",
        "misleading validation",
        "secret leakage",
    ]
    missing = [t for t in required if t not in text]
    assert not missing, f"threat model missing coverage: {missing}"


def _near(text: str, anchor_re: str, word: str, window: int = 200) -> bool:
    text = text.lower()
    for match in re.finditer(anchor_re, text):
        if word in text[match.start() : match.start() + window]:
            return True
    return False


def _section(text: str, heading_re: str) -> str:
    """Return the text of the first section whose heading matches ``heading_re``."""
    heads = list(re.finditer(r"^\#{1,6}\s+.*$", text, re.IGNORECASE | re.MULTILINE))
    for i, h in enumerate(heads):
        if re.search(heading_re, h.group(0), re.IGNORECASE):
            start = h.start()
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            return text[start:end]
    return ""


def test_stage_status_claims() -> None:
    road = (REPO_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert _near(road, r"stage 0\b", "complete")
    assert _near(road, r"stage 1\b", "in progress")
    assert _near(road, r"stage 1a\b", "implement") or _near(
        road, r"stage 1a\b", "complete"
    )
    assert _near(road, r"stage 1b\b", "in progress")
    assert _near(road, r"stage 1c\b", "planned")
    # Stage 1 *as a whole* must not be described as complete; individual
    # sub-stages (e.g. Stage 1A) may be. Check the top-level Stage 1 status
    # line only, not every "stage 1" substring (which would also catch the
    # sub-stage headers and the whole-of-Stage-1 exclusions sentence).
    stage1 = _section(road, r"^##\s+stage 1\b")
    first_status = re.search(r"\*\*status:\*\*\s*([^\n]*)", stage1, re.IGNORECASE)
    assert first_status is not None
    assert "in progress" in first_status.group(1).lower()
    assert "complete" not in first_status.group(1).lower()


def test_stage_1b_baseline_new_files_exist() -> None:
    required = [
        DOCS_DIR / "canonicalization-spec.md",
        DOCS_DIR / "payoff-graph-spec.md",
        DOCS_DIR / "canonical-test-vectors.md",
        DOCS_DIR / "adr" / "0007-canonical-contract-identity-and-payoff-graph.md",
    ]
    for path in required:
        assert path.exists(), f"missing Stage 1B baseline file: {path}"


def test_stage_1b_baseline_status() -> None:
    road = (REPO_ROOT / "ROADMAP.md").read_text(encoding="utf-8").lower()
    # Stage 1A is complete.
    assert _near(road, r"stage 1a\b", "complete")
    # Stage 1B in progress: baseline complete; R1 implemented; R2 planned.
    assert _near(road, r"stage 1b\b", "in progress")
    # Stage 1C remains planned.
    assert _near(road, r"stage 1c\b", "planned")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "stage 1b" in readme
    # R1 canonical runtime implemented; R2 payoff-graph runtime planned.
    assert "implemented" in readme
    assert "payoff-graph runtime" in readme and "planned" in readme


def test_stage_1b_status_distinctions() -> None:
    # Stage 1B-R1 canonical runtime is implemented; the R2 payoff-graph runtime
    # remains specified but not implemented.
    canon = (DOCS_DIR / "canonicalization-spec.md").read_text(encoding="utf-8").lower()
    assert "implemented" in canon
    # The conservative principle must still be stated.
    assert "conservative" in canon

    pgspec = (DOCS_DIR / "payoff-graph-spec.md").read_text(encoding="utf-8").lower()
    assert "not implemented" in pgspec

    vectors = (
        (DOCS_DIR / "canonical-test-vectors.md").read_text(encoding="utf-8").lower()
    )
    assert "implemented" in vectors

    adr = (
        (DOCS_DIR / "adr" / "0007-canonical-contract-identity-and-payoff-graph.md")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "implemented" in adr
    assert "planned" in adr


def test_no_canonicalization_or_hashing_implementation_claimed() -> None:
    # The Stage 1B baseline / R2 spec must not claim a runtime implementation
    # exists. The proposed (future) `compile_payoff_graph` signature is allowed
    # to be documented as a specification, so it is deliberately not listed here;
    # runtime presence is instead guarded by test_no_payoff_graph_runtime_module.
    impl_claims = [
        "canonicalize(",
        "def canonicalize",
        "canonicalize_contract",
        "sha256(",
        "hash_canonical",
        "serialize(",
        "def serialize",
    ]
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for claim in impl_claims:
            assert claim not in text.lower(), (
                f"{markdown}: implementation claim '{claim}'"
            )


def test_stage_1b_baseline_forbids_overclaiming_equivalence() -> None:
    spec = (DOCS_DIR / "canonicalization-spec.md").read_text(encoding="utf-8").lower()
    # Must explicitly deny claiming complete mathematical/economic equivalence.
    assert "economic equivalence" in spec
    assert "not" in spec
    assert "complete mathematical" in spec or "mathematical or economic" in spec


def test_package_remains_prealpha_unpublished() -> None:
    combined = (
        (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        + "\n"
        + (REPO_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    ).lower()
    assert "pre-alpha" in combined
    assert ("not published" in combined) or ("unpublished" in combined)


def test_no_pricing_functionality_in_docs() -> None:
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        offending = []
        for claim in PRICING_CLAIMS:
            if lines_without_negation(text, claim):
                offending.append(claim)
        assert not offending, f"{markdown}: pricing claims: {offending}"


def test_stage_1a_exclusions_documented() -> None:
    api = (DOCS_DIR / "contract-api.md").read_text(encoding="utf-8").lower()
    for term in [
        "canonical",
        "hash",
        "payoff graph",
        "certificate",
        "serialize",
        "price",
        "model",
        "engine",
    ]:
        assert term in api, f"contract-api.md should discuss exclusion of '{term}'"


def test_no_prohibited_capabilities_in_public_api() -> None:
    import derivatrace.contracts as contracts

    banned = [
        "canonical",
        "hash",
        "payoff",
        "certificate",
        "price",
        "evaluate",
        "serialize",
        "model",
        "engine",
    ]
    public_names = [n for n in dir(contracts) if not n.startswith("_")]
    for prefix in banned:
        assert not any(n.startswith(prefix) for n in public_names), prefix


def test_adr_0006_and_contract_api_exist() -> None:
    assert (
        DOCS_DIR / "adr" / "0006-stage-1-contract-algebra-and-runtime-type-system.md"
    ).exists()
    assert (DOCS_DIR / "contract-api.md").exists()


def test_dependencies_remain_empty() -> None:
    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    assert data["project"]["dependencies"] == []


def test_version_unchanged() -> None:
    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    assert data["project"]["version"] == "0.1.0.dev0"


# ---- Stage 1B canonicalization / payoff-graph conformance (Review 13) ----


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    # Drop markdown emphasis/code markers so phrase matching is robust.
    return text.lower().replace("*", "").replace("`", "")


def test_canonical_json_policy_is_byte_exact() -> None:
    spec = _text(DOCS_DIR / "canonicalization-spec.md").lower()
    # exact separators / no whitespace
    assert 'separators=(",", ":")' in _text(DOCS_DIR / "canonicalization-spec.md")
    for token in [
        "no bom",
        "no trailing newline",
        "no spaces",
        "ensure_ascii=true",
        "sorted keys",
        "no json floating-point",
        "solidus",
        "non-ascii",
    ]:
        assert token in spec, token


def test_node_classification_distinguishes_three_classes() -> None:
    spec = _norm(_text(DOCS_DIR / "canonicalization-spec.md"))
    # The three node classes must all be named.
    assert "commutative associative collection" in spec
    assert "commutative binary" in spec
    assert "author-order-preserving" in spec
    # The collection class is n-ary and flattened; Multiply is binary, not.
    assert "n-ary" in spec
    assert "multiply" in spec
    assert "multiply is binary" in spec
    # Multiply must be explicitly excluded from associative flattening.
    assert "nested multiply" in spec and "not" in spec
    # The collection list enumerates exactly the five nodes, not Multiply.
    assert "add" in spec and "maximum" in spec and "minimum" in spec
    assert "allof" in spec and "anyof" in spec


def test_no_contradictory_multiply_flatten_language() -> None:
    spec = _text(DOCS_DIR / "canonicalization-spec.md")
    adr = _text(
        DOCS_DIR / "adr" / "0007-canonical-contract-identity-and-payoff-graph.md"
    )
    # "Multiply" must never be described as flattened/associative-collection
    # without a negation.
    for text in (spec, adr):
        low = text.lower()
        assert "multiply" in low
        for m in re.finditer(r"multiply.{0,140}flatten", low):
            assert "not" in m.group(0) or "no" in m.group(0), m.group(0)


def test_divide_folding_removed_from_schema_1_0_0() -> None:
    spec = _norm(_text(DOCS_DIR / "canonicalization-spec.md"))
    # The policy line is contiguous; the follow-up sentence wraps across a line.
    assert "divide-folding policy (schema 1.0.0): removed" in spec
    assert "divide folding" in spec and "excluded" in spec
    assert "1.0.0" in spec


def test_payoff_divide_maps_directly_not_reciprocal() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    adr = _text(
        DOCS_DIR / "adr" / "0007-canonical-contract-identity-and-payoff-graph.md"
    )
    assert "PGDivide" in pg
    # No unresolved / implementation-finalized mapping language.
    low = (pg + adr).lower()
    assert "implementation-finalized" not in low
    assert "implementation-finalised" not in low
    # No reciprocal rewrite; Divide maps to PGDivide directly.
    assert "pgdivide" in low
    assert "no reciprocal" in low or ("never" in low and "reciprocal" not in low)


def test_collision_handling_present() -> None:
    spec = _norm(_text(DOCS_DIR / "canonicalization-spec.md"))
    threat = _norm(_text(DOCS_DIR / "threat-model.md"))
    adr = _norm(
        _text(DOCS_DIR / "adr" / "0007-canonical-contract-identity-and-payoff-graph.md")
    )
    assert "canonicalization.collision" in spec
    assert "canonicalization.collision" in threat
    assert "canonicalization.collision" in adr
    assert "if the same" in spec and "different" in spec


def test_object_identity_not_part_of_identity() -> None:
    spec = _norm(_text(DOCS_DIR / "canonicalization-spec.md"))
    assert "python object identity is never part of canonical identity" in spec
    assert "content-addressed" in spec
    assert "shared subtree" in spec and "independently allocated" in spec


def test_schema_version_participates_in_identity_framing() -> None:
    spec = _norm(_text(DOCS_DIR / "canonicalization-spec.md"))
    assert '"1.0.0"' in spec
    assert "participates" in spec and "directly" in spec
    # The preimage framing includes the version between NUL separators.
    assert "0x00" in spec


def test_stage_1a_status_field_is_complete() -> None:
    road = _text(REPO_ROOT / "ROADMAP.md")
    assert "- **Status:** Complete." in road
    assert "- **Status:** In progress" in road
    assert "- **Status:** Planned." in road


def test_specification_denies_complete_equivalence_claims() -> None:
    spec = _norm(_text(DOCS_DIR / "canonicalization-spec.md"))
    for claim in [
        "not complete mathematical equivalence",
        "not economic equivalence",
        "not pricing equivalence",
        "not legal equivalence",
        "no formal verification claim",
        "assumed, not proven",
    ]:
        assert claim in spec, claim


def test_no_placeholder_identities_in_normative_vectors() -> None:
    text = _text(DOCS_DIR / "canonical-test-vectors.md")
    # Find every contract/payoff-graph identity value and check it is literal 64-hex.
    placeholder_words = ("placeholder", "tbd", "example", "<hex>")
    count = 0
    for m in re.finditer(r"(canonical|payoffgraph):sha256:([^\s`,]+)", text):
        suffix = m.group(2)
        if re.fullmatch(r"[0-9a-f]{64}", suffix):
            count += 1
            assert set(suffix) != {"0"}, f"all-zero identity: {m.group(0)}"
            for w in placeholder_words:
                assert w not in suffix, f"placeholder identity: {m.group(0)}"
    # There must be real normative identities present.
    assert count >= 10, f"too few identities found: {count}"


def test_no_stage_1b_runtime_implementation_in_docs() -> None:
    # The proposed (future) payoff-graph API may be documented as a specification,
    # so `compile_payoff_graph` / `payoff_graph(` are not flagged here; runtime
    # presence is guarded by test_no_payoff_graph_runtime_module.
    impl_claims = [
        "canonicalize(",
        "def canonicalize",
        "canonicalize_contract",
        "sha256(",
        "hash_canonical",
        "serialize(",
        "def serialize",
    ]
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8")
        for claim in impl_claims:
            assert claim not in text.lower(), (
                f"{markdown}: implementation claim '{claim}'"
            )


def test_payoff_graph_schema_and_identity_defined() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "payoffgraph:sha256:" in pg
    assert "derivatrace.payoffgraph.graph" in pg
    assert "derivatrace.payoffgraph.node" in pg
    assert "provenance" in pg.lower()
    assert "identity-exempt" in pg.lower() or "excludes" in pg.lower()
    # PG boolean condition nodes must be specified (no mapping left finalised).
    for node in ("PGComparison", "PGAllOf", "PGAnyOf", "PGNot"):
        assert node in pg, node


# ---- Stage 1B-R2 payoff-graph specification-closure guards (issues #1 / #3) ----


SRC_ROOT = REPO_ROOT / "src" / "derivatrace"

CANONICAL_NODES = [
    "Number",
    "Observable",
    "Add",
    "Subtract",
    "Multiply",
    "Divide",
    "Negate",
    "Maximum",
    "Minimum",
    "ConditionalValue",
    "BooleanConstant",
    "Comparison",
    "AllOf",
    "AnyOf",
    "Not",
    "Zero",
    "Payment",
    "Both",
    "Scale",
    "ConditionalContract",
]


def test_pg_payment_uses_amount_not_payoff_leaf() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    # The field is explicitly denied the obsolete name.
    assert "never `payoff_leaf`" in pg
    # PGPayment carries an `amount` field (with currency and settlement_time).
    assert "| `PGPayment` | `amount`, `currency`, `settlement_time` |" in pg


def test_pg_constant_and_observable_no_settlement_time() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    # The obsolete blanket "leaves carry settlement time" statement is gone.
    assert "Leaves are the only nodes that carry" not in pg
    assert "PGConstant" in pg and "does **not** contain `settlement_time`" in pg
    assert "PGObservable" in pg and "does **not** contain `settlement_time`" in pg


def test_pg_payment_contains_settlement_time() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "is owned exclusively by `PGPayment`" in pg


def test_pg_subtract_exists() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "`PGSubtract`" in pg


def test_subtract_does_not_lower_to_pgadd_pgnegate() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "PGAdd`+`PGNegate`" in pg
    assert "NOT lowered" in pg or "not lowered" in pg.lower()


def test_pg_allof_anyof_flattened_sorted_commutative() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "Commutative, associative, flattened, sorted" in pg


def test_pg_comparison_preserves_order() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "operator-sensitive, author-order preserved, not commutative" in pg


def test_pg_multiply_binary_not_flattened() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md").lower()
    assert "pgmultiply" in pg
    assert "binary" in pg
    assert "not flattened" in pg


def test_provenance_excluded_from_identity() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "changing provenance alone does **not** change payoff-graph identity" in pg
    assert "provenance" in pg.lower()
    assert "excluded" in pg.lower()


def test_all_stage1a_r1_nodes_have_pg_mapping() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    for node in CANONICAL_NODES:
        assert node in pg, f"canonical node {node} not mentioned in payoff spec"
    # The complete matrix header must enumerate all twenty output mappings.
    for pg_node in (
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
        "PGBooleanConstant",
        "PGComparison",
        "PGAllOf",
        "PGAnyOf",
        "PGNot",
        "PGCombine",
        "PGPayment",
        "PGScale",
        "PGConditionalContract",
    ):
        assert pg_node in pg, f"payoff node {pg_node} missing from mapping"


def test_r1_complete_r2_planned_status() -> None:
    road = _text(REPO_ROOT / "ROADMAP.md")
    # Stage 1B baseline complete; R1 implemented; R2 planned.
    assert _near(road, r"stage 1b\b", "in progress")
    assert "complete" in road.lower()
    # R2 explicitly not implemented.
    pg = _text(DOCS_DIR / "payoff-graph-spec.md").lower()
    assert "not implemented" in pg
    # R1 is implemented.
    canon = _text(DOCS_DIR / "canonicalization-spec.md").lower()
    assert "implemented" in canon
    adr = _text(
        DOCS_DIR / "adr" / "0007-canonical-contract-identity-and-payoff-graph.md"
    ).lower()
    assert "implemented" in adr
    assert "planned" in adr


def test_no_payoff_graph_runtime_module() -> None:
    # No payoff-graph runtime package may exist yet (either spelling).
    assert not (SRC_ROOT / "payoffgraph").exists()
    assert not (SRC_ROOT / "payoff_graph").exists()

    # No importable derivatrace.payoffgraph / derivatrace.payoff_graph package.
    for mod in ("derivatrace.payoffgraph", "derivatrace.payoff_graph"):
        try:
            importlib.import_module(mod)
        except ImportError:
            pass
        else:
            raise AssertionError(f"importable module present: {mod}")

    # No runtime implementation of the proposed R2 API in src/.
    forbidden_defs = ("def compile_payoff_graph",)
    forbidden_classes = (
        "class PayoffGraph",
        "class PayoffGraphLimits",
        "class PayoffGraphSchemaVersion",
    )
    hits: list[str] = []
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(d in text for d in forbidden_defs):
            hits.append(f"def:{path}")
        if any(c in text for c in forbidden_classes):
            hits.append(f"class:{path}")
    assert not hits, f"payoff-graph runtime implementation present: {hits}"

    # No package exports of the proposed R2 API.
    pkg_text = (REPO_ROOT / "src" / "derivatrace" / "__init__.py").read_text(
        encoding="utf-8"
    )
    for name in (
        "PayoffGraph",
        "PayoffGraphLimits",
        "PayoffGraphSchemaVersion",
        "compile_payoff_graph",
        "payoffgraph",
    ):
        assert name not in pkg_text, f"package export present: {name}"


def test_payoff_graph_error_taxonomy_is_dedicated() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "payoff_graph.collision" in pg
    assert "payoff_graph.error" in pg
    assert "payoff_graph.input" in pg
    assert "payoff_graph.compilation" in pg
    assert "payoff_graph.complexity" in pg
    assert "payoff_graph.encoding" in pg
    # Must not reuse the canonicalization collision code for payoff nodes.
    assert "must **not** reuse `canonicalization.collision`" in pg


def test_payoff_graph_limits_are_exact_positive_ints() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    for limit in (
        "max_payoff_nodes",
        "max_document_bytes",
        "max_structural_bytes",
    ):
        assert limit in pg, limit
    assert "exact positive `int`" in pg


def test_reachable_only_policy_excludes_intermediates() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "reachable" in pg.lower()
    # Intermediates must never participate in identity / node_count.
    assert "node_count" in pg
    assert "structural_bytes" in pg
    assert "document_bytes" in pg


def test_zeros_compile_to_empty_pgcombine() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "PGCombine` with an **empty** `operands` array" in pg


def test_pg_boolean_constant_made_explicit() -> None:
    pg = _text(DOCS_DIR / "payoff-graph-spec.md")
    assert "PGBooleanConstant" in pg
    assert "explicit" in pg.lower()


# ---- Stage 1B-R2 specification-closure guards (PR #6) ----

_PG_SPEC = DOCS_DIR / "payoff-graph-spec.md"
_VEC = DOCS_DIR / "canonical-test-vectors.md"


def _sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^#{2,6}\s+(.*)$", line)
        if m:
            if current is not None:
                out[current] = "\n".join(buf)
            current = m.group(1)
            buf = []
        else:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf)
    return out


def _is_separator(line: str) -> bool:
    return set(line.replace("|", "").strip()) <= set("-: ")


def _table_rows(section_body: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section_body.splitlines():
        if not line.strip().startswith("|"):
            continue
        if _is_separator(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


EXPECTED_SOURCES = [
    "Number",
    "Observable",
    "Add",
    "Subtract",
    "Multiply",
    "Divide",
    "Negate",
    "Maximum",
    "Minimum",
    "ConditionalValue",
    "BooleanConstant",
    "Comparison",
    "AllOf",
    "AnyOf",
    "Not",
    "Zero",
    "Payment",
    "Both",
    "Scale",
    "ConditionalContract",
]

EXPECTED_MAPPING = {
    "Number": "PGConstant",
    "Observable": "PGObservable",
    "Add": "PGAdd",
    "Subtract": "PGSubtract",
    "Multiply": "PGMultiply",
    "Divide": "PGDivide",
    "Negate": "PGNegate",
    "Maximum": "PGMaximum",
    "Minimum": "PGMinimum",
    "ConditionalValue": "PGConditionalValue",
    "BooleanConstant": "PGBooleanConstant",
    "Comparison": "PGComparison",
    "AllOf": "PGAllOf",
    "AnyOf": "PGAnyOf",
    "Not": "PGNot",
    "Zero": "PGCombine",
    "Payment": "PGPayment",
    "Both": "PGCombine",
    "Scale": "PGScale",
    "ConditionalContract": "PGConditionalContract",
}

EXPECTED_19_PG = {
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
    "PGBooleanConstant",
    "PGComparison",
    "PGAllOf",
    "PGAnyOf",
    "PGNot",
    "PGCombine",
    "PGPayment",
    "PGScale",
    "PGConditionalContract",
}

EXPECTED_PAYLOAD_FIELDS = {
    "PGConstant": {"type", "amount", "unit"},
    "PGObservable": {"type", "observable_id", "observation_time", "unit"},
    "PGAdd": {"type", "operands"},
    "PGSubtract": {"type", "minuend", "subtrahend"},
    "PGMultiply": {"type", "left", "right"},
    "PGDivide": {"type", "numerator", "denominator"},
    "PGNegate": {"type", "operand"},
    "PGMaximum": {"type", "operands"},
    "PGMinimum": {"type", "operands"},
    "PGConditionalValue": {"type", "condition", "true_payoff", "false_payoff"},
    "PGBooleanConstant": {"type", "value"},
    "PGComparison": {"type", "left", "right", "operator"},
    "PGAllOf": {"type", "operands"},
    "PGAnyOf": {"type", "operands"},
    "PGNot": {"type", "operand"},
    "PGCombine": {"type", "operands"},
    "PGPayment": {"type", "amount", "currency", "settlement_time"},
    "PGScale": {"type", "factor", "payoff"},
    "PGConditionalContract": {"type", "condition", "true_payoff", "false_payoff"},
}


def _payload_keys(template: str) -> set[str]:
    return set(re.findall(r'"([A-Za-z_]+)":', template))


def test_exact_mapping_table_parser() -> None:
    pg = _text(_PG_SPEC)
    sections = _sections(pg)
    body = sections[next(k for k in sections if "Complete node mapping" in k)]
    rows = _table_rows(body)
    # drop header row
    rows = [r for r in rows if "Canonical node" not in r[0]]
    sources = [r[0].strip("`") for r in rows]
    outputs = [r[1].strip("`") for r in rows]
    assert len(rows) == 20, len(rows)
    assert set(sources) == set(EXPECTED_SOURCES), set(sources) ^ set(EXPECTED_SOURCES)
    assert len(set(sources)) == 20  # every source appears exactly once
    for src, out in zip(sources, outputs, strict=True):
        assert EXPECTED_MAPPING[src] == out, (src, out)
    assert set(outputs) == EXPECTED_19_PG
    assert all(o in EXPECTED_19_PG for o in outputs)
    assert all(s in EXPECTED_SOURCES for s in sources)


def test_exact_payload_schema_parser() -> None:
    pg = _text(_PG_SPEC)
    sections = _sections(pg)
    body = sections[next(k for k in sections if "Exact payoff payload schema" in k)]
    rows = _table_rows(body)
    rows = [r for r in rows if r[0] not in ("Node", "`Node`")]
    nodes = [r[0].strip("`") for r in rows]
    assert len(rows) == 19, len(rows)
    assert set(nodes) == set(EXPECTED_PAYLOAD_FIELDS), set(nodes) ^ set(
        EXPECTED_PAYLOAD_FIELDS
    )
    for row in rows:
        node = row[0].strip("`")
        template = row[1].strip("`")
        keys = _payload_keys(template)
        assert keys == EXPECTED_PAYLOAD_FIELDS[node], (node, keys)
        assert "payoff_leaf" not in template
    # Unit field policy: only PGConstant / PGObservable serialize `unit`.
    for row in rows:
        node = row[0].strip("`")
        keys = _payload_keys(row[1].strip("`"))
        if node in ("PGConstant", "PGObservable"):
            assert "unit" in keys, node
        else:
            assert "unit" not in keys, node
        if node in ("PGConstant", "PGObservable"):
            assert "settlement_time" not in keys, node
    # PGPayment required fields.
    pay = next(r for r in rows if r[0].strip("`") == "PGPayment")
    assert {"amount", "currency", "settlement_time"} <= _payload_keys(pay[1].strip("`"))
    # PGSubtract dedicated fields.
    sub = next(r for r in rows if r[0].strip("`") == "PGSubtract")
    assert {"minuend", "subtrahend"} <= _payload_keys(sub[1].strip("`"))


def test_reference_target_category_restrictions() -> None:
    pg = _text(_PG_SPEC)
    sections = _sections(pg)
    body = sections[
        next(k for k in sections if "Payoff node categories and reference-target" in k)
    ]
    phrases = [
        "`PGPayment.amount` -> a **money-denominated value payoff node**",
        "`PGScale.factor` -> a **dimensionless value payoff node**",
        "`PGScale.payoff` -> a **contract payoff node**",
        "`PGConditionalValue.condition` -> a **Boolean payoff node**",
        "`PGConditionalValue.true_payoff` / `false_payoff` -> **value payoff nodes of",
        "`PGConditionalContract.condition` -> a **Boolean payoff node**",
        "`PGConditionalContract.true_payoff` / `false_payoff` -> **contract payoff",
        "`PGCombine.operands` -> **contract payoff nodes**",
        "`PGComparison.left` / `right` -> **value payoff nodes**",
        "`PGAllOf` / `PGAnyOf` `operands` -> **Boolean payoff nodes**",
        "`PGNot.operand` -> a **Boolean payoff node**",
    ]
    for phrase in phrases:
        assert phrase in body, phrase


USD = Currency.from_code("USD")
T0 = ObservationTime.from_datetime(datetime(2030, 1, 1, tzinfo=UTC))
T0_ST = SettlementTime.from_datetime(datetime(2030, 1, 1, tzinfo=UTC))
T0_MS_ST = SettlementTime.from_datetime(
    datetime(2030, 1, 1, 0, 0, 0, 500000, tzinfo=UTC)
)


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


def _pay(amt: ScalarExpression) -> Payment:
    return Payment(amt, USD, T0_ST)


def _shared() -> Both:
    shared = _pay(Add((_obs("AAA"), _obs("BBB"))))
    return Both((shared, Scale(_num("2", scalar=True), shared)))


def test_planned_vector_sources_construct_and_validate() -> None:
    sources: list[Callable[[], Contract]] = [
        lambda: _pay(_num("100")),
        lambda: _pay(Add((_obs("AAA"), _obs("BBB")))),
        lambda: _pay(Subtract(_obs("AAA"), _obs("BBB"))),
        lambda: _pay(Add((_obs("AAA"), Add((_obs("BBB"), _obs("XXX")))))),
        lambda: _pay(Add((_obs("AAA"), _obs("BBB"), _obs("XXX")))),
        lambda: _pay(Multiply(_obs("AAA"), _num("2", scalar=True))),
        lambda: _pay(Multiply(_num("2", scalar=True), _obs("AAA"))),
        lambda: _pay(
            Multiply(
                _obs("AAA"),
                Multiply(_num("2", scalar=True), _num("3", scalar=True)),
            )
        ),
        lambda: Scale(Divide(_scobs("SCALARA"), _scobs("SCALARB")), _pay(_obs("AAA"))),
        lambda: Scale(Divide(_scobs("SCALARB"), _scobs("SCALARA")), _pay(_obs("AAA"))),
        lambda: Both((_pay(_obs("AAA")), _pay(_obs("BBB")))),
        lambda: Both((_pay(_obs("BBB")), _pay(_obs("AAA")))),
        lambda: _pay(Add((_obs("AAA"), _obs("AAA")))),
        lambda: _pay(_obs("AAA")),
        lambda: _shared(),
        lambda: Both(
            (
                _pay(Add((_obs("AAA"), _obs("BBB")))),
                Scale(_num("2", scalar=True), _pay(Add((_obs("AAA"), _obs("BBB"))))),
            )
        ),
        lambda: _pay(
            ConditionalValue(
                AllOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        AllOf(
                            (
                                Comparison(
                                    _obs("BBB"),
                                    _obs("XXX"),
                                    ComparisonOperator.GREATER_THAN,
                                ),
                                Comparison(
                                    _obs("AAA"),
                                    _obs("XXX"),
                                    ComparisonOperator.GREATER_THAN,
                                ),
                            )
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        ),
        lambda: _pay(
            ConditionalValue(
                AllOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("BBB"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("AAA"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        ),
        lambda: _pay(
            ConditionalValue(
                AnyOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        AnyOf(
                            (
                                Comparison(
                                    _obs("BBB"),
                                    _obs("XXX"),
                                    ComparisonOperator.GREATER_THAN,
                                ),
                                Comparison(
                                    _obs("AAA"),
                                    _obs("XXX"),
                                    ComparisonOperator.GREATER_THAN,
                                ),
                            )
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        ),
        lambda: _pay(
            ConditionalValue(
                AnyOf(
                    (
                        Comparison(
                            _obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("BBB"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                        Comparison(
                            _obs("AAA"), _obs("XXX"), ComparisonOperator.GREATER_THAN
                        ),
                    )
                ),
                _obs("AAA"),
                _obs("BBB"),
            )
        ),
        lambda: _pay(
            ConditionalValue(
                Comparison(_obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN),
                _obs("AAA"),
                _obs("BBB"),
            )
        ),
        lambda: ConditionalContract(
            Comparison(_obs("AAA"), _obs("BBB"), ComparisonOperator.GREATER_THAN),
            _pay(_obs("AAA")),
            _pay(_obs("BBB")),
        ),
        lambda: Both((Zero(), Zero())),
        lambda: _pay(Add((_obs("AAA"), _obs("BBB")))),
        lambda: Payment(_num("1"), USD, T0_MS_ST),
    ]
    for builder in sources:
        contract = builder()
        metrics = validate_contract(contract)
        assert metrics.node_count > 0


def test_planned_vector_invalid_sources_rejected() -> None:
    # money-denominated Divide denominator must be rejected
    with pytest.raises(ContractError):
        validate_contract(Divide(_obs("AAA"), _obs("BBB")))  # type: ignore[arg-type]
    # single-operand Add must be rejected
    with pytest.raises(ContractError):
        validate_contract(Add((_obs("AAA"),)))  # type: ignore[arg-type]
    # an Expression passed where a Contract is required must be rejected
    with pytest.raises(ContractError):
        validate_contract(Scale(_num("2", scalar=True), _obs("AAA")))  # type: ignore[arg-type]
    # Multiply without a dimensionless factor (money x money) must be rejected
    with pytest.raises(ContractError):
        validate_contract(Multiply(_obs("AAA"), _obs("BBB")))  # type: ignore[arg-type]


def test_r2_coverage_section_no_stale_rules() -> None:
    vec = _VEC.read_text(encoding="utf-8")
    sections = _sections(vec)
    r2_parts = "\n".join(
        v
        for k, v in sections.items()
        if ("Planned R2 vectors" in k) or ("Coverage obligations" in k)
    )
    # payoff collisions must not map onto canonicalization.collision
    assert "canonicalization.collision" not in r2_parts, "stale payoff collision rule"
    # R2 coverage must not say "When Stage 1B is implemented"
    assert "When Stage 1B is implemented" not in r2_parts
    # R2 stability must not be "re-running canonicalization"
    assert "re-running canonicalization" not in r2_parts
    # no `<hex>` placeholder identity values
    assert ":sha256:<hex>" not in r2_parts
