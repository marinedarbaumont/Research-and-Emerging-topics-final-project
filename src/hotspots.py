from pathlib import Path
import duckdb
import pandas as pd


def aggregate_hotspots_by_geometry(parquet_path: Path) -> pd.DataFrame:
    """
    Aggregate onsite fuel emissions by administrative geometry using DuckDB.

    Returns a DataFrame with iso3_country, geometry_ref, total_emissions,
    n_sources, and latest_end_time sorted by total_emissions (DESC).
    """
    con = duckdb.connect()
    try:
        cols = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(parquet_path)]
        ).df()["column_name"].tolist()

        required = {
            "iso3_country",
            "geometry_ref",
            "emissions_quantity",
            "source_id",
            "end_time",
        }
        missing = required - set(cols)
        if missing:
            raise ValueError(
                f"{parquet_path.name} is missing required columns: {sorted(missing)}"
            )

        # Compute aggregates without loading full dataset into pandas
        query = """
            SELECT
                iso3_country,
                geometry_ref,
                SUM(TRY_CAST(emissions_quantity AS DOUBLE)) AS total_emissions,
                COUNT(DISTINCT source_id) AS n_sources,
                MAX(end_time) AS latest_end_time
            FROM read_parquet(?)
            WHERE iso3_country IS NOT NULL
              AND geometry_ref IS NOT NULL
            GROUP BY iso3_country, geometry_ref
            ORDER BY total_emissions DESC NULLS LAST
        """
        df = con.execute(query, [str(parquet_path)]).df()
        return df
    finally:
        con.close()
