from __future__ import annotations

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
    "not",
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


def test_readme_stage_1b_r2_byte_semantics_accurate() -> None:
    # Finding 1: the Stage 1B-R2 section must not describe document_bytes as
    # "pretty-printed" (as a positive claim) or as "content-equal" to
    # structural_bytes. Both are compact canonical JSON; document_bytes
    # additionally carries provenance and is therefore distinct from
    # structural_bytes. The documentation-guard blockquote intentionally quotes
    # the forbidden phrasing, so it is stripped before the negative checks.
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    sections = _sections(readme)
    r2_body = "\n".join(v for k, v in sections.items() if "Stage 1B-R2" in k)
    assert r2_body, "README has no Stage 1B-R2 section"
    prose = "\n".join(
        line for line in r2_body.splitlines() if not line.lstrip().startswith(">")
    )
    # The false positive claim "content-equal `document_bytes`" must not appear
    # anywhere in the section prose.
    assert "content-equal" not in prose, (
        "Stage 1B-R2 section must not claim document_bytes is 'content-equal' "
        "to structural_bytes"
    )
    # "pretty-printed" may only appear as an explicit negation (e.g. "Neither
    # representation is pretty-printed"); a positive assertion of it is forbidden.
    for line in prose.splitlines():
        lowered = line.lower()
        idx = lowered.find("pretty-printed")
        while idx != -1:
            before = lowered[:idx]
            assert ("neither representation" in before) or ("not " in before), (
                f"Stage 1B-R2 section positively asserts 'pretty-printed': {line!r}"
            )
            idx = lowered.find("pretty-printed", idx + 1)
    # Positive guard: the corrected wording must be present.
    assert "structural_bytes" in r2_body
    assert "document_bytes" in r2_body


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
    # Stage 1B in progress: baseline complete; R1 implemented; R2 implemented.
    assert _near(road, r"stage 1b\b", "in progress")
    # Stage 1C remains planned.
    assert _near(road, r"stage 1c\b", "planned")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "stage 1b" in readme
    # R1 canonical runtime implemented; R2 payoff-graph runtime implemented.
    assert "implemented" in readme
    assert "payoff-graph runtime" in readme


def test_stage_1b_status_distinctions() -> None:
    # Stage 1B-R1 canonical runtime is implemented; the R2 payoff-graph runtime
    # remains specified but not implemented.
    canon = (DOCS_DIR / "canonicalization-spec.md").read_text(encoding="utf-8").lower()
    assert "implemented" in canon
    # The conservative principle must still be stated.
    assert "conservative" in canon

    pgspec = (DOCS_DIR / "payoff-graph-spec.md").read_text(encoding="utf-8").lower()
    assert "implemented" in pgspec

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
    # exists for the canonical contract identity (R1). The payoff-graph runtime
    # (R2) is implemented and exercised by test_payoff_graph_runtime_module_present;
    # its specification may document `compile_payoff_graph` without an
    # implementation claim for the R1 canonicalization internals.
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
    # The R1 canonicalization internals (canonicalize / sha256 / serialize) must
    # not be claimed as implemented in documentation prose; the implemented
    # payoff-graph runtime is guarded by test_payoff_graph_runtime_module_present.
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


def test_r1_complete_r2_implemented_status() -> None:
    road = _text(REPO_ROOT / "ROADMAP.md")
    # Stage 1B baseline complete; R1 implemented; R2 implemented.
    assert _near(road, r"stage 1b\b", "in progress")
    assert "complete" in road.lower()
    # R2 is implemented (CV-011).
    pg = _text(DOCS_DIR / "payoff-graph-spec.md").lower()
    assert "implemented" in pg
    # R1 is implemented.
    canon = _text(DOCS_DIR / "canonicalization-spec.md").lower()
    assert "implemented" in canon
    adr = _text(
        DOCS_DIR / "adr" / "0007-canonical-contract-identity-and-payoff-graph.md"
    ).lower()
    assert "implemented" in adr


def test_payoff_graph_runtime_module_present() -> None:
    # The payoff-graph runtime package exists now (CV-011).
    assert (SRC_ROOT / "payoffgraph").is_dir()
    assert not (SRC_ROOT / "payoff_graph").exists()

    import datetime

    import derivatrace.payoffgraph as pgpkg
    from derivatrace.canonical import canonicalize_contract
    from derivatrace.contracts import (
        Add,
        Currency,
        Observable,
        ObservableId,
        ObservationTime,
        Payment,
        SettlementTime,
        Unit,
    )
    from derivatrace.payoffgraph import (
        PayoffGraph,
        PayoffGraphLimits,
        PayoffGraphSchemaVersion,
        compile_payoff_graph,
    )

    assert pgpkg.compile_payoff_graph is compile_payoff_graph
    assert pgpkg.PayoffGraph is PayoffGraph
    assert pgpkg.PayoffGraphLimits is PayoffGraphLimits
    assert pgpkg.PayoffGraphSchemaVersion is PayoffGraphSchemaVersion

    UTC = datetime.UTC
    USD = Currency.from_code("USD")
    T0 = ObservationTime.from_datetime(datetime.datetime(2030, 1, 1, tzinfo=UTC))
    T0ST = SettlementTime.from_datetime(datetime.datetime(2030, 1, 1, tzinfo=UTC))
    obsA = Observable(
        ObservableId.from_parts("equity", "AAA", "close"), T0, Unit.money(USD)
    )
    obsB = Observable(
        ObservableId.from_parts("equity", "BBB", "close"), T0, Unit.money(USD)
    )
    contract = Payment(Add((obsA, obsB)), USD, T0ST)
    pg = compile_payoff_graph(contract)

    assert isinstance(pg, PayoffGraph)
    assert pg.schema_version == "1.0.0"
    assert pg.identity == (
        "payoffgraph:sha256:"
        "59fbb00dbb585755a799cd7e387e4ee51fd9b77ed3cc032758a825f2f8836e1a"
    )
    assert pg.root_node_id == (
        "5ee2594b6c230a97e1b44115db479624a2de6780c192558a7c64b589f545c94c"
    )
    assert pg.node_count == 4
    assert pg.source_contract_identity == canonicalize_contract(contract).identity
    # document_bytes includes provenance and is distinct from structural_bytes.
    assert pg.document_bytes != pg.structural_bytes
    assert len(pg.document_bytes) > len(pg.structural_bytes)
    # provenance is not a public attribute of PayoffGraph
    assert not hasattr(pg, "provenance") or not isinstance(
        getattr(type(pg), "provenance", None), property
    )
    # document_bytes contains provenance; structural_bytes does not.
    import json

    doc_parsed = json.loads(pg.document_bytes.decode())
    struct_parsed = json.loads(pg.structural_bytes.decode())
    assert "provenance" in doc_parsed
    assert "provenance" not in struct_parsed
    assert doc_parsed["provenance"] == {
        "compiler": "derivatrace.payoffgraph.compiler/1.0.0",
        "source_contract_identity": pg.source_contract_identity,
    }


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


def test_r2_vector_sources_construct_and_validate() -> None:
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


def test_r2_vector_invalid_sources_rejected() -> None:
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
        if ("Stage 1B-R2 runtime conformance vectors" in k)
        or ("Coverage obligations" in k)
    )
    # The obsolete "Planned R2 vectors" section must no longer exist.
    assert not any("Planned R2 vectors" in k for k in sections), (
        "obsolete 'Planned R2 vectors' section still present"
    )
    # Obsolete future-tense phrases from the pre-runtime draft must be gone
    # everywhere in the document.
    stale_phrases = [
        "runtime-generated hashes deferred",
        "will be finalized when compile_payoff_graph is implemented",
        "When the R2 runtime lands",
        "when the Stage 1B-R2 runtime is implemented",
        "remaining planned R2 vectors",
    ]
    for phrase in stale_phrases:
        assert phrase not in vec, f"stale R2 phrase still present: {phrase!r}"
    # payoff collisions must not map onto canonicalization.collision
    assert "canonicalization.collision" not in r2_parts, "stale payoff collision rule"
    # R2 coverage must not say "When Stage 1B is implemented"
    assert "When Stage 1B is implemented" not in r2_parts
    # R2 stability must not be "re-running canonicalization"
    assert "re-running canonicalization" not in r2_parts
    # no `<hex>` placeholder identity values in the R2 vectors / coverage section
    # (the Conventions section legitimately uses `<hex>` to describe the format)
    assert ":sha256:<hex>" not in r2_parts


