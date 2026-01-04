from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def _select_k_silhouette(X: np.ndarray, k_min: int, k_max: int, random_state: int) -> Tuple[int, float]:
    """Pick k with highest silhouette score in [k_min, k_max]."""
    best_k = k_min
    best_score = -1.0
    for k in range(k_min, k_max + 1):
        if k <= 1 or k >= len(X):
            continue  # silhouette needs 2 <= k < n_samples
        km = KMeans(n_clusters=k, n_init="auto", random_state=random_state)
        labels = km.fit_predict(X)
        score = silhouette_score(X, labels)
        if score > best_score:
            best_score = score
            best_k = k
    # Fallback: if no valid k tried (very small dataset), default to k_min
    if best_score < 0:
        best_k = max(k_min, 2) if len(X) >= 2 else 1
        best_score = -1.0
    return best_k, best_score


def _label_cluster(mean_res_share: float, median_emissions: float, overall_median: float) -> str:
    """
    Assign a human-readable label based on residential share and emissions magnitude.
    Simple deterministic rules to aid planning conversations.
    """
    high_emissions = median_emissions >= overall_median
    if mean_res_share >= 0.8 and high_emissions:
        return "Residential-dominant high"
    if mean_res_share >= 0.8:
        return "Residential-dominant moderate"
    if mean_res_share <= 0.4 and high_emissions:
        return "Non-residential heavy high"
    if mean_res_share <= 0.4:
        return "Non-residential heavy moderate"
    if high_emissions:
        return "Mixed high"
    return "Mixed moderate"


def cluster_hotspots(
    combined_hotspots_csv: Path,
    output_clustered_csv: Path,
    output_cluster_summary_csv: Path,
    k_min: int = 3,
    k_max: int = 10,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Cluster hotspots into archetypes using KMeans with silhouette-based k selection.

    Features: log emissions (total/res/nonres), res_share (clipped), and log sources.
    Returns (clustered_df, summary_df) and writes both CSVs for planning use.
    """
    df = pd.read_csv(combined_hotspots_csv)

    # Prepare numeric inputs; fill missing to keep robust on sparse data
    for col in [
        "combined_emissions",
        "res_emissions",
        "nonres_emissions",
        "combined_n_sources",
        "res_share",
    ]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0)

    df["res_share"] = df["res_share"].clip(0, 1)

    features = pd.DataFrame({
        "log_emissions": np.log1p(df["combined_emissions"]),
        "res_share": df["res_share"],
        "log_res_emissions": np.log1p(df["res_emissions"]),
        "log_nonres_emissions": np.log1p(df["nonres_emissions"]),
        "log_sources": np.log1p(df["combined_n_sources"]),
    })

    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    # Select k by silhouette
    k_selected, silhouette_selected = _select_k_silhouette(
        X, k_min=k_min, k_max=k_max, random_state=random_state
    )

    kmeans = KMeans(n_clusters=k_selected, n_init="auto", random_state=random_state)
    cluster_ids = kmeans.fit_predict(X)
    df["cluster_id"] = cluster_ids
    df["k_selected"] = k_selected
    df["silhouette_score_selected"] = silhouette_selected

    # Build summary stats for interpretability
    overall_emissions = df["combined_emissions"].sum()
    overall_median_emissions = df["combined_emissions"].median()

    summary = df.groupby("cluster_id").agg(
        n_hotspots=("geometry_ref", "count"),
        sum_combined_emissions=("combined_emissions", "sum"),
        median_combined_emissions=("combined_emissions", "median"),
        mean_res_share=("res_share", "mean"),
        median_res_share=("res_share", "median"),
    ).reset_index()

    summary["share_of_hotspots"] = summary["n_hotspots"] / len(df)
    summary["share_of_total_emissions"] = summary["sum_combined_emissions"] / max(overall_emissions, 1e-9)

    summary["cluster_label"] = summary.apply(
        lambda row: _label_cluster(
            mean_res_share=row["mean_res_share"],
            median_emissions=row["median_combined_emissions"],
            overall_median=overall_median_emissions,
        ),
        axis=1,
    )

    # Attach labels back to full df
    label_map = dict(zip(summary["cluster_id"], summary["cluster_label"]))
    df["cluster_label"] = df["cluster_id"].map(label_map)

    # Save outputs
    output_clustered_csv.parent.mkdir(parents=True, exist_ok=True)
    df_sorted = df.sort_values("combined_emissions", ascending=False)
    df_sorted.to_csv(output_clustered_csv, index=False)

    summary_sorted = summary.sort_values("share_of_total_emissions", ascending=False)
    summary_sorted.to_csv(output_cluster_summary_csv, index=False)

    return df_sorted, summary_sorted
