"""Cost-bounded BigQuery execution for the single approved analysis."""

from __future__ import annotations

from google.cloud import bigquery

from authority.policy import QueryPolicy

ANALYSIS_SQL = """
WITH ordered AS (
  SELECT
    contract_id,
    measure_code,
    measure_name,
    year,
    score,
    denominator,
     LAG(year) OVER (
      PARTITION BY contract_id, measure_code ORDER BY year
    ) AS prior_year,
    LAG(score) OVER (
      PARTITION BY contract_id, measure_code ORDER BY year
    ) AS prior_score,
    LAG(denominator) OVER (
      PARTITION BY contract_id, measure_code ORDER BY year
    ) AS prior_denominator
  FROM `{project}.{dataset}.{table}`
), scored AS (
  SELECT
    *,
    SAFE_DIVIDE(
      score * denominator + prior_score * prior_denominator,
      denominator + prior_denominator
    ) AS pooled_rate
  FROM ordered
  WHERE prior_score IS NOT NULL
), tested AS (
  SELECT
    contract_id,
    measure_code,
    measure_name,
    prior_year,
    year AS current_year,
    prior_score,
    score AS current_score,
    score - prior_score AS change,
    SAFE_DIVIDE(
      score - prior_score,
      SQRT(
        pooled_rate * (1 - pooled_rate)
        * (SAFE_DIVIDE(1, denominator) + SAFE_DIVIDE(1, prior_denominator))
      )
    ) AS z_score
  FROM scored
)
SELECT
  contract_id,
  measure_code,
  measure_name,
  prior_year,
  current_year,
  ROUND(prior_score, 4) AS prior_score,
  ROUND(current_score, 4) AS current_score,
  ROUND(change, 4) AS change,
  ROUND(z_score, 3) AS z_score
FROM tested
WHERE z_score <= @z_threshold
ORDER BY z_score
LIMIT @row_limit
""".strip()


def run_analysis(project: str, policy: QueryPolicy | None = None) -> dict:
    policy = policy or QueryPolicy()
    policy.validate_identifiers()
    client = bigquery.Client(project=project)
    sql = ANALYSIS_SQL.format(
        project=project,
        dataset=policy.dataset,
        table=policy.table,
    )
    parameters = [
        bigquery.ScalarQueryParameter("z_threshold", "FLOAT64", -1.96),
        bigquery.ScalarQueryParameter("row_limit", "INT64", policy.row_limit),
    ]

    dry_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
        query_parameters=parameters,
    )
    estimate = client.query(sql, job_config=dry_config).total_bytes_processed or 0
    policy.authorize_dry_run(estimate)

    job_config = bigquery.QueryJobConfig(
        use_query_cache=True,
        maximum_bytes_billed=policy.maximum_bytes_billed,
        query_parameters=parameters,
        labels={"workload": "stars-agent-demo", "authority": "bounded"},
    )
    rows = [dict(row.items()) for row in client.query(sql, job_config=job_config).result()]
    return {
        "status": "authorized",
        "evidence": rows,
        "controls": {
            "aggregate_only": True,
            "dry_run_bytes": estimate,
            "maximum_bytes_billed": policy.maximum_bytes_billed,
            "row_limit": policy.row_limit,
        },
    }
