import streamlit as st
import pandas as pd


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    """Load a CSV with caching and friendly error handling."""
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        st.warning(f"Missing file: {path}")
        return pd.DataFrame()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load {path}: {exc}")
        return pd.DataFrame()


def add_geometry_type(df: pd.DataFrame) -> pd.DataFrame:
    """Annotate geometry type based on geometry_ref convention."""
    if "geometry_ref" not in df.columns:
        return df
    def _type(ref: str) -> str:
        if isinstance(ref, str) and ref.startswith("ghs-fua"):
            return "Urban area (FUA)"
        if isinstance(ref, str) and ref.startswith("gadm"):
            return "Administrative region (GADM)"
        return "Other/Unknown"
    df = df.copy()
    df["geometry_type"] = df["geometry_ref"].apply(_type)
    return df


def format_large_number(x: float) -> str:
    """Human-friendly large number formatting for KPIs."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "-"
    if x >= 1_000_000_000:
        return f"{x/1_000_000_000:.1f}B"
    if x >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"{x/1_000:.1f}K"
    return f"{x:.0f}"


def sidebar_filters_common(df: pd.DataFrame):
    """Shared filters: country, cluster_label, geometry_type, res_share range, Top N."""
    countries = sorted(df["iso3_country"].dropna().unique()) if "iso3_country" in df else []
    country = st.sidebar.selectbox("Country (optional)", ["All"] + countries) if countries else "All"

    cluster_labels = sorted(df["cluster_label"].dropna().unique()) if "cluster_label" in df else []
    selected_clusters = st.sidebar.multiselect("Cluster label (optional)", cluster_labels) if cluster_labels else []

    geometry_types = sorted(df["geometry_type"].dropna().unique()) if "geometry_type" in df else []
    geom_choice = st.sidebar.multiselect("Geometry type", geometry_types, default=geometry_types) if geometry_types else []

    res_min, res_max = st.sidebar.slider("Residential share range", 0.0, 1.0, (0.0, 1.0), step=0.05)
    top_n = st.sidebar.slider("Top N", 10, 1000, 100 if len(df) > 100 else max(len(df), 10))

    return {
        "country": None if country == "All" else country,
        "clusters": selected_clusters,
        "geometry_types": geom_choice,
        "res_range": (res_min, res_max),
        "top_n": top_n,
    }
