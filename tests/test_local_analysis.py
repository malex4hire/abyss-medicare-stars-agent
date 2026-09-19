from pathlib import Path

from analytics.local import analyze_csv


def test_detects_expected_declines():
    path = Path(__file__).parents[1] / "data" / "member_experience.csv"
    rows = analyze_csv(path)
    pairs = {(row["contract_id"], row["measure_code"]) for row in rows}
    assert pairs == {("H1001", "C01"), ("H2042", "C02"), ("H3307", "C02")}
    assert all(row["change"] < 0 and row["z_score"] <= -1.96 for row in rows)

