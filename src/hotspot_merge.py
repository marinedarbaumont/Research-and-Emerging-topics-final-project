from pathlib import Path
import pandas as pd


def merge_hotspot_tables(
    residential_csv: Path,
    non_residential_csv: Path
) -> pd.DataFrame:
    """
    Merge residential and non-residential hotspot tables on iso3_country + geometry_ref.

    Missing emissions/source counts are treated as zero, and combined/share metrics are
    computed safely. Result is sorted by combined_emissions descending.
    """
    res_df = pd.read_csv(residential_csv)
    nonres_df = pd.read_csv(non_residential_csv)

    # Rename for clarity before join
    res_df = res_df.rename(columns={
        "total_emissions": "res_emissions",
        "n_sources": "res_n_sources",
        "latest_end_time": "res_latest_end_time",
    })
    nonres_df = nonres_df.rename(columns={
        "total_emissions": "nonres_emissions",
        "n_sources": "nonres_n_sources",
        "latest_end_time": "nonres_latest_end_time",
    })

    merged = pd.merge(
        res_df,
        nonres_df,
        on=["iso3_country", "geometry_ref"],
        how="outer",
    )

    # Normalize numeric fields to numeric types and fill missing with zero
    numeric_cols = [
        "res_emissions",
        "nonres_emissions",
        "res_n_sources",
        "nonres_n_sources",
    ]
    for col in numeric_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    merged["combined_emissions"] = (
        merged["res_emissions"] + merged["nonres_emissions"]
    )
    merged["combined_n_sources"] = (
        merged["res_n_sources"] + merged["nonres_n_sources"]
    )

    # Safe share calculations; when combined_emissions is zero, set shares to zero
    merged["res_share"] = merged["res_emissions"].where(
        merged["combined_emissions"] > 0, 0
    ) / merged["combined_emissions"].where(
        merged["combined_emissions"] > 0, 1
    )
    merged["nonres_share"] = merged["nonres_emissions"].where(
        merged["combined_emissions"] > 0, 0
    ) / merged["combined_emissions"].where(
        merged["combined_emissions"] > 0, 1
    )

    # Latest end time per geometry across both datasets; coerce to datetime to compare
    latest_dt = pd.concat(
        [
            pd.to_datetime(merged["res_latest_end_time"], errors="coerce"),
            pd.to_datetime(merged["nonres_latest_end_time"], errors="coerce"),
        ],
        axis=1,
    ).max(axis=1)
    merged["latest_end_time"] = latest_dt.dt.strftime("%Y-%m-%dT%H:%M:%S")
    merged["latest_end_time"] = merged["latest_end_time"].fillna("")

    ordered_cols = [
        "iso3_country",
        "geometry_ref",
        "res_emissions",
        "nonres_emissions",
        "combined_emissions",
        "res_share",
        "nonres_share",
        "res_n_sources",
        "nonres_n_sources",
        "combined_n_sources",
        "latest_end_time",
    ]

    merged = merged[ordered_cols].sort_values(
        "combined_emissions",
        ascending=False,
    )

    return merged.reset_index(drop=True)
