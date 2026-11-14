import os
import sys
import json
import asyncio
import logging
import threading
import urllib.request
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from cryptography.fernet import Fernet
from telegram import Update, BotCommand
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- DUMMY HTTP SERVER & AUTO-PING KEEP ALIVE ---
PORT = int(os.environ.get("PORT", 8080))
START_TIME = time.time()

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running with Advanced AI & Granular Shield!")

def start_dummy_server():
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Server start error: {e}")

threading.Thread(target=start_dummy_server, daemon=True).start()

def self_ping_loop():
    while True:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}")
        except Exception:
            pass
        time.sleep(180)

threading.Thread(target=self_ping_loop, daemon=True).start()

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = 1448151744  # Owner ID
DATA_FILE = "bot_data.json"
KEY_FILE = "secret.key"

# --- ENCRYPTION SETUP (FERNET) ---
def get_or_create_encryption_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key

cipher = Fernet(get_or_create_encryption_key())

# --- ENCRYPTED PERSISTENT STORAGE FUNCTIONS ---
def load_data():
    default_banned = {
        "abuse", "badword", "idiot", "sex", "porn", "adult", "fuck", "shit", 
        "bitch", "bastard", "asshole", "cunt", "dick", "pussy", "slut", "whore",
        "crap", "damn", "cock", "piss", "bhadwa", "chutiya", "randi", "gali", 
        "madarchod", "behanchod", "bhenchod", "bhosdike", "gandu", "harami", 
        "kamine", "kamin", "lauda", "loda", "lund", "choot", "chuut", "saala", 
        "saali", "kamina", "randwa", "tatta", "jhant"
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "rb") as f:
                encrypted_data = f.read()
                decrypted_data = cipher.decrypt(encrypted_data)
                data = json.loads(decrypted_data.decode("utf-8"))
                return (
                    set(data.get("banned_words", list(default_banned))),
                    set(data.get("approved_users", [1448151744])),
                    set(data.get("photo_video_approved", [1448151744])),
                    set(data.get("sticker_emoji_approved", [1448151744])),
                    set(data.get("document_audio_approved", [1448151744])),
                    set(data.get("blocked_users", [])),
                    set(data.get("manual_handled_users", []))
                )
        except Exception as e:
            print(f"Data Load/Decrypt Error: {e}")
    return (
        default_banned,
        {1448151744},
        {1448151744},
        {1448151744},
        {1448151744},
        set(),
        set()
    )

def save_data():
    try:
        data = {
            "banned_words": list(BANNED_WORDS),
            "approved_users": list(APPROVED_USERS),
            "photo_video_approved": list(PHOTO_VIDEO_APPROVED),
            "sticker_emoji_approved": list(STICKER_EMOJI_APPROVED),
            "document_audio_approved": list(DOCUMENT_AUDIO_APPROVED),
            "blocked_users": list(BLOCKED_USERS),
            "manual_handled_users": list(MANUAL_HANDLED_USERS)
        }
        json_str = json.dumps(data)
        encrypted_data = cipher.encrypt(json_str.encode("utf-8"))
        with open(DATA_FILE, "wb") as f:
            f.write(encrypted_data)
    except Exception as e:
        print(f"Data Save/Encrypt Error: {e}")

(
    BANNED_WORDS, 
    APPROVED_USERS, 
    PHOTO_VIDEO_APPROVED, 
    STICKER_EMOJI_APPROVED, 
    DOCUMENT_AUDIO_APPROVED, 
    BLOCKED_USERS, 
    MANUAL_HANDLED_USERS
) = load_data()

USER_STATES = {}
last_error_state = None


# --- HELPER TO EXTRACT TARGET USER ID ---
def get_target_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.reply_to_message and update.message.reply_to_message.from_user:
        return update.message.reply_to_message.from_user.id
    elif context.args:
        arg = context.args[0]
        if arg.isdigit():
            return int(arg)
        elif arg.startswith("@"):
            target_username = arg.replace("@", "").lower()
            return context.bot_data.get(f"user_{target_username}")
    return None


