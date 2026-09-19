"""Private stdio MCP server exposing one bounded BigQuery capability."""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from analytics.bigquery import run_analysis
from authority.policy import QueryPolicy

mcp = FastMCP("medicare-stars-authority")


@mcp.tool()
def analyze_member_experience(question: str) -> dict:
    """Find statistically meaningful aggregate contract/measure declines.

    This tool cannot retrieve member-level data or execute model-authored SQL.
    """
    policy = QueryPolicy()
    policy.authorize_question(question)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT is required")
    return run_analysis(project, policy)


if __name__ == "__main__":
    mcp.run(transport="stdio")

