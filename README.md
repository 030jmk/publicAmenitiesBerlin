AI-generated README.md


# Overview
The provided Python script is a Telegram bot designed to assist users in Berlin by providing the locations of the nearest public amenities such as public toilets, water fountains, and demonstrations/protests. When a user sends their location to the bot, it calculates the closest amenities and sends this information back to the user.
Features

- Location-Based Services: The bot can determine the nearest public toilets and water fountains based on the user's current location.
- Demonstration Alerts: It can also provide information about ongoing demonstrations or protests in Berlin, including their locations.
- Interactive User Interface: Utilizes Telegram's inline buttons and keyboards to create an interactive experience for users.
- Data Handling: Retrieves and processes data from various sources, including CSV files and online resources, to provide accurate location information.

# How It Works

- Data Collection: The bot collects data on public toilets and water fountains from online sources and converts it into a usable format.
- User Interaction: When a user starts the bot and sends their location, the bot presents options for finding nearby amenities.
- Distance Calculation: Using the Haversine formula, the bot calculates the distance from the user's location to various amenities.
- Response Generation: The bot then sends back a list of the closest amenities, complete with clickable links to view them on a map.

# Technical Details

Libraries Used:
- pandas for data manipulation.
- haversine for distance calculations.
- BeautifulSoup for web scraping.
- requests for handling HTTP requests.
- kml2geojson for converting KML files to GeoJSON.
- telegram and telegram.ext for creating the bot interface and handling user interactions.
  
Data Sources:
- Public toilet locations are retrieved from an Excel file hosted online.
- Water fountain locations are extracted from a KML file provided by the Berlin water company.
- Demonstration data is scraped from the Berlin police website.

# Usage
To use the bot, users need to:

- Start the bot on Telegram.
- Send their current location.
- Choose the type of amenity they are interested in (toilets, water fountains, or demonstrations).
- Receive a list of the nearest options with direct links to view them on a map.

This bot is particularly useful for residents and visitors in Berlin who need quick access to public amenities.
