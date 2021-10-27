#!/usr/bin/env python

"""publicAmenitiesBerlinTelegramBot.py: Telegram bot which returns the closest public toilets or public water fountains in Berlin, when a location is sent to it"""
__author__      = "Jan Kopankiewicz"


import pandas as pd
import folium
import haversine as hs
from bs4 import BeautifulSoup
import requests
import kml2geojson
from zipfile import ZipFile
import xmltodict
from datetime import datetime, timezone

import logging

from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Location, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, ConversationHandler,PicklePersistence,InlineQueryHandler
from telegram.error import TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError

def com2dot(text):
  if type(text) != 'int':
    return float(text.replace(",","."))
  else:
    return text


def distance2pos(location1, location2):
  return float(round(hs.haversine(location1,location2),2))

def yesno(i):
  if i == 1:
    return "yes"
  else:
    return "no"



def location_cal(df,my_location):
  '''Given a DataFrame containing Location and Longitude columns and by providing the a location, 
  this functions returns the distance to the locations to the rows from the provided location in kilometers in a new column.
  The new DataFrame with the Distance column is then sorted and only the closest row entries are returned.'''
  
  Top = df
  Top["Distance"] = Top.apply(lambda row: distance2pos(my_location,(row.Latitude,row.Longitude)) ,axis=1)
  Top5 = Top.sort_values(by="Distance",ascending=True)[:5]
  return Top5

def gLink(lat,long):
  #"https://www.google.com/maps/place/{},+{}"                                       
  #"https://maps.apple.com/maps?q={},{}"
  return 'https://www.google.com/maps/place/{},{}'.format(lat,long)

plz_df=pd.read_csv("PLZ_locations.csv")
def latlongFromPLZ(plz):
  """Get a location in lat long from a Postleitzahl"""
  plz_long = round(plz_df.loc[plz_df['PLZ'] == plz].Longitude.values[0],8)
  plz_lat = round(plz_df.loc[plz_df['PLZ'] == plz].Latitude.values[0],8)
  return (plz_lat,plz_long)

def get_police_demo_data():
  """Return a DataFrame containing the demonstrations or protests listed for today including a rough estimation of where it is happening"""
  currentDate = datetime.now().strftime("%d.%m.%Y")
  event_url = "https://www.berlin.de/polizei/service/versammlungsbehoerde/versammlungen-aufzuege/"
  req = requests.get(event_url)
  soup = BeautifulSoup(req.content, 'html.parser')
  table_r = soup.findAll("tr", class_="odd line_1")
  demo_list = []
  for row in table_r:
    try:
      if row.find("td", class_="text", headers="Datum").text == currentDate:
        Datum = row.find("td", class_="text", headers="Datum").text
        Von = row.find("td", class_="text", headers="Von").text
        Bis = row.find("td", class_="text", headers="Bis").text
        Thema = row.find("td", class_="text", headers="Thema").text
        PLZ = int(row.find("td", class_="text", headers="PLZ").text)
        Versammlungsort = row.find("td", class_="text", headers="Versammlungsort").text
        Aufzugsstrecke = row.find("td", class_="text", headers="Aufzugsstrecke").text
        demo_list.append([Datum,Von,Bis,Thema,PLZ,Versammlungsort,Aufzugsstrecke])
    except:
      continue
  demo_df = pd.DataFrame(demo_list, columns=["Datum","Von","Bis","Thema","PLZ","Versammlungsort","Aufzugsstrecke"])
  demo_df['Latitude'] = demo_df.apply(lambda row: latlongFromPLZ(row.PLZ)[0] ,axis=1)
  demo_df['Longitude'] = demo_df.apply(lambda row: latlongFromPLZ(row.PLZ)[1] ,axis=1)
  return(demo_df)

# read location of public toilets into dataframe
url = "https://www.berlin.de/sen/uvk/_assets/verkehr/infrastruktur/oeffentliche-toiletten/berliner-toiletten-standorte.xlsx"
df = pd.read_excel(url,'Toiletten', header=3)
df["Longitude"] = df["Longitude"].apply(lambda x: com2dot(x)) 
df["Latitude"] = df["Latitude"].apply(lambda x: com2dot(x)) 

#Get the google KML URL from the bwb website
bwb_url = "https://www.bwb.de/de/trinkbrunnen.php"
req = requests.get(bwb_url)
soup = BeautifulSoup(req.content, 'html.parser')
kmz_url = soup.find("a", class_="trinkbrunnen")['href']

# download the kmz from google and save it
r = requests.get(kmz_url, allow_redirects=True)
open('Trinkbrunnen.kmz', 'wb').write(r.content)

# unzip the kmz and extract the kml
kmz = ZipFile("Trinkbrunnen.kmz", 'r')
kml = kmz.open('doc.kml', 'r').read()

# save the contents of the kml to xml
f = open("Trinkbrunnen.xml", "w")
f.write(str(kml,'utf-8'))
f.close()

#convert the xml to more usable json format
test = kml2geojson.main.convert("Trinkbrunnen.xml", "leaflet")

rows_list = []
for i in range(len(test[1]["features"])):
  long, lat = test[1]["features"][i]['geometry']['coordinates'][:2]
  description = test[1]["features"][i]['properties']['description']
  name = test[1]["features"][i]['properties']['name']

  dict1 = {'Name': name, 'Description': description, 'Longitude': long, 'Latitude': lat}
  rows_list.append(dict1)

