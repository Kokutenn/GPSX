import streamlit as st
from st_paywall import add_auth
import pandas as pd
from geopy.distance import distance
import folium
from streamlit_folium import folium_static
import simplekml

st.set_page_config(layout="wide")
st.title("Aircraft Predicted Trajectory Algorithm")

add_auth(required=True)

# ONLY AFTER THE AUTHENTICATION + SUBSCRIPTION, THE USER WILL SEE THIS ⤵
# The email and subscription status is stored in session state.
st.write(f"Subscription Status: {st.session_state.user_subscribed}")
st.write("🎉 Yay! You're all set and subscribed! 🎉")
st.write(f'By the way, your email is: {st.session_state.email}')

# Function to calculate new coordinates based on initial coordinates, ground speed, and bearing
def calculate_new_coordinates(initial_lat, initial_lon, bearing, ground_speed_knots, time_interval_seconds):
    # Convert ground speed from knots to meters per second
    ground_speed_meters_per_second = ground_speed_knots * 0.514444  # knots to meters per second

    # Calculate horizontal distance traveled in the given time interval
    horizontal_distance_traveled = ground_speed_meters_per_second * time_interval_seconds  # distance in meters

    # Convert horizontal distance traveled to kilometers (for geopy)
    horizontal_distance_traveled_km = horizontal_distance_traveled / 1000

    # Calculate new coordinates using geopy's distance and destination method
    destination = distance(kilometers=horizontal_distance_traveled_km).destination((initial_lat, initial_lon), bearing)
    new_lat, new_lon = destination.latitude, destination.longitude

    return new_lat, new_lon

# Read input CSV file and predict coordinates
def read_csv_and_predict(input_csv, initial_lat, initial_lon, time_interval_seconds=1):
    df = pd.read_csv(input_csv)  # Read CSV file using provided path

    # Ensure the required columns are present (case-insensitive)
    required_columns = ['groundspeed', 'heading']
    df.columns = df.columns.str.lower()
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    # Initialize initial coordinates
    current_lat, current_lon = initial_lat, initial_lon

    # List to store predicted data
    predicted_data = []

    # Append initial coordinates data to list
    predicted_data.append({
        'latitude': current_lat,
        'longitude': current_lon,
        'name': 1  # First step
    })

    # Predict latitude and longitude for subsequent rows
    for index, row in df.iterrows():
        step_number = index + 1  # Step number starts from 1 for the first row
        ground_speed_knots = row['groundspeed']
        bearing = row['heading']

        # Calculate new coordinates based on current coordinates and ground speed
        new_lat, new_lon = calculate_new_coordinates(current_lat, current_lon, bearing, ground_speed_knots, time_interval_seconds)

        # Append predicted data to list
        predicted_data.append({
            'latitude': new_lat,
            'longitude': new_lon,
            'name': step_number
        })

        # Update current coordinates to newly calculated values
        current_lat, current_lon = new_lat, new_lon

    return predicted_data, current_lat, current_lon  # Return final coordinates after prediction

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
    # Create a map centered at the initial coordinates
    initial_coords = (predicted_data[0]['latitude'], predicted_data[0]['longitude'])
    map_ = folium.Map(location=initial_coords, zoom_start=13, tiles='OpenStreetMap')

    # Custom icon for smaller size
    icon_url = 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png'

    # Add a marker for each predicted coordinate
    for data in predicted_data:
        folium.Marker(
            location=(data['latitude'], data['longitude']),
            popup=f"Step {data['name']}",
            icon=folium.CustomIcon(icon_url, icon_size=(2, 2))
        ).add_to(map_)

    # Draw lines between the points
    points = [(data['latitude'], data['longitude']) for data in predicted_data]
    folium.PolyLine(points, color="blue", weight=5, opacity=1).add_to(map_)  # Set weight to 5 for a thicker line

    # Display the map in Streamlit
    folium_static(map_)

# Streamlit app
def main():
    st.title("Aircraft Trajectory Predictor")

    # Description on how to use the app
    st.markdown("""
    ### Instructions for Using the App

    1. **Upload a CSV File**: Click on the "Choose a CSV file" button to upload your data file. 
       The CSV file should contain the following columns (extra columns will be ignored):
       - `Groundspeed`: The speed of the aircraft in knots.
       - `Heading`: The direction in which the aircraft is moving (in degrees).

    2. **Enter Initial Coordinates**: Provide the initial reliable latitude and longitude coordinates of the aircraft.

    3. **Enter Time Interval**: Specify the time interval (in seconds) for the data points in your CSV file.
       - **1 Hz** = 1 second
       - **4 Hz** = 0.25 seconds

       Ensure that the heading and groundspeed data are recorded at the same frequency.

    4. **Run the Prediction**: Click on the "Run" button to execute the prediction.

    5. **Download the Results**: Once the prediction is complete, you can download the predicted trajectory as a CSV file or KML file (Google Earth).

    6. **View the Map**: The predicted trajectory will be displayed on a map.

    **Accuracy Tips**:
    - The closer the initial coordinates are to the predicted point, the greater the accuracy.
    - Ensure the data is of high quality (e.g., no breaks or erroneous values).
    - Using "Track true" or a true heading or magnetic heading will produce more accurate predictions.
    - Data with higher resolution (more decimal places) will also improve accuracy.
    - Higher frequencies of data produce more accurate tracks but ensure all data remains at the same frequency.
    - To assess the reliability of the predicted track, compare it to a reliable coordinate such as a landing/takeoff runway or the lat/long of a known waypoint.
    """)

    # File uploader for input CSV
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    # Input initial coordinates
    initial_lat = st.number_input("Enter initial reliable latitude:", value=0.0, format="%.1f")
    initial_lon = st.number_input("Enter initial reliable longitude:", value=0.0, format="%.1f")
    time_interval_seconds = st.number_input("Enter time interval of data in seconds:", value=1.0, format="%f")

    # Run button
    if st.button("Run"):
        if uploaded_file is not None:
            try:
                # Predict data
                predicted_data, final_lat, final_lon = read_csv_and_predict(uploaded_file, initial_lat, initial_lon, time_interval_seconds)

                # Write predicted data to CSV
                output_csv = 'predicted_trajectory.csv'
                write_to_csv(predicted_data, output_csv)

                # Write predicted data to KML
                output_kml = 'predicted_trajectory.kml'
                write_to_kml(predicted_data, output_kml)

                st.success(f"Predicted coordinates have been written to {output_csv} and {output_kml}")
                st.write(f"Final coordinates: Latitude = {final_lat}, Longitude = {final_lon}")

                # Provide download link for the output CSV
                st.download_button(
                    label="Download Predicted Trajectory CSV",
                    data=open(output_csv, "rb"),
                    file_name=output_csv,
                    mime="text/csv"
                )

                # Provide download link for the output KML
                st.download_button(
                    label="Download Predicted Trajectory KML (Google Earth)",
                    data=open(output_kml, "rb"),
                    file_name=output_kml,
                    mime="application/vnd.google-earth.kml+xml"
                )

                # Plot predicted data on a satellite map
                plot_predicted_data_on_map(predicted_data)

            except ValueError as e:
                st.error(e)
        else:
            st.error("Please upload a CSV file to proceed.")

if __name__ == "__main__":
    main()
