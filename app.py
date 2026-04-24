
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="NYC 311 Dashboard",
    layout="wide"
)

@st.cache_data
def load_data():
    agency = pd.read_parquet("agency_summary.parquet")
    borough = pd.read_parquet("borough_summary.parquet")
    return agency, borough

agency, borough = load_data()

st.title("NYC 311 Analytics Dashboard")
st.caption("Closed 311 complaints — model-ready summary dashboard")

c1, c2, c3 = st.columns(3)

total_complaints = borough["complaints"].sum()
avg_resolution = (
    borough["avg_resolution_days"] * borough["complaints"]
).sum() / borough["complaints"].sum()

c1.metric("Total Complaints", f"{total_complaints:,.0f}")
c2.metric("Avg Resolution Days", f"{avg_resolution:.2f}")
c3.metric("Boroughs", f"{borough['borough'].nunique()}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Complaints by Borough")
    st.bar_chart(borough.set_index("borough")["complaints"])

with right:
    st.subheader("Avg Resolution Days by Borough")
    st.bar_chart(borough.set_index("borough")["avg_resolution_days"])

st.subheader("Agency Performance")
agency = agency.sort_values("complaints", ascending=False)
st.dataframe(agency, use_container_width=True)

st.subheader("Top Agencies by Volume")
st.bar_chart(agency.head(15).set_index("agency_group")["complaints"])
