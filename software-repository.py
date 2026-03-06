"""
Software Repository – Streamlit app for software license management.
Optimized for performance, structure, and maintainability.
"""
import base64
import json
from pathlib import Path

import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# Configuration & constants
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = BASE_DIR / "dataset" / "F-710-004-A Software.xlsx"
DEFAULT_PDF_PATH = BASE_DIR / "dataset" / "F-710-003_Lab_Inventory.pdf"
EUPHYIA_LOGO_PATH = BASE_DIR / "logo" / "Euphyia-png.PNG"
SHEET_NAME = "SERG_Software"
EXPIRING_DAYS_THRESHOLD = 30

HEADER_CSS = """
h1, h2, h3, h4, h5, h6 { font-weight: normal; }
.header-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 20px;
}
.header-logo-left img, .header-logo-right img { width: 150px; }
.header-title {
    font-size: 32px;
    font-weight: normal;
    text-align: center;
    flex-grow: 1;
    margin: 0 20px;
}
"""

# -----------------------------------------------------------------------------
# Data loading (cached when reading from path)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def _load_data_from_path(path: str):
    """Load and process Excel from file path. Cached to avoid repeated disk reads."""
    df = pd.read_excel(path, sheet_name=SHEET_NAME, engine="openpyxl")
    return _process_dataframe(df)


def _process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize types and compute derived columns."""
    df = df.copy()
    df["Purchase Date"] = pd.to_datetime(df["Purchase Date"], errors="coerce")
    df["Expiration Date"] = pd.to_datetime(df["Expiration Date"], errors="coerce")
    df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")
    today = pd.Timestamp.today()
    df["Days to Expire"] = (df["Expiration Date"] - today).dt.days
    return df


def load_data(file):  # noqa: ANN001
    """Load and process Excel from path (str) or uploaded file. Uses cache for paths."""
    if isinstance(file, str) and Path(file).is_file():
        return _load_data_from_path(file)
    df = pd.read_excel(file, sheet_name=SHEET_NAME, engine="openpyxl")
    return _process_dataframe(df)


@st.cache_data(ttl=3600)
def _get_logo_base64_cached(path_str: str) -> str:
    """Load image from path and return as base64 data URI. Cached for performance."""
    path = Path(path_str)
    if not path.exists():
        return ""
    raw = path.read_bytes()
    data = base64.b64encode(raw).decode()
    ext = path.suffix.lower()
    mime = "image/svg+xml" if ext == ".svg" else "image/png"
    return f"data:{mime};base64,{data}"


def get_logo_base64(path: Path) -> str:
    """Return base64 data URI for logo, or empty string if file missing."""
    try:
        return _get_logo_base64_cached(str(path))
    except Exception:
        return ""


@st.cache_data(ttl=300)
def _get_cached_pdf_bytes(path_str: str) -> bytes:
    """Read PDF file from path. Cached to avoid repeated disk I/O."""
    return Path(path_str).read_bytes()


# -----------------------------------------------------------------------------
# UI: header with logos
# -----------------------------------------------------------------------------
def render_header():
    """Render the app header with SERG and Euphyia logos."""
    euphyia_src = get_logo_base64(EUPHYIA_LOGO_PATH)
    st.markdown(
        f"<style>{HEADER_CSS}</style>"
        '<div class="header-container">'
        '<div class="header-logo-left">'
        '<img src="https://static.wixstatic.com/media/55b627_e0213c85c7a44421a1a0739381374639~mv2.png/v1/crop/x_0,y_64,w_2000,h_833/fill/w_522,h_218,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/serg-logo-transparent.png" alt="SERG Logo">'
        "</div>"
        '<h3 class="header-title">Software Management</h3>'
        '<div class="header-logo-right">'
        f'<img src="{euphyia_src}" alt="Euphyia Logo">'
        "</div></div>",
        unsafe_allow_html=True,
    )


render_header()

# -----------------------------------------------------------------------------
# Main app flow
# -----------------------------------------------------------------------------
st.subheader("Upload an Excel file (optional)")
uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

if uploaded_file is not None:
    file_to_load = uploaded_file
    source_label = "Uploaded file"
else:
    file_to_load = str(DEFAULT_DATASET_PATH)
    source_label = "F-710-004-A Software.xlsx"

try:
    data = load_data(file_to_load)
    col1, col2 = st.columns([7, 5])

    with col1:
        st.success(f"✅ Loaded data from: {source_label}")

    if DEFAULT_PDF_PATH.exists():
        pdf_bytes = _get_cached_pdf_bytes(str(DEFAULT_PDF_PATH))
        with col2:
            st.download_button(
                label="📄 Export: F-710-003_Lab_Inventory",
                data=pdf_bytes,
                file_name="F-710-003_Lab_Inventory.pdf",
                mime="application/pdf",
            )
    else:
        st.warning("PDF export file not found.")

except Exception as e:
    st.error(f"❌ Failed to load the Excel file: {e}")
    st.stop()

if "Cost" in data.columns and "Software Name" in data.columns:
    LICENSE_COLUMNS = [
        "Software Name",
        "Version",
        "Purchase Date",
        "Expiration Date",
        "Expired",
        "Cost",
        "Days to Expire",
    ]

    st.header("1. Licenses Details")
    st.dataframe(data[LICENSE_COLUMNS])

    st.header("2. Licenses Expiring Soon")
    # Only show licenses that expire in the future (0–30 days), not already expired or without a date
    days = data["Days to Expire"]
    expiring_soon = data[(days >= 0) & (days <= EXPIRING_DAYS_THRESHOLD)]
    if not expiring_soon.empty:
        st.warning(f"The following licenses are expiring soon (<= {EXPIRING_DAYS_THRESHOLD} days):")
        st.dataframe(expiring_soon)
    else:
        st.info(f"No licenses are expiring within the next {EXPIRING_DAYS_THRESHOLD} days.")

    st.header("3. Cost per Software")
    software_costs = data.groupby("Software Name")["Cost"].sum().sort_values(ascending=False)
    categories_js = json.dumps(software_costs.index.tolist())
    values_js = json.dumps(software_costs.values.tolist())
    chart_html = f"""
    <div id="container"></div>
    <script src="https://cdn.jsdelivr.net/npm/highcharts@11/highcharts.min.js"></script>
    <script>
    Highcharts.chart('container', {{
        chart: {{ type: 'bar' }},
        title: {{ text: 'Cost per Software' }},
        xAxis: {{ categories: {categories_js} }},
        yAxis: {{ title: {{ text: '' }} }},
        series: [{{ name: 'Cost (€)', data: {values_js} }}]
    }});
    </script>
    """
    st.components.v1.html(chart_html, height=500)
else:
    st.error("The data is missing required columns (e.g., 'Cost', 'Software Name'). Please check the file.")

