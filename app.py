import streamlit as st
import pandas as pd
import folium
import json
from folium.plugins import LocateControl
from streamlit_folium import st_folium
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Nursery Locator", layout="wide")
st.title("🌱 Public Nursery Locator")

# Load the Excel file
df = pd.read_excel("/mnt/data/NURSARY.xlsx")

# Fill down merged cells (species repeated rows)
df[['Name of the Schemes', 'Name of the Range', 'Name of the Section', 'Name of the Beat',
    'Name of the Nursery', 'Seedlings for distribution (Nos)', 'Name of the Incharge',
    'Mobile No. of Incharge', 'Longitude', 'Latitude']] = df[[
    'Name of the Schemes', 'Name of the Range', 'Name of the Section', 'Name of the Beat',
    'Name of the Nursery', 'Seedlings for distribution (Nos)', 'Name of the Incharge',
    'Mobile No. of Incharge', 'Longitude', 'Latitude']].ffill()

# Convert lat/lon to numeric
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

# Drop invalid lat/lon rows
df_clean = df.dropna(subset=['Latitude', 'Longitude'])

# Show invalid rows if any
invalid_rows = df[df['Latitude'].isna() | df['Longitude'].isna()]
if not invalid_rows.empty:
    st.warning("⚠️ Some rows have missing or invalid coordinates and were excluded.")
    st.dataframe(invalid_rows[['Name of the Nursery', 'Latitude', 'Longitude']])

# Stop if no valid data
if df_clean.empty:
    st.error("❌ No valid nursery locations with Latitude and Longitude found.")
    st.stop()

# Unique nurseries
nurseries = df_clean[['Name of the Nursery', 'Latitude', 'Longitude',
                      'Seedlings for distribution (Nos)', 'Name of the Incharge', 'Mobile No. of Incharge']].drop_duplicates()

# Detect user location
loc = streamlit_js_eval(
    js_expressions="navigator.geolocation.getCurrentPosition((pos) => pos.coords)",
    key="get_user_location"
)

if loc and "latitude" in loc and "longitude" in loc:
    user_location = (loc["latitude"], loc["longitude"])
    st.success("📍 Your location detected.")
else:
    user_location = ( 20.30250, 82.755278)  # Khariar fallback
    st.warning("⚠️ Using fallback location: Khariar.")

# Create folium map
m = folium.Map(location=[nurseries['Latitude'].mean(), nurseries['Longitude'].mean()], zoom_start=11)
LocateControl(auto_start=True).add_to(m)

# Optional: add Khariar boundary
try:
    with open("khariar_boundary.geojson", "r") as f:
        khariar_boundary = json.load(f)
    folium.GeoJson(
        khariar_boundary,
        name="Khariar Division",
        style_function=lambda x: {"fillColor": "orange", "color": "black", "weight": 2, "fillOpacity": 0.1},
    ).add_to(m)
except:
    pass

# User location marker
folium.Marker(
    location=user_location,
    tooltip="Your Location",
    icon=folium.Icon(color="blue", icon="user")
).add_to(m)

# Add nursery markers
for _, row in nurseries.iterrows():
    folium.Marker(
        location=[row['Latitude'], row['Longitude']],
        tooltip=row['Name of the Nursery'],
        popup=f"""
        <b>{row['Name of the Nursery']}</b><br>
        Seedlings: {row['Seedlings for distribution (Nos)']}<br>
        Incharge: {row['Name of the Incharge']}<br>
        Contact: {row['Mobile No. of Incharge']}
        """,
        icon=folium.Icon(color="green", icon="leaf")
    ).add_to(m)

# Show map
st.subheader("🗺️ Nursery Map")
map_data = st_folium(m, width=1000, height=600)

# Clicked nursery info
if map_data and map_data.get("last_object_clicked_tooltip"):
    name = map_data["last_object_clicked_tooltip"]
    nursery_info = df_clean[df_clean["Name of the Nursery"] == name].iloc[0]
    species_table = df_clean[df_clean["Name of the Nursery"] == name][['NAME OF SPECIES', 'NO OF SPECIES']]

    st.subheader(f"🏡 {name} Details")
    st.markdown(f"""
    **Range:** {nursery_info['Name of the Range']}  
    **Section:** {nursery_info['Name of the Section']}  
    **Beat:** {nursery_info['Name of the Beat']}  
    **Seedlings Available:** {nursery_info['Seedlings for distribution (Nos)']}  
    **Incharge:** {nursery_info['Name of the Incharge']}  
    **Contact:** {nursery_info['Mobile No. of Incharge']}  
    """)

    st.markdown("### 🌿 Species Available")
    st.dataframe(species_table.reset_index(drop=True), use_container_width=True)

else:
    st.info("Click on a nursery marker to view its details.")
