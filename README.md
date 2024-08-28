AI-generated README.md with human edits.


# Overview
A Telegram bot designed to assist users in Berlin that provides the locations of the nearest public amenities such as public toilets, water fountains, and demonstrations/protests. When a user sends their location to the bot, it calculates the closest amenities and sends this information back to the user.

# Data Sources
The bot collects data on public toilets and water fountains from online sources and converts it into a usable format.
  - Drinking Fountains: The Berliner Wasser Betriebe (BWB) provide a Google Maps with built in Points of Interests on their [website](https://www.bwb.de/de/trinkbrunnen.php).
  - Public Toilettes: The Senatsverwaltung für Mobilität, Verkehr, Klimaschutz und Umwelt in Berlin provides the following 
[files](https://www.berlin.de/sen/uvk/mobilitaet-und-verkehr/infrastruktur/oeffentliche-toiletten/download/) for users to download.
  - Demonstrations: The Berlin Police updates a list of announced public gatherings and demonstrations on through [their website](https://www.berlin.de/polizei/service/versammlungsbehoerde/versammlungen-aufzuege/) 

# How It Works
- User Interaction: When a user starts the bot and sends their location, the bot presents options for finding nearby amenities.
- Response Generation: The bot calculates the distance from the user's location to various amenities and sends back a list of the closest amenities, complete with clickable links to view them on a map.

# Dependencies
- Telegram Bot Token
- requirements.txt
