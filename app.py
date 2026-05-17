import streamlit as st
import pandas as pd
import pydeck as pdk
import altair as alt
import json
from chatbot_utils import generate_311_response

st.markdown("""
<link rel="apple-touch-icon" sizes="180x180" href="icon.png">
<link rel="icon" type="image/png" sizes="32x32" href="icon.png">
<link rel="icon" type="image/png" sizes="16x16" href="icon.png">
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="Team 51 | NYC 311 Tracker",
    layout="wide"
)

# =========================
# THEME
# =========================
st.markdown("""
<style>
.stApp {
    background-color: #000000;
    color: #F5F5F5;
}

h1, h2, h3 {
    color: #F7E300;
}

[data-testid="stMetricValue"] {
    color: #F7E300;
}

.block-container {
    padding-top: 1.5rem;
}

div.stButton > button {
    background-color: #111111;
    color: #FFD700;
    border: 1px solid #333333;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    font-weight: 700;
}

div.stButton > button:hover {
    background-color: #FFD700;
    color: #000000;
    border: 1px solid #FFD700;
}

.section-card {
    background-color:#0D0D0D;
    border:1px solid #2E2E2E;
    border-left:6px solid #FFD700;
    padding:24px;
    border-radius:16px;
    margin-bottom:24px;
}

.mini-card {
    background-color:#111111;
    padding:20px;
    border-radius:14px;
    border:1px solid #2E2E2E;
    min-height:150px;
}
[data-testid="stRadio"] div[role="radiogroup"] {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    flex-wrap: nowrap;
}

[data-testid="stRadio"] label {
    background-color: #111111;
    color: #FFD700 !important;
    border: 1px solid #333333;
    border-radius: 999px;
    padding: 10px 18px;
    font-weight: 700;
    white-space: nowrap;
}

[data-testid="stRadio"] label:hover {
    background-color: #FFD700;
    color: #000000 !important;
}

</style>
""", unsafe_allow_html=True)


[data-testid="stRadio"] label {
    background-color: #111111;
    color: #FFD700 !important;
    border: 1px solid #333333;
    border-radius: 999px;
    padding: 10px 18px;
    font-weight: 700;
    white-space: nowrap;
}

[data-testid="stRadio"] label:hover {
    background-color: #FFD700;
    color: #000000 !important;
}
# =========================
# NAVIGATION
# =========================
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

if "saved_views" not in st.session_state:
    st.session_state.saved_views = []

nav_left, nav_right = st.columns([5, 3])

with nav_left:
    st.markdown(
        "<h3 style='margin-bottom:0; color:#F5F5F5;'>Team 51 | NYC 311 Tracker</h3>",
        unsafe_allow_html=True
    )

with nav_right:
    page_options = {
        "Dashboard": "dashboard",
        "About Us": "about",
        "User Profile": "profile",
        "AI Chatbot": "chatbot"
    }

    selected_label = st.radio(
        "Navigation",
        list(page_options.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )

    st.session_state.page = page_options[selected_label]

# =========================
# DATA
# =========================
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
            break

    metrics = lookup.get(key, {})

    feature["properties"]["complaints"] = int(metrics.get("complaints", 0))
    feature["properties"]["avg_resolution_days"] = round(float(metrics.get("avg_resolution_days", 0)), 2)

    val = metrics.get("complaints", 0)
    feature["properties"]["color"] = [255, 215, 0, min(230, max(80, int(val / 30000)))]

# =========================
# CHART HELPERS
# =========================
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

# =========================
# DASHBOARD PAGE
# =========================
if st.session_state.page == "dashboard":

    col1, col2, col3 = st.columns([2, 4, 1])

    with col1:
        st.image("T51-NB2.png", width=1000)

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
    ### Key Insight  
    Workload and resolution times are not evenly distributed across the 311 system.  
    A small number of boroughs and agencies drive a large share of operational pressure.
    """)

    st.divider()

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

