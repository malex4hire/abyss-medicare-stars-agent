from decimal import Decimal
from types import SimpleNamespace

from google.adk.models import LlmResponse
from google.genai import types

from observability.adk_cost_callback import track_llm_cost
from observability.llm_cost import (
    CallUsage,
    ModelPricing,
    UsageTotals,
    build_cost_record,
    estimate_cost,
    format_cost_footer,
)


def pricing() -> ModelPricing:
    return ModelPricing(
        model="gemini-2.5-flash",
        input_usd_per_million=Decimal("0.30"),
        cached_input_usd_per_million=Decimal("0.03"),
        output_usd_per_million=Decimal("2.50"),
        version="test-pricing",
    )


def test_usage_includes_tool_results_and_reasoning_tokens():
    metadata = SimpleNamespace(
        prompt_token_count=1000,
        tool_use_prompt_token_count=200,
        cached_content_token_count=100,
        candidates_token_count=300,
        thoughts_token_count=50,
        total_token_count=1550,
    )
    usage = CallUsage.from_metadata(metadata)
    assert usage.input_tokens == 1200
    assert usage.billable_output_tokens == 350


def test_cost_uses_versioned_input_cached_and_output_rates():
    totals = UsageTotals(
        model_calls=1,
        prompt_tokens=1000,
        tool_input_tokens=200,
        cached_input_tokens=100,
        output_tokens=300,
        reasoning_tokens=50,
        billable_output_tokens=350,
        total_tokens=1550,
    )
    assert estimate_cost(totals, pricing()) == Decimal("0.00120800")


def test_record_and_footer_are_auditable():
    totals = UsageTotals(model_calls=2, prompt_tokens=900, total_tokens=1200)
    totals.billable_output_tokens = 300
    record = build_cost_record(totals, pricing(), "invocation-1")
    footer = format_cost_footer(record)
    assert record["estimated_cost_usd"] == "0.00102000"
    assert record["actual_cost_source"] == "Google Cloud Billing"
    assert "model_calls: `2`" in footer
    assert "estimated_cost_usd: `$0.00102000`" in footer


def test_callback_accumulates_tool_cycle_and_appends_final_footer(monkeypatch):
    monkeypatch.setenv("MODEL", "gemini-2.5-flash")
    context = SimpleNamespace(state={}, invocation_id="invocation-1")
    tool_call = LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="analyze_member_experience", args={}
                    )
                )
            ],
        ),
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=100,
            candidates_token_count=10,
            total_token_count=110,
        ),
    )
    final = LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text="Evidence")]),
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=200,
            tool_use_prompt_token_count=50,
            candidates_token_count=40,
            thoughts_token_count=5,
            total_token_count=295,
        ),
    )

    assert track_llm_cost(context, tool_call) is None
    replacement = track_llm_cost(context, final)

    assert replacement is not None
    rendered = "".join(part.text or "" for part in replacement.content.parts)
    assert "LLM usage estimate:" in rendered
    assert "model_calls: `2`" in rendered
    assert context.state["temp:llm_cost_estimate"]["input_tokens"] == 350
    assert context.state["temp:llm_cost_estimate"]["total_tokens"] == 405
    assert replacement.custom_metadata["llm_cost_estimate"]["invocation_id"] == "invocation-1"