# create dataframe 
df_water = pd.DataFrame.from_dict(rows_list)



### Telegram Bot ###

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> int:
   """Send message on `/start`."""
   user = update.message.from_user
   logger.info("User %s started the conversation.", user.first_name)
   send_location_keyboard = [[KeyboardButton(text="Send current location",request_location=True)]]
   update.message.reply_text('Help me figure out where you are by sending me your location.',
        reply_markup=ReplyKeyboardMarkup(send_location_keyboard, one_time_keyboard=False))

def button(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    user_location = update.message.location

    choice_keyboard = [
                       [InlineKeyboardButton("Public Toilet",
                                             callback_data=f"wc,{user_location.latitude},{user_location.longitude}")],
                       [InlineKeyboardButton("Potable Water",
                                             callback_data=f"water,{user_location.latitude},{user_location.longitude}")],
                       [InlineKeyboardButton("Demonstrations",
                                             callback_data=f"demo,{user_location.latitude},{user_location.longitude}")]]

    update.message.reply_text("Which public amenity are you looking to find?",
                              reply_markup=InlineKeyboardMarkup(choice_keyboard))



def pick_one(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    #query.edit_message_text(text=f"Selected: {query.data}")
    if query.data.split(',')[0] == "wc":
      my_location = float(query.data.split(',')[1]),float(query.data.split(',')[2])
      Top5 = location_cal(df,my_location)
      keyboard_t = [[InlineKeyboardButton(text="{}km - {}".format(Top5['Distance'].iloc[0],Top5['Description'].iloc[0]), url= "https://maps.apple.com/maps?q={},{}".format(Top5['Latitude'].iloc[0], Top5['Longitude'].iloc[0]))],
            [InlineKeyboardButton(text="{}km - {}".format(Top5['Distance'].iloc[1],Top5['Description'].iloc[1]), url= "https://maps.apple.com/maps?q={},{}".format(Top5['Latitude'].iloc[1], Top5['Longitude'].iloc[1]))],
            [InlineKeyboardButton(text="{}km - {}".format(Top5['Distance'].iloc[2],Top5['Description'].iloc[2]), url= "https://maps.apple.com/maps?q={},{}".format(Top5['Latitude'].iloc[2], Top5['Longitude'].iloc[2]))]]
      reply_markup_t = InlineKeyboardMarkup(keyboard_t)
      update.effective_message.reply_text("Closest Options:",reply_markup=reply_markup_t)

    if query.data.split(',')[0] == "water":
      my_location = float(query.data.split(',')[1]),float(query.data.split(',')[2])
      Top5w = location_cal(df_water,my_location)
      keyboard_w = [[InlineKeyboardButton(text="{}km - {}".format(Top5w['Distance'].iloc[0],Top5w['Name'].iloc[0]), url= "https://maps.apple.com/maps?q={},{}".format(Top5w['Latitude'].iloc[0], Top5w['Longitude'].iloc[0]))],
                  [InlineKeyboardButton(text="{}km - {}".format(Top5w['Distance'].iloc[1],Top5w['Name'].iloc[1]), url= "https://maps.apple.com/maps?q={},{}".format(Top5w['Latitude'].iloc[1], Top5w['Longitude'].iloc[1]))],
                  [InlineKeyboardButton(text="{}km - {}".format(Top5w['Distance'].iloc[2],Top5w['Name'].iloc[2]), url= "https://maps.apple.com/maps?q={},{}".format(Top5w['Latitude'].iloc[2], Top5w['Longitude'].iloc[2]))]]
      reply_markup_w = InlineKeyboardMarkup(keyboard_w)
      update.effective_message.reply_text("Closest Options:",reply_markup=reply_markup_w)

    if query.data.split(',')[0] == "demo":
      my_location = float(query.data.split(',')[1]),float(query.data.split(',')[2])
      Top5demo = location_cal(get_police_demo_data(),my_location)
      keyboard_demo = [[InlineKeyboardButton(text="~{}km - {}".format(round(Top5demo['Distance'].iloc[0],1),Top5demo['Thema'].iloc[0]), url= "https://maps.apple.com/maps?q={},{} Berlin".format(Top5demo['Versammlungsort'].iloc[0], Top5demo['PLZ'].iloc[0]))],
                  [InlineKeyboardButton(text="~{}km - {}".format(round(Top5demo['Distance'].iloc[1],1),Top5demo['Thema'].iloc[1]), url= "https://maps.apple.com/maps?q={},{} Berlin".format(Top5demo['Versammlungsort'].iloc[1], Top5demo['PLZ'].iloc[1]))],
                  [InlineKeyboardButton(text="~{}km - {}".format(round(Top5demo['Distance'].iloc[2],1),Top5demo['Thema'].iloc[2]), url= "https://maps.apple.com/maps?q={},{} Berlin".format(Top5demo['Versammlungsort'].iloc[2], Top5demo['PLZ'].iloc[2]))]]
      reply_markup_demo = InlineKeyboardMarkup(keyboard_demo)
      update.effective_message.reply_text("Nearby Protests:",reply_markup=reply_markup_demo)




def main() -> None:
    """Run the bot."""
    updater = Updater("TOKEN", use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CallbackQueryHandler(pick_one))
    dispatcher.add_handler(MessageHandler(Filters.location, button))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
