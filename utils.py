from math import ceil
import urllib  
import json
import pandas as pd  # for data
import datetime as dt  
from geopy.distance import geodesic  # distance calcs
import streamlit as st  # web app framework
import googlemaps

# Map marker colors
GREEN = '#50c468'
YELLOW = '#f6c942'
RED = '#e47367'

@st.cache_data(ttl=180)
def query_station_status(url):
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        df = pd.DataFrame(data["data"]["stations"])
        df = df[df.is_renting == 1] 
        df = df[df.is_returning == 1]
        df = df.drop_duplicates(['station_id', 'last_reported'])
        df.last_reported = df.last_reported.map(lambda x: dt.datetime.fromtimestamp(x))

        # df['time'] = data['last_updated']
        # df.time = df.time.map(lambda x: dt.datetime.fromtimestamp(x))
        # df = df.set_index('time') 
        # df.index = df.index.tz_localize('UTC')
        df = pd.concat([df, df['num_bikes_available_types'].apply(pd.Series)], axis=1)

        return df
        
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"Error querying station status: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)  
def get_station_location(url):
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
        data = pd.DataFrame(data["data"]["stations"])
        return data
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"Error getting station location: {e}")
        return pd.DataFrame()

def join_location(df1, df2):
    """Joins 2 dataframes on station_id"""
    try:
        required_cols = ['station_id', 'lat', 'lon']
        if not all(col in df2.columns for col in required_cols):
            print("Error: Missing required columns in df2")
            return df1
        df = df1.merge(df2[required_cols], on='station_id', how='left')
        return df
    except Exception as e:
        print(f"Error joining location data: {e}")
        return df1

def get_mark_colour(num_bikes_available):
    if num_bikes_available > 3:
        return GREEN
    elif num_bikes_available >=1:
        return YELLOW
    else:
        return RED

@st.cache_data(ttl=86400)  
def geocode(address):
    try:
        gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
        result = gmaps.geocode(address)

        if not result:
            print(f"Geocoding returned no results for address: {address}")
            return ''
        
        location = result[0]['geometry']['location']
        lat = location['lat']
        lon = location['lng']
        
        print(f"Successfully geocoded: {address} -> ({lat}, {lon})")
        return (lat, lon)
        
    except Exception as e:
        print(f"Error geocoding address '{address}': {type(e).__name__} - {e}")
        return ''

def get_bike_avail(location, df, input_bike_modes):
    """Calculates distance from each station to user, return nearest station id, lat, lon"""
    bike_type_mapping = {
        "Mechanical": "mechanical",
        "E-bike": "ebike"
    }
    
    df['distance'] = df.apply(lambda row: geodesic(location, (row['lat'], row['lon'])).km, axis=1)

    if len(input_bike_modes) == 0 or len(input_bike_modes) >= 2:
        df = df[(df['ebike'] > 0) | (df['mechanical'] > 0)]
    else:
        column_name = bike_type_mapping.get(input_bike_modes[0], input_bike_modes[0])
        df = df[df[column_name] > 0]

    if len(df) == 0:
        return []

    closest = df.loc[df['distance'].idxmin()]  
    closest_details = [closest['station_id'], closest['lat'], closest['lon']]
    return closest_details

def get_dock_avail(location, df):
    """Calculates distance from each dock to user, return nearest station id, lat, lon"""
    df['distance'] = df.apply(lambda row: geodesic(location, (row['lat'], row['lon'])).km, axis=1)
        
    df = df[df['num_docks_available'] > 0]
    
    if len(df) == 0:
        return []

    closest = df.loc[df['distance'].idxmin()]  
    closest_details = [closest['station_id'], closest['lat'], closest['lon']]
    return closest_details

@st.cache_data(ttl=3600)  
def run_osrm(dest_station, my_loc, profile='foot'):
    if not dest_station or not my_loc or len(dest_station) < 3:
        return [], 0
    
    try:
        mode_map = {
            'foot': 'walking',
            'bike': 'bicycling'
        }
        google_mode = mode_map.get(profile, 'walking')

        gmaps = googlemaps.Client(key=st.secrets["GOOGLE_MAPS_API_KEY"])
        
        origin = (my_loc[0], my_loc[1])  
        destination = (dest_station[1], dest_station[2])  
        
        result = gmaps.directions(
            origin=origin,
            destination=destination,
            mode=google_mode
        )
        
        if not result or len(result) == 0:
            print(f"No route found from {origin} to {destination}")
            return [], 0

        route = result[0]
        coords = []

        for leg in route['legs']:
            start_lat = leg['start_location']['lat']
            start_lng = leg['start_location']['lng']
            coords.append((start_lat, start_lng))

            for step in leg['steps']:
                end_lat = step['end_location']['lat']
                end_lng = step['end_location']['lng']
                coords.append((end_lat, end_lng))
        

        total_duration_seconds = sum(leg['duration']['value'] for leg in route['legs'])
        duration = ceil(total_duration_seconds / 60)
        
        print(f"Google Directions: Route found, {duration} min, {len(coords)} points")
        return coords, duration
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error getting route from Google Directions: {type(e).__name__} - {error_msg}")

        if "REQUEST_DENIED" in error_msg or "ApiError" in str(type(e)):
            print("   Make sure Directions API is enabled and API key restrictions allow your IP/domain")
        
        return [], 0
