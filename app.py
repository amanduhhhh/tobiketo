from utils import *
import streamlit as st
import folium  # for maps
from streamlit_folium import folium_static

st.set_page_config(page_title="Toronto Bikes", page_icon="🚲", layout="centered")
station_url = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_status"
location_url = "https://tor.publicbikesystem.net/ube/gbfs/v1/en/station_information"

st.title("Toronto Bike Share Status")
st.markdown("Need to borrow or dock a bike? Enter your location and we'll find the nearest bike station!")

# fetch data
data_df = query_station_status(station_url) 
location_df = get_station_location(location_url)
data = join_location(data_df, location_df)
# st.dataframe(data)

cols = st.columns(3)
with cols[0]:
    st.metric(label="Bikes available", value=data['num_bikes_available'].sum())
    st.metric(label = "Stations with bikes available", value = (data['num_bikes_available'] > 0).sum())
with cols[1]:
    st.metric(label="E-bikes available", value=data['ebike'].sum())
    st.metric(label = "Stations with e-bikes available", value = (data['ebike'] > 0).sum())
with cols[2]:
    st.metric(label = "Stations with docks available", value = (data['num_docks_available'] > 0).sum())

my_loc = 0
my_loc_return = 0
submit_rent = False
submit_return = False
input_bike_modes = []


# map display func
def show_station_map(user_loc, closest_station, data):
    m1 = folium.Map(location=user_loc, zoom_start=16, tiles='cartodbpositron')
    for _, row in data.iterrows():
        marker_color = get_mark_colour(row['num_bikes_available'])
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=2,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,
            popup=folium.Popup(f"Station ID: {row['station_id']}<br>"
                                f"Total Bikes Available: {row['num_bikes_available']}<br>"
                                f"Mechanical Bike Available: {row['mechanical']}<br>"
                                f"eBike Available: {row['ebike']}", max_width=300)
        ).add_to(m1)
    folium.Marker(
        location=user_loc,
        icon=folium.Icon(color="blue", icon="person", prefix="fa")
    ).add_to(m1)
    folium.Marker(location=(closest_station[1], closest_station[2]),
                    icon=folium.Icon(color="red", icon="bicycle", prefix="fa")
                    ).add_to(m1)
    coordinates, duration = run_osrm(closest_station, user_loc)
    folium.PolyLine(
        locations=coordinates,
        color="blue",
        weight=5,
        tooltip=f"ETA: {duration} min",
    ).add_to(m1)
    folium_static(m1)
    with cols[2]:
        st.metric(label=":green[Travel Time (min)]", value=duration)

# sidebar options
with st.sidebar:
    with st.form("search_form"):
        bike_method = st.selectbox("Renting or returning?", ["Rent", "Return"])
        
        if bike_method == "Rent":
            input_bike_modes = st.multiselect(
                "Select bike type",
                ["Mechanical", "E-bike"],
            )
        
        st.subheader("My Location")
        input_street = st.text_input("Street address", "")
        # driving = st.checkbox("I'm driving")
        submit_button = st.form_submit_button("Find nearest station", type='primary')

    if submit_button:
        if input_street != "":
            my_loc = geocode(input_street + " Toronto Canada")
            if my_loc == '':
                st.markdown(":red[Address invalid. Are you in Toronto?]")
            else:
                if bike_method == "Rent":
                    submit_rent = True
                else:
                    submit_return = True
           
        else:
            st.markdown(":red[Enter an address]")

# generic map
if not submit_rent and not submit_return:
    center = [43.65306613746548, -79.38815311015]  
    m = folium.Map(location=center, zoom_start=12, tiles='cartodbpositron')  
    for _, row in data.iterrows():
        marker_color = get_mark_colour(row['num_bikes_available'])  
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=2,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7,
            popup=folium.Popup(f"Station ID: {row['station_id']}<br>"
                                f"Total Bikes Available: {row['num_bikes_available']}<br>"
                                f"Mechanical: {row['mechanical']}<br>"
                                f"E-bike: {row['ebike']}", max_width=300)
        ).add_to(m)

    folium_static(m)


if submit_rent and input_street != "" and my_loc != '':
    closest_station = get_bike_avail(my_loc, data, input_bike_modes)
    show_station_map(my_loc, closest_station, data)

elif submit_return and input_street != "" and my_loc != '':
    closest_station = get_dock_avail(my_loc, data)
    show_station_map(my_loc, closest_station, data)