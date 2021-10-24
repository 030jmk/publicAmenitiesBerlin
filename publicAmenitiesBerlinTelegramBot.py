#!/usr/bin/env python

"""publicAmenitiesBerlinTelegramBot.py: Telegram bot which returns the closest public toilets or public water fountains in Berlin, when a location is sent to it"""
__author__      = "Jan Kopankiewicz"


import pandas as pd
#from ipywidgets import HTML
import folium
import haversine as hs
from bs4 import BeautifulSoup
import requests
import kml2geojson
from zipfile import ZipFile
import xmltodict

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CallbackQueryHandler, ConversationHandler, CallbackContext, Filters
from telegram.ext import CommandHandler, MessageHandler
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

def marker_text(row):
  lat= (row[1]["Latitude"])
  long= (row[1]["Longitude"])
  isAccessible = yesno(row[1]["isHandicappedAccessible"])
  price = "{} EUR".format(row[1]["Price"])
  urinal = yesno(row[1]["hasUrinal"])
  coins = yesno(row[1]["canBePayedWithCoins"])
  nfc = yesno(row[1]["canBePayedWithNFC"])
  table = yesno(row[1]["hasChangingTable"])
  name = row[1]["Street"]
  return "<b>{}</b><p>{}</p><p>price: {}<br>has urinal: {}<br>👛 takes coins: {}<br>📳 NFC: {}<br>🚼 table: {}<br>♿ accessible: {}".format(row[1]["Description"], name,price,urinal,coins,nfc,table,isAccessible)


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
                                             callback_data=f"water,{user_location.latitude},{user_location.longitude}")]]
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

def main() -> None:
    """Run the bot."""
    updater = Updater("2057690314:AAHByNjNOVB1AnidNG2zzr-VCcoB9EMG7bE", use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CallbackQueryHandler(pick_one))
    dispatcher.add_handler(MessageHandler(Filters.location, button))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
