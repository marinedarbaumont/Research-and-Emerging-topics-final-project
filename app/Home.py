import sys
from pathlib import Path
import streamlit as st

# Ensure project root is on path when running via `streamlit run`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from app.utils import load_csv, format_large_number  # noqa: E402


st.set_page_config(page_title="Electric Heating Planning", layout="wide")

st.title("Electric Heating Planning Dashboard")
st.markdown("""
This app highlights onsite fossil-fuel heating **hotspots** using Climate TRACE data to guide where utilities could prioritize electrification.

- **Hotspots**: administrative or functional urban areas with concentrated onsite fuel emissions.
- **geometry_ref**: an ID (e.g., `ghs-fua_*` for functional urban areas, `gadm_*` for administrative regions). Names are not provided; mapping to names would require an external lookup (not included here).
- No maps are shown because reliable lat/lon is not available.
""")

st.info("""
Run locally:
```
pip install streamlit plotly pandas scikit-learn
streamlit run app/Home.py
```
""")

data_dir = Path("outputs/tables")
global_priority = load_csv(str(data_dir / "hotspots_priority_global.csv"))
clustered = load_csv(str(data_dir / "hotspots_clustered.csv"))

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Hotspots (global file)", format_large_number(len(global_priority)))
with col2:
    n_countries = global_priority["iso3_country"].nunique() if not global_priority.empty else 0
    st.metric("Countries covered", format_large_number(n_countries))
with col3:
    k_selected = clustered["k_selected"].iloc[0] if "k_selected" in clustered and not clustered.empty else "N/A"
    st.metric("Clusters (k selected)", k_selected)
with col4:
    sil = clustered["silhouette_score_selected"].iloc[0] if "silhouette_score_selected" in clustered and not clustered.empty else "N/A"
    st.metric("Silhouette score", f"{sil:.3f}" if isinstance(sil, (int, float)) else sil)

st.markdown("""
**Navigation guidance**
- Start with **Global Overview** to see the largest hotspots and their characteristics.
- Use **Country Drilldown** for within-country prioritization.
- Explore **Cluster Explorer** to understand hotspot archetypes and suggested strategies.
- See **Data Dictionary** for column definitions and limitations.
""")
