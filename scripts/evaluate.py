"""Small deterministic regression suite for authority and evidence behavior."""

from __future__ import annotations

import json
from pathlib import Path

from analytics.local import analyze_csv
from authority.policy import PolicyViolation, QueryPolicy

ROOT = Path(__file__).parents[1]
cases = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
policy = QueryPolicy()
passed = 0

for case in cases:
    try:
        policy.authorize_question(case["question"])
        actual = "authorized"
    except PolicyViolation:
        actual = "denied"
    ok = actual == case["expected"]
    passed += int(ok)
    print(f"{'PASS' if ok else 'FAIL'} | {case['name']} | {actual}")

evidence = analyze_csv(ROOT / "data" / "member_experience.csv")
expected_pairs = {("H1001", "C01"), ("H2042", "C02"), ("H3307", "C02")}
actual_pairs = {(row["contract_id"], row["measure_code"]) for row in evidence}
evidence_ok = actual_pairs == expected_pairs
passed += int(evidence_ok)
print(f"{'PASS' if evidence_ok else 'FAIL'} | evidence regression | {len(evidence)} rows")

total = len(cases) + 1
print(f"\nscore: {passed}/{total}")
raise SystemExit(0 if passed == total else 1)

