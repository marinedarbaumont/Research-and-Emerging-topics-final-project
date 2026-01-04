import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import pandas as pd

# Ensure project root is on path when running via `streamlit run`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.utils import load_csv, add_geometry_type, format_large_number  # noqa: E402


st.set_page_config(page_title="Country Drilldown", layout="wide")
st.title("Country Drilldown")

data_dir = Path("outputs/tables")
country_df = load_csv(str(data_dir / "hotspots_priority_by_country.csv"))
clustered_df = load_csv(str(data_dir / "hotspots_clustered.csv"))

if country_df.empty:
    st.warning("Country priority file not found. Generate outputs/tables/hotspots_priority_by_country.csv and retry.")
    st.stop()

# Merge cluster labels if available
if "cluster_label" not in country_df.columns and not clustered_df.empty:
    country_df = pd.merge(
        country_df,
        clustered_df[["iso3_country", "geometry_ref", "cluster_label"]],
        on=["iso3_country", "geometry_ref"],
        how="left",
    )

country_df = add_geometry_type(country_df)

countries = sorted(country_df["iso3_country"].dropna().unique())
country = st.sidebar.selectbox("Country", countries)
rank_mode = st.sidebar.selectbox(
    "Ranking mode",
    ["priority_score_country", "combined_emissions", "nonres_emissions"],
    index=0,
)
top_k = st.sidebar.slider("Top K", 5, 200, 20)
geometry_types = sorted(country_df["geometry_type"].dropna().unique())
geom_choice = st.sidebar.multiselect("Geometry type", geometry_types, default=geometry_types)

df = country_df[country_df["iso3_country"] == country]
if geom_choice:
    df = df[df["geometry_type"].isin(geom_choice)]

df = df.sort_values(rank_mode, ascending=False).head(top_k)

# KPIs
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total combined emissions", format_large_number(df["combined_emissions"].sum()))
with col2:
    st.metric("Mean residential share", f"{df['res_share'].mean():.2f}" if not df.empty else "-")
with col3:
    st.metric("Hotspots shown", format_large_number(len(df)))
with col4:
    top_hotspot = df.iloc[0]["geometry_ref"] if not df.empty else "-"
    st.metric("Highest priority hotspot", top_hotspot)

st.subheader(f"Top {len(df)} hotspots in {country}")
cols = [
    "geometry_type",
    "geometry_ref",
    "combined_emissions",
    "res_emissions",
    "nonres_emissions",
    "res_share",
    "priority_rank_country",
]
if "cluster_label" in df.columns:
    cols.append("cluster_label")
st.dataframe(df[cols], use_container_width=True)

# Charts
if not df.empty:
    bar_stack = px.bar(
        df,
        x="geometry_ref",
        y=["res_emissions", "nonres_emissions"],
        title="Residential vs Non-residential emissions (Top K)",
    )
    st.plotly_chart(bar_stack, use_container_width=True)

    bar_combined = px.bar(df, x="geometry_ref", y="combined_emissions",
                          title="Combined emissions (Top K)")
    st.plotly_chart(bar_combined, use_container_width=True)

    if "cluster_label" in df.columns:
        cluster_counts = df.groupby("cluster_label")["geometry_ref"].count().reset_index(name="count")
        fig_cluster = px.bar(cluster_counts, x="cluster_label", y="count", title="Cluster composition (count)")
        st.plotly_chart(fig_cluster, use_container_width=True)
