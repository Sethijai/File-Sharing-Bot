import os
import asyncio
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from bot import Bot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT
from helper_func import subscribed, encode, decode, get_messages
from pymongo import MongoClient
from urllib.parse import quote_plus
import random
import string
import logging

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace this with your MongoDB connection URI
DATABASE_URI = "mongodb+srv://Cluster0:Cluster0@cluster0.c07xkuf.mongodb.net/ultroidxTeam?retryWrites=true&w=majority"

# Initialize MongoDB client and database
client = MongoClient(DATABASE_URI)
db = client.get_default_database()
collection = db['tokens']

# Function to generate a random token
def generate_token():
    # Generate a random string of characters for the token
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return token

# Function to save token to MongoDB
def save_token_to_db(user_id, token):
    # Insert token into the database
    token_doc = {'user_id': user_id, 'token': token}
    collection.insert_one(token_doc)

# Function to verify token
def verify_token(user_id, token):
    token_doc = collection.find_one({'user_id': user_id, 'token': token})
    return token_doc is not None

# Function to handle verified token
async def process_verified_token(client: Client, message: Message, token):
    id = message.from_user.id
    try:
        base64_string = token.split(" ", 1)[1]
    except IndexError:
        await message.reply_text("Invalid token or not verified.")
        return

    string = await decode(base64_string)
    argument = string.split("-")

    if len(argument) == 3:
        try:
            start = int(int(argument[1]) / abs(client.db_channel.id))
            end = int(int(argument[2]) / abs(client.db_channel.id))
        except ValueError:
            await message.reply_text("Invalid token or not verified.")
            return

        ids = range(start, end + 1) if start <= end else []
        temp_msg = await message.reply("Please wait...")

        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")
            await message.reply_text("Something went wrong!")
            return

        await temp_msg.delete()

        for msg in messages:
            caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html,
                                              filename=msg.document.file_name)
                       if bool(CUSTOM_CAPTION) and bool(msg.document) else
                       "" if not msg.caption else msg.caption.html)

            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML,
                               reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML,
                               reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
            except Exception as e:
                logger.error(f"Error copying message: {e}")

# Function to provide verification link
async def provide_verification_link(client: Client, message: Message):
    bot_username = (await client.get_me()).username

    if not bot_username:
        logger.error("Bot username not found")
        await message.reply_text("Bot username not found. Please set up the bot correctly.")
        return

    token = generate_token()
    save_token_to_db(message.from_user.id, token)
    token_encoded = quote_plus(token)
    link = f"https://t.me/{bot_username}?start=token_{token_encoded}"
    await message.reply_text(f'Use this link to verify: {link}')

# Bot initialization
@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    tokens = message.text.split(" ", 1)

    if len(tokens) > 1:
        # User provided a token, proceed with verification
        token = tokens[1]
        if verify_token(message.from_user.id, token):
            # Token is valid, proceed with the main code
            await process_verified_token(client, message, token)
        else:
            # Token is not valid or verified, provide instructions
            await message.reply_text("Invalid token or not verified.")
    else:
        # User didn't provide a token, provide the verification link instead
        await provide_verification_link(client, message)



#=====================================================================================##

WAIT_MSG = """"<b>Processing ...</b>"""

REPLY_ERROR = """<code>Use this command as a replay to any telegram message with out any spaces.</code>"""

#=====================================================================================##

    
    
@Bot.on_message(filters.command('start') & filters.private)
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

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
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
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
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