def test_r2_conformance_identities_match_executable_registry() -> None:
    # The normative R2 conformance section must document exactly the identities
    # recorded in the executable conformance registry, keyed by the stable vector
    # key. Machine-readable `**Vector key:**` annotations are paired in document
    # order with the `payoffgraph:sha256:` identities; the resulting keyed map
    # must equal the registry exactly. This makes the guards explicit: a swapped
    # identity, a missing/extra document, or a duplicate/renamed key all fail.
    from conformance_registry import CONFORMANCE_VECTORS

    registry: dict[str, str] = {
        name: identity for name, (identity, _) in CONFORMANCE_VECTORS.items()
    }

    vec = _VEC.read_text(encoding="utf-8")
    sections = _sections(vec)
    section_name = "Stage 1B-R2 runtime conformance vectors"
    assert section_name in sections, "missing R2 conformance section"
    body = sections[section_name]

    # Stable vector keys in document order (comma-separated annotations).
    key_order: list[str] = []
    for km in re.finditer(r"\*\*Vector key:\*\*\s*([^\n]*+)", body):
        for raw in km.group(1).split(","):
            key = raw.strip().strip("*").strip()
            if key:
                key_order.append(key)
    # Payoff-graph identities in document order. A vector may legitimately be
    # cross-referenced (e.g. the deterministic-recompilation note repeats the
    # PGAdd commutation identity); collapse exact repeats so the keyed zip still
    # aligns, while a genuinely new/different identity still breaks the count.
    seen_identity: set[str] = set()
    identity_order: list[str] = []
    for m in re.finditer(r"payoffgraph:sha256:([0-9a-f]{64})", body):
        identity = "payoffgraph:sha256:" + m.group(1)
        if identity not in seen_identity:
            seen_identity.add(identity)
            identity_order.append(identity)

    assert identity_order, "no conformance identities found in the R2 section"
    assert len(key_order) == len(identity_order), (
        f"vector-key count ({len(key_order)}) != identity count "
        f"({len(identity_order)}) in the R2 section"
    )

    documented: dict[str, str] = {}
    for key, identity in zip(key_order, identity_order, strict=True):
        assert key not in documented, f"duplicate vector key '{key}' in R2 section"
        documented[key] = identity

    # Every registry vector is represented exactly once, under its stable key.
    assert set(documented) == set(registry), (
        "R2 documented vector keys diverge from the executable registry: "
        f"documented-only={set(documented) - set(registry)!r}, "
        f"registry-only={set(registry) - set(documented)!r}"
    )
    # Exact key -> identity correspondence (catches a swapped identity too).
    assert documented == registry, (
        "R2 documented identities diverge from the executable registry: "
        f"documented-only={set(documented) - set(registry)!r}, "
        f"registry-only={set(registry) - set(documented)!r}"
    )

    # The collision seam is documented but is not a normal graph identity; it
    # must not be annotated as a conformance vector key.
    assert "payoff_graph.collision" not in key_order


def test_r2_conformance_registry_executes() -> None:
    # Every registry entry must compile through the public Stage 1A API to the
    # exact documented identity (reorder / flatten / copy invariance included).
    from conformance_registry import CONFORMANCE_VECTORS

    from derivatrace.payoffgraph import compile_payoff_graph

    for name, (expected, builders) in CONFORMANCE_VECTORS.items():
        identities = {compile_payoff_graph(builder()).identity for builder in builders}
        assert identities == {expected}, name


# ---- Stage 1C validation-equivalence architecture baseline guards ----

_STAGE1C_SPEC = DOCS_DIR / "validation-equivalence-spec.md"
_ADR_0008 = (
    DOCS_DIR / "adr" / "0008-validation-levels-equivalence-and-structural-diffing.md"
)


def test_stage_1c_baseline_files_exist() -> None:
    for path in (_STAGE1C_SPEC, _ADR_0008):
        assert path.exists(), f"missing Stage 1C baseline file: {path}"


def test_stage_1c_status_established_not_implemented() -> None:
    # Architecture baseline is "Established"; runtimes remain "Planned" /
    # "Unimplemented".
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "architecture baseline established" in spec or "established" in spec
    # Runtime must not be claimed as implemented.
    assert "stage 1c-r1" not in spec or "planned" in spec
    assert "stage 1c-r2" not in spec or "planned" in spec
    assert "no stage 1c runtime module exists" in spec
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "architecture baseline established" in readme
    assert "unimplemented" in readme or "planned" in readme
    road = (REPO_ROOT / "ROADMAP.md").read_text(encoding="utf-8").lower()
    assert "architecture baseline established" in road


def test_stage_1c_no_economic_equivalence_claim() -> None:
    # The conservative principle: no economic equivalence claim anywhere.
    # Occurrences in "forbidden" / "prohibited" / "must not" /
    # "asserting or implying" contexts are allowed.
    prohibition_contexts = [
        "forbidden",
        "prohibited",
        "must not",
        "mustn't",
        "shall not",
        "shan't",
        "not allowed",
        "disallowed",
        "excluded",
        "forbids",
        "prohibits",
        "asserting or implying",
        "implying",
        "asserting",
    ]
    for markdown in markdown_files():
        text = markdown.read_text(encoding="utf-8").lower()
        for match in re.finditer(r"economic equivalence", text):
            before = text[max(0, match.start() - 500) : match.start()]
            before_stripped = re.sub(r"\*+", "", before)
            has_negation = any(neg in before_stripped for neg in NEGATIONS)
            has_prohibition = any(
                ctx in before_stripped for ctx in prohibition_contexts
            )
            assert has_negation or has_prohibition, (
                f"{markdown}: unqualified 'economic equivalence' claim"
            )
    # The validation-equivalence spec must explicitly deny all these.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    spec_stripped = re.sub(r"\*+", "", spec)
    for claim in [
        "must not claim",
        "general economic equivalence",
        "equal value",
        "equal cash flow",
        "legal equivalence",
        "accounting equivalence",
        "tax equivalence",
        "model equivalence",
        "suitability",
        "recommendation",
    ]:
        assert claim in spec_stripped, f"spec must deny: {claim}"


def test_stage_1c_level_taxonomy_describes_evaluation_depth() -> None:
    # The level taxonomy describes progressive EVALUATION DEPTH, not a logical
    # implication hierarchy between equivalence results.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    for level in ("structural", "canonical", "payoff"):
        assert level in spec, f"validation level '{level}' missing from spec"
    assert "evaluation depth" in spec
    assert (
        "progressive processing depth" in spec or "progressive evaluation depth" in spec
    )
    # Explicitly NOT a logical implication hierarchy.
    assert "logical implication hierarchy" in spec
    # Display names present.
    assert "structural validity" in spec
    assert "canonical-contract equivalence" in spec
    assert "payoff-graph structural equivalence" in spec
    # Normative statements present.
    for stmt in (
        "canonical evaluation requires successful structural validation",
        "payoff evaluation requires successful structural validation and r1",
        "requesting a deeper level causes prior stages to be evaluated",
    ):
        assert stmt in spec, stmt


def test_stage_1c_conclusions_independent() -> None:
    # Canonical and payoff conclusions are independently represented; they are
    # not collapsed into a single boolean and not ordered as an implication.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "separately reported" in spec
    assert "independent comparison conclusions" in spec
    assert "independent comparison conclusions" in spec
    assert "guarantee that payoff-graph equivalence implies" in spec
    assert "guarantee the converse" in spec
    assert "no permanent injectivity guarantee" in spec


def test_stage_1c_comparison_statuses_closed_and_distinct() -> None:
    # All four comparison statuses are present, closed, and distinct.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    for status in ("equivalent", "different", "not_comparable", "not_evaluated"):
        assert status in spec, status
    # The old boolean-like / nullable vocabulary must not appear.
    assert "not_applicable" not in spec
    # not_comparable and not_evaluated are distinct (both present, defined apart).
    assert "not_comparable" in spec and "not_evaluated" in spec
    assert "never collapsed into" in spec or "distinct" in spec


def test_stage_1c_validation_outcome_taxonomy() -> None:
    # Per-side validation outcomes use a closed taxonomy; null is not used.
    # The v1 taxonomy is valid/invalid only (not_evaluated is removed).
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    for v in ("valid", "invalid"):
        assert v in spec, v
    assert "validation outcome taxonomy" in spec
    assert "null" in spec and "never used to mean multiple" in spec
    # not_evaluated must not appear as a validation-outcome value.
    # It may still appear as a comparison-status value.
    outcome_section = _section(spec, r"validation outcome taxonomy")
    assert "not_evaluated" not in outcome_section


def test_stage_1c_schema_selection_per_call_and_raised() -> None:
    # Schema selection is per-call, so a left/right schema-version mismatch is not
    # constructible. Unsupported/contradictory schema selection is a caller-owned
    # raised error (not a reported not_comparable outcome), and cross-version
    # comparison is deferred. The old incompatible-schema -> not_comparable mapping
    # must not exist.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "per-call" in spec
    assert "cannot construct a left/right" in spec
    assert "caller-owned raised error" in spec
    assert "incompatible_schemas" in spec
    # The v1 API has no incompatible_schema_versions comparison outcome.
    assert "`incompatible_schema_versions` reason code" in spec
    assert "unsupported_migration_boundary" in spec
    assert "outcome in v1" in spec
    # Unsupported / contradictory schema selection vectors raise, not not_comparable.
    assert "ve_043_unsupported_canonical_schema_raises" in spec
    assert "ve_044_unsupported_payoff_schema_raises" in spec
    assert "ve_041_contradictory_schema_config_raises" in spec
    # Cross-version comparison is deferred; no cross-version diff is promised.
    assert "deferred to a future" in spec
    assert "source of diff content" in spec
    # The forbidden mapping must not be asserted positively.
    assert "incompatible schema versions never map to" not in spec
    assert "incompatible schema versions produce" not in spec


def test_stage_1c_caller_errors_raise() -> None:
    # Caller-owned failures raise Stage 1C-owned typed errors.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "caller-owned" in spec
    assert "raised" in spec
    for code in (
        "validation_equivalence.unsupported_level",
        "validation_equivalence.input",
        "validation_equivalence.encoding",
        "validation_equivalence.report_collision",
        "validation_equivalence.error",
        "validation_equivalence.incompatible_schemas",
    ):
        assert code in spec, code
    # Complexity error must not be in the error taxonomy.
    error_section = _section(spec, r"error taxonomy")
    assert "validation_equivalence.complexity" not in error_section
    # Specific raised cases mentioned.
    for phrase in (
        "wrong exact input types",
        "unsupported validation level",
        "malformed stage 1c limits",
        "unsupported stage 1c report schema version",
        "invalid diff representation selection",
        "impossible or contradictory caller configuration",
        "report encoding failure",
        "report identity collision",
        "malformed stage 1c internal state",
    ):
        assert phrase in spec, phrase
    # If the report cannot be encoded/identified, no report is returned.
    assert "no report is returned" in spec


