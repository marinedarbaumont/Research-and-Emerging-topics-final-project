import sys
from pathlib import Path
import streamlit as st

# Ensure project root is on path when running via `streamlit run`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

st.set_page_config(page_title="Data Dictionary", layout="wide")
st.title("Data Dictionary")

st.markdown("""
**Glossary**
- `iso3_country`: ISO 3166-1 alpha-3 country code.
- `geometry_ref`: spatial identifier (no names included).
  - `ghs-fua_*`: functional urban areas (Global Human Settlement).
  - `gadm_*`: administrative regions (GADM).
- `res_share`: residential share of combined emissions (0-1).
- `priority_score`: global priority metric (log emissions * residential multiplier).
- `priority_score_country`: country-normalized priority metric.
- `cluster_label`: ML-assigned hotspot archetype for planning context.

**Notes**
- Mapping `geometry_ref` to place names would require external lookup tables (not included here).
- Emissions are onsite fossil fuel heating emissions (co2e_100yr metric).
- Some geometries may appear only in residential or non-residential sources; combined tables use outer joins.
""")
