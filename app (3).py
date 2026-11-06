import requests
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Live Weather & Air Quality", layout="wide")
st.title("🌦️ Live City Weather & Air Quality Dashboard")
st.caption("Live data from Open-Meteo (free public API, no key needed). Auto-refreshes every 10 min.")

CITIES = {
    "Mumbai": (19.07, 72.88), "Delhi": (28.61, 77.21), "Bengaluru": (12.97, 77.59),
    "Chennai": (13.08, 80.27), "Kolkata": (22.57, 88.36), "Pune": (18.52, 73.86),
}
city = st.sidebar.selectbox("Select city", list(CITIES))
lat, lon = CITIES[city]


@st.cache_data(ttl=600)  # re-fetch at most every 10 minutes
def fetch(lat, lon):
    w = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 2,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m",
                "hourly": "temperature_2m,precipitation_probability"},
        timeout=15)
    a = requests.get(
        "https://air-quality-api.open-meteo.com/v1/air-quality",
        params={"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 2,
                "current": "us_aqi,pm2_5,pm10", "hourly": "us_aqi,pm2_5"},
        timeout=15)
    w.raise_for_status()
    a.raise_for_status()
    return w.json(), a.json()


def aqi_label(x):
    if x is None: return "n/a"
    for limit, name in [(50, "Good"), (100, "Moderate"), (150, "Unhealthy (sensitive)"),
                        (200, "Unhealthy"), (300, "Very unhealthy")]:
        if x <= limit: return name
    return "Hazardous"


try:
    w, a = fetch(lat, lon)
except Exception as e:
    st.error(f"Could not fetch live data: {e}")
    st.stop()

cw, ca = w["current"], a["current"]
st.subheader(f"{city} — right now (updated {cw['time'].replace('T', ' ')})")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Temperature", f"{cw['temperature_2m']} °C", f"feels {cw['apparent_temperature']} °C", delta_color="off")
c2.metric("Humidity", f"{cw['relative_humidity_2m']} %")
c3.metric("Wind", f"{cw['wind_speed_10m']} km/h")
c4.metric("AQI (US)", ca["us_aqi"], aqi_label(ca["us_aqi"]), delta_color="off")
c5.metric("PM2.5", f"{ca['pm2_5']} µg/m³")

wdf = pd.DataFrame(w["hourly"]); wdf["time"] = pd.to_datetime(wdf["time"])
adf = pd.DataFrame(a["hourly"]); adf["time"] = pd.to_datetime(adf["time"])

left, right = st.columns(2)
left.plotly_chart(px.line(wdf, x="time", y="temperature_2m", title="Temperature forecast (°C)"),
                  use_container_width=True)
right.plotly_chart(px.bar(wdf, x="time", y="precipitation_probability", title="Rain probability (%)"),
                   use_container_width=True)
st.plotly_chart(px.line(adf, x="time", y=["us_aqi", "pm2_5"], title="Air quality: AQI & PM2.5 (next 48h)"),
                use_container_width=True)

with st.expander("Show raw data"):
    st.dataframe(wdf.merge(adf, on="time", how="outer"))
