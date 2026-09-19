"""ADK callback that meters all model calls and annotates the final response."""

from __future__ import annotations

import json
from copy import deepcopy

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.genai import types

from observability.llm_cost import (
    CallUsage,
    ModelPricing,
    UsageTotals,
    build_cost_record,
    format_cost_footer,
)

_USAGE_STATE_KEY = "temp:llm_usage_totals"
_COST_STATE_KEY = "temp:llm_cost_estimate"
_FOOTER_MARKER = "LLM usage estimate:"


def _is_final_text_response(response: LlmResponse) -> bool:
    if response.partial or not response.content or not response.content.parts:
        return False
    parts = response.content.parts
    return any(part.text for part in parts) and not any(part.function_call for part in parts)


def track_llm_cost(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> LlmResponse | None:
    """Accumulate token use, log it, and append a post-generation estimate."""
    usage = CallUsage.from_metadata(llm_response.usage_metadata)
    totals = UsageTotals.from_dict(callback_context.state.get(_USAGE_STATE_KEY))
    totals.add(usage)
    callback_context.state[_USAGE_STATE_KEY] = totals.to_dict()

    if not _is_final_text_response(llm_response) or totals.model_calls == 0:
        return None

    pricing = ModelPricing.from_environment()
    record = build_cost_record(totals, pricing, callback_context.invocation_id)
    callback_context.state[_COST_STATE_KEY] = record
    print(
        json.dumps(
            {
                "severity": "INFO",
                "message": "Vertex AI LLM usage estimate",
                **record,
            },
            sort_keys=True,
        ),
        flush=True,
    )

    replacement = deepcopy(llm_response)
    replacement.custom_metadata = dict(replacement.custom_metadata or {})
    replacement.custom_metadata["llm_cost_estimate"] = record
    text = "".join(part.text or "" for part in replacement.content.parts)
    if _FOOTER_MARKER not in text:
        replacement.content.parts.append(types.Part(text=format_cost_footer(record)))
    return replacement
