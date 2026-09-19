"""Deterministic authority checks. The model cannot override these rules."""

from __future__ import annotations

import re
from dataclasses import dataclass


class PolicyViolation(ValueError):
    """Raised before a request can reach a tool or data source."""


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,1023}$")
_PHI_TERMS = {
    "member name",
    "patient name",
    "date of birth",
    "dob",
    "address",
    "phone number",
    "email address",
    "medical record",
    "member id",
}
_ALLOWED_INTENT_TERMS = {
    "contract",
    "decline",
    "experience",
    "measure",
    "score",
    "star",
    "trend",
    "year",
}


@dataclass(frozen=True)
class QueryPolicy:
    dataset: str = "medicare_stars_demo"
    table: str = "member_experience"
    maximum_bytes_billed: int = 100_000_000
    row_limit: int = 25

    def validate_identifiers(self) -> None:
        for label, value in (("dataset", self.dataset), ("table", self.table)):
            if not _IDENTIFIER.fullmatch(value):
                raise PolicyViolation(f"Invalid {label} identifier")

    def authorize_question(self, question: str) -> str:
        normalized = " ".join(question.lower().split())
        if not normalized or len(normalized) > 500:
            raise PolicyViolation("Question must contain 1-500 characters")
        if any(term in normalized for term in _PHI_TERMS):
            raise PolicyViolation(
                "Member-level or identifying data is outside this agent's authority"
            )
        if not any(term in normalized for term in _ALLOWED_INTENT_TERMS):
            raise PolicyViolation("Request is outside the Medicare Stars analytical scope")
        return normalized

    def authorize_dry_run(self, bytes_processed: int) -> None:
        if bytes_processed < 0:
            raise PolicyViolation("BigQuery returned an invalid byte estimate")
        if bytes_processed > self.maximum_bytes_billed:
            raise PolicyViolation(
                f"Query estimate {bytes_processed:,} exceeds the "
                f"{self.maximum_bytes_billed:,}-byte ceiling"
            )