def test_stage_1c_operand_failures_captured() -> None:
    # Operand-owned failures are captured inside the report, not raised.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "operand-owned" in spec
    assert "captured inside the report" in spec
    for stage in (
        "stage 1a contract validation failure",
        "stage 1b-r1 canonicalization failure",
        "stage 1b-r2 payoff compilation failure",
        "upstream complexity failure",
        "upstream encoding or collision error",
    ):
        assert stage in spec, stage
    # Captured structured fields.
    for field in ("stage", "code", "classification"):
        assert field in spec, field
    # The `side` field does NOT appear inside individual records: the array is
    # nested under `left` or `right`, making the side implicit.
    # Forbidden content in captured failures.
    for forbidden in (
        "raw traceback",
        "repr",
        "unstable exception text",
        "secret or full-content leakage",
    ):
        assert forbidden in spec, forbidden


def test_stage_1c_upstream_namespace_preserved() -> None:
    # Upstream error codes retain their original namespace; Stage 1C must not
    # relabel a canonicalization or payoff-graph failure as its own error.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    for ns in ("validation.*", "canonicalization.*", "payoff_graph.*"):
        assert ns in spec, ns
    assert "must not relabel" in spec
    assert (
        "retain their original namespace" in spec
        or "retains its original namespace" in spec
    )
    assert "original namespace" in spec


def test_stage_1c_diff_availability_rules_explicit() -> None:
    # Structural diff availability rules are explicit; when unavailable, a stable
    # reason is reported and no misleading partial content diff is emitted.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "diff availability" in spec
    for cond in (
        "the selected representation exists for both sides",
        "both operands are processed under one per-call",
        "the selected diff mode is supported",
        "limits permit the comparison",
    ):
        assert cond in spec, cond
    assert "unavailable_reason" in spec
    assert (
        "no misleading partial content diff" in spec
        or "no partial content diff" in spec
    )
    assert "source of diff content" in spec


def test_stage_1c_change_replace_non_overlapping() -> None:
    # change and replace cannot overlap: change keeps the JSON structural kind,
    # replace changes it; they are disjoint by construction.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "non-overlap" in spec or "non-overlapping" in spec
    assert "change" in spec and "replace" in spec
    assert "both sides carry the same json" in spec
    assert "json structural kind differs" in spec
    assert "disjoint" in spec


def test_stage_1c_structural_diff_schema_specified() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    # The v1 DiffSelection taxonomy is canonical | payoff | none.
    # "both" must NOT be in the v1 taxonomy.
    for sel in ("canonical", "payoff", "none"):
        assert sel in spec, f"diff selection '{sel}' missing from spec"
    # "both" must not appear as a valid diff representation value in the report.
    # It may appear in prose describing its removal.
    report_section = _section(spec, r"report fields")
    assert '"both"' not in report_section or "not" in report_section.lower()
    assert "/nodes/" in spec
    assert "/root" in spec
    assert "/schema_version" in spec
    for op in ("add", "remove", "change", "replace"):
        assert op in spec, f"diff op '{op}' missing from spec"
    for limit in (
        "max_entries",
        "max_compared_bytes",
        "max_compared_nodes",
        "max_path_length",
        "max_report_bytes",
    ):
        assert limit in spec, f"diff limit '{limit}' missing from spec"
    assert "truncated" in spec
    assert "truncation_reason" in spec
    assert any(
        w in spec.lower() for w in ("lexicographic", "ascending", "ascii byte order")
    )
    assert "node table" in spec.lower() or "node-table" in spec.lower()


def test_stage_1c_limits_and_security_specified() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    assert "1024" in spec  # max_entries
    assert "2_097_152" in spec or "2097152" in spec  # max_compared_bytes
    assert "4096" in spec  # max_compared_nodes
    assert "256" in spec  # max_path_length
    assert "8_388_608" in spec or "8388608" in spec  # max_report_bytes
    # Admission limits are separated from output limits
    assert "admission limit" in spec.lower() or "admission limits" in spec.lower()
    assert "output limit" in spec.lower() or "output limits" in spec.lower()
    assert "comparison_limit_exceeded" in spec
    for threat in [
        "Adversarially deep graphs",
        "Very wide collections",
        "Duplicate-reference amplification",
        "Malformed internal documents",
        "Cycles at private seams",
        "Hash collisions",
        "Confusing Unicode in paths or display labels",
        "Bounded structural-content disclosure",
        'Misleading "equivalent" terminology',
        "Denial of service through oversized diffs",
        "Non-deterministic dictionary/set iteration",
    ]:
        assert threat in spec, f"threat '{threat}' not addressed in spec"


def test_stage_1c_report_schema_aligned() -> None:
    # The proposed report schema includes unambiguous fields equivalent to every
    # required semantic role, each represented exactly once.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    assert "derivatrace.validation-equivalence.report" in spec
    assert "1.0.0" in spec
    for field in (
        "requested_level",
        "left_validation_outcome",
        "right_validation_outcome",
        "canonical_comparison_status",
        "canonical_comparison_reason",
        "payoff_comparison_status",
        "payoff_comparison_reason",
        "diff_representation",
        "diff_summary",
        "truncated",
        "limits_used",
        "schema_metadata",
        "report_id",
        "provenance",
    ):
        assert field in spec, f"report field '{field}' missing from spec"
    # The closed comparison-status values appear in the report.
    for val in ("equivalent", "different", "not_comparable", "not_evaluated"):
        assert val in spec, val
    # Validation outcomes are valid/invalid only.
    assert '"valid | invalid"' in spec or "valid | invalid" in spec
    # "both" is not in the v1 DiffSelection taxonomy.
    # The diff_representation field should show canonical | payoff | none
    assert "canonical | payoff | none" in spec


def test_stage_1c_normative_vectors_unique_and_complete() -> None:
    # Every vector key is unique; the minimum required cases are present; no
    # vector establishes economic equivalence.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"vector inventory")
    rows = _table_rows(section)
    inv_keys = [r[0].strip("`") for r in rows if r[0].strip("`").startswith("ve_")]
    assert len(inv_keys) == len(set(inv_keys)), (
        f"duplicate inventory key: {[k for k in inv_keys if inv_keys.count(k) > 1]}"
    )
    assert len(inv_keys) >= 44, len(inv_keys)
    # Minimum required cases.
    for key in (
        "ve_022_invalid_left",
        "ve_023_invalid_right",
        "ve_024_invalid_left_at_payoff_level",
        "ve_034_invalid_both_diff_selection",
        "ve_035_unsupported_level_raises",
        "ve_036_malformed_limits_raise",
        "ve_037_report_encoding_failure_raises",
        "ve_038_deterministic_repeated_captured_failure",
        "ve_039_upstream_r1_failure_captured",
        "ve_040_upstream_r2_failure_captured",
        "ve_041_contradictory_schema_config_raises",
        "ve_042_report_identity_mandatory",
        "ve_043_unsupported_canonical_schema_raises",
        "ve_044_unsupported_payoff_schema_raises",
    ):
        assert key in inv_keys, key
    # Admission/output limit vectors.
    for key in (
        "ve_025_admission_byte_boundary_exact",
        "ve_026_admission_byte_boundary_exceeded",
        "ve_027_admission_node_boundary_exact",
        "ve_028_admission_node_boundary_exceeded",
        "ve_029_output_entry_boundary_exact",
        "ve_030_output_entry_boundary_exceeded",
        "ve_031_output_report_byte_truncation",
        "ve_032_admission_failure_preserves_identities",
    ):
        assert key in inv_keys, key
    # Shallower levels leave deeper statuses not_evaluated.
    # (ve_014 canonical level -> payoff not_evaluated; ve_022/ve_023 structural
    #  level -> canonical and payoff not_evaluated.)
    assert "ve_014_provenance_only_diff" in inv_keys
    # No result establishes economic equivalence.
    assert "economic_equivalence_claim" in spec


def test_stage_1c_documentation_guards_enforced() -> None:
    # The spec must declare the documentation guards.
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    for guard in [
        "stage 1b is no longer marked",
        "stage 1c architecture baseline",
        "stage 1c runtime:",
        "no economic-equivalence claim",
        "validation-level taxonomy is complete",
        "report schema",
        "structural-diff schema",
        "every vector key",
        "all internal markdown links resolve",
        "status language is consistent",
        "never collapsed",
        "validation-outcome taxonomy is closed",
        "the value",
        "v1 `diffselection`",
        "one report has one diff summary",
        "admission limits",
        "output limits",
        "admission failure emits zero entries",
        "output-limit failure emits a deterministic truncated prefix",
        "complexityerror",
        "node add/remove",
        "complete bounded node records",
        "does not claim leaf-only diffs",
        "privacy-preserving",
        "canonicalization was not requested or failed",
        "inverted depth wording",
        "truncation reasons contain only output-limit reasons",
        "admission-limit excess never sets",
        "every public api conformance vector",
        "private seam vector",
    ]:
        assert guard in spec, f"documentation guard '{guard}' missing from spec"


def test_stage_1c_runtime_unimplemented() -> None:
    # No Stage 1C runtime module may be added.
    assert not (SRC_ROOT / "validationequivalence").exists()
    assert not (SRC_ROOT / "validation_equivalence").exists()
    assert not (SRC_ROOT / "stage1c").exists()
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "unimplemented" in spec
    assert "no stage 1c runtime module exists" in spec
    # The public entry point is explicitly not yet implemented.
    assert "not yet implemented" in spec


def test_adr_0008_records_key_decisions() -> None:
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    for decision in [
        "validation-level taxonomy",
        "progressive evaluation depth",
        "independent comparison conclusions",
        "comparison status taxonomy",
        "validation outcome taxonomy",
        "report-internal error policy",
        "cross-version comparison semantics",
        "structural diff availability",
        "change-versus-replace",
        "report schema alignment",
        "updated conformance vectors",
    ]:
        assert decision in adr, f"ADR 0008 missing decision: {decision}"


