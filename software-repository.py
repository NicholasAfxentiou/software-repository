import streamlit as st
import pandas as pd
import os
import streamlit_highcharts as st_hc

# Function to load and process Excel data
def load_data(file):
    # Read the Excel file
    df = pd.read_excel(file, sheet_name="SERG_Software", engine="openpyxl")

    # Ensure data types are consistent
    df['Purchase Date'] = pd.to_datetime(df['Purchase Date'], errors='coerce')
    df['Expiration Date'] = pd.to_datetime(df['Expiration Date'], errors='coerce')
    df['Cost'] = pd.to_numeric(df['Cost'], errors='coerce')

    # Calculate days to expiration
    today = pd.Timestamp.today()
    df['Days to Expire'] = (df['Expiration Date'] - today).dt.days

    return df

# CSS for custom headers and logos
st.markdown(
    """
    <style>
        h1, h2, h3, h4, h5, h6 {
            font-weight: normal; /* Set font weight to normal */
        }
        .header-container {
            display: flex;
            align-items: center; /* Align items vertically */
            justify-content: space-between; /* Space out the left, center, and right content */
            padding: 10px 20px; /* Add padding for spacing */
        }
        .header-logo-left img, .header-logo-right img {
            width: 150px; /* Adjust logo size */
        }
        .header-title {
            font-size: 32px; /* Adjust font size for title */
            font-weight: normal; /* Set font weight to normal */
            text-align: center; /* Center align the title */
            flex-grow: 1; /* Allow title to take up remaining space */
            margin: 0 20px; /* Add spacing between logos and title */
        }
    </style>
    <div class="header-container">
        <div class="header-logo-left">
            <img src="https://static.wixstatic.com/media/55b627_e0213c85c7a44421a1a0739381374639~mv2.png/v1/crop/x_0,y_64,w_2000,h_833/fill/w_522,h_218,al_c,q_85,usm_0.66_1.00_0.01,enc_avif,quality_auto/serg-logo-transparent.png" alt="SERG Logo">
        </div>
        <h3 class="header-title">Software Management</h3>
        <div class="header-logo-right">
            <img src="https://euphyia-tech.com/wp-content/uploads/2024/07/logo.svg" alt="Euphyia Logo">
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# File uploader
st.subheader("Upload an Excel file (optional)")
uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

# Use uploaded file or fall back to default
if uploaded_file is not None:
    file_to_load = uploaded_file
    source_label = "Uploaded file"
else:
    file_to_load = "dataset/F-710-004-A Software.xlsx"
    source_label = "F-710-004-A Software.xlsx"

# Load and process data
try:
    data = load_data(file_to_load)

    # Split row into two columns
    col1, col2 = st.columns([7, 5])  # Adjust ratio as needed

    with col1:
        st.success(f"✅ Loaded data from: {source_label}")

    pdf_path = "dataset/F-710-003_Lab_Inventory.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        with col2:
            st.download_button(
                label="📄 Export: F-710-003_Lab_Inventory",
                data=pdf_bytes,
                file_name="F-710-003_Lab_Inventory.pdf",
                mime="application/pdf"
            )
    else:
        st.warning("PDF export file not found.")

except Exception as e:
    st.error(f"❌ Failed to load the Excel file: {e}")
    st.stop()

# Safeguard: Ensure necessary columns are present
if 'Cost' in data.columns and 'Software Name' in data.columns:
    # Summary statistics
    total_cost = data['Cost'].sum()
    total_licenses = data.get('Number of Licenses', pd.Series(dtype=int)).sum()
    expired_count = data.get('Expired', pd.Series(dtype=str)).str.lower().eq('yes').sum()
    expiring_soon_count = data[data['Days to Expire'] <= 30].shape[0]

    # **1. Full Software Licenses Data**
    st.header("1. Licenses Details")
    filtered_data = data[
        ['Software Name', 'Version', 'Purchase Date', 'Expiration Date', 'Expired', 'Cost', 'Days to Expire']
    ]
    st.dataframe(filtered_data)

    # **2. Licenses Expiring Soon**
    st.header("2. Licenses Expiring Soon")
    expiring_soon = data[data['Days to Expire'] <= 30]
    if not expiring_soon.empty:
        st.warning("The following licenses are expiring soon (<= 30 days):")
        st.dataframe(expiring_soon)
    else:
        st.info("No licenses are expiring within the next 30 days.")

    # **3. Cost per Software**
    st.header("3. Cost per Software")

    # Prepare data for Highcharts
    software_costs = data.groupby('Software Name')['Cost'].sum().sort_values(ascending=False)

    # Create Highcharts configuration as HTML
    chart_html = f"""
    <div id="container"></div>
    <script src="https://code.highcharts.com/highcharts.js"></script>
    <script>
    Highcharts.chart('container', {{
        chart: {{
            type: 'bar'
        }},
        title: {{
            text: 'Cost per Software'
        }},
        xAxis: {{
            categories: {software_costs.index.tolist()}
        }},
        yAxis: {{
            title: {{
                text: ''
            }}
        }},
        series: [{{
            name: 'Cost (€)',
            data: {software_costs.values.tolist()}
        }}]
    }});
    </script>
    """
    st.components.v1.html(chart_html, height=500)

else:
    st.error("The data is missing required columns (e.g., 'Cost', 'Software Name'). Please check the file.")

