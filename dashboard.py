import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
from scripts.fetch_gtfs import fetch_routes, fetch_trips, fetch_shape, fetch_stops
import folium

st.set_page_config(page_title="Wellington GTFS Viewer", layout="wide")
st.title("Wellington GTFS Viewer")

#load data
@st.cache_data
def load_data():
    return fetch_trips(), fetch_routes()

trips_df, routes_df = load_data()
trips_df["route_id"] = trips_df["route_id"].astype(str).str.strip()
routes_df["route_id"] = routes_df["route_id"].astype(str).str.strip()

#calc trips per route
trips_per_route = trips_df.groupby("route_id")["trip_id"].count()

#tabs
tab1, tab2 = st.tabs(["Overview", "Route Explorer"])

with tab1:
    st.subheader("Summary")
    total_routes = routes_df["route_id"].nunique()
    total_trips_all = trips_df["trip_id"].nunique()
    avg_trips = trips_per_route.mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Routes", total_routes)
    col2.metric("Total Trips", total_trips_all)
    col3.metric("Avg Trips per Route", f"{avg_trips:.2f}")

    max_route_id = trips_per_route.idxmax()
    max_trip_count = trips_per_route.max()
    min_route_id = trips_per_route.idxmin()
    min_trip_count = trips_per_route.min()

    col4, col5, _ = st.columns(3)
    col4.metric("Most Trips", f"Route {max_route_id}", f"{max_trip_count} trips")

    with st.expander("Show trip counts per route"):
        st.dataframe(
            trips_per_route.reset_index().rename(columns={"trip_id": "Trip Count"}),
            use_container_width=True
        )

    st.divider()

    st.subheader("Top 10 Routes by Number of Trips")
    top_routes = trips_per_route.sort_values(ascending=False).head(10)
    top_routes_df = (
        top_routes.reset_index()
        .merge(routes_df[["route_id", "route_short_name", "route_long_name"]], on="route_id", how="left")
    )
    top_routes_df["label"] = top_routes_df["route_short_name"].fillna("") + " - " + top_routes_df["route_long_name"].fillna("")
    st.bar_chart(top_routes_df.set_index("label")["trip_id"])

with tab2:
    # Route Explorer Tab

    trips_with_routes = trips_df.merge(routes_df, on="route_id", suffixes=("_trip", "_route"))
    route_options = (
        trips_with_routes[["route_id", "route_short_name", "route_long_name"]]
        .drop_duplicates()
        .assign(
            label=lambda df: df["route_short_name"].fillna(df["route_long_name"]).fillna("Unnamed Route") +
                             " – " + df["route_long_name"].fillna("")
        )
    )

    selected_route_label = st.selectbox("Select a Route to Explore", route_options["label"])
    route_id = route_options[route_options["label"] == selected_route_label]["route_id"].values[0]

    stops_df = fetch_stops(route_id)
    route_trips = trips_df[trips_df["route_id"] == route_id]
    shape_meta = (
        route_trips.dropna(subset=["shape_id"])
        .groupby(["shape_id", "direction_id"])
        .size()
        .reset_index(name="trip_count")
    )
    shape_ids = shape_meta["shape_id"].unique()

    # Side-by-side: Summary Metrics on left, Map on right
    left_col, right_col = st.columns([1, 2])  # summary (1), map (2)

    with left_col:
        st.markdown(f"## Summary for Route: ")
        st.markdown(f"**{selected_route_label}**")
        total_trips = len(route_trips)
        unique_shapes = route_trips["shape_id"].nunique()
        unique_stops = stops_df["stop_id"].nunique()
        num_directions = route_trips["direction_id"].nunique()
        direction_label = "One-way" if num_directions == 1 else "Two-way"

        col1, col2 = st.columns(2)
        col1.metric("Total Trips", total_trips)
        col2.metric("Unique Shapes", unique_shapes)

        col3, col4 = st.columns(2)
        col3.metric("Unique Stops", unique_stops)
        col4.metric("Directionality", direction_label)

    with right_col:
        if len(shape_ids) == 0:
            st.warning("No shapes found for this route.")
        else:
            st.markdown("## Route Shape")

            first_shape_df = fetch_shape(shape_ids[0])
            center = [first_shape_df['shape_pt_lat'].mean(), first_shape_df['shape_pt_lon'].mean()]
            folium_map = folium.Map(location=center, zoom_start=12)
            colors = ["red", "blue", "green", "purple", "orange", "darkred", "cadetblue", "black"]

            for idx, shape_id in enumerate(shape_ids):
                shape_df = fetch_shape(shape_id)
                if not shape_df.empty:
                    coords = shape_df[["shape_pt_lat", "shape_pt_lon"]].values.tolist()
                    folium.PolyLine(
                        coords,
                        color=colors[idx % len(colors)],
                        weight=4,
                        opacity=0.6,
                        tooltip=f"Shape ID: {shape_id}"
                    ).add_to(folium_map)

            for _, stop in stops_df.iterrows():
                folium.CircleMarker(
                    location=(stop['stop_lat'], stop['stop_lon']),
                    radius=5,
                    color='red',
                    fill=True,
                    fill_color='red',
                    fill_opacity=0.7,
                    popup=f"{stop['stop_name']} (ID: {stop['stop_id']})"
                ).add_to(folium_map)

            st_folium(folium_map, width=700, height=500)

    st.divider()


    st.markdown("### Trips by Shape ID")
    shape_counts = route_trips["shape_id"].fillna("No Shape").value_counts()
    st.dataframe(shape_counts.rename_axis("Shape ID").reset_index(name="Trip Count"), use_container_width=True)

    st.divider()

    with st.expander("Show full trip details for this route"):
        st.dataframe(route_trips.reset_index(drop=True), use_container_width=True)
