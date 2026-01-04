import sys
from pathlib import Path
import streamlit as st
import plotly.express as px

# Ensure project root is on path when running via `streamlit run`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.utils import load_csv, add_geometry_type, format_large_number  # noqa: E402


st.set_page_config(page_title="Cluster Explorer", layout="wide")
st.title("Cluster Explorer")

data_dir = Path("outputs/tables")
clustered_df = load_csv(str(data_dir / "hotspots_clustered.csv"))
summary_df = load_csv(str(data_dir / "hotspots_cluster_summary.csv"))

if clustered_df.empty or summary_df.empty:
    st.warning("Clustered data not found. Generate hotspots_clustered.csv and hotspots_cluster_summary.csv and retry.")
    st.stop()

clustered_df = add_geometry_type(clustered_df)

cluster_options = summary_df["cluster_label"] if "cluster_label" in summary_df.columns else summary_df["cluster_id"]
cluster_options = cluster_options.dropna().unique()
selected_cluster = st.selectbox("Cluster", cluster_options)
top_n = st.slider("Top N hotspots", 10, 500, 50)

countries = sorted(clustered_df["iso3_country"].dropna().unique())
country_filter = st.multiselect("Filter by country (optional)", countries)

summary_sel = summary_df[
    (summary_df["cluster_label"] == selected_cluster) if "cluster_label" in summary_df.columns else (summary_df["cluster_id"] == selected_cluster)
]
if summary_sel.empty:
    st.warning("Selected cluster not found in summary.")
    st.stop()

row = summary_sel.iloc[0]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Hotspots in cluster", format_large_number(row.get("n_hotspots", 0)))
with col2:
    st.metric("Share of total emissions", f"{row.get('share_of_total_emissions', 0):.2%}")
with col3:
    st.metric("Median combined emissions", format_large_number(row.get("median_combined_emissions", 0)))
with col4:
    st.metric("Mean residential share", f"{row.get('mean_res_share', 0):.2f}")

st.subheader("Emissions share by cluster")
fig_share = px.bar(
    summary_df.sort_values("share_of_total_emissions", ascending=False),
    x="cluster_label" if "cluster_label" in summary_df.columns else "cluster_id",
    y="share_of_total_emissions",
    title="Share of total emissions by cluster",
)
st.plotly_chart(fig_share, use_container_width=True)

filtered = clustered_df.copy()
if country_filter:
    filtered = filtered[filtered["iso3_country"].isin(country_filter)]

cluster_col = "cluster_label" if "cluster_label" in clustered_df.columns else "cluster_id"
filtered = filtered[filtered[cluster_col] == selected_cluster]
filtered = filtered.sort_values("combined_emissions", ascending=False).head(top_n)

if not filtered.empty:
    st.subheader(f"Top {len(filtered)} hotspots in cluster")
    cols = [
        "iso3_country",
        "geometry_type",
        "geometry_ref",
        "combined_emissions",
        "res_share",
    ]
    if "priority_rank_global" in filtered.columns:
        cols.append("priority_rank_global")
    st.dataframe(filtered[cols], use_container_width=True)

    fig_box = px.box(clustered_df, x=cluster_col, y="combined_emissions", title="Combined emissions by cluster")
    st.plotly_chart(fig_box, use_container_width=True)

# Recommended strategy text
strategy = "General electrification strategy"
if isinstance(selected_cluster, str):
    label = selected_cluster
else:
    label = row.get("cluster_label", "")

if "Residential-dominant high" in label:
    strategy = "Emphasize heat pumps and distribution grid reinforcement; accelerate residential building retrofits."
elif "Residential-dominant" in label:
    strategy = "Residential heat pumps plus targeted envelope improvements."
elif "Non-residential heavy" in label:
    strategy = "Focus on commercial retrofits, building management systems, and process heat electrification."
elif "Mixed" in label:
    strategy = "Consider district heating or hybrid electrification combining residential and commercial measures."

st.info(f"Recommended strategy: {strategy}")
