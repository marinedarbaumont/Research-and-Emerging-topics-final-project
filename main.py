from src.config import Paths
from src.ingest import csv_to_parquet
from src.analysis import rank_countries_countryfile
from src.eda import missing_value_summary
from src.hotspots import aggregate_hotspots_by_geometry
from src.hotspot_merge import merge_hotspot_tables
from src.priority_score import compute_priority_scores
from src.ml_hotspot_clustering import cluster_hotspots

def process_file(paths: Paths, fname: str) -> None:
    csv_path = paths.raw / fname
    pq_path = paths.processed / fname.replace(".csv", ".parquet")

    (paths.outputs / "tables").mkdir(parents=True, exist_ok=True)
    paths.processed.mkdir(parents=True, exist_ok=True)

    # Ingest
    if not pq_path.exists():
        csv_to_parquet(csv_path, pq_path)
        print(f"Parquet created: {pq_path}")
    else:
        print(f"Parquet exists, skipping ingest: {pq_path}")

    # EDA always
    eda_df = missing_value_summary(pq_path)
    eda_out = paths.outputs / "tables" / f"eda_missing_{pq_path.stem}.csv"
    eda_df.to_csv(eda_out, index=False)
    print(f"Saved: {eda_out}")

    # Ranking only for country emissions files
    if "_country_emissions_" in fname:
        ranking_df = rank_countries_countryfile(pq_path)
        ranking_out = paths.outputs / "tables" / f"ranking_{pq_path.stem}.csv"
        ranking_df.to_csv(ranking_out, index=False)
        print(f"Saved: {ranking_out}")
    else:
        print("Skipping ranking (not a *_country_emissions_* file).")

def generate_hotspots(paths: Paths) -> None:
    # Only emissions_sources files are aggregated for hotspots
    targets = {
        "residential-onsite-fuel-usage_emissions_sources_v4_7_1.parquet": "hotspots_residential_geometry.csv",
        "non-residential-onsite-fuel-usage_emissions_sources_v4_7_1.parquet": "hotspots_non_residential_geometry.csv",
    }

    for pq_name, out_name in targets.items():
        pq_path = paths.processed / pq_name
        if not pq_path.exists():
            print(f"Skipping hotspots (missing Parquet): {pq_path}")
            continue

        hotspots_df = aggregate_hotspots_by_geometry(pq_path)
        out_path = paths.outputs / "tables" / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        hotspots_df.to_csv(out_path, index=False)
        print(f"Saved hotspots: {out_path}")

def generate_combined_hotspots(paths: Paths) -> None:
    # Merge the already-produced hotspot CSVs (no re-aggregation from Parquet)
    out_dir = paths.outputs / "tables"
    residential_csv = out_dir / "hotspots_residential_geometry.csv"
    non_residential_csv = out_dir / "hotspots_non_residential_geometry.csv"

    if not residential_csv.exists() or not non_residential_csv.exists():
        print("Skipping combined hotspots (one of the hotspot CSVs is missing).")
        return

    combined_df = merge_hotspot_tables(residential_csv, non_residential_csv)
    out_path = out_dir / "hotspots_combined_geometry.csv"
    combined_df.to_csv(out_path, index=False)
    print(f"Saved combined hotspots: {out_path}")

def generate_priority_scores(paths: Paths) -> None:
    # Derive priority rankings from the merged hotspots CSV
    input_csv = paths.outputs / "tables" / "hotspots_combined_geometry.csv"
    if not input_csv.exists():
        print("Skipping priority scores (missing combined hotspots CSV).")
        return

    global_out = paths.outputs / "tables" / "hotspots_priority_global.csv"
    compute_priority_scores(
        combined_hotspots_csv=input_csv,
        output_csv=global_out,
        top_k_global=500,
        top_k_per_country=50,
    )
    print(f"Saved priority scores (global): {global_out}")
    print(f"Saved priority scores (per country): {global_out.parent / 'hotspots_priority_by_country.csv'}")

def run_hotspot_clustering(paths: Paths) -> None:
    # Cluster hotspots into archetypes to guide differentiated electrification strategies
    input_csv = paths.outputs / "tables" / "hotspots_combined_geometry.csv"
    if not input_csv.exists():
        print("Skipping clustering (missing combined hotspots CSV).")
        return

    clustered_out = paths.outputs / "tables" / "hotspots_clustered.csv"
    summary_out = paths.outputs / "tables" / "hotspots_cluster_summary.csv"
    cluster_hotspots(
        combined_hotspots_csv=input_csv,
        output_clustered_csv=clustered_out,
        output_cluster_summary_csv=summary_out,
        k_min=3,
        k_max=10,
        random_state=42,
    )
    print(f"Saved clustered hotspots: {clustered_out}")
    print(f"Saved cluster summary: {summary_out}")


def main() -> None:
    paths = Paths()

    files = [
        "non-residential-onsite-fuel-usage_country_emissions_v4_7_1.csv",
        "non-residential-onsite-fuel-usage_emissions_sources_confidence_v4_7_1.csv",
        "non-residential-onsite-fuel-usage_emissions_sources_v4_7_1.csv",
        "other-onsite-fuel-usage_country_emissions_v4_7_1.csv",
        "residential-onsite-fuel-usage_country_emissions_v4_7_1.csv",
        "residential-onsite-fuel-usage_emissions_sources_confidence_v4_7_1.csv",
        "residential-onsite-fuel-usage_emissions_sources_v4_7_1.csv",
    ]

    for fname in files:
        print("\n" + "=" * 80)
        print(f"Processing: {fname}")
        process_file(paths, fname)

    print("\n" + "=" * 80)
    print("Aggregating hotspots by geometry")
    generate_hotspots(paths)
    generate_combined_hotspots(paths)
    generate_priority_scores(paths)
    run_hotspot_clustering(paths)

    print("\nDone ✅")


if __name__ == "__main__":
    main()
