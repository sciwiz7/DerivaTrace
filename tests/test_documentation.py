from __future__ import annotations

import re
import tomllib
from pathlib import Path

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
    # Stage 1A is complete / implemented.
    assert _near(road, r"stage 1a\b", "implement") or _near(
        road, r"stage 1a\b", "complete"
    )
    # Stage 1B is in progress (architecture baseline).
    assert _near(road, r"stage 1b\b", "in progress")
    # Stage 1C remains planned.
    assert _near(road, r"stage 1c\b", "planned")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "stage 1b" in readme
    assert "specification-only" in readme or "specification only" in readme


def test_stage_1b_baseline_is_specification_only() -> None:
    files = [
        DOCS_DIR / "canonicalization-spec.md",
        DOCS_DIR / "payoff-graph-spec.md",
        DOCS_DIR / "canonical-test-vectors.md",
        DOCS_DIR / "adr" / "0007-canonical-contract-identity-and-payoff-graph.md",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8").lower()
        assert ("specification only" in text) or ("specification-only" in text), path
        assert "not implemented" in text, path
        # The conservative principle must be stated.
        assert "conservative" in text, path


def test_no_canonicalization_or_hashing_implementation_claimed() -> None:
    # The Stage 1B baseline must not claim a runtime implementation exists.
    impl_claims = [
        "canonicalize(",
        "def canonicalize",
        "canonicalize_contract",
        "sha256(",
        "hash_canonical",
        "serialize(",
        "def serialize",
        "compile_payoff",
        "payoff_graph(",
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
    impl_claims = [
        "canonicalize(",
        "def canonicalize",
        "canonicalize_contract",
        "sha256(",
        "hash_canonical",
        "serialize(",
        "def serialize",
        "compile_payoff",
        "payoff_graph(",
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
