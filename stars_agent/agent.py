"""Deployable Google ADK agent with an MCP tool boundary."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

_root = Path(__file__).resolve().parents[1]
_server = _root / "mcp_server.py"
_mcp_env = {
    key: value
    for key in (
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "PYTHONPATH",
    )
    if (value := os.environ.get(key))
}

root_agent = LlmAgent(
    model=os.environ.get("MODEL", "gemini-2.5-flash"),
    name="medicare_stars_evidence_agent",
    description="Analyzes aggregate Medicare Stars member-experience trends.",
        instruction="""
You are an evidence-first Medicare Stars analytical agent.
Use analyze_member_experience for any factual trend claim. Never invent rows,
member details, significance, dates, or causal explanations. Report contract
and measure evidence. For every evidence row, report contract_id, measure_code, measure_name,
prior_year, prior_score, current_year, current_score, change, and z_score
exactly as returned by the tool. Never infer, substitute, omit, or relabel
these evidence fields. Never infer, substitute, omit, or relabel either year. Distinguish
association from causation, and include the tool-returned controls in a short
'Authority checks' section. If the tool rejects a request, explain the boundary
without attempting a workaround.
""".strip(),
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=sys.executable,
                    args=[str(_server)],
                    env=_mcp_env,
                ),
                timeout=30,
            ),
            tool_filter=["analyze_member_experience"],
        )
    ],
)
