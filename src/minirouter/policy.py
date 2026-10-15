"""Pure selective routing policy over neural model scores and trusted inputs."""

from __future__ import annotations

import ast
import math
import operator
import re
from dataclasses import dataclass

from .contract import (
    CAPABILITIES,
    AbstainReason,
    Decision,
    Prediction,
    Request,
    Route,
    ToolCatalog,
)


@dataclass(frozen=True)
class PolicyConfig:
    min_confidence: float = 0.65
    min_margin: float = 0.15
    capability_threshold: float = 0.5
    max_tokens: int = 512

    def __post_init__(self) -> None:
        for name in ("min_confidence", "min_margin", "capability_threshold"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if type(self.max_tokens) is not int or self.max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")


@dataclass(frozen=True)
class CalculatorHandler:
    """A deliberately narrow deterministic handler for ``calc: <expression>``."""

    max_expression_chars: int = 160
    max_nodes: int = 48
    max_abs_value: float = 1e12

    def __post_init__(self) -> None:
        if type(self.max_expression_chars) is not int or not 1 <= self.max_expression_chars <= 160:
            raise ValueError("max_expression_chars must be between 1 and 160")
        if type(self.max_nodes) is not int or not 1 <= self.max_nodes <= 48:
            raise ValueError("max_nodes must be between 1 and 48")
        if isinstance(self.max_abs_value, bool) or not isinstance(self.max_abs_value, (int, float)) or not math.isfinite(self.max_abs_value) or self.max_abs_value <= 0:
            raise ValueError("max_abs_value must be positive and finite")

    def evaluate(self, text: str) -> float | int | None:
        match = re.fullmatch(r"\s*calc:\s*(.*?)\s*", text, flags=re.IGNORECASE | re.DOTALL)
        if not match or not match.group(1) or len(match.group(1)) > self.max_expression_chars:
            return None
        try:
            tree = ast.parse(match.group(1), mode="eval")
            if sum(1 for _ in ast.walk(tree)) > self.max_nodes:
                return None
            value = self._eval(tree.body)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            if not math.isfinite(value) or abs(value) > self.max_abs_value:
                return None
            return value
        except (SyntaxError, ValueError, TypeError, OverflowError, ZeroDivisionError):
            return None

    def _eval(self, node: ast.AST) -> float | int:
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = self._eval(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp):
            left, right = self._eval(node.left), self._eval(node.right)
            operations = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.FloorDiv: operator.floordiv,
                ast.Mod: operator.mod,
                ast.Pow: operator.pow,
            }
            op = operations.get(type(node.op))
            if op is None:
                raise ValueError("unsupported operator")
            if isinstance(node.op, ast.Pow) and abs(right) > 12:
                raise ValueError("exponent too large")
            result = op(left, right)
            if isinstance(result, bool) or not isinstance(result, (int, float)):
                raise ValueError("invalid arithmetic result")
            if not math.isfinite(result) or abs(result) > self.max_abs_value:
                raise ValueError("arithmetic result out of range")
            return result
        raise ValueError("unsupported expression")


_ROUTE_CAPABILITY = {
    Route.CODING: "coding",
    Route.REASONING: "reasoning",
    Route.SEARCH: "search",
    Route.DATABASE: "database",
}


def decide(
    request: Request,
    catalog: ToolCatalog,
    prediction: Prediction,
    *,
    token_count: int,
    context_complete: bool = True,
    config: PolicyConfig = PolicyConfig(),
) -> Decision:
    """Choose a next action or abstain. This function never executes a tool."""
    if type(token_count) is not int or token_count < 0:
        raise ValueError("token_count must be a non-negative integer")
    flags = {name: prediction.capability_scores[name] >= config.capability_threshold for name in CAPABILITIES}

    def abstain(reason: AbstainReason, confidence: float = 0.0) -> Decision:
        return Decision(None, reason, confidence, flags)

    if token_count > config.max_tokens:
        return abstain(AbstainReason.OVERLENGTH)
    if not context_complete:
        return abstain(AbstainReason.MISSING_CONTEXT)
    if request.locale.split("-", 1)[0].lower() != "en":
        return abstain(AbstainReason.UNSUPPORTED)

    ranked = sorted(prediction.route_probabilities.items(), key=lambda item: item[1], reverse=True)
    route, confidence = ranked[0]
    margin = confidence - ranked[1][1]
    if confidence < config.min_confidence or margin < config.min_margin:
        return abstain(AbstainReason.LOW_CONFIDENCE, confidence)

    missing = {name for name, needed in flags.items() if needed and name not in catalog.available_capabilities}
    if missing:
        return abstain(AbstainReason.MISSING_CAPABILITY, confidence)

    if route is Route.NO_LLM:
        if any(flags.values()):
            return abstain(AbstainReason.UNSUPPORTED, confidence)
        # Only code-registered handlers can establish deterministic eligibility.
        for handler_id, handler in catalog.deterministic_handlers.items():
            if handler_id == "calculator_v1" and type(handler) is CalculatorHandler:
                if handler.evaluate(request.text) is not None:
                    return Decision(route, None, confidence, flags, eligible_handler=handler_id)
        return abstain(AbstainReason.MISSING_CAPABILITY, confidence)

    required = _ROUTE_CAPABILITY[route]
    if required not in catalog.available_capabilities:
        return abstain(AbstainReason.MISSING_CAPABILITY, confidence)
    if not flags[required]:
        return abstain(AbstainReason.AMBIGUOUS, confidence)
    return Decision(route, None, confidence, flags)
