# 🚲 To Bike To - Toronto Bike Share Finder

A Streamlit web app to help you find the nearest Toronto Bike Share station with available bikes or docks.

**Live App:** [to-bike-to.streamlit.app](https://to-bike-to.streamlit.app)

## Features

- Interactive map showing all Toronto Bike Share stations
- Find nearest station with available bikes or docks
- Walking and biking route calculations
- Real-time travel time estimates
- Address geocoding to find your location
- Custom dark theme

## Tech Stack

- **Streamlit** - Web app framework
- **Pandas** - Data processing
- **Toronto Open Data** - Real-time bike share station data via [GBFS API](https://tor.publicbikesystem.net/ube/gbfs/v1/en/)
- **Folium** - Interactive map visualization
- **Google Maps API** - Geocoding and route directions
- **Geopy** - Distance calculations

## Data Source

Real-time bike share data is fetched from the Toronto Public Bike System GBFS API:
- Station status and bike availability
- Station locations and information

## Screenshots

_Coming soon..._

## How It Works

1. Enter your address in Toronto
2. Choose whether you're renting or returning a bike
3. Select bike type preferences (optional)
4. Get directions to the nearest available station with travel time

## License

This project uses open data from the City of Toronto.