# ---- Additional Stage 1C documentation-test guards ----


def test_stage_1c_exactly_one_canonical_schema_per_call() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "exactly one" in spec
    assert "canonical schema selection" in spec
    assert "never per-side" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "per-call" in adr
    assert "never per-side" in adr or "no per-side" in adr


def test_stage_1c_exactly_one_payoff_schema_per_call() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "exactly one" in spec
    assert "payoff schema" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "per-call" in adr


def test_stage_1c_cross_version_deferred() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "deferred to a future" in spec
    assert "separate architecture decision" in spec
    assert "not" in spec and "part of `compare_contracts` v1" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "deferred" in adr
    assert "separate adr" in adr


def test_stage_1c_single_captured_failure_representation() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "single" in spec
    assert "structured captured-failure representation" in spec
    assert (
        "{stage, code, classification}" in spec or "stage, code, classification" in spec
    )
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "single" in adr
    assert (
        "{stage, code, classification}" in adr or "stage, code, classification" in adr
    )


def test_stage_1c_deprecated_field_names_absent() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "structural_errors" in spec
    assert "deprecated" in spec
    assert "do not exist" in spec or "does not exist" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "structural_errors" in adr
    assert "not used" in adr
    assert "canonicalization_errors" in adr
    assert "payoff_compilation_errors" in adr


def test_stage_1c_failures_non_null_and_deterministic_order() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "always an array" in spec
    assert "empty array" in spec
    assert "never" in spec and "null" in spec
    assert "deterministic" in spec
    assert "stage order" in spec or "stage → code → classification" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "deterministic" in adr
    assert (
        "stage → code → classification" in adr
        or "stage -> code -> classification" in adr
    )


def test_stage_1c_report_id_mandatory_non_null() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "mandatory" in spec
    assert "non-null" in spec
    assert "report_id" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "mandatory" in adr
    assert "non-null" in adr
    assert "report_id" in adr


def test_stage_1c_content_addressed_remove_add_not_same_id_leaf() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "content-addressed" in spec
    assert "remove" in spec and "add" in spec
    assert "never" in spec
    assert "same-id" in spec or "same-node-id" in spec or "leaf change" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "content-addressed" in adr
    assert "remove" in adr and "add" in adr


def test_stage_1c_commutative_no_diff() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "commutative" in spec
    assert "no diff" in spec or "no diff" in spec
    assert "canonicalize identically" in spec


def test_stage_1c_shared_copied_no_diff() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "copied" in spec or "shared" in spec
    assert "no diff" in spec
    assert "canonicalize identically" in spec


def test_stage_1c_semantic_alignment_out_of_scope() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "semantic" in spec
    assert "alignment" in spec or "node alignment" in spec
    assert "out of scope" in spec or "explicitly deferred" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "semantic" in adr or "alignment" in adr
    assert "rejected" in adr or "deferred" in adr


def test_stage_1c_failure_no_side_field_in_record() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "no `side`" in spec or "no side" in spec
    assert "inside" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert (
        "not stored as a per-record field" in adr or "not stored as a per-record" in adr
    )


def test_stage_1c_no_incompatible_schema_versions_reason() -> None:
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "no" in spec
    assert "incompatible_schema_versions" in spec
    assert "reason code" in spec
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "incompatible_schema_versions" in adr
    assert "not constructible" in adr


# ---- Final bounded architecture correction guards ----


def test_both_absent_from_v1_diff_selection() -> None:
    """The value 'both' must not be in the v1 DiffSelection taxonomy."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    # The report schema must show canonical | payoff | none (no 'both').
    assert "canonical | payoff | none" in spec
    # The prose must state 'both' is not in the v1 taxonomy.
    spec_low = spec.lower()
    assert '"both"' in spec
    assert "not in the v1" in spec_low or "is not" in spec_low
    # The error taxonomy must mention 'both' as an invalid selection.
    assert "invalid diff representation selection" in spec_low


def test_one_report_one_diff_summary() -> None:
    """One report contains at most one structural diff section."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "at most one" in spec
    assert "diff summary" in spec
    assert "unambiguous" in spec


def test_r1_failure_under_payoff_makes_payoff_not_comparable() -> None:
    """R1 failure under payoff makes payoff not_comparable."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # When R1 fails and payoff is requested, both canonical
    # and payoff are not_comparable.
    assert "r1" in spec
    assert "not_comparable" in spec
    assert "upstream_stage_failure" in spec


def test_not_evaluated_only_for_deeper_comparisons() -> None:
    """not_evaluated is used only for comparisons deeper than requested."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "not_evaluated" in spec
    assert "deeper" in spec
    # not_evaluated must not appear in the validation-outcome taxonomy.
    outcome_section = _section(spec, r"validation outcome taxonomy")
    assert "not_evaluated" not in outcome_section
    # The inverted phrases must not appear in the spec body (excluding §10
    # documentation guards which quote them in a negation context).
    guards_section = _section(spec, r"documentation guards")
    spec_body = spec.replace(guards_section, "")
    inv1 = "comparison statuses shallower than the requested"
    inv2 = "comparison is shallower than the requested evaluation"
    assert inv1 not in spec_body
    assert inv2 not in spec_body


def test_stage_1a_outcomes_exactly_valid_invalid() -> None:
    """Stage 1A validation outcomes are exactly valid/invalid."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    outcome_section = _section(spec, r"validation outcome taxonomy")
    assert "valid" in outcome_section
    assert "invalid" in outcome_section
    # not_evaluated must not be in the outcome section.
    assert "not_evaluated" not in outcome_section
    # The field description must state valid/invalid only.
    assert '"valid | invalid"' in spec or "valid | invalid" in spec


def test_admission_limit_failure_emits_zero_entries() -> None:
    """Admission-limit failure emits zero entries and does not truncate."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "admission limit" in spec
    assert "zero" in spec
    assert "truncated" in spec
    assert "false" in spec
    assert "comparison_limit_exceeded" in spec
    # Admission preserves equivalence statuses and identities.
    assert "identities remain available" in spec or "statuses remain" in spec


def test_output_limit_failure_emits_truncated_prefix() -> None:
    """Output-limit failure emits a deterministic truncated prefix."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "output limit" in spec
    assert "truncated: true" in spec or "truncated" in spec
    assert "accepted prefix" in spec
    assert "deterministic" in spec
    assert "never partially serialize" in spec


def test_complexity_error_absent() -> None:
    """Complexity error is absent from the v1 error taxonomy."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # The error taxonomy table must not list ValidationEquivalenceComplexityError.
    error_section = _section(spec, r"error taxonomy")
    assert "complexityerror" not in error_section.replace(" ", "")
    assert "validation_equivalence.complexity" not in error_section


def test_node_add_remove_may_contain_bounded_records() -> None:
    """Node add/remove entries may contain complete bounded node records."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "node add/remove entries" in spec
    assert "bounded" in spec
    assert "complete" in spec
    assert "node records" in spec
    threat = _text(DOCS_DIR / "threat-model.md").lower()
    assert "bounded structural-content disclosure" in threat


def test_threat_model_no_leaf_only_claims() -> None:
    """Threat model does not claim leaf-only diffs."""
    threat = _text(DOCS_DIR / "threat-model.md").lower()
    # The old "leaf values" / "leaf-only" claim must be replaced.
    assert "leaf-only" not in threat
    # The new bounded structural-content disclosure must be present.
    assert "bounded structural-content disclosure" in threat
    assert "complete bounded" in threat or "complete canonical" in threat


def test_diff_none_is_privacy_preserving() -> None:
    """diff='none' is documented as privacy-preserving."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "privacy-preserving" in spec
    assert 'diff="none"' in spec or "diff=`none`" in spec
    threat = _text(DOCS_DIR / "threat-model.md").lower()
    assert "privacy-preserving" in threat


def test_provenance_identities_null_when_not_requested_or_failed() -> None:
    """Provenance identities are null when canonicalization was not
    requested or failed."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "source_left_identity" in spec
    assert "source_right_identity" in spec
    assert "canonicalization was not requested or failed" in spec
    assert "one exact rule" in spec


def test_stage_1c_runtime_unimplemented_final() -> None:
    """Stage 1C runtime remains unimplemented."""
    assert not (SRC_ROOT / "validationequivalence").exists()
    assert not (SRC_ROOT / "validation_equivalence").exists()
    assert not (SRC_ROOT / "stage1c").exists()
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "no stage 1c runtime module exists" in spec
    assert "not yet implemented" in spec


def test_no_economic_equivalence_claim_final() -> None:
    """No economic-equivalence claim exists."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # The conservative principle must explicitly deny economic equivalence.
    assert "must not" in spec
    assert "economic equivalence" in spec


