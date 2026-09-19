"""Cloud Run entry point using Google's supported ADK FastAPI wrapper."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

ROOT = Path(__file__).resolve().parent

app: FastAPI = get_fast_api_app(
    agents_dir=str(ROOT),
    session_service_uri="memory://",
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        ],
    web=True,
)



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))

