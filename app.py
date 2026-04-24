import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(
    page_title="Team 51 | NYC 311 Dashboard",
    layout="wide"
)

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
.block-container {
    padding-top: 2rem;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    agency = pd.read_parquet("agency_summary.parquet")
    borough = pd.read_parquet("borough_summary.parquet")
    return agency, borough

agency, borough = load_data()

# Clean borough names
borough["borough"] = borough["borough"].astype(str).str.upper().str.strip()

# Borough centroids
coords = pd.DataFrame({
    "borough": ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"],
    "lat": [40.7831, 40.6782, 40.7282, 40.8448, 40.5795],
    "lon": [-73.9712, -73.9442, -73.7949, -73.8648, -74.1502]
})

map_df = borough.merge(coords, on="borough", how="left").dropna(subset=["lat", "lon"])
map_df["radius"] = (map_df["complaints"] / map_df["complaints"].max()) * 25000 + 3000

st.markdown("# TEAM 51 | NYC 311 Analytics Dashboard")
st.markdown("### Clarity at the highest level")
st.caption("Closed 311 complaints — model-ready summary dashboard")

kpi1, kpi2, kpi3 = st.columns(3)

total_complaints = borough["complaints"].sum()
avg_resolution = (
    borough["avg_resolution_days"] * borough["complaints"]
).sum() / borough["complaints"].sum()

kpi1.metric("Total Complaints", f"{total_complaints:,.0f}")
kpi2.metric("Avg Resolution Days", f"{avg_resolution:.2f}")
kpi3.metric("Boroughs", f"{borough['borough'].nunique()}")

st.divider()

st.subheader("Interactive NYC Complaint Volume Map")

layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position="[lon, lat]",
    get_radius="radius",
    get_fill_color="[247, 227, 0, 150]",
    pickable=True
)

view_state = pdk.ViewState(
    latitude=40.7128,
    longitude=-74.0060,
    zoom=9.3,
    pitch=35
)

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/dark-v10",
    initial_view_state=view_state,
    layers=[layer],
    tooltip={
        "html": "<b>{borough}</b><br/>Complaints: {complaints}<br/>Avg Resolution Days: {avg_resolution_days}",
        "style": {"backgroundColor": "black", "color": "white"}
    }
))

left, right = st.columns(2)

with left:
    st.subheader("Complaints by Borough")
    borough_chart = borough.sort_values("complaints", ascending=False)
    st.bar_chart(borough_chart.set_index("borough")["complaints"])

with right:
    st.subheader("Avg Resolution Days by Borough")
    st.bar_chart(borough_chart.set_index("borough")["avg_resolution_days"])

st.divider()

st.subheader("Agency Performance")

agency = agency.sort_values("complaints", ascending=False)

agency_filter = st.multiselect(
    "Filter agencies",
    options=agency["agency_group"].unique(),
    default=list(agency["agency_group"].head(10))
)

filtered_agency = agency[agency["agency_group"].isin(agency_filter)]

st.dataframe(filtered_agency, use_container_width=True)

st.subheader("Top Agencies by Volume")
st.bar_chart(filtered_agency.set_index("agency_group")["complaints"])

st.markdown("---")
st.caption("Built by Team 51 using Python, Streamlit, GitHub, Parquet, and NYC 311 data.")
