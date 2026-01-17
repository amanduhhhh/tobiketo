import urllib  
import json
import pandas as pd  # for data
import datetime as dt  
from geopy.distance import geodesic  # distance calcs
from geopy.geocoders import Nominatim  # geocoding
import streamlit as st  # web app framework

@st.cache_data  
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
        return 'green'
    elif num_bikes_available >=1:
        return 'yellow'
    else:
        return 'red'

def geocode(address):
    try:
        geolocator = Nominatim(user_agent="amanduhhhh")
        location = geolocator.geocode(address)

        if location is None:
            return ''
        else:
            return (location.latitude, location.longitude)
    except Exception as e:
        print(f"Error geocoding address: {e}")
        return ''

def get_bike_avail(location, df, input_bike_modes):
    """Calculates distance from each station to user, return nearest station id, lat, lon"""
    df['distance'] = float('nan')
    for i in range(len(df)):
        df.loc[i, 'distance'] = geodesic(location, (df['lat'][i], df['lon'][i])).km

    if len(input_bike_modes) == 0 or len(input_bike_modes) > 2:
        df = df[(df['ebike'] > 0) | (df['mechanical'] > 0)]
    else:
        df = df[df[input_bike_modes[0]] > 0]

    if len(df) == 0:
        return []

    closest = df.loc[df['distance'].idxmin()]  
    closest_details = [closest['station_id'], closest['lat'], closest['lon']]
    return closest_details

def get_dock_avail(location, df):
    """Calculates distance from each dock to user, return nearest station id, lat, lon"""
    df['distance'] = float('nan')
    for i in range(len(df)):
        df.loc[i, 'distance'] = geodesic(location, (df['lat'][i], df['lon'][i])).km
        
    df = df[df['num_docks_available'] > 0]
    
    if len(df) == 0:
        return []

    closest = df.loc[df['distance'].idxmin()]  
    closest_details = [closest['station_id'], closest['lat'], closest['lon']]
    return closest_details

def run_osrm(dest_station, my_loc):
    if not dest_station or not my_loc or len(dest_station) < 3:
        return [], 0
    start = f"{my_loc[1]},{my_loc[0]}"
    end = f"{dest_station[2]},{dest_station[1]}"
    url = f"http://router.project-osrm.org/route/v1/driving/{start};{end}?geometries=geojson"

    req = urllib.request.Request(url, headers={'Content-type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            route_json = json.loads(response.read().decode())
            print("API call status:", response.getcode())
        
        if 'routes' not in route_json or len(route_json['routes']) == 0:
            return [], 0

        coord_lst = route_json['routes'][0]['geometry']['coordinates']
        coords = [(coord[1], coord[0]) for coord in coord_lst]

        duration = round(route_json['routes'][0]['duration'] / 60, 2)
        return coords, duration
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"Error getting route: {e}")
        return [], 0