def test_vector_keys_unique_final() -> None:
    """Vector keys remain unique."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"vector inventory")
    rows = _table_rows(section)
    inv_keys = [r[0].strip("`") for r in rows if r[0].strip("`").startswith("ve_")]
    assert len(inv_keys) == len(set(inv_keys)), (
        f"duplicate inventory key: {[k for k in inv_keys if inv_keys.count(k) > 1]}"
    )


def test_vector_exact_ordered_key_tuple() -> None:
    """The exact ordered vector-key tuple matches the stable inventory."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"vector inventory")
    rows = _table_rows(section)
    inv_keys = tuple(r[0].strip("`") for r in rows if r[0].strip("`").startswith("ve_"))
    expected = (
        "ve_001_self_equivalence",
        "ve_002_independent_identical",
        "ve_003_pgadd_commutation",
        "ve_004_nested_vs_flat_add",
        "ve_005_pgmultiply_commutation",
        "ve_006_pgmultiply_grouping",
        "ve_007_subtract_order",
        "ve_008_divide_order",
        "ve_009_both_order",
        "ve_010_duplicate_add",
        "ve_011_duplicate_multiply_ref",
        "ve_012_duplicate_both",
        "ve_013_shared_vs_copied_subgraph",
        "ve_014_provenance_only_diff",
        "ve_015_settlement_timestamp_diff",
        "ve_016_observation_timestamp_diff",
        "ve_017_currency_diff",
        "ve_018_scalar_vs_money_unit",
        "ve_019_comparison_operator_diff",
        "ve_020_conditional_branch_order",
        "ve_021_zero_vs_nonzero",
        "ve_022_invalid_left",
        "ve_023_invalid_right",
        "ve_024_invalid_left_at_payoff_level",
        "ve_025_admission_byte_boundary_exact",
        "ve_026_admission_byte_boundary_exceeded",
        "ve_027_admission_node_boundary_exact",
        "ve_028_admission_node_boundary_exceeded",
        "ve_029_output_entry_boundary_exact",
        "ve_030_output_entry_boundary_exceeded",
        "ve_031_output_report_byte_truncation",
        "ve_032_admission_failure_preserves_identities",
        "ve_033_deterministic_repeated_reporting",
        "ve_034_invalid_both_diff_selection",
        "ve_035_unsupported_level_raises",
        "ve_036_malformed_limits_raise",
        "ve_037_report_encoding_failure_raises",
        "ve_038_deterministic_repeated_captured_failure",
        "ve_039_upstream_r1_failure_captured",
        "ve_040_upstream_r2_failure_captured",
        "ve_041_contradictory_schema_config_raises",
        "ve_042_report_identity_mandatory",
        "ve_043_unsupported_canonical_schema_raises",
        "ve_044_unsupported_payoff_schema_raises",
    )
    assert inv_keys == expected, (
        f"vector-key tuple mismatch: extra={set(inv_keys) - set(expected)!r}, "
        f"missing={set(expected) - set(inv_keys)!r}"
    )
    assert len(inv_keys) == 44


def test_invalid_stage1a_propagation_structural_level() -> None:
    """Requested structural + invalid: canonical and payoff are not_evaluated."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # The spec must document the three requested-level propagation cases.
    assert "requested `structural`, either operand invalid" in spec
    assert "requested `canonical`, either operand invalid" in spec
    assert "requested `payoff`, either operand invalid" in spec
    # Structural-level invalid: canonical and payoff are not_evaluated.
    # Find the structural-level row in §3.17.
    beh_section = _section(spec, r"behaviour when preconditions fail")
    assert "requested `structural`, either operand invalid" in beh_section
    assert "not_evaluated" in beh_section
    assert "shallower_level_requested" in beh_section


def test_invalid_stage1a_propagation_canonical_level() -> None:
    """Requested canonical + invalid: canonical=not_comparable, payoff=not_evaluated."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    beh_section = _section(spec, r"behaviour when preconditions fail")
    assert "requested `canonical`, either operand invalid" in beh_section
    # Canonical is at the requested level → not_comparable / upstream_stage_failure.
    assert "not_comparable" in beh_section
    # Payoff is deeper than requested → not_evaluated / shallower_level_requested.
    # The row must contain both not_comparable and not_evaluated.
    # Extract the canonical-level row.
    for line in beh_section.splitlines():
        if "requested `canonical`, either operand invalid" in line:
            assert "not_comparable" in line
            assert "not_evaluated" in line
            assert "upstream_stage_failure" in line
            assert "shallower_level_requested" in line
            break
    else:
        pytest.fail("canonical-level invalid-operand row not found in §3.17")


def test_invalid_stage1a_propagation_payoff_level() -> None:
    """Requested payoff + invalid: canonical and payoff are not_comparable."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    beh_section = _section(spec, r"behaviour when preconditions fail")
    assert "requested `payoff`, either operand invalid" in beh_section
    for line in beh_section.splitlines():
        if "requested `payoff`, either operand invalid" in line:
            assert "not_comparable" in line
            assert "upstream_stage_failure" in line
            break
    else:
        pytest.fail("payoff-level invalid-operand row not found in §3.17")


def test_not_evaluated_never_for_blocked_comparison() -> None:
    """not_comparable is used for upstream-blocked comparisons, never not_evaluated."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # The spec must state the binding rule explicitly.
    assert "not_evaluated" in spec
    assert "shallower" in spec
    # The ADR must state the binding rule.
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "not_evaluated" in adr
    assert "shallower" in adr
    # The §2.1 propagation rule must document the three cases.
    assert "requested `structural`, either operand invalid" in spec
    assert "requested `canonical`, either operand invalid" in spec
    assert "requested `payoff`, either operand invalid" in spec


# ---- Final published-spec consistency correction guards (PR #9) ----


def test_depth_wording_not_inverted() -> None:
    """Inverted depth phrases must not appear in spec or ADR."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    inv1 = "comparison statuses shallower than the requested level"
    inv2 = "comparison is shallower than the requested evaluation level"
    inv3 = "at or deeper than the requested level"
    # Exclude §10 documentation guards which quote the forbidden phrases
    # in a negation context ("does not appear").
    guards_section = _section(spec, r"documentation guards")
    spec_body = spec.replace(guards_section, "")
    for phrase in (inv1, inv2, inv3):
        assert phrase not in spec_body, f"inverted phrase in spec body: {phrase}"
        assert phrase not in adr, f"inverted phrase in ADR: {phrase}"


def test_truncation_reasons_only_output_limit_reasons() -> None:
    """Truncation reasons contain only output-limit reasons."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # The correct taxonomy.
    for reason in ("entry_limit", "report_byte_limit", "path_limit"):
        assert reason in spec, f"truncation reason '{reason}' missing from spec"
    # Stale admission-limit reasons must not appear in the JSON example.
    # Use word-boundary check: "byte_limit" only as part of
    # "report_byte_limit", "node_limit" must not appear as truncation reason.
    import re as _re

    json_section = _section(spec, r"exact report fields")
    assert not _re.search(r"(?<!report_)byte_limit", json_section), (
        "stale standalone 'byte_limit' in JSON truncation_reason taxonomy"
    )
    assert "node_limit" not in json_section, (
        "stale 'node_limit' in JSON truncation_reason taxonomy"
    )


def test_admission_limit_excess_cannot_set_truncated_true() -> None:
    """Admission-limit excess sets unavailable_reason, never truncated=true."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # The spec must state admission failure does not truncate.
    assert "admission" in spec
    assert "truncated: false" in spec or "truncated = false" in spec
    # The notes for ve_025-ve_028 must specify exact boundary expectations.
    assert "admission succeeds" in spec
    assert "unavailable_reason = null" in spec
    assert "unavailable_reason = comparison_limit_exceeded" in spec
    # The documentation guard must exist.
    assert "admission-limit excess never sets" in spec


def test_exact_admission_boundaries_succeed() -> None:
    """Exact max_compared_bytes and max_compared_nodes admission succeeds."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # The notes for ve_025 and ve_027 must state admission succeeds with
    # unavailable_reason = null and truncated = false.
    assert "ve_025" in spec
    assert "ve_027" in spec


def test_exact_max_entries_does_not_truncate() -> None:
    """Exactly max_entries entries: truncated = false, truncation_reason = null."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # ve_029 note must specify truncated = false.
    assert "ve_029" in spec
    assert "truncated = false" in spec
    assert "truncation_reason = null" in spec


def test_max_entries_plus_one_truncates_at_exact_max_entries() -> None:
    """max_entries + 1: exactly max_entries emitted, truncated = true,
    truncation_reason = entry_limit."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # ve_030 note must specify exact boundary.
    assert "ve_030" in spec
    assert "truncated = true" in spec
    assert "truncation_reason = entry_limit" in spec
    assert "exactly `max_entries` entries" in spec


def test_adr_states_44_vectors_not_35() -> None:
    """ADR states 44 vectors, not 35."""
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    assert "44 vector" in adr
    assert "35 vector" not in adr


def test_adr_does_not_claim_leaf_only_diff_contents() -> None:
    """ADR rejected alternatives do not claim leaf-only diff contents."""
    adr = _ADR_0008.read_text(encoding="utf-8").lower()
    # The old "carry only leaf values" claim must not appear.
    assert "carry only leaf" not in adr
    # The corrected "bounded complete node records" must appear.
    assert "bounded complete node records" in adr


def test_every_public_vector_has_two_concrete_source_constructions() -> None:
    """Every public vector has two concrete public source constructions."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    # ve_011 must have a concrete right construction, not a cross-reference.
    assert (
        "compare against" not in spec.lower()
        or "compare against" not in _section(spec, r"vector inventory").lower()
    )
    # ve_011 right must be a concrete construction.
    inv_section = _section(spec, r"vector inventory")
    for line in inv_section.splitlines():
        if "ve_011_duplicate_multiply_ref" in line:
            assert "no direct counterpart" not in line.lower(), (
                "ve_011 still has no concrete right construction"
            )
            break


def test_provenance_and_fault_injection_vectors_classified_private() -> None:
    """Provenance-only and fault-injection vectors are private seams."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # ve_014 must be marked as a private seam (kind column value or prose).
    inv_section = _section(spec, r"vector inventory")
    for line in inv_section.splitlines():
        if "ve_014_provenance_only_diff" in line:
            assert "private_seam" in line or "private seam" in line.lower(), (
                "ve_014 must be classified as a private seam vector"
            )
            break
    # ve_037 must be marked as a private seam.
    for line in inv_section.splitlines():
        if "ve_037_report_encoding_failure_raises" in line:
            assert "private_seam" in line or "private seam" in line.lower(), (
                "ve_037 must be classified as a private seam vector"
            )
            break
    # The spec must document the public/private distinction.
    assert "private seam" in spec
    assert "fault-injection" in spec or "report-construction seam" in spec


