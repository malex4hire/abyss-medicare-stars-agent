"""Deterministic token accounting and Vertex AI cost estimation."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

TOKENS_PER_MILLION = Decimal("1000000")
COST_QUANTUM = Decimal("0.00000001")


def _count(metadata: Any, name: str) -> int:
    value = getattr(metadata, name, 0) if metadata is not None else 0
    return max(int(value or 0), 0)


@dataclass(frozen=True)
class ModelPricing:
    """Versioned list-price configuration for one Vertex AI model."""

    model: str
    input_usd_per_million: Decimal
    cached_input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    version: str

    @classmethod
    def from_environment(cls) -> ModelPricing:
        return cls(
            model=os.environ.get("MODEL", "gemini-2.5-flash"),
            input_usd_per_million=Decimal(
                os.environ.get("LLM_INPUT_USD_PER_MILLION", "0.30")
            ),
            cached_input_usd_per_million=Decimal(
                os.environ.get("LLM_CACHED_INPUT_USD_PER_MILLION", "0.03")
            ),
            output_usd_per_million=Decimal(
                os.environ.get("LLM_OUTPUT_USD_PER_MILLION", "2.50")
            ),
            version=os.environ.get(
                "LLM_PRICING_VERSION", "vertex-ai-standard-2026-09-19"
            ),
        )


@dataclass(frozen=True)
class CallUsage:
    """Token counts returned for one model call."""

    prompt_tokens: int = 0
    tool_input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_metadata(cls, metadata: Any) -> CallUsage:
        return cls(
            prompt_tokens=_count(metadata, "prompt_token_count"),
            tool_input_tokens=_count(metadata, "tool_use_prompt_token_count"),
            cached_input_tokens=_count(metadata, "cached_content_token_count"),
            output_tokens=_count(metadata, "candidates_token_count"),
            reasoning_tokens=_count(metadata, "thoughts_token_count"),
            total_tokens=_count(metadata, "total_token_count"),
        )

    @property
    def input_tokens(self) -> int:
        return self.prompt_tokens + self.tool_input_tokens

    @property
    def billable_output_tokens(self) -> int:
        reported = self.output_tokens + self.reasoning_tokens
        inferred = max(self.total_tokens - self.input_tokens, 0)
        return max(reported, inferred)

    @property
    def has_usage(self) -> bool:
        return (
            self.total_tokens > 0
            or self.input_tokens > 0
            or self.billable_output_tokens > 0
        )


@dataclass
class UsageTotals:
    """Invocation-scoped totals across every model call."""

    model_calls: int = 0
    prompt_tokens: int = 0
    tool_input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    billable_output_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> UsageTotals:
        value = value or {}
        fields = cls.__dataclass_fields__
        return cls(**{name: int(value.get(name, 0)) for name in fields})

    def add(self, usage: CallUsage) -> None:
        if not usage.has_usage:
            return
        self.model_calls += 1
        self.prompt_tokens += usage.prompt_tokens
        self.tool_input_tokens += usage.tool_input_tokens
        self.cached_input_tokens += usage.cached_input_tokens
        self.output_tokens += usage.output_tokens
        self.reasoning_tokens += usage.reasoning_tokens
        self.billable_output_tokens += usage.billable_output_tokens
        self.total_tokens += usage.total_tokens or (
            usage.input_tokens + usage.billable_output_tokens
        )

    @property
    def input_tokens(self) -> int:
        return self.prompt_tokens + self.tool_input_tokens

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def estimate_cost(totals: UsageTotals, pricing: ModelPricing) -> Decimal:
    """Estimate list-price cost; Google Cloud Billing remains authoritative."""
    cached = min(totals.cached_input_tokens, totals.prompt_tokens)
    uncached = max(totals.input_tokens - cached, 0)
    cost = (
        Decimal(uncached) * pricing.input_usd_per_million
        + Decimal(cached) * pricing.cached_input_usd_per_million
        + Decimal(totals.billable_output_tokens) * pricing.output_usd_per_million
    ) / TOKENS_PER_MILLION
    return cost.quantize(COST_QUANTUM, rounding=ROUND_HALF_UP)


def build_cost_record(
    totals: UsageTotals,
    pricing: ModelPricing,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    """Create the serializable record used by UI state, traces, and logs."""
    return {
        "event": "llm_usage_estimate",
        "model": pricing.model,
        "model_calls": totals.model_calls,
        "input_tokens": totals.input_tokens,
        "prompt_tokens": totals.prompt_tokens,
        "tool_input_tokens": totals.tool_input_tokens,
        "cached_input_tokens": totals.cached_input_tokens,
        "output_tokens": totals.output_tokens,
        "reasoning_tokens": totals.reasoning_tokens,
        "billable_output_tokens": totals.billable_output_tokens,
        "total_tokens": totals.total_tokens,
        "estimated_cost_usd": format(estimate_cost(totals, pricing), ".8f"),
        "pricing_version": pricing.version,
        "actual_cost_source": "Google Cloud Billing",
        "invocation_id": invocation_id,
    }


def format_cost_footer(record: dict[str, Any]) -> str:
    """Render a compact, deterministic footer after model generation."""
    return (
        "\n\nLLM usage estimate:\n"
        f"- model: `{record['model']}`\n"
        f"- model_calls: `{record['model_calls']}`\n"
        f"- input_tokens: `{record['input_tokens']}` "
        f"(tool results: `{record['tool_input_tokens']}`, "
        f"cached: `{record['cached_input_tokens']}`)\n"
        f"- output_tokens: `{record['billable_output_tokens']}` "
        f"(reasoning: `{record['reasoning_tokens']}`)\n"
        f"- total_tokens: `{record['total_tokens']}`\n"
        f"- estimated_cost_usd: `${record['estimated_cost_usd']}`\n"
        f"- pricing_version: `{record['pricing_version']}`\n"
        "- actual_cost_source: `Google Cloud Billing`"
    )
