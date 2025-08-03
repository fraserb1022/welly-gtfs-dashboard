import requests
import pandas as pd
import os
import folium

BASE_URL = "https://api.opendata.metlink.org.nz/v1"
API_KEY = "xTbUusAjtl2h7y7UzY3vt6PdiG2Sbxzb3ZiUZ8rD"

HEADERS = {
    "accept": "application/json",
    "x-api-key": API_KEY
}

def fetch_routes(save_csv=True):
    url = f"{BASE_URL}/gtfs/routes"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    routes = response.json()
    routes_df = pd.DataFrame(routes)

    if save_csv:
        routes_df.to_csv("routes.csv", index=False)

    return routes_df

def fetch_trips(save_csv=True):
    url = f"{BASE_URL}/gtfs/trips"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    trips = response.json()
    trips_df = pd.DataFrame(trips)

    if save_csv:
        trips_df.to_csv("trips.csv", index=False)

    return trips_df

def fetch_shape(shape_id, save_csv=True):
    url = f"{BASE_URL}/gtfs/shapes?shape_id={shape_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    shape = response.json()

    if not shape:
        print(f"⚠️ No shape data found for shape_id: {shape_id}")
        return pd.DataFrame()

    shape_df = pd.DataFrame(shape)

    if save_csv:
        shape_df.to_csv(f"shape_{shape_id}.csv", index=False)

    return shape_df

import folium


def fetch_stops(route_id, save_csv=True):
    url = f"{BASE_URL}/gtfs/stops?route_id={route_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    stops = response.json()
    stops_df = pd.DataFrame(stops)

    if save_csv:
        stops_df.to_csv(f"stops_{route_id}.csv", index=False)

    return stops_df



def plot_shape_map(shape_df, shape_id, save_html=False):
    if shape_df.empty:
        print(f"⚠️ No data to plot for shape_id: {shape_id}")
        return None  # important

    shape_df = shape_df.sort_values("shape_pt_sequence")
    coords = list(zip(shape_df['shape_pt_lat'], shape_df['shape_pt_lon']))

    fmap = folium.Map(location=coords[0], zoom_start=13)
    folium.PolyLine(coords, color='blue', weight=4, tooltip=f"Shape ID: {shape_id}").add_to(fmap)

    if save_html:
        html_path = f"shape_{shape_id}.html"
        fmap.save(html_path)
        print(f"✅ Map saved to {html_path}")

    return fmap  # 🟢 always return this


if __name__ == "__main__":
    print("📦 Fetching GTFS routes...")
    routes_df = fetch_routes()
    print(f"✅ Routes fetched: {len(routes_df)}")


    print("\n📦 Fetching GTFS trips...")
    trips_df = fetch_trips()
    print(f"✅ Trips fetched: {len(trips_df)}")

    # Example shape_id — replace this with any valid one from trips_df['shape_id']
    example_shape_id = trips_df['shape_id'].dropna().iloc[0]
    print(f"\n🗺️ Fetching shape for: {example_shape_id}")
    shape_df = fetch_shape(example_shape_id)

    if not shape_df.empty:
        plot_shape(shape_df, example_shape_id)