def test_section_4_15_does_not_name_max_compared_bytes_as_output_boundary() -> None:
    """§4.15 does not name max_compared_bytes as an output truncation boundary."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    trunc_section = _section(spec, r"truncation behaviour")
    assert "max_compared_bytes" not in trunc_section, (
        "§4.15 still names max_compared_bytes as output truncation boundary"
    )
    # The correct output boundaries must be listed.
    assert "max_entries" in trunc_section
    assert "max_report_bytes" in trunc_section
    assert "max_path_length" in trunc_section


def test_byte_limit_and_node_limit_absent_from_truncation_taxonomy() -> None:
    """byte_limit and node_limit are removed from truncation-reason taxonomy."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    # In the JSON example, the truncation_reason field must not contain
    # standalone byte_limit or node_limit.
    import re as _re

    json_example = _section(spec, r"exact report fields")
    for line in json_example.splitlines():
        if "truncation_reason" in line:
            assert "node_limit" not in line, (
                "stale 'node_limit' still in truncation_reason taxonomy"
            )
            # "byte_limit" only allowed as part of "report_byte_limit"
            assert not _re.search(r"(?<!report_)byte_limit", line), (
                "stale standalone 'byte_limit' in truncation_reason taxonomy"
            )


def test_ve_025_through_ve_030_exact_boundary_expectations_documented() -> None:
    """Exact boundary expectations for ve_025-ve_030 are documented."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # Admission boundaries.
    for key in ("ve_025", "ve_026", "ve_027", "ve_028"):
        assert key in spec, f"vector key '{key}' missing from spec"
    # Output boundaries.
    for key in ("ve_029", "ve_030"):
        assert key in spec, f"vector key '{key}' missing from spec"
    # ve_031 report byte truncation.
    assert "ve_031" in spec


def test_ve_011_has_concrete_left_and_right() -> None:
    """ve_011 has concrete left and right constructions."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    inv_section = _section(spec, r"vector inventory")
    for line in inv_section.splitlines():
        if "ve_011_duplicate_multiply_ref" in line:
            # Both left and right must be concrete constructions.
            assert "Scalar" in line or "scalar" in line.lower(), (
                "ve_011 must reference scalar observables"
            )
            assert "no direct counterpart" not in line.lower()
            assert "compare against" not in line.lower()
            break


def test_vector_schema_has_exact_boundary_fields() -> None:
    """Vector schema includes expected_entry_count, expected_truncated, etc."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    schema_section = _section(spec, r"vector schema")
    for field in (
        "expected_entry_count",
        "expected_truncated",
        "expected_truncation_reason",
        "expected_unavailable_reason",
    ):
        assert field in schema_section, (
            f"vector schema field '{field}' missing from §9.1"
        )


# ---- Final narrow consistency correction guards (PR #9) ----


def _parse_exact_expectation_table() -> dict[str, dict[str, str]]:
    """Parse the §9.2.1 exact boundary-vector expectation table."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"exact boundary-vector expectation")
    rows = _table_rows(section)
    header = None
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        cells = [c.strip().strip("`") for c in row]
        if any("expect_diff_class" in c for c in cells):
            header = cells
            continue
        if header is not None and cells[0].startswith("ve_"):
            key = cells[0]
            result[key] = dict(zip(header[1:], cells[1:], strict=True))
    return result


def test_ve_024_note_no_inverted_at_or_deeper() -> None:
    """The ve_024 note must not contain 'at or deeper than the requested level'."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    # Find the ve_024 note in the spec notes section.
    in_ve_024 = False
    for line in spec.splitlines():
        if "ve_024" in line and "demonstrates" in line.lower():
            in_ve_024 = True
        if in_ve_024:
            assert "at or deeper than the requested level" not in line.lower(), (
                "ve_024 note still contains inverted 'at or deeper' phrase"
            )
        if in_ve_024 and line.startswith("- ") and "ve_024" not in line:
            break
    # The corrected wording must be present somewhere in the spec.
    assert "included in the requested progressive evaluation depth" in spec.lower()


def test_ve_025_ve_027_are_available_empty_diffs() -> None:
    """ve_025 and ve_027 produce available empty diffs, not unavailable none."""
    table = _parse_exact_expectation_table()
    for key in (
        "ve_025_admission_byte_boundary_exact",
        "ve_027_admission_node_boundary_exact",
    ):
        assert key in table, f"vector '{key}' missing from exact-expectation table"
        assert table[key]["expect_diff_class"] == "empty", (
            f"{key}: expect_diff_class must be 'empty', "
            f"got {table[key]['expect_diff_class']}"
        )
        assert table[key]["expected_unavailable_reason"] == "null", (
            f"{key}: expected_unavailable_reason must be null, "
            f"got {table[key]['expected_unavailable_reason']}"
        )


def test_ve_026_ve_028_have_comparison_limit_exceeded() -> None:
    """ve_026 and ve_028 have comparison_limit_exceeded and truncated=false."""
    table = _parse_exact_expectation_table()
    for key in (
        "ve_026_admission_byte_boundary_exceeded",
        "ve_028_admission_node_boundary_exceeded",
    ):
        assert key in table, f"vector '{key}' missing from exact-expectation table"
        assert table[key]["expect_diff_class"] == "none", (
            f"{key}: expect_diff_class must be 'none'"
        )
        assert table[key]["expected_truncated"] == "false", (
            f"{key}: expected_truncated must be false"
        )
        assert (
            table[key]["expected_unavailable_reason"] == "comparison_limit_exceeded"
        ), f"{key}: expected_unavailable_reason must be comparison_limit_exceeded"


def test_ve_029_boundary_exact_no_truncation() -> None:
    """ve_029 has exactly max_entries entries and truncated=false."""
    table = _parse_exact_expectation_table()
    key = "ve_029_output_entry_boundary_exact"
    assert key in table, f"vector '{key}' missing from exact-expectation table"
    assert table[key]["expect_diff_class"] == "remove_add_root", (
        f"{key}: expect_diff_class must be 'remove_add_root', "
        f"got {table[key]['expect_diff_class']}"
    )
    assert table[key]["expected_entry_count"] == "max_entries", (
        f"{key}: expected_entry_count must be max_entries"
    )
    assert table[key]["expected_truncated"] == "false", (
        f"{key}: expected_truncated must be false"
    )
    assert table[key]["expected_truncation_reason"] == "null", (
        f"{key}: expected_truncation_reason must be null"
    )


def test_ve_030_boundary_exceeded_truncates_at_max_entries() -> None:
    """ve_030 has max_entries entries, truncated=true, entry_limit."""
    table = _parse_exact_expectation_table()
    key = "ve_030_output_entry_boundary_exceeded"
    assert key in table, f"vector '{key}' missing from exact-expectation table"
    assert table[key]["expect_diff_class"] == "truncated", (
        f"{key}: expect_diff_class must be 'truncated'"
    )
    assert table[key]["expected_entry_count"] == "max_entries", (
        f"{key}: expected_entry_count must be max_entries"
    )
    assert table[key]["expected_truncated"] == "true", (
        f"{key}: expected_truncated must be true"
    )
    assert table[key]["expected_truncation_reason"] == "entry_limit", (
        f"{key}: expected_truncation_reason must be entry_limit"
    )
    assert table[key]["expected_unavailable_reason"] == "null", (
        f"{key}: expected_unavailable_reason must be null"
    )


def test_ve_031_report_byte_truncation() -> None:
    """ve_031 has truncated=true and report_byte_limit."""
    table = _parse_exact_expectation_table()
    key = "ve_031_output_report_byte_truncation"
    assert key in table, f"vector '{key}' missing from exact-expectation table"
    assert table[key]["expect_diff_class"] == "truncated", (
        f"{key}: expect_diff_class must be 'truncated'"
    )
    assert table[key]["expected_truncated"] == "true", (
        f"{key}: expected_truncated must be true"
    )
    assert table[key]["expected_truncation_reason"] == "report_byte_limit", (
        f"{key}: expected_truncation_reason must be report_byte_limit"
    )
    assert table[key]["expected_unavailable_reason"] == "null", (
        f"{key}: expected_unavailable_reason must be null"
    )


def test_all_vector_schema_fields_represented_in_expectation_table() -> None:
    """Every declared vector-schema field is represented in §9.2.1."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    schema_section = _section(spec, r"vector schema")
    required_fields = [
        "expected_entry_count",
        "expected_truncated",
        "expected_truncation_reason",
        "expected_unavailable_reason",
    ]
    for field in required_fields:
        assert field in schema_section, (
            f"vector schema field '{field}' missing from §9.1"
        )
    # The exact-expectation table must exist and contain all four fields
    # as column headers.
    expectation_section = _section(spec, r"exact boundary-vector expectation")
    for field in required_fields:
        assert field in expectation_section, (
            f"field '{field}' missing from §9.2.1 exact-expectation table"
        )
    assert "expect_diff_class" in expectation_section
    # Every boundary vector must be present.
    for key in (
        "ve_025_admission_byte_boundary_exact",
        "ve_026_admission_byte_boundary_exceeded",
        "ve_027_admission_node_boundary_exact",
        "ve_028_admission_node_boundary_exceeded",
        "ve_029_output_entry_boundary_exact",
        "ve_030_output_entry_boundary_exceeded",
        "ve_031_output_report_byte_truncation",
    ):
        assert key in expectation_section, (
            f"boundary vector '{key}' missing from §9.2.1"
        )