# --- ADMIN COMMANDS: STATUS, DATASTORE, MANUAL, RESTART ---
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    uptime_seconds = int(time.time() - START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    status_text = (
        "🟢 **BOT SYSTEM STATUS REPORT** 🚀\n\n"
        f"⏱️ **Uptime:** `{hours}h {minutes}m {seconds}s`\n"
        f"🛡️ **Active Banned Words:** `{len(BANNED_WORDS)}`\n"
        f"✨ **Approved Text Users:** `{len(APPROVED_USERS)}`\n"
        f"🔒 **Blocked/Restricted Users:** `{len(BLOCKED_USERS)}`\n"
        f"👤 **Manual Handled Chats:** `{len(MANUAL_HANDLED_USERS)}`\n"
        f"🟢 **Core Security:** AES Encrypted & Online"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def datastore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    
    report = (
        "📂 **SECURE DATA STORE LISTS** 📊\n\n"
        f"✨ **Approved Text Users:** `{list(APPROVED_USERS)}`\n"
        f"🖼️ **Photo/Video Approved:** `{list(PHOTO_VIDEO_APPROVED)}`\n"
        f"🎨 **Sticker/Emoji Approved:** `{list(STICKER_EMOJI_APPROVED)}`\n"
        f"📁 **Document/Audio Approved:** `{list(DOCUMENT_AUDIO_APPROVED)}`\n"
        f"🔒 **Blocked Users:** `{list(BLOCKED_USERS)}`\n"
        f"🤝 **Manual Handled Mode Users:** `{list(MANUAL_HANDLED_USERS)}`"
    )
    await update.message.reply_text(report, parse_mode="Markdown")

async def manual_mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if not target_id:
        await update.message.reply_text("⚠️ **Usage:** `/manual <USER_ID>` (Bot pauses automated replies when you handle the chat)", parse_mode="Markdown")
        return
    
    if target_id in MANUAL_HANDLED_USERS:
        MANUAL_HANDLED_USERS.remove(target_id)
        save_data()
        await update.message.reply_text(f"🤖 **Auto-Shield Resumed** for User `{target_id}`.", parse_mode="Markdown")
    else:
        MANUAL_HANDLED_USERS.add(target_id)
        save_data()
        await update.message.reply_text(f"✋ **Manual Intervention Mode Enabled** for User `{target_id}`. Bot has paused automated actions.", parse_mode="Markdown")

async def restart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text("🔄 **Restarting bot system...** Please wait a few seconds.")
    os._exit(0)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    
    help_text = (
        "🤖 **ADVANCED SECURE BOT COMMANDS GUIDE** 🚀\n\n"
        "1️⃣ **/status** — Bot system uptime & health\n"
        "2️⃣ **/datastore** — Sabhi approved aur banned lists dekhein\n"
        "3️⃣ **/manual <user_id>** — Manual chat handling toggle karein\n"
        "4️⃣ **/check <user_id>** — User ka granular approval status check karein\n\n"
        "💬 **GLOBAL & TEXT CONTROLS:**\n"
        "   • `/approve <id>` / `/restrict <id>` — Full access control\n"
        "   • `/textapprove <id>` / `/textrestrict <id>` — Sirf text chat control\n\n"
        "📁 **MEDIA CONTROLS (ALL & SPECIFIC):**\n"
        "   • `/mediaapprove <id>` / `/mediarestrict <id>` — All media control\n"
        "   • `/photoapprove <id>` / `/photorestrict <id>` — Photos & Videos\n"
        "   • `/stickerapprove <id>` / `/stickerrestrict <id>` — Stickers, GIFs & Emojis\n"
        "   • `/docapprove <id>` / `/docrestrict <id>` — Documents, Audio & Voice\n\n"
        "📝 **BANNED WORDS & STEALTH:**\n"
        "   • `/addword` | `/delword` | `/listwords`\n"
        "   • `.del` or `/del` — Stealth delete message\n"
        "   • `/restart` — Bot restart karein"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# --- DYNAMIC BANNED WORDS COMMANDS ---
async def add_word_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text("⚠️ **Usage:** `/addword <banned_word>`", parse_mode="Markdown")
        return
    word = context.args[0].lower().strip()
    BANNED_WORDS.add(word)
    save_data()
    await update.message.reply_text(f"✅ `{word}` added to encrypted banned words list.", parse_mode="Markdown")

async def del_word_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text("⚠️ **Usage:** `/delword <banned_word>`", parse_mode="Markdown")
        return
    word = context.args[0].lower().strip()
    if word in BANNED_WORDS:
        BANNED_WORDS.remove(word)
        save_data()
        await update.message.reply_text(f"🗑️ `{word}` removed from banned words list.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ `{word}` not found in list.", parse_mode="Markdown")

async def list_words_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    words_list = ", ".join([f"`{w}`" for w in BANNED_WORDS])
    await update.message.reply_text(f"📋 **Encrypted Banned Words List:**\n\n{words_list}", parse_mode="Markdown")


# --- CHECK USER COMMAND ---
async def check_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        is_blocked = target_id in BLOCKED_USERS
        is_manual = target_id in MANUAL_HANDLED_USERS
        is_text = target_id in APPROVED_USERS and not is_blocked
        
        report_text = (
            f"🔍 **GRANULAR USER REPORT** (ID: `{target_id}`)\n\n"
            f"💬 **Text Status:** {'✨ Approved' if is_text else '🔒 Restricted'}\n"
            f"🖼️ **Photo/Video:** {'✨ Approved' if target_id in PHOTO_VIDEO_APPROVED else '🚫 Restricted'}\n"
            f"🎨 **Sticker/Emoji:** {'✨ Approved' if target_id in STICKER_EMOJI_APPROVED else '🚫 Restricted'}\n"
            f"📁 **Doc/Audio:** {'✨ Approved' if target_id in DOCUMENT_AUDIO_APPROVED else '🚫 Restricted'}\n"
            f"✋ **Manual Mode:** {'Active (Bot Paused)' if is_manual else 'Inactive (Auto Shield)'}"
        )
        await update.message.reply_text(report_text, parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/check <USER_ID>` ya message par reply karein.", parse_mode="Markdown")


# --- GLOBAL APPROVE / RESTRICT COMMANDS ---
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        APPROVED_USERS.add(target_id)
        PHOTO_VIDEO_APPROVED.add(target_id)
        STICKER_EMOJI_APPROVED.add(target_id)
        DOCUMENT_AUDIO_APPROVED.add(target_id)
        BLOCKED_USERS.discard(target_id)
        MANUAL_HANDLED_USERS.discard(target_id)
        USER_STATES.pop(target_id, None)
        save_data()
        await update.message.reply_text(f"✨ **Success!** User (`{target_id}`) fully approved across all text & media categories.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/approve <USER_ID>`", parse_mode="Markdown")

async def restrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        if target_id == ADMIN_CHAT_ID:
            return
        BLOCKED_USERS.add(target_id)
        APPROVED_USERS.discard(target_id)
        PHOTO_VIDEO_APPROVED.discard(target_id)
        STICKER_EMOJI_APPROVED.discard(target_id)
        DOCUMENT_AUDIO_APPROVED.discard(target_id)
        MANUAL_HANDLED_USERS.discard(target_id)
        save_data()
        await update.message.reply_text(f"🔒 **Success!** User (`{target_id}`) fully restricted across all categories!", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/restrict <USER_ID>`", parse_mode="Markdown")


# --- TEXT SPECIFIC APPROVE & RESTRICT ---
async def text_approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        APPROVED_USERS.add(target_id)
        BLOCKED_USERS.discard(target_id)
        USER_STATES.pop(target_id, None)
        save_data()
        await update.message.reply_text(f"💬 **Text Approved** for User (`{target_id}`)", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/textapprove <USER_ID>`", parse_mode="Markdown")

async def text_restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id and target_id != ADMIN_CHAT_ID:
        APPROVED_USERS.discard(target_id)
        BLOCKED_USERS.add(target_id)
        save_data()
        await update.message.reply_text(f"🔒 **Text Restricted** for User (`{target_id}`)", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/textrestrict <USER_ID>`", parse_mode="Markdown")


# --- ALL MEDIA SPECIFIC APPROVE & RESTRICT ---
async def media_approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        PHOTO_VIDEO_APPROVED.add(target_id)
        STICKER_EMOJI_APPROVED.add(target_id)
        DOCUMENT_AUDIO_APPROVED.add(target_id)
        save_data()
        await update.message.reply_text(f"🖼️📂 **All Media Approved** for User (`{target_id}`)", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/mediaapprove <USER_ID>`", parse_mode="Markdown")

async def media_restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id and target_id != ADMIN_CHAT_ID:
        PHOTO_VIDEO_APPROVED.discard(target_id)
        STICKER_EMOJI_APPROVED.discard(target_id)
        DOCUMENT_AUDIO_APPROVED.discard(target_id)
        save_data()
        await update.message.reply_text(f"🔒 **All Media Restricted** for User (`{target_id}`)", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/mediarestrict <USER_ID>`", parse_mode="Markdown")


# --- GRANULAR CATEGORY COMMANDS ---
async def photo_approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        PHOTO_VIDEO_APPROVED.add(target_id)
        save_data()
        await update.message.reply_text(f"🖼️ **Photo/Video Approved** for `{target_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/photoapprove <USER_ID>`", parse_mode="Markdown")

async def photo_restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        PHOTO_VIDEO_APPROVED.discard(target_id)
        save_data()
        await update.message.reply_text(f"🔒 **Photo/Video Restricted** for `{target_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/photorestrict <USER_ID>`", parse_mode="Markdown")

async def sticker_approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        STICKER_EMOJI_APPROVED.add(target_id)
        save_data()
        await update.message.reply_text(f"🎨 **Sticker/Emoji/GIF Approved** for `{target_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/stickerapprove <USER_ID>`", parse_mode="Markdown")

async def sticker_restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        STICKER_EMOJI_APPROVED.discard(target_id)
        save_data()
        await update.message.reply_text(f"🔒 **Sticker/Emoji/GIF Restricted** for `{target_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/stickerrestrict <USER_ID>`", parse_mode="Markdown")

async def doc_approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        DOCUMENT_AUDIO_APPROVED.add(target_id)
        save_data()
        await update.message.reply_text(f"📁 **Document/Audio/Voice Approved** for `{target_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/docapprove <USER_ID>`", parse_mode="Markdown")

async def doc_restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = get_target_id(update, context)
    if target_id:
        DOCUMENT_AUDIO_APPROVED.discard(target_id)
        save_data()
        await update.message.reply_text(f"🔒 **Document/Audio/Voice Restricted** for `{target_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/docrestrict <USER_ID>`", parse_mode="Markdown")


# --- CONTACT CARD APPROVER ---
async def handle_contact_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    contact = update.message.contact
    if contact and contact.user_id:
        APPROVED_USERS.add(contact.user_id)
        PHOTO_VIDEO_APPROVED.add(contact.user_id)
        STICKER_EMOJI_APPROVED.add(contact.user_id)
        DOCUMENT_AUDIO_APPROVED.add(contact.user_id)
        BLOCKED_USERS.discard(contact.user_id)
        save_data()
        await update.message.reply_text(f"✨ Contact **{contact.first_name}** fully approved and saved securely!")


# --- UNIFIED DM & GRANULAR RESTRICTION HANDLER WITH AI FLOW & MANUAL PAUSE ---
async def process_incoming_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_error_state
    if last_error_state is not None:
        last_error_state = None

    is_business = False
    business_conn_id = None
    
    if update.business_message:
        message = update.business_message
        is_business = True
        business_conn_id = message.business_connection_id
    elif update.message:
        message = update.message
    else:
        return

    sender = message.from_user
    if not sender:
        return

    user_id = sender.id

    if sender.username:
        context.bot_data[f"user_{sender.username.lower()}"] = sender.id

    # 1. ADMIN OR OWNER BYPASS (Auto-enable manual pause if you message an unapproved user directly)
    if user_id == ADMIN_CHAT_ID or getattr(message, "out", False):
        if getattr(message, "out", False) and message.chat and message.chat.id != ADMIN_CHAT_ID:
            target_chat_id = message.chat.id
            if target_chat_id not in APPROVED_USERS and target_chat_id not in MANUAL_HANDLED_USERS:
                MANUAL_HANDLED_USERS.add(target_chat_id)
                save_data()
        return

    if user_id == context.bot.id:
        return

    # 2. MANUAL INTERVENTION MODE CHECK (BOT PAUSED FOR THIS USER)
    if user_id in MANUAL_HANDLED_USERS:
        return  # Bot stays completely silent until you approve or change restrictions

    # 3. BLOCKED USER CHECK
    if user_id in BLOCKED_USERS:
        try:
            await message.delete()
        except Exception as e:
            print(f"Blocked User Delete Error: {e}")
        return

    user_name = sender.first_name or "User"

    # --- CATEGORIZED MEDIA CHECKS ---
    is_photo_video = bool(message.photo or message.video or message.video_note)
    is_sticker_emoji = bool(message.sticker or message.animation)
    is_doc_audio = bool(message.document or message.audio or message.voice)

    if is_photo_video and (user_id not in PHOTO_VIDEO_APPROVED):
        await handle_restricted_media(message, context, user_id, user_name, "Photo/Video", "/photoapprove", is_business, business_conn_id)
        return

    if is_sticker_emoji and (user_id not in STICKER_EMOJI_APPROVED):
        await handle_restricted_media(message, context, user_id, user_name, "Sticker/Emoji/GIF", "/stickerapprove", is_business, business_conn_id)
        return

    if is_doc_audio and (user_id not in DOCUMENT_AUDIO_APPROVED):
        await handle_restricted_media(message, context, user_id, user_name, "Document/Audio/Voice", "/docapprove", is_business, business_conn_id)
        return

    # --- TEXT CONTENT & BANNED WORDS CHECK ---
    text_content = (message.text or message.caption or "").lower()
    has_banned_content = any(banned in text_content for banned in BANNED_WORDS)

    if has_banned_content:
        try:
            await send_stealth_text_alert(context, user_name, user_id, message.text or message.caption or "Media Caption", "BANNED WORD")
            await message.delete()
            rejection_text = "I was already clear about not wanting inappropriate content. Respect that and stop messaging me."
            if is_business and business_conn_id:
                await context.bot.send_message(chat_id=message.chat_id, text=rejection_text, business_connection_id=business_conn_id)
            else:
                await message.reply_text(rejection_text)
        except Exception as e:
            print(f"Banned Word Error: {e}")
        return

    # --- UNKNOWN USER CONVERSATION STATE MACHINE (CALM AUTHORITY FLOW) ---
    if user_id not in APPROVED_USERS:
        # Notify Admin DM about incoming unknown message before any action
        await send_stealth_text_alert(context, user_name, user_id, message.text or "None", "UNKNOWN DM")

        if user_id not in USER_STATES:
            USER_STATES[user_id] = 'initial_prompt'
            try:
                prompt_text = "Hey. Who's this, and what's this regarding?"
                if is_business and business_conn_id:
                    await context.bot.send_message(chat_id=message.chat_id, text=prompt_text, business_connection_id=business_conn_id)
                else:
                    await message.reply_text(prompt_text)
            except Exception as e:
                print(f"Initial Prompt Error: {e}")
            return

        current_state = USER_STATES.get(user_id)

        if current_state == 'initial_prompt':
            USER_STATES[user_id] = 'awaiting_reason'
            try:
                response_text = "I'm doing well, but I don't really do random chats with unknown people unless there's a specific reason or work involved."
                if is_business and business_conn_id:
                    await context.bot.send_message(chat_id=message.chat_id, text=response_text, business_connection_id=business_conn_id)
                else:
                    await message.reply_text(response_text)
            except Exception as e:
                print(f"Awaiting Reason Error: {e}")
            return

        elif current_state == 'awaiting_reason':
            try:
                response_text = "I was already clear about not wanting random chats. Respect that and stop messaging me."
                if is_business and business_conn_id:
                    await context.bot.send_message(chat_id=message.chat_id, text=response_text, business_connection_id=business_conn_id)
                else:
                    await message.reply_text(response_text)
                USER_STATES[user_id] = 'handled'
            except Exception as e:
                print(f"Final Boundary Error: {e}")
            return


# --- HELPER FOR STEALTH DM ALERTS (MEDIA & TEXT) ---
async def send_stealth_text_alert(context, user_name, user_id, content_text, alert_type):
    try:
        alert_header = (
            f"📩 **{alert_type} ALERT**\n\n"
            f"👤 **Sender:** {user_name} (ID: `{user_id}`)\n"
            f"💬 **Message:** `{content_text}`\n"
            f"⚡ **Actions:** `/approve {user_id}` | `/textapprove {user_id}` | `/manual {user_id}` | `/restrict {user_id}`"
        )
        alert_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=alert_header, parse_mode="Markdown")
        async def delete_alert_later(chat_id, alert_id):
            await asyncio.sleep(600)
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=alert_id)
            except Exception:
                pass
        asyncio.create_task(delete_alert_later(ADMIN_CHAT_ID, alert_msg.message_id))
    except Exception as e:
        print(f"Text Alert Error: {e}")

async def handle_restricted_media(message, context, user_id, user_name, media_type, quick_cmd, is_business, business_conn_id):
    try:
        # 1. Forward/Copy to Admin DM BEFORE deleting
        alert_header = (
            f"🚨 **STEALTH BLOCKED {media_type.upper()}**\n\n"
            f"👤 **Sender:** {user_name} (ID: `{user_id}`)\n"
            f"⚡ **Quick Action:** `{quick_cmd} {user_id}` or `/mediaapprove {user_id}`"
        )
        alert_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=alert_header, parse_mode="Markdown")
        
        forwarded_media = None
        if is_business and business_conn_id:
            forwarded_media = await context.bot.copy_message(chat_id=ADMIN_CHAT_ID, from_chat_id=message.chat_id, message_id=message.message_id)
        else:
            forwarded_media = await message.forward(chat_id=ADMIN_CHAT_ID)

        # 2. Delete original media from user chat
        await message.delete()

        # 3. Auto-cleanup preview after 10 minutes
        async def delete_preview_later(chat_id, alert_id, media_id):
            await asyncio.sleep(600)
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=alert_id)
                if media_id:
                    await context.bot.delete_message(chat_id=chat_id, message_id=media_id.message_id)
            except Exception:
                pass
        asyncio.create_task(delete_preview_later(ADMIN_CHAT_ID, alert_msg.message_id, forwarded_media))
    except Exception as e:
        print(f"Media Alert Error: {e}")


# --- STEALTH DELETE COMMAND (.del / /del) ---
async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.business_message or update.message
    if not message:
        return
    try:
        if message.reply_to_message:
            await message.reply_to_message.delete()
        await message.delete()
    except Exception as e:
        print(f"Delete Error: {e}")


# --- ERROR HANDLER ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    global last_error_state
    error_str = str(context.error)
    ignored_errors = ["Business_peer_invalid", "httpx.ReadError", "httpx.ConnectError", "Timed out", "NetworkError"]
    if any(ign in error_str for ign in ignored_errors):
        return
    last_error_state = error_str
    logging.error(msg="Exception while handling an update:", exc_info=context.error)


async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("help", "Sabhi commands ki complete list dekhein"),
        BotCommand("status", "Bot uptime aur status check karein"),
        BotCommand("datastore", "Approved aur banned lists dekhein"),
        BotCommand("manual", "Manual handling toggle (Bot pause)"),
        BotCommand("check", "User ka granular status check karein"),
        BotCommand("approve", "User ko sabhi access dein"),
        BotCommand("restrict", "User ko poori tarah restrict karein"),
        BotCommand("textapprove", "Sirf text chat approve karein"),
        BotCommand("textrestrict", "Sirf text chat restrict karein"),
        BotCommand("mediaapprove", "All media approve karein"),
        BotCommand("mediarestrict", "All media restrict karein"),
        BotCommand("photoapprove", "Photo/Video approve karein"),
        BotCommand("photorestrict", "Photo/Video restrict karein"),
        BotCommand("stickerapprove", "Sticker/Emoji/GIF approve karein"),
        BotCommand("stickerrestrict", "Sticker/Emoji/GIF restrict karein"),
        BotCommand("docapprove", "Document/Audio approve karein"),
        BotCommand("docrestrict", "Document/Audio restrict karein"),
        BotCommand("del", "Stealth delete message (.del)"),
        BotCommand("restart", "Bot system restart karein")
    ])
    await application.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="🔐 **Advanced Shield Bot Online!** All granular commands, auto-manual pause, and DM alerts active. 🚀",
        parse_mode="Markdown"
    )


def main():
    try:
        request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
        app = ApplicationBuilder().token(BOT_TOKEN).request(request).post_init(post_init).build()

        # System & Admin Commands
        app.add_handler(CommandHandler("status", status_cmd))
        app.add_handler(CommandHandler("datastore", datastore_cmd))
        app.add_handler(CommandHandler("manual", manual_mode_cmd))
        app.add_handler(CommandHandler("restart", restart_cmd))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("check", check_user_cmd))

        # Global & Text Commands
        app.add_handler(CommandHandler("approve", approve_user))
        app.add_handler(CommandHandler("restrict", restrict_user))
        app.add_handler(CommandHandler("textapprove", text_approve_cmd))
        app.add_handler(CommandHandler("textrestrict", text_restrict_cmd))

        # Global & Granular Media Commands
        app.add_handler(CommandHandler("mediaapprove", media_approve_cmd))
        app.add_handler(CommandHandler("mediarestrict", media_restrict_cmd))
        app.add_handler(CommandHandler("photoapprove", photo_approve_cmd))
        app.add_handler(CommandHandler("photorestrict", photo_restrict_cmd))
        app.add_handler(CommandHandler("stickerapprove", sticker_approve_cmd))
        app.add_handler(CommandHandler("stickerrestrict", sticker_restrict_cmd))
        app.add_handler(CommandHandler("docapprove", doc_approve_cmd))
        app.add_handler(CommandHandler("docrestrict", doc_restrict_cmd))

        # Banned Words & Stealth Delete
        app.add_handler(CommandHandler("addword", add_word_cmd))
        app.add_handler(CommandHandler("delword", del_word_cmd))
        app.add_handler(CommandHandler("listwords", list_words_cmd))
        app.add_handler(CommandHandler("del", delete_cmd))
        app.add_handler(MessageHandler(filters.Regex(r"^\.del$"), delete_cmd))
        app.add_handler(MessageHandler(filters.CONTACT, handle_contact_share))
        
        # Main Unified DM & Business Handler
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_incoming_dm))

        app.add_error_handler(error_handler)

        print("Advanced Bot is running smoothly...")
        app.run_polling(poll_interval=1.0, timeout=30, drop_pending_updates=True)
        
    except Exception as e:
        print(f"Bot start error: {e}")


if __name__ == "__main__":
    main()
