"""Offline reference implementation over synthetic, aggregate-only data."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path


def analyze_csv(path: Path, z_threshold: float = -1.96, limit: int = 25) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            row["year"] = int(row["year"])
            row["score"] = float(row["score"])
            row["denominator"] = int(row["denominator"])
            grouped[(row["contract_id"], row["measure_code"])].append(row)

    results: list[dict] = []
    for rows in grouped.values():
        rows.sort(key=lambda item: item["year"])
        for prior, current in zip(rows, rows[1:], strict=False):
            pooled = (
                prior["score"] * prior["denominator"]
                + current["score"] * current["denominator"]
            ) / (prior["denominator"] + current["denominator"])
            standard_error = math.sqrt(
                pooled * (1 - pooled)
                * (1 / prior["denominator"] + 1 / current["denominator"])
            )
            z_score = (current["score"] - prior["score"]) / standard_error
            if z_score <= z_threshold:
                results.append(
                    {
                        "contract_id": current["contract_id"],
                        "measure_code": current["measure_code"],
                        "measure_name": current["measure_name"],
                        "prior_year": prior["year"],
                        "current_year": current["year"],
                        "prior_score": round(prior["score"], 4),
                        "current_score": round(current["score"], 4),
                        "change": round(current["score"] - prior["score"], 4),
                        "z_score": round(z_score, 3),
                    }
                )
    return sorted(results, key=lambda item: item["z_score"])[:limit]