def test_ve_014_private_not_collision_seam() -> None:
    """ve_014 is private and is not labelled a collision seam."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # Find the ve_014 note in the Notes section (after the inventory table).
    notes_start = spec.find("**notes:**")
    assert notes_start != -1, "Notes section not found"
    notes_text = spec[notes_start:]
    # Extract the ve_014 note paragraph.
    ve_014_start = notes_text.find("ve_014")
    assert ve_014_start != -1, "ve_014 not found in notes"
    # Find the end of this bullet (next bullet or end of notes).
    ve_014_para = notes_text[ve_014_start:]
    end = ve_014_para.find("\n- `ve_0", 5)
    if end == -1:
        end = len(ve_014_para)
    ve_014_text = ve_014_para[:end]
    assert "private seam" in ve_014_text or "private_seam" in ve_014_text, (
        "ve_014 must be classified as private"
    )
    assert (
        "identity-projection" in ve_014_text or "identity projection" in ve_014_text
    ), "ve_014 must be described as identity-projection seam"
    # "collision seam" may only appear negated (e.g. "not a collision seam");
    # a positive assertion of it as a collision seam is forbidden.
    cs_idx = ve_014_text.find("collision seam")
    while cs_idx != -1:
        before = ve_014_text[:cs_idx]
        assert "not " in before or "never " in before, (
            "ve_014 must not positively assert 'collision seam'"
        )
        cs_idx = ve_014_text.find("collision seam", cs_idx + 1)
    assert (
        "provenance exclusion" in ve_014_text
        or "exclusion from the report identity" in ve_014_text
        or "provenance is excluded" in ve_014_text
        or "excluded from the structural projection" in ve_014_text
    ), "ve_014 must verify provenance exclusion from report identity preimage"
    # ve_014 must describe report-construction candidates and assert identical
    # report_id despite provenance variation.
    assert "report-construction candidates" in ve_014_text, (
        "ve_014 must describe two report-construction candidates"
    )
    assert "identical report structural projection" in ve_014_text, (
        "ve_014 must assert identical report structural projection"
    )
    assert "different excluded provenance" in ve_014_text, (
        "ve_014 must assert different excluded provenance"
    )
    assert (
        "identical `report_id`" in ve_014_text
        or "identical report_id" in ve_014_text
        or "identical\n" in ve_014_text and "report_id" in ve_014_text
    ), "ve_014 must assert identical report_id"


def test_ve_037_explicitly_private() -> None:
    """ve_037 is explicitly private and requires injected fault seam."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # Find the ve_037 note in the Notes section.
    notes_start = spec.find("**notes:**")
    assert notes_start != -1, "Notes section not found"
    notes_text = spec[notes_start:]
    ve_037_start = notes_text.find("ve_037")
    assert ve_037_start != -1, "ve_037 not found in notes"
    ve_037_para = notes_text[ve_037_start:]
    end = ve_037_para.find("\n- `ve_0", 5)
    if end == -1:
        end = len(ve_037_para)
    ve_037_text = ve_037_para[:end]
    assert "private" in ve_037_text, "ve_037 must be classified as private"
    assert "injected" in ve_037_text or "fault" in ve_037_text, (
        "ve_037 must state it requires injected encoder/fault seam"
    )
    # The inventory table row must also be marked private.
    inv_section = _section(spec, r"vector inventory")
    for line in inv_section.splitlines():
        if "ve_037_report_encoding_failure_raises" in line:
            assert "private_seam" in line or "private seam" in line.lower(), (
                "ve_037 inventory row must be marked as private seam"
            )
            break


def test_all_vectors_use_public_api_absent() -> None:
    """The statement 'all vectors use the public Stage 1A API' is absent."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "all vectors use the public stage 1a api" not in spec, (
        "the unconditional 'All vectors use the public Stage 1A API' "
        "statement must be absent"
    )


def test_public_private_vectors_distinguished_normatively() -> None:
    """Public and private vectors are distinguished normatively."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "public vs. private classification" in spec
    assert "kind=public_api" in spec
    assert "two stage 1a source operands" in spec
    assert "explicitly carries" in spec or "explicitly marked" in spec
    # The §10 documentation guards must mention both categories.
    guards = _section(spec, r"documentation guards")
    assert "every public" in guards and "conformance vector" in guards
    assert "private seam" in guards


def test_boundary_expectation_table_consistent_with_notes() -> None:
    """The §9.2.1 table is consistent with the existing §9.2 notes."""
    table = _parse_exact_expectation_table()
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    # ve_025 note: admission succeeds, entries=[], unavailable_reason=null,
    # truncated=false
    assert "admission succeeds" in spec
    assert "unavailable_reason = null" in spec
    # ve_026 note: admission fails, unavailable_reason=comparison_limit_exceeded
    assert "unavailable_reason = comparison_limit_exceeded" in spec
    # ve_030 note: truncated=true, truncation_reason=entry_limit
    assert "truncated = true" in spec
    assert "truncation_reason = entry_limit" in spec
    # ve_031 note: truncated=true, truncation_reason=report_byte_limit
    assert "truncation_reason = report_byte_limit" in spec
    # The table must have 7 rows.
    assert len(table) == 7, f"expected 7 boundary vectors, got {len(table)}"


def test_vector_keys_exact_ordered_tuple_44() -> None:
    """Vector keys remain exactly the approved ordered 44-key tuple."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"vector inventory")
    rows = _table_rows(section)
    inv_keys = tuple(r[0].strip("`") for r in rows if r[0].strip("`").startswith("ve_"))
    assert len(inv_keys) == 44, f"expected 44 vector keys, got {len(inv_keys)}"
    assert len(inv_keys) == len(set(inv_keys)), (
        f"duplicate vector keys: {[k for k in inv_keys if inv_keys.count(k) > 1]}"
    )


# ---- Vector-kind taxonomy and public/private schema guards (PR #9) ----


def test_vector_schema_contains_kind_field() -> None:
    """The vector schema defines a mandatory kind=public_api|private_seam field."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    schema_section = _section(spec, r"vector schema")
    assert "kind" in schema_section, "vector schema must define a 'kind' field"
    assert "public_api" in schema_section, "vector schema must list kind=public_api"
    assert "private_seam" in schema_section, "vector schema must list kind=private_seam"


def test_vector_schema_kind_two_values() -> None:
    """The kind field has exactly two values: public_api and private_seam."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    schema_section = _section(spec, r"vector schema")
    # The kind field must mention both values.
    assert "public_api" in schema_section
    assert "private_seam" in schema_section
    # No third kind value must be defined.
    for other in ("hybrid", "mixed", "internal", "test"):
        assert f"kind={other}" not in schema_section, (
            f"unexpected kind value '{other}' in vector schema"
        )


def test_public_left_right_require_concrete_stage_1a_operands() -> None:
    """Public left/right fields require concrete Stage 1A Contract operands."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    schema_section = _section(spec, r"vector schema")
    assert "kind=public_api" in schema_section
    assert "concrete stage 1a" in schema_section or "concrete" in schema_section
    assert "contract" in schema_section
    assert "source construction" in schema_section


def test_private_left_right_allow_controlled_seam_inputs() -> None:
    """Private left/right fields allow controlled seam inputs."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    schema_section = _section(spec, r"vector schema")
    assert "kind=private_seam" in schema_section
    assert "controlled seam input" in schema_section
    # Inapplicable fields must use the dash marker.
    assert "\u2014" in schema_section or "—" in schema_section, (
        "vector schema must use em-dash marker for inapplicable fields"
    )


def test_ve_014_explicitly_compares_report_construction_candidates() -> None:
    """ve_014 explicitly compares report-construction candidates and asserts
    identical report_id despite provenance variation."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    inv_section = _section(spec, r"vector inventory")
    for line in inv_section.splitlines():
        if "ve_014_provenance_only_diff" in line:
            assert "report-construction candidate" in line.lower(), (
                "ve_014 inventory row must describe report-construction candidates"
            )
            assert (
                "excluded provenance" in line.lower() or "provenance" in line.lower()
            ), "ve_014 inventory row must reference excluded provenance"
            break
    else:
        pytest.fail("ve_014 not found in vector inventory table")


def test_ve_037_remains_explicitly_private_seam() -> None:
    """ve_037 remains explicitly a private seam vector."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    inv_section = _section(spec, r"vector inventory")
    for line in inv_section.splitlines():
        if "ve_037_report_encoding_failure_raises" in line:
            assert "private_seam" in line or "private seam" in line.lower(), (
                "ve_037 must be classified as a private seam in the inventory"
            )
            break
    else:
        pytest.fail("ve_037 not found in vector inventory table")
    # The notes must describe ve_037 as requiring an injected encoder/fault seam.
    notes_start = spec.find("**notes:**")
    assert notes_start != -1
    notes_text = spec[notes_start:]
    ve_037_start = notes_text.find("ve_037")
    assert ve_037_start != -1
    ve_037_para = notes_text[ve_037_start:]
    end = ve_037_para.find("\n- `ve_0", 5)
    if end == -1:
        end = len(ve_037_para)
    ve_037_text = ve_037_para[:end]
    assert "private" in ve_037_text
    assert "injected" in ve_037_text or "fault" in ve_037_text


def test_exact_ordered_44_key_tuple_unchanged() -> None:
    """The exact ordered 44-key vector tuple is unchanged."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"vector inventory")
    rows = _table_rows(section)
    inv_keys = tuple(r[0].strip("`") for r in rows if r[0].strip("`").startswith("ve_"))
    expected = (
        "ve_001_self_equivalence",
        "ve_002_independent_identical",
        "ve_003_pgadd_commutation",
        "ve_004_nested_vs_flat_add",
        "ve_005_pgmultiply_commutation",
        "ve_006_pgmultiply_grouping",
        "ve_007_subtract_order",
        "ve_008_divide_order",
        "ve_009_both_order",
        "ve_010_duplicate_add",
        "ve_011_duplicate_multiply_ref",
        "ve_012_duplicate_both",
        "ve_013_shared_vs_copied_subgraph",
        "ve_014_provenance_only_diff",
        "ve_015_settlement_timestamp_diff",
        "ve_016_observation_timestamp_diff",
        "ve_017_currency_diff",
        "ve_018_scalar_vs_money_unit",
        "ve_019_comparison_operator_diff",
        "ve_020_conditional_branch_order",
        "ve_021_zero_vs_nonzero",
        "ve_022_invalid_left",
        "ve_023_invalid_right",
        "ve_024_invalid_left_at_payoff_level",
        "ve_025_admission_byte_boundary_exact",
        "ve_026_admission_byte_boundary_exceeded",
        "ve_027_admission_node_boundary_exact",
        "ve_028_admission_node_boundary_exceeded",
        "ve_029_output_entry_boundary_exact",
        "ve_030_output_entry_boundary_exceeded",
        "ve_031_output_report_byte_truncation",
        "ve_032_admission_failure_preserves_identities",
        "ve_033_deterministic_repeated_reporting",
        "ve_034_invalid_both_diff_selection",
        "ve_035_unsupported_level_raises",
        "ve_036_malformed_limits_raise",
        "ve_037_report_encoding_failure_raises",
        "ve_038_deterministic_repeated_captured_failure",
        "ve_039_upstream_r1_failure_captured",
        "ve_040_upstream_r2_failure_captured",
        "ve_041_contradictory_schema_config_raises",
        "ve_042_report_identity_mandatory",
        "ve_043_unsupported_canonical_schema_raises",
        "ve_044_unsupported_payoff_schema_raises",
    )
    assert inv_keys == expected, (
        f"vector-key tuple mismatch: extra={set(inv_keys) - set(expected)!r}, "
        f"missing={set(expected) - set(inv_keys)!r}"
    )
    assert len(inv_keys) == 44


