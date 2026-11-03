"""Read-only attendance data gateway. No LLM-generated SQL is executed."""
import os
import re

DEMO_SCHOOLS = [
    {"school_id": "1001", "school": "רימון", "grade": "ד׳", "previous": 91.0, "current": 79.0, "students": 122},
    {"school_id": "1002", "school": "הדקל", "grade": "ד׳", "previous": 89.0, "current": 85.0, "students": 116},
    {"school_id": "1003", "school": "האלון", "grade": "ד׳", "previous": 92.0, "current": 91.0, "students": 104},
    {"school_id": "1004", "school": "שקד", "grade": "ד׳", "previous": 87.0, "current": 83.0, "students": 109},
]
# Demonstration identity only. Replace with verified OIDC and server-side entitlements.
DEMO_PERMISSIONS = {"demo-supervisor": ["1001", "1002", "1003", "1004"]}


def allowed_ids(user_id: str) -> set[str]:
    return set(DEMO_PERMISSIONS.get(user_id, []))


def get_attendance(user_id: str, school_id: str | None = None) -> list[dict]:
    ids = allowed_ids(user_id)
    if not ids:
        return []
    if school_id and school_id not in ids:
        raise PermissionError("school is not authorized")
    mode = os.getenv("DATA_MODE", "demo").lower()
    if mode == "demo":
        rows = [r.copy() for r in DEMO_SCHOOLS if r["school_id"] in ids]
        return [r for r in rows if r["school_id"] == school_id] if school_id else rows
    if mode != "bigquery":
        raise ValueError("Unsupported DATA_MODE")
    table = os.environ["BQ_ATTENDANCE_TABLE"]
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+", table):
        raise ValueError("BQ_ATTENDANCE_TABLE has an invalid identifier")
    from google.cloud import bigquery
    client = bigquery.Client()
    sql = f"""SELECT CAST(school_id AS STRING) AS school_id, school, grade,
      CAST(previous AS FLOAT64) AS previous, CAST(current AS FLOAT64) AS current,
      CAST(students AS INT64) AS students
      FROM `{table}` WHERE CAST(school_id AS STRING) IN UNNEST(@allowed_school_ids)
      AND (@school_id IS NULL OR CAST(school_id AS STRING) = @school_id)
      LIMIT 100"""
    config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ArrayQueryParameter("allowed_school_ids", "STRING", sorted(ids)),
        bigquery.ScalarQueryParameter("school_id", "STRING", school_id),
    ], maximum_bytes_billed=100000000)
    # IMPORTANT: POC allowlist only; production also requires database-level access policy,
    # trusted identity mapping, least-privilege SA and validated tenant isolation.
    return [dict(row.items()) for row in client.query(sql, job_config=config).result()]


def summary(rows: list[dict]) -> dict:
    if not rows:
        return {"schools": 0, "average": None, "decline": None, "flagged": 0}
    n=len(rows)
    return {"schools":n,"average":round(sum(r['current'] for r in rows)/n,1),
      "decline":round(sum(r['current']-r['previous'] for r in rows)/n,1),
      "flagged":sum((r['previous']-r['current'])>=5 for r in rows)}
