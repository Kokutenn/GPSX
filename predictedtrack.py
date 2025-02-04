import streamlit as st
import pandas as pd
from geopy.distance import distance
import folium
from streamlit_folium import folium_static
import simplekml

st.set_page_config(layout="wide")
st.title("Aircraft Predicted Trajectory Algorithm")

# Function to calculate new coordinates based on initial coordinates, ground speed, and bearing
def calculate_new_coordinates(initial_lat, initial_lon, bearing, ground_speed_knots, time_interval_seconds):
    ground_speed_meters_per_second = ground_speed_knots * 0.514444  # knots to meters per second
    horizontal_distance_traveled = ground_speed_meters_per_second * time_interval_seconds  # distance in meters
    horizontal_distance_traveled_km = horizontal_distance_traveled / 1000
    destination = distance(kilometers=horizontal_distance_traveled_km).destination((initial_lat, initial_lon), bearing)
    new_lat, new_lon = destination.latitude, destination.longitude
    return new_lat, new_lon

# Read input CSV file and predict coordinates
def read_csv_and_predict(input_csv, initial_lat, initial_lon, time_interval_seconds=1):
    df = pd.read_csv(input_csv)
    required_columns = ['groundspeed', 'heading']
    df.columns = df.columns.str.lower()
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    
    current_lat, current_lon = initial_lat, initial_lon
    predicted_data = [{'latitude': current_lat, 'longitude': current_lon, 'name': 1}]
    
    for index, row in df.iterrows():
        step_number = index + 1
        ground_speed_knots = row['groundspeed']
        bearing = row['heading']
        new_lat, new_lon = calculate_new_coordinates(current_lat, current_lon, bearing, ground_speed_knots, time_interval_seconds)
        predicted_data.append({'latitude': new_lat, 'longitude': new_lon, 'name': step_number})
        current_lat, current_lon = new_lat, new_lon
    
    return predicted_data, current_lat, current_lon

# Function to write predicted data to CSV file
def write_to_csv(predicted_data, output_csv):
    df = pd.DataFrame(predicted_data)
    df.to_csv(output_csv, index=False)

# Function to write predicted data to KML file
def write_to_kml(predicted_data, output_kml):
    kml = simplekml.Kml()
    for data in predicted_data:
        kml.newpoint(name=f"Step {data['name']}", coords=[(data['longitude'], data['latitude'])])
    kml.save(output_kml)

# Function to plot predicted data on a satellite map
def plot_predicted_data_on_map(predicted_data):
    initial_coords = (predicted_data[0]['latitude'], predicted_data[0]['longitude'])
    map_ = folium.Map(location=initial_coords, zoom_start=13, tiles='OpenStreetMap')
    icon_url = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png'
    for data in predicted_data:
        folium.Marker(
            location=(data['latitude'], data['longitude']),
            popup=f"Step {data['name']}",
            icon=folium.CustomIcon(icon_url, icon_size=(2, 2))
        ).add_to(map_)
    points = [(data['latitude'], data['longitude']) for data in predicted_data]
    folium.PolyLine(points, color="blue", weight=5, opacity=1).add_to(map_)
    folium_static(map_)

# Streamlit app
def main():
    st.title("Aircraft Trajectory Predictor")
    
    st.markdown("""
    ### Instructions for Using the App
    1. **Upload a CSV File** containing `Groundspeed` (knots) and `Heading` (degrees).
    2. **Enter Initial Coordinates** of the aircraft.
    3. **Enter Time Interval** for the data points.
    4. **Run the Prediction** to generate the trajectory.
    5. **Download Results** as CSV or KML files.
    6. **View the Map** with the predicted trajectory.
    """)
    
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    initial_lat = st.number_input("Enter initial latitude:", value=0.0, format="%.6f")
    initial_lon = st.number_input("Enter initial longitude:", value=0.0, format="%.6f")
    time_interval_seconds = st.number_input("Enter time interval in seconds:", value=1.0, format="%.1f")
    
    if st.button("Run"):
        if uploaded_file is not None:
            try:
                predicted_data, final_lat, final_lon = read_csv_and_predict(uploaded_file, initial_lat, initial_lon, time_interval_seconds)
                output_csv = 'predicted_trajectory.csv'
                write_to_csv(predicted_data, output_csv)
                output_kml = 'predicted_trajectory.kml'
                write_to_kml(predicted_data, output_kml)
                st.success(f"Predicted coordinates saved to {output_csv} and {output_kml}")
                st.write(f"Final coordinates: Latitude = {final_lat}, Longitude = {final_lon}")
                
                st.download_button("Download Predicted Trajectory CSV", open(output_csv, "rb"), output_csv, "text/csv")
                st.download_button("Download Predicted Trajectory KML", open(output_kml, "rb"), output_kml, "application/vnd.google-earth.kml+xml")
                plot_predicted_data_on_map(predicted_data)
            except ValueError as e:
                st.error(e)
        else:
            st.error("Please upload a CSV file to proceed.")

if __name__ == "__main__":
    main()
