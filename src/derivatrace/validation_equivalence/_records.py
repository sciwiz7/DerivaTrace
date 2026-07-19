from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CapturedFailure:
    """Single captured-failure record inside a per-side failures array."""

    stage: str
    code: str
    classification: str


@dataclass(frozen=True)
class DiffEntry:
    """A single structural-diff entry."""

    path: str
    op: str
    left_value: Any = None
    right_value: Any = None


@dataclass(frozen=True)
class DiffSummary:
    """Deterministic structural-diff summary."""

    entries: tuple[DiffEntry, ...] = ()
    truncated: bool = False
    truncation_reason: str | None = None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class ReportSide:
    """Per-side structured capture in the report."""

    contract_identity: str | None = None
    payoff_graph_identity: str | None = None
    failures: tuple[CapturedFailure, ...] = ()


@dataclass(frozen=True)
class LimitsUsed:
    """Echoed limit objects so the report is self-describing."""

    validation_max_depth: int = 64
    validation_max_unique_nodes: int = 4096
    canonicalization_max_canonical_nodes: int = 16384
    canonicalization_max_canonical_bytes: int = 8_000_000
    payoff_max_payoff_nodes: int = 4096
    payoff_max_document_bytes: int = 4_194_304
    payoff_max_structural_bytes: int = 2_097_152
    diff_max_compared_bytes: int = 2_097_152
    diff_max_compared_nodes: int = 4096
    diff_max_entries: int = 1024
    diff_max_report_bytes: int = 8_388_608
    diff_max_path_length: int = 256


@dataclass(frozen=True)
class SchemaMetadataRecord:
    """Deterministic schema metadata recorded for reproducibility."""

    canonical_schema_name: str = "derivatrace.contract.canonical"
    canonical_schema_version: str = "1.0.0"
    canonical_node_identity_domain: str = "derivatrace.canonical.node"
    canonical_representation_identity_domain: str = "derivatrace.canonical.contract"
    payoff_schema_name: str = "derivatrace.payoffgraph"
    payoff_schema_version: str = "1.0.0"
    payoff_node_identity_domain: str = "derivatrace.payoffgraph.node"
    payoff_representation_identity_domain: str = "derivatrace.payoffgraph.graph"


@dataclass(frozen=True)
class ProvenanceRecord:
    """Compiler tag, exclusion policy, and source canonical identities."""

    compiler: str = "derivatrace.validation-equivalence/1.0.0"
    policy: str = "excluded_from_identity"
    source_left_identity: str | None = None
    source_right_identity: str | None = None


@dataclass(frozen=True)
class CompleteReport:
    """Complete validation-equivalence report (immutable).

    This is the structural projection used for report_id computation.
    Provenance is excluded from the structural projection (§7).
    """

    report_id: str
    schema_name: str
    schema_version: str
    requested_level: str
    canonical_schema_version: str
    payoff_schema_version: str
    left_validation_outcome: str
    right_validation_outcome: str
    canonical_comparison_status: str
    canonical_comparison_reason: str | None
    payoff_comparison_status: str
    payoff_comparison_reason: str | None
    left: ReportSide
    right: ReportSide
    diff_representation: str
    diff_summary: DiffSummary
    limits_used: LimitsUsed
    schema_metadata: SchemaMetadataRecord
    provenance: ProvenanceRecord


__all__: list[str] = [
    "CapturedFailure",
    "CompleteReport",
    "DiffEntry",
    "DiffSummary",
    "LimitsUsed",
    "ProvenanceRecord",
    "ReportSide",
    "SchemaMetadataRecord",
]
