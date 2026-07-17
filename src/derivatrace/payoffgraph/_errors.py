from __future__ import annotations

from derivatrace.contracts._errors import DerivaTraceError, Path, format_path

__all__: list[str] = [
    "Path",
    "PayoffGraphCollisionError",
    "PayoffGraphCompilationError",
    "PayoffGraphComplexityError",
    "PayoffGraphEncodingError",
    "PayoffGraphError",
    "PayoffGraphInputError",
    "format_path",
]


class PayoffGraphError(DerivaTraceError):
    """Base class for all payoff-graph runtime errors."""

    code: str = "payoff_graph.error"


class PayoffGraphInputError(PayoffGraphError):
    """A payoff-graph input or compiled-reference boundary is malformed."""

    code: str = "payoff_graph.input"


class PayoffGraphCompilationError(PayoffGraphError):
    """An internal payoff-graph compilation step failed."""

    code: str = "payoff_graph.compilation"


class PayoffGraphComplexityError(PayoffGraphError):
    """A payoff-graph output exceeded a configured complexity limit."""

    code: str = "payoff_graph.complexity"


class PayoffGraphEncodingError(PayoffGraphError):
    """A payoff-graph value could not be encoded canonically."""

    code: str = "payoff_graph.encoding"


class PayoffGraphCollisionError(PayoffGraphError):
    """Two distinct payoff payloads hashed to the same payoff-node id."""

    code: str = "payoff_graph.collision"
