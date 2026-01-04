from pathlib import Path
import duckdb
import pandas as pd

def rank_countries_countryfile(parquet_path: Path) -> pd.DataFrame:
    con = duckdb.connect()

    # Check columns exist
    cols = con.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(parquet_path)]
    ).df()["column_name"].tolist()

    required = {"iso3_country", "end_time", "emissions_quantity"}
    missing = required - set(cols)
    if missing:
        con.close()
        raise ValueError(
            f"{parquet_path.name} is not rankable (missing columns: {sorted(missing)}). "
            "Only *_country_emissions_* files should be ranked."
        )

    # Cast emissions_quantity to DOUBLE to avoid SUM(VARCHAR)
    df = con.execute("""
        SELECT
          iso3_country,
          MAX(end_time) AS latest_end_time,
          SUM(TRY_CAST(emissions_quantity AS DOUBLE)) AS total_emissions
        FROM read_parquet(?)
        GROUP BY iso3_country
        ORDER BY total_emissions DESC NULLS LAST
    """, [str(parquet_path)]).df()

    con.close()
    return df


