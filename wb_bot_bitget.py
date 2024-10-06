import discord
import requests
import json
import asyncio
import hmac
import base64
import time
from pybitget.stream import BitgetWsClient, SubscribeReq, handel_error
from pybitget.enums import *
from pybitget import logger
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BITGET_API_KEY = os.getenv('BITGET_API_KEY')
BITGET_SECRET_KEY = os.getenv('BITGET_SECRET_KEY')
BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE')
CHANNEL_ID = os.getenv('CHANNEL_ID')
WAITING_TIME =  os.getenv('WAITING_TIME')

api_url = "https://api.bitget.com"
symbol = "BTCUSDT_UMCBL"

def parse_params_to_str(params):
    url = '?'
    for key, value in params.items():
        url = url + str(key) + '=' + str(value) + '&'
    return url[0:-1]

def get_signature(message):
    mac = hmac.new(bytes(BITGET_SECRET_KEY, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()
    return base64.b64encode(d)

def bitget_request(request_path, body, query, method):
    std_time = time.time() * 1000
    new_time = int(std_time)
    if str(body) == '{}' or str(body) == 'None':
        converted_body = ''
    else:
        converted_body = json.dumps(body)
    message = str(new_time) + method + request_path + parse_params_to_str(query) + converted_body
    headers = {"ACCESS-KEY": BITGET_API_KEY,
               "ACCESS-SIGN": get_signature(message),
               "ACCESS-TIMESTAMP": str(new_time),
               "ACCESS-PASSPHRASE": BITGET_PASSPHRASE,
               "Content-Type": "application/json",
               "Locale": "en-US"
               }
    if method == "GET":
        request_resp = requests.get((api_url + request_path), headers=headers, params=query)
    return request_resp

def convert_ctime_to_date(ctime):
    ctime = int(ctime)
    ctime_in_seconds = ctime / 1000
    date_time = datetime.fromtimestamp(ctime_in_seconds)
    readable_date = date_time.strftime('%Y-%m-%d %H:%M:%S')
    return readable_date


query = {
    "productType": "umcbl",
    "marginCoin": "USDT"
}

intents = discord.Intents.default()
intents.message_content = True

timesPositions = []



class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timesPositions = [] 
        self.timesOrders = [] 
        
    async def on_ready(self):
        print(f'Connecté en tant que {self.user}')
        self.check_positions_task = self.loop.create_task(self.check_positions())
        self.check_positions_task = self.loop.create_task(self.check_orders())

    async def send_position_update(self, position):
        channel = self.get_channel(int(CHANNEL_ID))
        if channel:
           if position['cTime'] not in self.timesPositions:  
                try:
                    await channel.send(
                        f"**-----------------------------------------------**\n"
                        f"**New Position:**\n"
                        f"**Token:** {position['symbol']}\n" 
                        f"**Leverage:** {position['leverage']}\n"
                        f"**Market Price:** {position['marketPrice']}\n"
                        f"**Average Open Price:** {position['averageOpenPrice']}\n"
                        f"**Time:** `{convert_ctime_to_date(position['cTime'])}`\n"
                        f"**Hold Side:** {position['holdSide']}\n"
                        f"**-----------------------------------------------**\n"
                    )
                    self.timesPositions.append(position['cTime']) 
                    print("Message envoyé avec succès.")
                except discord.Forbidden:
                    print("Le bot n'a pas les permissions nécessaires pour envoyer un message dans ce canal.")
                except Exception as e:
                    print(f"Erreur lors de l'envoi du message : {e}")
           else: 
                print(f"deja envoyé")
        else:
            print(f"Le canal n'a pas été trouvé. {self.get_channel(int(CHANNEL_ID))}")
            
    async def send_order_update(self, order):
        channel = self.get_channel(int(CHANNEL_ID))
        if channel:
           if order['cTime'] not in self.timesOrders:  
                try:
                    await channel.send(
                        f"**-----------------------------------------------**\n"
                        f"**New Order:**\n"
                        f"**Token:** {order['symbol']}\n" 
                        f"**Leverage:** {order['leverage']}\n"
                        f"**Order Price:** {order['price']}\n"
                        f"**Time:** `{convert_ctime_to_date(order['cTime'])}`\n"
                        f"**Side:** {order['side']}\n"
                        f"**-----------------------------------------------**\n"
                    )
                    self.timesOrders.append(order['cTime']) 
                    print("Message envoyé avec succès.")
                except discord.Forbidden:
                    print("Le bot n'a pas les permissions nécessaires pour envoyer un message dans ce canal.")
                except Exception as e:
                    print(f"Erreur lors de l'envoi du message : {e}")
           else: 
                print(f"deja envoyé")
        else:
            print(f"Le canal n'a pas été trouvé. {self.get_channel(int(CHANNEL_ID))}")

    def get_positions(self):
        order_resp = bitget_request("/api/mix/v1/position/allPosition", None, query, "GET")
        return order_resp.json().get('data', {})
    
    def get_orders(self):
      order_resp = bitget_request("/api/mix/v1/order/marginCoinCurrent", None, query, "GET")
      return order_resp.json().get('data', {})

    async def check_positions(self):
        while True:
            positions = self.get_positions()
            print(f"Positions: {positions}")
            for position in positions:
                position_info =position
                await self.send_position_update(position_info)
            await asyncio.sleep(1)  
            
    async def check_orders(self):
       while True:
           orders = self.get_orders()
           print(f"Orders: {orders}")
           for order in orders:
               await self.send_order_update(order)
           await asyncio.sleep(WAITING_TIME)  

   

async def main():
    client = MyClient(intents=intents)
    await client.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
