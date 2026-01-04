from pathlib import Path
import duckdb


def csv_to_parquet(csv_path: Path, parquet_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path.resolve()}")

    parquet_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    try:
        csv_str = str(csv_path)
        pq_str = str(parquet_path)

        # Robust CSV parsing:
        # - Force quote/escape to handle commas inside quotes
        # - sample_size=-1 to scan the whole file for consistent dialect
        # - all_varchar=true to avoid brittle type inference on huge files
        # - strict_mode=false to be more forgiving
        con.execute(f"""
            COPY (
                SELECT *
                FROM read_csv(
                    '{csv_str}',
                    header=true,
                    delim=',',
                    quote='"',
                    escape='"',
                    sample_size=-1,
                    all_varchar=true,
                    strict_mode=false
                )
            )
            TO '{pq_str}' (FORMAT PARQUET, COMPRESSION ZSTD);
        """)
    finally:
        con.close()

