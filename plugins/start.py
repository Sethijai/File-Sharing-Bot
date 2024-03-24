import os
import asyncio
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, MessageNotModified, PeerIdInvalid
from typing import Union
import pytz
import random 
import logging
import re
from datetime import datetime, date
import string
from typing import List
from database.users_chats_db import tech_vj
from bs4 import BeautifulSoup
import requests
import aiohttp
import json
from config import Config
from bot import Bot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT
from helper_func import subscribed, encode, decode, get_messages
from database.database import add_user, del_user, full_userbase, present_user

TOKENS = {}
VERIFIED = {}

LOG_TEXT_P = """#NewUser
ID - <code>{}</code>
Nᴀᴍᴇ - {}"""
logger = logging.getLogger(__name__)

import motor.motor_asyncio
from config import Config
import random
import string

DATABASE_NAME = "vjbotztechvj"
DATABASE_URI = "mongodb+srv://Cluster0:Cluster0@cluster0.c07xkuf.mongodb.net/?retryWrites=true&w=majority"

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.users = self.db.users

    async def is_user_exist(self, user_id):
        user = await self.users.find_one({"_id": user_id})
        return bool(user)
    
    async def add_user(self, user_id, name):
        user = {"_id": user_id, "name": name}
        await self.users.insert_one(user)
        
    async def create_user_token(self, user_id):
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
        await self.users.update_one({"_id": user_id}, {"$set": {"token": token}}, upsert=True)
        return token
    
    async def get_user_token(self, user_id):
        user = await self.users.find_one({"_id": user_id})
        if user:
            return user.get("token")
        return None
    
    async def verify_user_token(self, user_id, token):
        user = await self.users.find_one({"_id": user_id, "token": token})
        if user:
            await self.users.update_one({"_id": user_id}, {"$unset": {"token": ""}})
            return True
        return False

tech_vj = Database(DATABASE_URI, DATABASE_NAME)

# Configure logging
logging.basicConfig(filename='bot.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_token(bot, user_id):
    user = await bot.get_users(user_id)
    if not await tech_vj.is_user_exist(user.id):
        await tech_vj.add_user(user.id, user.first_name)
        await bot.send_message(Config.TECH_VJ_LOG_CHANNEL, LOG_TEXT_P.format(user.id, user.mention))
        logger.info(f"New user added: {user.id}")
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    link = f"https://t.me/{bot.username}?start={user_id}-{token}"  # Adjust the link format here
    TOKENS[user.id] = {token: False}
    shortened_verify_url = await get_verify_shorted_link(user.id, token, link)  # Pass 'link' argument here
    logger.info(f"Token generated for user {user.id}: {token}")
    return token, str(shortened_verify_url)

async def verify_user(bot, userid, token):
    user = await bot.get_users(userid)
    if not await tech_vj.is_user_exist(user.id):
        await tech_vj.add_user(user.id, user.first_name)
        await bot.send_message(Config.TECH_VJ_LOG_CHANNEL, LOG_TEXT_P.format(user.id, user.mention))
        logger.info(f"New user added: {user.id}")
    TOKENS[user.id] = {token: True}
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    VERIFIED[user.id] = str(today)
    logger.info(f"User {user.id} verified with token: {token}")

async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    logger.info(f"Checking token for user {user.id}: {token}")

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except:
            pass
    
    token_verified = await check_verification(client, user_id)
    if not token_verified:
        text = message.text
        if len(text) > 7:
            try:
                base64_string = text.split(" ", 1)[1]
                token = await decode(base64_string)
                user_id_from_token, token = token.split("-")
                user_id_from_token = int(user_id_from_token)
            except Exception as e:
                await message.reply("Invalid verification link.")
                return
            if user_id != user_id_from_token:
                await message.reply("Invalid verification link.")
                return
            
            # Verify the token
            if await check_token(client, user_id, token):
                await verify_user(client, user_id, token)
                await message.reply("Verification successful!")
            else:
                await message.reply("Invalid token. Please try again.")
        else:
            token, shortened_url = await get_token(client, user_id)
            await message.reply(f"Click on the link to verify: {shortened_url}")
            return
    else:
        # If token is verified, continue with the regular start command logic
        text = message.text
        if len(text) > 7:
            try:
                base64_string = text.split(" ", 1)[1]
            except:
                return
            string = await decode(base64_string)
            argument = string.split("-")
            if len(argument) == 3:
                try:
                    start = int(int(argument[1]) / abs(client.db_channel.id))
                    end = int(int(argument[2]) / abs(client.db_channel.id))
                except:
                    return
                if start <= end:
                    ids = range(start,end+1)
                else:
                    ids = []
                    i = start
                    while True:
                        ids.append(i)
                        i -= 1
                        if i < end:
                            break
            elif len(argument) == 2:
                try:
                    ids = [int(int(argument[1]) / abs(client.db_channel.id))]
                except:
                    return
            temp_msg = await message.reply("Please wait...")
            try:
                messages = await get_messages(client, ids)
            except:
                await message.reply_text("Something went wrong..!")
                return
            await temp_msg.delete()

            for msg in messages:

                if bool(CUSTOM_CAPTION) & bool(msg.document):
                    caption = CUSTOM_CAPTION.format(previouscaption = "" if not msg.caption else msg.caption.html, filename = msg.document.file_name)
                else:
                    caption = "" if not msg.caption else msg.caption.html

                if DISABLE_CHANNEL_BUTTON:
                    reply_markup = msg.reply_markup
                else:
                    reply_markup = None

                try:
                    await msg.copy(chat_id=message.from_user.id, caption = caption, parse_mode = ParseMode.HTML, reply_markup = reply_markup, protect_content=PROTECT_CONTENT)
                    await asyncio.sleep(0.5)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(chat_id=message.from_user.id, caption = caption, parse_mode = ParseMode.HTML, reply_markup = reply_markup, protect_content=PROTECT_CONTENT)
                except:
                    pass
            return
        else:
            reply_markup = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("😊 About Me", callback_data = "about"),
                        InlineKeyboardButton("❤️‍🔥 subscribe", url = "http://youtube.com/@ultroidofficial")
                    ]
                ]
            )
            await message.reply_text(
                text = START_MSG.format(
                    first = message.from_user.first_name,
                    last = message.from_user.last_name,
                    username = None if not message.from_user.username else '@' + message.from_user.username,
                    mention = message.from_user.mention,
                    id = message.from_user.id
                ),
                reply_markup = reply_markup,
                disable_web_page_preview = True,
                quote = True
            )
            return

    
