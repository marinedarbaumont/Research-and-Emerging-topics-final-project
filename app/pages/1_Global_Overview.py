import sys
from pathlib import Path
import streamlit as st
import plotly.express as px
import pandas as pd

# Ensure project root is on path when running via `streamlit run`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.utils import load_csv, add_geometry_type, sidebar_filters_common, format_large_number  # noqa: E402


st.set_page_config(page_title="Global Overview", layout="wide")
st.title("Global Hotspot Overview")

data_dir = Path("outputs/tables")
global_df = load_csv(str(data_dir / "hotspots_priority_global.csv"))
clustered_df = load_csv(str(data_dir / "hotspots_clustered.csv"))

if global_df.empty:
    st.warning("Global priority file not found. Generate outputs/tables/hotspots_priority_global.csv and retry.")
    st.stop()

# Merge cluster labels if not present
if "cluster_label" not in global_df.columns and not clustered_df.empty:
    merged = pd.merge(
        global_df,
        clustered_df[["iso3_country", "geometry_ref", "cluster_label"]],
        on=["iso3_country", "geometry_ref"],
        how="left",
    )
else:
    merged = global_df.copy()

merged = add_geometry_type(merged)

filters = sidebar_filters_common(merged)

df = merged.copy()
if filters["country"]:
    df = df[df["iso3_country"] == filters["country"]]
if filters["clusters"]:
    df = df[df["cluster_label"].isin(filters["clusters"])]
if filters["geometry_types"]:
    df = df[df["geometry_type"].isin(filters["geometry_types"])]
res_min, res_max = filters["res_range"]
df = df[(df["res_share"] >= res_min) & (df["res_share"] <= res_max)]

top_n = filters["top_n"]
df_top = df.sort_values("priority_score", ascending=False).head(top_n)

# KPIs
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total emissions (filtered)", format_large_number(df["combined_emissions"].sum()))
with col2:
    st.metric("Avg residential share", f"{df['res_share'].mean():.2f}" if not df.empty else "-")
with col3:
    st.metric("Countries in view", format_large_number(df["iso3_country"].nunique()))
with col4:
    if "cluster_label" in df.columns and not df.empty:
        cluster_by_em = df.groupby("cluster_label")["combined_emissions"].sum()
        if not cluster_by_em.empty:
            top_cluster = cluster_by_em.sort_values(ascending=False).index[0]
            share = cluster_by_em.iloc[0] / max(df["combined_emissions"].sum(), 1e-9)
            st.metric(f"Emissions share ({top_cluster})", f"{share:.2%}")
        else:
            st.metric("Emissions share (top cluster)", "-")
    else:
        st.metric("Emissions share (top cluster)", "-")

st.subheader(f"Top {min(top_n, len(df_top))} hotspots")
cols = [
    "iso3_country",
    "geometry_type",
    "geometry_ref",
    "combined_emissions",
    "res_share",
    "priority_score",
]
if "cluster_label" in df_top.columns:
    cols.append("cluster_label")
st.dataframe(df_top[cols], use_container_width=True)

# Charts
chart_top = df_top.nlargest(10, "combined_emissions")
if not chart_top.empty:
    fig = px.bar(chart_top, x="geometry_ref", y="combined_emissions", color="iso3_country",
                 title="Top 10 hotspots by combined emissions")
    st.plotly_chart(fig, use_container_width=True)

country_em = df.groupby("iso3_country")["combined_emissions"].sum().reset_index().sort_values("combined_emissions", ascending=False).head(10)
if not country_em.empty:
    fig_country = px.bar(country_em, x="iso3_country", y="combined_emissions",
                         title="Top countries by combined emissions (filtered)")
    st.plotly_chart(fig_country, use_container_width=True)

hist_data = df["res_share"].dropna()
if not hist_data.empty:
    fig_hist = px.histogram(hist_data, nbins=20, title="Residential share distribution")
    st.plotly_chart(fig_hist, use_container_width=True)