# =========================
# ABOUT PAGE
# =========================
elif st.session_state.page == "about":

    col1, col2, col3 = st.columns([2, 4, 1])

    with col1:
        st.image("T51-NB2.png", width=500)

    with col2:
        st.markdown("""
        <div style="display:flex; flex-direction:column; justify-content:center; height:100%;">
            <h1 style='margin-bottom:5px;'>About Team 51</h1>
            <h3 style='margin-top:0; color:#FFD700;'>MSDS 498 Capstone Project | 2026</h3>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.image("nyc311-logo.png", width=120)

    st.markdown("""
    <div class="section-card">
        <h3 style="color:#FFD700; margin-top:0;">Project Overview</h3>
        <p style="font-size:16px; line-height:1.6;">
        This dashboard was developed as part of the <b>Northwestern University MSDS 498 Capstone Project</b>.
        Team 51 analyzes New York City’s 311 service request system to identify where operational pressure,
        long-duration cases, and repeat complaints are concentrated.
        </p>
    </div>
    """, unsafe_allow_html=True)

    colA, colB, colC = st.columns(3)

    with colA:
        st.markdown("""
        <div class="mini-card">
            <h4 style="color:#FFD700;">Objective</h4>
            <p>Improve service responsiveness and operational efficiency across NYC 311.</p>
        </div>
        """, unsafe_allow_html=True)

    with colB:
        st.markdown("""
        <div class="mini-card">
            <h4 style="color:#FFD700;">Focus Areas</h4>
            <p>Workload drivers, agency performance gaps, delay risk, and repeat complaint patterns.</p>
        </div>
        """, unsafe_allow_html=True)

    with colC:
        st.markdown("""
        <div class="mini-card">
            <h4 style="color:#FFD700;">Deliverable</h4>
            <p>An interactive analytics tracker to support prioritization and data-driven decision-making.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    ### About the Team
    Team 51 is composed of graduate students specializing in data science. Our work transforms large-scale public data into decision-ready insights
    through data engineering, visualization, and applied analytics.
    """)

    st.image("TEAM51.png", use_column_width=True)

    st.markdown("""
    <div style='text-align:center; color:#8A8A8A; margin-top:16px; font-size:14px;'>
    Northwestern University — Master of Science in Data Science<br>
    MSDS 498 Capstone Project | 2026
    </div>
    """, unsafe_allow_html=True)

# =========================
# USER PROFILE PAGE
# =========================
elif st.session_state.page == "profile":

    col1, col2, col3 = st.columns([2, 4, 1])

    with col1:
        st.image("T51-NB2.png", width=500)

    with col2:
        st.markdown("""
        <div style="display:flex; flex-direction:column; justify-content:center; height:100%;">
            <h1 style='margin-bottom:5px;'>User Profile</h1>
            <h3 style='margin-top:0; color:#FFD700;'>Personalized NYC 311 Experience</h3>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.image("nyc311-logo.png", width=120)

    st.markdown("""
    <div class="section-card">
        <h3 style="color:#FFD700; margin-top:0;">Personalization</h3>
        <p style="font-size:16px; line-height:1.6;">
        This section helps transform the dashboard into a more app-like experience by allowing users
        to define their preferences, save views, and focus on the insights that matter most to them.
        </p>
    </div>
    """, unsafe_allow_html=True)

    profile_col1, profile_col2, profile_col3 = st.columns(3)

    with profile_col1:
        st.markdown("""
        <div class="mini-card">
            <h4 style="color:#FFD700;">Favorite Borough</h4>
            <p>Select the borough you want to prioritize in your 311 analysis.</p>
        </div>
        """, unsafe_allow_html=True)

        favorite_borough = st.selectbox(
            "Choose your favorite borough",
            sorted(borough["borough"].unique())
        )

    with profile_col2:
        st.markdown("""
        <div class="mini-card">
            <h4 style="color:#FFD700;">Preferred Complaint Types</h4>
            <p>Pick the complaint categories you would like to monitor more closely.</p>
        </div>
        """, unsafe_allow_html=True)

        preferred_complaints = st.multiselect(
            "Choose preferred complaint types",
            [
                "Noise",
                "Heat / Hot Water",
                "Illegal Parking",
                "Street Condition",
                "Sanitation",
                "Water System",
                "Building Maintenance",
                "Traffic Signal",
                "Other"
            ]
        )

    with profile_col3:
        st.markdown("""
        <div class="mini-card">
            <h4 style="color:#FFD700;">Saved Views</h4>
            <p>Create bookmarks for views or analyses you want to revisit later.</p>
        </div>
        """, unsafe_allow_html=True)

        saved_view_name = st.text_input("Name this saved view")

        if st.button("Save View"):
            if saved_view_name.strip():
                st.session_state.saved_views.append({
                    "name": saved_view_name,
                    "borough": favorite_borough,
                    "complaints": preferred_complaints
                })
                st.success(f"Saved view: {saved_view_name}")
            else:
                st.warning("Please enter a name before saving the view.")

    st.divider()

    st.subheader("Your Personalized Summary")

    summary1, summary2, summary3 = st.columns(3)

    with summary1:
        st.metric("Selected Borough", favorite_borough)

    with summary2:
        st.metric("Preferred Types", len(preferred_complaints))

    with summary3:
        st.metric("Saved Views", len(st.session_state.saved_views))

    st.markdown(f"""
    ### Profile Readout  
    - Your selected borough is **{favorite_borough}**.  
    - Your preferred complaint types are: **{", ".join(preferred_complaints) if preferred_complaints else "None selected yet"}**.  
    - These preferences can later be connected to dashboard filters, personalized alerts, and custom analytics views.
    """)

    st.divider()

    st.subheader("Saved Views / Bookmarks")

    if len(st.session_state.saved_views) > 0:
        saved_views_df = pd.DataFrame(st.session_state.saved_views)
        st.dataframe(saved_views_df, use_container_width=True)
    else:
        st.info("No saved views yet. Create one above to bookmark your preferred view.")

    st.caption("User profile section added to make the Team 51 app feel more personalized and interactive.")

# =========================
# AI CHATBOT PAGE
# =========================
elif st.session_state.page == "chatbot":

    col1, col2, col3 = st.columns([2, 4, 1])

    with col1:
        st.image("T51-NB2.png", width=500)

    with col2:
        st.markdown("""
        <div style="display:flex; flex-direction:column; justify-content:center; height:100%;">
            <h1 style='margin-bottom:5px;'>NYC 311 AI Assistant</h1>
            <h3 style='margin-top:0; color:#FFD700;'>Interactive service guidance powered by GenAI</h3>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.image("nyc311-logo.png", width=120)

    st.markdown("""
    <div class="section-card">
        <h3 style="color:#FFD700; margin-top:0;">Ask the Assistant</h3>
        <p style="font-size:16px; line-height:1.6;">
        This prototype helps classify common NYC 311 service questions and provides short,
        resident-friendly next steps based on the likely complaint category and responsible agency.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_question = st.chat_input("Ask a NYC 311 question...")

    if user_question:

        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question
        })

        result = generate_311_response(user_question)

        assistant_response = f"""
### Classification
- **Issue:** {result["issue"]}
- **Agency:** {result["agency"]}
- **Confidence Score:** {result["confidence"]}
- **Escalation Recommendation:** {result["urgency"]}
- **Recommended Action:** {result["action"]}

### Response
{result["response"]}
"""

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": assistant_response
        })

        st.rerun()
