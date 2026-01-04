from pathlib import Path
import numpy as np
import pandas as pd


def compute_priority_scores(
    combined_hotspots_csv: Path,
    output_csv: Path,
    top_k_global: int = 500,
    top_k_per_country: int = 50
) -> pd.DataFrame:
    """
    Compute global and within-country priority scores for hotspot geometries.

    Scores favor higher emissions and residential-heavy areas (via R multiplier).
    Writes two CSVs:
      - output_csv: top K globally by priority_score
      - <output_csv.parent>/hotspots_priority_by_country.csv: top K per country
    """
    df = pd.read_csv(combined_hotspots_csv)

    # Ensure numeric fields are usable; treat missing as zero
    numeric_cols = [
        "combined_emissions",
        "res_emissions",
        "nonres_emissions",
        "res_share",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0)

    # Clip residential share to valid bounds for the multiplier
    df["res_share"] = df["res_share"].clip(lower=0, upper=1)

    R = 0.7 + 0.6 * df["res_share"]
    E = np.log1p(df["combined_emissions"])
    df["priority_score"] = E * R

    # Country-normalized score using min-max within each iso3_country
    E_country = E
    min_e = df.groupby("iso3_country")["combined_emissions"].transform(
        lambda s: np.log1p(s.min())
    )
    max_e = df.groupby("iso3_country")["combined_emissions"].transform(
        lambda s: np.log1p(s.max())
    )
    denom = (max_e - min_e).replace(0, np.nan)
    df["priority_score_country"] = ((E_country - min_e) / denom).fillna(0) * R

    # Ranks (dense) for interpretability
    df["priority_rank_global"] = df["priority_score"].rank(
        method="dense", ascending=False
    ).astype(int)
    df["priority_rank_country"] = df.groupby("iso3_country")[
        "priority_score_country"
    ].rank(method="dense", ascending=False).astype(int)

    ordered_cols = [
        "iso3_country",
        "geometry_ref",
        "combined_emissions",
        "res_emissions",
        "nonres_emissions",
        "res_share",
        "priority_score",
        "priority_rank_global",
        "priority_score_country",
        "priority_rank_country",
        "latest_end_time",
    ]

    df = df[ordered_cols]
    df_sorted = df.sort_values("priority_score", ascending=False)

    # Global top-K
    global_top = df_sorted.head(top_k_global)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    global_top.to_csv(output_csv, index=False)

    # Per-country top-K by country-normalized score
    by_country = (
        df.sort_values(["iso3_country", "priority_score_country"], ascending=[True, False])
        .groupby("iso3_country")
        .head(top_k_per_country)
    )
    by_country_path = output_csv.parent / "hotspots_priority_by_country.csv"
    by_country.to_csv(by_country_path, index=False)

    return df_sorted
