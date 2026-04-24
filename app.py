import streamlit as st
import pandas as pd
import pydeck as pdk
import json

st.set_page_config(
    page_title="Team 51 | NYC 311 Tracker",
    layout="wide"
)

# THEME
st.markdown("""
<style>
.stApp {
    background-color: #050505;
    color: #F5F5F5;
}
h1, h2, h3 {
    color: #F7E300;
}
[data-testid="stMetricValue"] {
    color: #F7E300;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    agency = pd.read_parquet("agency_summary.parquet")
    borough = pd.read_parquet("borough_summary.parquet")
    with open("nyc_boroughs.geojson") as f:
        geojson = json.load(f)
    return agency, borough, geojson

agency, borough, geojson = load_data()

# NORMALIZE
borough["borough"] = borough["borough"].str.upper().str.strip()

# FIX NOMBRES
name_map = {
    "STATEN ISLAND": "Staten Island",
    "BROOKLYN": "Brooklyn",
    "QUEENS": "Queens",
    "BRONX": "Bronx",
    "MANHATTAN": "Manhattan"
}

lookup = borough.set_index("borough").to_dict("index")

# INJECT DATA INTO GEOJSON
for feature in geojson["features"]:
    boro = feature["properties"]["BoroName"]

    # reverse map
    key = None
    for k, v in name_map.items():
        if v == boro:
            key = k

    metrics = lookup.get(key, {})

    feature["properties"]["complaints"] = int(metrics.get("complaints", 0))
    feature["properties"]["avg_resolution_days"] = round(float(metrics.get("avg_resolution_days", 0)), 2)

    # color intensity
    val = metrics.get("complaints", 0)
    feature["properties"]["color"] = [247, 227, 0, min(255, int(val / 50000))]

#  LOGO
col1, col2 = st.columns([1,3])

with col1:
    st.image("T51-NB2.png", use_column_width=True)

with col2:
    st.markdown("""
    # NYC 311 Analytics Tracker  
    ### Clarity at the highest level
    """)

# HEADER
st.title("Team 51 - Northwestern University")
st.caption("Harrison Karp - Elizabeth Conwell - Rachel Nugent - Christopher Lee - Jimena Navarro")

# KPIs
c1, c2, c3 = st.columns(3)

total = borough["complaints"].sum()
avg = (borough["avg_resolution_days"] * borough["complaints"]).sum() / total

c1.metric("Total Complaints", f"{total:,.0f}")
c2.metric("Avg Resolution Days", f"{avg:.2f}")
c3.metric("Boroughs", borough["borough"].nunique())

st.divider()

#  MAP
layer = pdk.Layer(
    "GeoJsonLayer",
    geojson,
    pickable=True,
    filled=True,
    stroked=True,
    get_fill_color="properties.color",
    get_line_color=[255, 255, 255],
    get_line_width=50
)

view = pdk.ViewState(
    latitude=40.7128,
    longitude=-74.0060,
    zoom=9.2
)

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/dark-v10",
    initial_view_state=view,
    layers=[layer],
    tooltip={
        "html": """
        <b>{BoroName}</b><br/>
        Complaints: {complaints}<br/>
        Avg Days: {avg_resolution_days}
        """,
        "style": {"backgroundColor": "black", "color": "white"}
    }
))

st.divider()

#  CHARTS
left, right = st.columns(2)

with left:
    st.subheader("Complaints by Borough")
    st.bar_chart(borough.set_index("borough")["complaints"])

with right:
    st.subheader("Resolution Time by Borough")
    st.bar_chart(borough.set_index("borough")["avg_resolution_days"])

st.subheader("Agency Performance")
st.dataframe(agency.sort_values("complaints", ascending=False), use_container_width=True)
