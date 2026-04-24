import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
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
.block-container {
    padding-top: 2rem;
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

borough["borough"] = borough["borough"].astype(str).str.upper().str.strip()
agency["agency_group"] = agency["agency_group"].astype(str).str.upper().str.strip()

name_map = {
    "STATEN ISLAND": "Staten Island",
    "BROOKLYN": "Brooklyn",
    "QUEENS": "Queens",
    "BRONX": "Bronx",
    "MANHATTAN": "Manhattan"
}

lookup = borough.set_index("borough").to_dict("index")

for feature in geojson["features"]:
    boro = feature["properties"]["BoroName"]

    key = None
    for k, v in name_map.items():
        if v == boro:
            key = k

    metrics = lookup.get(key, {})

    feature["properties"]["complaints"] = int(metrics.get("complaints", 0))
    feature["properties"]["avg_resolution_days"] = round(float(metrics.get("avg_resolution_days", 0)), 2)

    val = metrics.get("complaints", 0)
    feature["properties"]["color"] = [255, 215, 0, min(230, max(80, int(val / 30000)))]

# LOGO / HERO
col1, col2, col3 = st.columns([2,4,1])

with col1:
    st.image("T51-NB2.png", width=400)

with col2:
    st.markdown("""
    <div style="display:flex; flex-direction:column; justify-content:center; height:100%;">
        <h1 style='margin-bottom:5px;'>NYC 311 Analytics Tracker</h1>
        <h3 style='margin-top:0; color:#FFD700;'>Clarity at the highest level</h3>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.image("nyc311-logo.png", width=120)

st.title("Team 51 - 498 Capstone")
st.caption("Harrison Karp - Elizabeth Conwell - Rachel Nugent - Christopher Lee - Jimena Navarro")

total = borough["complaints"].sum()
avg = (borough["avg_resolution_days"] * borough["complaints"]).sum() / total
top_borough = borough.sort_values("complaints", ascending=False).iloc[0]["borough"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Complaints", f"{total:,.0f}")
c2.metric("Avg Resolution Days", f"{avg:.2f}")
c3.metric("Boroughs", borough["borough"].nunique())
c4.metric("Top Volume Borough", top_borough)

st.markdown("""
### 🔎 Key Insight  
Workload and resolution times are not evenly distributed across the 311 system.  
A small number of boroughs and agencies drive a large share of operational pressure.
""")

st.divider()

# MAP
st.subheader("Interactive NYC Borough Map")

layer = pdk.Layer(
    "GeoJsonLayer",
    geojson,
    pickable=True,
    filled=True,
    stroked=True,
    get_fill_color="properties.color",
    get_line_color=[230, 230, 230],
    get_line_width=60
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
        Complaints: <b>{complaints}</b><br/>
        Avg Resolution Days: <b>{avg_resolution_days}</b>
        """,
        "style": {"backgroundColor": "black", "color": "white"}
    }
))

st.divider()

# CHART HELPERS
chart_bg = "#050505"
axis_color = "#F5F5F5"
grid_color = "#333333"

def theme_chart(chart):
    return chart.configure_view(
        strokeWidth=0
    ).configure_axis(
        labelColor=axis_color,
        titleColor=axis_color,
        gridColor=grid_color
    ).configure_title(
        color=axis_color,
        fontSize=18
    )

borough_chart = borough.sort_values("complaints", ascending=False)

left, right = st.columns(2)

with left:
    st.subheader("Complaints by Borough")
    chart1 = alt.Chart(borough_chart).mark_bar(color="#FFD700").encode(
        x=alt.X("borough:N", sort="-y", title="Borough"),
        y=alt.Y("complaints:Q", title="Total Complaints"),
        tooltip=[
            alt.Tooltip("borough:N", title="Borough"),
            alt.Tooltip("complaints:Q", title="Complaints", format=",")
        ]
    ).properties(height=360)
    st.altair_chart(theme_chart(chart1), use_container_width=True)

with right:
    st.subheader("Resolution Time by Borough")
    chart2 = alt.Chart(borough_chart).mark_bar(color="#9CA3AF").encode(
        x=alt.X("borough:N", sort="-y", title="Borough"),
        y=alt.Y("avg_resolution_days:Q", title="Avg Resolution Days"),
        tooltip=[
            alt.Tooltip("borough:N", title="Borough"),
            alt.Tooltip("avg_resolution_days:Q", title="Avg Days", format=".2f")
        ]
    ).properties(height=360)
    st.altair_chart(theme_chart(chart2), use_container_width=True)

st.divider()

# AGENCY CHARTS
top_agency = agency.sort_values("complaints", ascending=False).head(10)
worst_agency = agency.sort_values("avg_resolution_days", ascending=False).head(10)

left2, right2 = st.columns(2)

with left2:
    st.subheader("Top Agencies by Complaint Volume")
    chart3 = alt.Chart(top_agency).mark_bar(color="#FFD700").encode(
        x=alt.X("complaints:Q", title="Total Complaints"),
        y=alt.Y("agency_group:N", sort="-x", title="Agency"),
        tooltip=[
            alt.Tooltip("agency_group:N", title="Agency"),
            alt.Tooltip("complaints:Q", title="Complaints", format=",")
        ]
    ).properties(height=380)
    st.altair_chart(theme_chart(chart3), use_container_width=True)

with right2:
    st.subheader("Agencies with Longest Resolution Time")
    chart4 = alt.Chart(worst_agency).mark_bar(color="#B0B0B0").encode(
        x=alt.X("avg_resolution_days:Q", title="Avg Resolution Days"),
        y=alt.Y("agency_group:N", sort="-x", title="Agency"),
        tooltip=[
            alt.Tooltip("agency_group:N", title="Agency"),
            alt.Tooltip("avg_resolution_days:Q", title="Avg Days", format=".2f")
        ]
    ).properties(height=380)
    st.altair_chart(theme_chart(chart4), use_container_width=True)

st.divider()

st.subheader("Agency Efficiency: Volume vs Resolution Time")

scatter = alt.Chart(agency).mark_circle(
    size=120,
    color="#FFD700",
    opacity=0.75
).encode(
    x=alt.X("complaints:Q", title="Total Complaints"),
    y=alt.Y("avg_resolution_days:Q", title="Avg Resolution Days"),
    tooltip=[
        alt.Tooltip("agency_group:N", title="Agency"),
        alt.Tooltip("complaints:Q", title="Complaints", format=","),
        alt.Tooltip("avg_resolution_days:Q", title="Avg Days", format=".2f")
    ]
).properties(height=430)

st.altair_chart(theme_chart(scatter), use_container_width=True)

worst = agency.sort_values("avg_resolution_days", ascending=False).iloc[0]
highest_volume = agency.sort_values("complaints", ascending=False).iloc[0]

st.markdown(f"""
### Operational Readout  
- **{highest_volume['agency_group']}** handles the highest complaint volume.  
- **{worst['agency_group']}** shows the longest average resolution time.  
- This suggests that workload pressure and delay risk are driven by different operational patterns.
""")

st.divider()

st.subheader("Agency Performance Table")
st.dataframe(
    agency.sort_values("complaints", ascending=False),
    use_container_width=True
)

st.caption("Built by Team 51 using Python, Streamlit, GitHub, Parquet, PyDeck, and NYC 311 data.")
