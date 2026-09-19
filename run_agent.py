"""Run one question through the ADK/Vertex/MCP/BigQuery path."""

from __future__ import annotations

import asyncio
import sys
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from stars_agent.agent import root_agent

APP_NAME = "medicare_stars_demo"
DEFAULT_QUESTION = (
    "Which Medicare contracts show a statistically meaningful decline in "
    "member-experience measures, and what measures contributed most?"
)


async def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or DEFAULT_QUESTION
    sessions = InMemorySessionService()
    session = await sessions.create_session(
        app_name=APP_NAME,
        user_id="demo-user",
        session_id=str(uuid.uuid4()),
        state={"data_classification": "synthetic-aggregate"},
    )
    runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=sessions)
    message = types.Content(role="user", parts=[types.Part(text=question)])
    final_text = ""
    async for event in runner.run_async(
        user_id="demo-user", session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content:
            final_text = "".join(part.text or "" for part in event.content.parts)
    if not final_text:
        raise RuntimeError("Agent completed without a final response")
    print(final_text)


if __name__ == "__main__":
    asyncio.run(main())

