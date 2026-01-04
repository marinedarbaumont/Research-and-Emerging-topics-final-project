from pathlib import Path
import duckdb
import pandas as pd

def missing_value_summary(parquet_path: Path) -> pd.DataFrame:
    con = duckdb.connect()

    # Get column names
    cols = con.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(parquet_path)]
    ).df()["column_name"].tolist()

    rows = []

    for col in cols:
        q = f"""
        SELECT
            '{col}' AS column_name,
            COUNT(*) AS total_rows,
            SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS missing_rows,
            ROUND(
                100.0 * SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) / COUNT(*),
                2
            ) AS pct_missing
        FROM read_parquet(?)
        """
        res = con.execute(q, [str(parquet_path)]).fetchone()
        rows.append(res)

    con.close()
    return pd.DataFrame(
        rows,
        columns=["column_name", "total_rows", "missing_rows", "pct_missing"]
    ).sort_values("pct_missing", ascending=False)