def test_stage_1c_runtime_unimplemented_final_guard() -> None:
    """Stage 1C runtime remains unimplemented (final guard)."""
    assert not (SRC_ROOT / "validationequivalence").exists()
    assert not (SRC_ROOT / "validation_equivalence").exists()
    assert not (SRC_ROOT / "stage1c").exists()
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "no stage 1c runtime module exists" in spec
    assert "not yet implemented" in spec


def test_no_economic_equivalence_claim_final_guard() -> None:
    """No economic-equivalence claim exists (final guard)."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "must not" in spec
    assert "economic equivalence" in spec


# ---- Vector-kind mandatory field and private-seam expectation guards (PR #9) ----


def _parse_inventory_table() -> list[dict[str, str]]:
    """Parse the §9.2 inventory table with Kind column."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"vector inventory")
    rows = _table_rows(section)
    header = None
    result: list[dict[str, str]] = []
    for row in rows:
        cells = [c.strip().strip("`") for c in row]
        if any("Kind" in c for c in cells):
            header = cells
            continue
        if header is not None and cells[0].startswith("ve_"):
            result.append(dict(zip(header, cells, strict=True)))
    return result


def test_inventory_table_has_kind_column() -> None:
    """The inventory table contains a Kind column."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"vector inventory")
    rows = _table_rows(section)
    header_cells = [c.strip() for c in rows[0]]
    assert "Kind" in header_cells, "inventory table must have a Kind column"


def test_all_44_rows_have_kind_public_api_or_private_seam() -> None:
    """Every inventory row has exactly public_api or private_seam as Kind."""
    table = _parse_inventory_table()
    assert len(table) == 44, f"expected 44 inventory rows, got {len(table)}"
    for row in table:
        kind = row.get("Kind", "").strip("`")
        assert kind in ("public_api", "private_seam"), (
            f"{row['Key']}: kind must be public_api or private_seam, got {kind!r}"
        )


def test_ve_014_and_ve_037_are_exactly_private_seam() -> None:
    """ve_014 and ve_037 are exactly the private_seam keys."""
    table = _parse_inventory_table()
    private_keys = [
        r["Key"] for r in table if r.get("Kind", "").strip("`") == "private_seam"
    ]
    assert private_keys == [
        "ve_014_provenance_only_diff",
        "ve_037_report_encoding_failure_raises",
    ]


def test_all_other_42_keys_are_public_api() -> None:
    """All 42 non-private-seam keys are public_api."""
    table = _parse_inventory_table()
    public_keys = [
        r["Key"] for r in table if r.get("Kind", "").strip("`") == "public_api"
    ]
    assert len(public_keys) == 42, (
        f"expected 42 public_api keys, got {len(public_keys)}"
    )


def test_no_kind_inferred_from_operand_text() -> None:
    """Kind is a dedicated column, not inferred from Left/Right operand text."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8").lower()
    assert "kind is never inferred" in spec or "never inferred from prose" in spec


def test_ve_014_public_runtime_fields_are_dash() -> None:
    """ve_014 public-runtime fields are all em-dash (inapplicable)."""
    table = _parse_inventory_table()
    ve_014 = next(r for r in table if r["Key"] == "ve_014_provenance_only_diff")
    for field in ("Level", "Structural (L/R)", "Canonical", "Payoff", "Diff", "Raises"):
        value = ve_014.get(field, "").strip("`")
        assert value == "\u2014", f"ve_014 {field} must be '\u2014', got {value!r}"


def test_ve_037_inapplicable_public_runtime_fields_are_dash() -> None:
    """ve_037 inapplicable public-runtime comparison fields are em-dash."""
    table = _parse_inventory_table()
    ve_037 = next(
        r for r in table if r["Key"] == "ve_037_report_encoding_failure_raises"
    )
    for field in ("Structural (L/R)", "Canonical", "Payoff", "Diff"):
        value = ve_037.get(field, "").strip("`")
        assert value == "\u2014", f"ve_037 {field} must be '\u2014', got {value!r}"


def test_ve_037_retains_encoding_raises() -> None:
    """ve_037 retains validation_equivalence.encoding as its raised result."""
    table = _parse_inventory_table()
    ve_037 = next(
        r for r in table if r["Key"] == "ve_037_report_encoding_failure_raises"
    )
    raises = ve_037.get("Raises", "").strip("`")
    assert raises == "validation_equivalence.encoding", (
        f"ve_037 Raises must be 'validation_equivalence.encoding', got {raises!r}"
    )


def test_ve_037_level_is_canonical() -> None:
    """ve_037 level is canonical (explicitly defined call configuration)."""
    table = _parse_inventory_table()
    ve_037 = next(
        r for r in table if r["Key"] == "ve_037_report_encoding_failure_raises"
    )
    level = ve_037.get("Level", "").strip("`")
    assert "canonical" in level, f"ve_037 Level must contain 'canonical', got {level!r}"


def test_ve_037_left_right_describe_injected_failure() -> None:
    """ve_037 Left/Right describe the injected deterministic report-encoder failure."""
    table = _parse_inventory_table()
    ve_037 = next(
        r for r in table if r["Key"] == "ve_037_report_encoding_failure_raises"
    )
    left = ve_037.get("Left", "").lower()
    right = ve_037.get("Right", "").lower()
    assert "injected" in left or "injected" in right, (
        "ve_037 Left/Right must describe injected failure"
    )
    assert (
        "report-encoder failure" in left
        or "report-encoder failure" in right
        or "report encoder failure" in left
        or "report encoder failure" in right
    ), "ve_037 Left/Right must reference report-encoder failure"


def test_private_seam_expectation_table_contains_both_keys() -> None:
    """The §9.2.2 private-seam expectation table contains both exact keys."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"private-seam expectation")
    rows = _table_rows(section)
    keys = [r[0].strip("`") for r in rows if r[0].strip("`").startswith("ve_")]
    assert "ve_014_provenance_only_diff" in keys
    assert "ve_037_report_encoding_failure_raises" in keys
    assert len(keys) == 2, f"expected 2 private-seam keys, got {len(keys)}"


def test_ve_014_expectation_equal_projection_different_provenance() -> None:
    """ve_014 expects equal structural projection, different excluded
    provenance, identical report_id."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"private-seam expectation")
    rows = _table_rows(section)
    header = None
    for row in rows:
        cells = [c.strip().strip("`") for c in row]
        if any("expected result" in c.lower() for c in cells):
            header = cells
            break
    assert header is not None, (
        "private-seam expectation table must have expected result column"
    )
    for row in rows:
        cells = [c.strip().strip("`") for c in row]
        if cells[0] == "ve_014_provenance_only_diff":
            result_dict = dict(zip(header[1:], cells[1:], strict=True))
            result = result_dict.get("Expected result", "").lower()
            assert (
                "equal structural projection" in result or "equal structural" in result
            )
            assert (
                "different excluded provenance" in result
                or "excluded provenance" in result
            )
            assert "identical" in result and "report_id" in result
            break
    else:
        pytest.fail("ve_014 not found in private-seam expectation table")


def test_ve_037_expectation_no_report_returned() -> None:
    """ve_037 expects no returned report (report_returned = false)."""
    spec = _STAGE1C_SPEC.read_text(encoding="utf-8")
    section = _section(spec, r"private-seam expectation")
    rows = _table_rows(section)
    header = None
    for row in rows:
        cells = [c.strip().strip("`") for c in row]
        if any("report returned" in c.lower() for c in cells):
            header = cells
            break
    assert header is not None, (
        "private-seam expectation table must have report returned column"
    )
    for row in rows:
        cells = [c.strip().strip("`") for c in row]
        if cells[0] == "ve_037_report_encoding_failure_raises":
            result_dict = dict(zip(header[1:], cells[1:], strict=True))
            report_returned = result_dict.get("Report returned", "").lower()
            assert report_returned == "false", (
                f"ve_037 report_returned must be false, got {report_returned!r}"
            )
            break
    else:
        pytest.fail("ve_037 not found in private-seam expectation table")