# Token verification
@Bot.on_message(filters.private)
async def handle_verification_message(client, message):
    user_id = message.from_user.id
    text = message.text.strip()
    if user_id in TOKENS and text in TOKENS[user_id].values():
        token = text
        if await tech_vj.verify_user_token(user_id, token):
            await message.reply("Verification successful!")
        else:
            await message.reply("Invalid token. Please try again.")
    
#=====================================================================================##

WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""

#=====================================================================================##


@Bot.on_message(filters.private & filters.command('start') & filters.user(ADMINS))
async def not_joined(client: Client, message: Message):
    buttons = [
        [
            InlineKeyboardButton(
                "Join Channel",
                url = client.invitelink)
        ]
    ]
    try:
        buttons.append(
            [
                InlineKeyboardButton(
                    text = 'Try Again',
                    url = f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ]
        )
    except IndexError:
        pass

    await message.reply(
        text = FORCE_MSG.format(
                first = message.from_user.first_name,
                last = message.from_user.last_name,
                username = None if not message.from_user.username else '@' + message.from_user.username,
                mention = message.from_user.mention,
                id = message.from_user.id
            ),
        reply_markup = InlineKeyboardMarkup(buttons),
        quote = True,
        disable_web_page_preview = True
    )

@Bot.on_message(filters.private & filters.command('users') & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await tech_vj.full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await tech_vj.full_userbase()
        broadcast_msg = message.reply_to_message
        total = 0
        successful = 0
        blocked = 0
        deleted = 0
        unsuccessful = 0
        
        pls_wait = await message.reply("<i>Broadcasting Message.. This will Take Some Time</i>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await tech_vj.del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await tech_vj.del_user(chat_id)
                deleted += 1
            except:
                unsuccessful += 1
                pass
            total += 1
        
        status = f"""<b><u>Broadcast Completed</u>

Total Users: <code>{total}</code>
Successful: <code>{successful}</code>
Blocked Users: <code>{blocked}</code>
Deleted Accounts: <code>{deleted}</code>
Unsuccessful: <code>{unsuccessful}</code></b>"""
        
        return await pls_wait.edit(status)

    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()
