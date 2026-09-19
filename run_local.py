"""No-cloud proof of the deterministic policy and statistical analysis."""

from pathlib import Path

from analytics.local import analyze_csv
from authority.policy import QueryPolicy

QUESTION = (
    "Which Medicare contracts show a statistically meaningful decline in "
    "member-experience measures, and what measures contributed most?"
)

policy = QueryPolicy()
policy.authorize_question(QUESTION)
rows = analyze_csv(Path(__file__).parent / "data" / "member_experience.csv")

print("MEDICARE STARS AGENT — LOCAL AUTHORITY PROOF")
print("question:", QUESTION)
print("decision: AUTHORIZED (synthetic aggregate data only)\n")
for row in rows:
    print(
        f"{row['contract_id']} | {row['measure_code']} | "
        f"{row['prior_year']} {row['prior_score']:.1%} -> "
        f"{row['current_year']} {row['current_score']:.1%} | "
        f"change {row['change']:.1%} | z={row['z_score']}"
    )
print("\ncontrols: fixed analysis, PHI denial, dry-run ceiling in cloud mode, row limit=25")

