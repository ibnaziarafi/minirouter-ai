"""Validated public contracts for MiniRouter's local routing boundary.

The caller is responsible for constructing ``ToolCatalog`` from trusted
application configuration. Request text is never consulted to grant a tool.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Mapping


class Route(str, Enum):
    CODING = "coding"
    REASONING = "reasoning"
    SEARCH = "search"
    DATABASE = "database"
    NO_LLM = "no_llm"


class AbstainReason(str, Enum):
    MISSING_CAPABILITY = "missing_capability"
    MISSING_CONTEXT = "missing_context"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
    OVERLENGTH = "overlength"
    LOW_CONFIDENCE = "low_confidence"


CAPABILITIES = ("coding", "reasoning", "search", "database")
_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


def _text(value: object, name: str, *, required: bool, max_chars: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{name} must not be empty")
    if len(value) > max_chars:
        raise ValueError(f"{name} exceeds {max_chars} characters")
    return value


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase identifier")
    return value


@dataclass(frozen=True)
class Request:
    """User request and bounded context, kept distinct from trusted metadata."""

    text: str
    context: tuple[str, ...] = ()
    locale: str = "en"

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _text(self.text, "text", required=True, max_chars=32_768))
        if not isinstance(self.context, (tuple, list)) or len(self.context) > 4:
            raise ValueError("context must contain at most four strings")
        cleaned = tuple(_text(item, "context item", required=True, max_chars=8_192) for item in self.context)
        object.__setattr__(self, "context", cleaned)
        locale = _text(self.locale, "locale", required=True, max_chars=32)
        if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", locale):
            raise ValueError("locale must be a BCP-47-like language tag")
        object.__setattr__(self, "locale", locale)


@dataclass(frozen=True)
class ToolCatalog:
    """Allowlisted capabilities and deterministic handlers supplied by caller."""

    available_capabilities: frozenset[str] = field(default_factory=frozenset)
    deterministic_handlers: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        caps = frozenset(self.available_capabilities)
        if not caps <= set(CAPABILITIES):
            raise ValueError("available_capabilities contains an unknown capability")
        object.__setattr__(self, "available_capabilities", caps)
        if not isinstance(self.deterministic_handlers, Mapping):
            raise ValueError("deterministic_handlers must be a mapping")
        handlers = {}
        for key, handler in self.deterministic_handlers.items():
            handlers[_identifier(key, "handler id")] = handler
        object.__setattr__(self, "deterministic_handlers", handlers)


@dataclass(frozen=True)
class Prediction:
    """Neural-model outputs. Primary probabilities sum to one; flags are scores."""

    route_probabilities: Mapping[Route | str, float]
    capability_scores: Mapping[str, float]

    def __post_init__(self) -> None:
        routes = {}
        for key, value in self.route_probabilities.items():
            try:
                route = Route(key)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"unknown route: {key!r}") from exc
            if route in routes:
                raise ValueError(f"duplicate route: {route.value}")
            routes[route] = _probability(value, f"route probability {route.value}")
        if set(routes) != set(Route):
            raise ValueError("exactly the five primary routes are required")
        if abs(sum(routes.values()) - 1.0) > 1e-5:
            raise ValueError("primary route probabilities must sum to 1")
        flags = dict(self.capability_scores)
        if set(flags) != set(CAPABILITIES):
            raise ValueError("exactly four capability scores are required")
        for cap, score in flags.items():
            flags[cap] = _probability(score, f"capability score {cap}")
        object.__setattr__(self, "route_probabilities", routes)
        object.__setattr__(self, "capability_scores", flags)


@dataclass(frozen=True)
class Decision:
    route: Route | None
    abstain_reason: AbstainReason | None
    confidence: float
    capability_flags: Mapping[str, bool]
    eligible_handler: str | None = None

    def __post_init__(self) -> None:
        if (self.route is None) == (self.abstain_reason is None):
            raise ValueError("decision must contain exactly one of route or abstain_reason")
        _probability(self.confidence, "confidence")
        if set(self.capability_flags) != set(CAPABILITIES) or any(type(v) is not bool for v in self.capability_flags.values()):
            raise ValueError("capability_flags must contain four boolean flags")
        if self.route is Route.NO_LLM and not self.eligible_handler:
            raise ValueError("no_llm requires an eligible registered handler")


def _probability(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    if result != result or result in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite")
    return result
