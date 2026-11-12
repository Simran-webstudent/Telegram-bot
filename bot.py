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

NOTIFIED_USERS = set()
USER_STATES = {}
last_error_state = None


# --- ADMIN COMMANDS: STATUS & ACTIVITY ---
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


# --- DATA STORE VIEW COMMAND ---
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


# --- MANUAL INTERVENTION TOGGLE COMMAND ---
async def manual_mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text("⚠️ **Usage:** `/manual <USER_ID>` (Isse bot us user ke liye automatic replies/restrictions pause kar dega jab aap khud handle kar rahe hon)", parse_mode="Markdown")
        return
    
    try:
        target_id = int(context.args[0])
        if target_id in MANUAL_HANDLED_USERS:
            MANUAL_HANDLED_USERS.remove(target_id)
            save_data()
            await update.message.reply_text(f"🤖 **Auto-Shield Resumed** for User `{target_id}`.", parse_mode="Markdown")
        else:
            MANUAL_HANDLED_USERS.add(target_id)
            save_data()
            await update.message.reply_text(f"✋ **Manual Intervention Mode Enabled** for User `{target_id}`. Bot has paused automatic replies/restrictions for this chat.", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid User ID format.")


# --- RESTART COMMAND ---
async def restart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text("🔄 **Restarting bot system...** Please wait a few seconds.")
    os._exit(0)


# --- HELP COMMAND ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    
    help_text = (
        "🤖 **ADVANCED SECURE BOT COMMANDS GUIDE** 🚀\n\n"
        "1️⃣ **/status** — Bot system uptime & health check\n"
        "2️⃣ **/datastore** — Sabhi approved aur banned lists dekhein\n"
        "3️⃣ **/manual <user_id>** — Manual chat handling mode toggle karein (Bot pause)\n"
        "4️⃣ **/check** — User details aur approval status check karein\n"
        "5️⃣ **/approve** — Text chat approve karein\n"
        "6️⃣ **/restrict** — Text chat restrict karein\n"
        "7️⃣ **Granular Media Commands:**\n"
        "   • `/photorestrict` / `/photoapprove`\n"
        "   • `/stickerrestrict` / `/stickerapprove`\n"
        "   • `/docrestrict` / `/docapprove`\n"
        "8️⃣ **.del** — Kisi bhi message ko quietly delete karne ke liye.\n"
        "9️⃣ **/restart** — Bot ko restart karein."
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
    await update.message.reply_text(f"✅ **Success!** `{word}` ko securely encrypted banned words list mein add kar diya gaya hai.", parse_mode="Markdown")

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
        await update.message.reply_text(f"🗑️ **Success!** `{word}` ko list se hata kar data re-encrypt kar diya gaya hai.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ `{word}` list mein maujud nahi hai.", parse_mode="Markdown")

async def list_words_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    
    words_list = ", ".join([f"`{w}`" for w in BANNED_WORDS])
    await update.message.reply_text(
        f"📋 **Encrypted Banned Words List:**\n\n{words_list}",
        parse_mode="Markdown"
    )


# --- CHECK USER COMMAND ---
async def check_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    target_id = None
    target_identifier = "Unknown"

    if update.message and update.message.reply_to_message:
        replied = update.message.reply_to_message
        if replied.from_user:
            target_id = replied.from_user.id
            target_identifier = f"ID: `{target_id}` (Name: {replied.from_user.first_name})"

    elif context.args:
        arg = context.args[0]
        if arg.isdigit():
            target_id = int(arg)
            target_identifier = f"ID: `{target_id}`"

    if target_id:
        is_blocked = target_id in BLOCKED_USERS
        is_manual = target_id in MANUAL_HANDLED_USERS
        
        report_text = (
            f"🔍 **GRANULAR USER REPORT**\n\n"
            f"👤 **Target:** {target_identifier}\n"
            f"💬 **Text Status:** {'🔒 Restricted' if is_blocked else '✨ Approved'}\n"
            f"🖼️ **Photo/Video:** {'✨ Approved' if target_id in PHOTO_VIDEO_APPROVED else '🚫 Restricted'}\n"
            f"🎨 **Sticker/Emoji:** {'✨ Approved' if target_id in STICKER_EMOJI_APPROVED else '🚫 Restricted'}\n"
            f"📁 **Doc/Audio:** {'✨ Approved' if target_id in DOCUMENT_AUDIO_APPROVED else '🚫 Restricted'}\n"
            f"✋ **Manual Mode:** {'Active (Bot Paused)' if is_manual else 'Inactive (Auto Shield)'}"
        )
        await update.message.reply_text(report_text, parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/check <USER_ID>` ya message par reply karein.", parse_mode="Markdown")


# --- APPROVE / RESTRICT COMMANDS (TEXT & CATEGORIES) ---
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = None
    if update.message and update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args and context.args[0].isdigit():
        target_id = int(context.args[0])

    if target_id:
        APPROVED_USERS.add(target_id)
        PHOTO_VIDEO_APPROVED.add(target_id)
        STICKER_EMOJI_APPROVED.add(target_id)
        DOCUMENT_AUDIO_APPROVED.add(target_id)
        if target_id in BLOCKED_USERS:
            BLOCKED_USERS.remove(target_id)
        save_data()
        await update.message.reply_text(f"✨ **Success!** User (`{target_id}`) fully approved across all text & media categories.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/approve <USER_ID>`", parse_mode="Markdown")

async def restrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = None
    if update.message and update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args and context.args[0].isdigit():
        target_id = int(context.args[0])

    if target_id:
        if target_id == ADMIN_CHAT_ID:
            return
        BLOCKED_USERS.add(target_id)
        if target_id in APPROVED_USERS:
            APPROVED_USERS.remove(target_id)
        save_data()
        await update.message.reply_text(f"🔒 **Success!** User (`{target_id}`) restricted securely!", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/restrict <USER_ID>`", parse_mode="Markdown")


# --- GRANULAR CATEGORY COMMANDS ---
async def photo_approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None
    if target_id:
        PHOTO_VIDEO_APPROVED.add(target_id)
        save_data()
        await update.message.reply_text(f"🖼️ Photo/Video approved for `{target_id}`", parse_mode="Markdown")

async def photo_restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None
    if target_id and target_id in PHOTO_VIDEO_APPROVED:
        PHOTO_VIDEO_APPROVED.remove(target_id)
        save_data()
        await update.message.reply_text(f"🔒 Photo/Video restricted for `{target_id}`", parse_mode="Markdown")

async def sticker_approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None
    if target_id:
        STICKER_EMOJI_APPROVED.add(target_id)
        save_data()
        await update.message.reply_text(f"🎨 Sticker/Emoji approved for `{target_id}`", parse_mode="Markdown")

async def sticker_restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None
    if target_id and target_id in STICKER_EMOJI_APPROVED:
        STICKER_EMOJI_APPROVED.remove(target_id)
        save_data()
        await update.message.reply_text(f"🔒 Sticker/Emoji restricted for `{target_id}`", parse_mode="Markdown")

async def doc_approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None
    if target_id:
        DOCUMENT_AUDIO_APPROVED.add(target_id)
        save_data()
        await update.message.reply_text(f"📁 Document/Audio approved for `{target_id}`", parse_mode="Markdown")

async def doc_restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None
    if target_id and target_id in DOCUMENT_AUDIO_APPROVED:
        DOCUMENT_AUDIO_APPROVED.remove(target_id)
        save_data()
        await update.message.reply_text(f"🔒 Document/Audio restricted for `{target_id}`", parse_mode="Markdown")


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

    # 1. ADMIN OR OWNER BYPASS
    if user_id == ADMIN_CHAT_ID or user_id == context.bot.id or getattr(message, "out", False):
        return

    # 2. MANUAL INTERVENTION MODE CHECK (BOT PAUSED FOR THIS USER)
    if user_id in MANUAL_HANDLED_USERS:
        return  # Bot stays completely silent so you can handle the chat manually!

    # 3. BLOCKED USER CHECK
    if user_id in BLOCKED_USERS:
        try:
            await message.delete()
        except Exception as e:
            print(f"Blocked User Delete Error: {e}")
        return

    user_name = sender.first_name or "Dear"

    # --- CATEGORIZED MEDIA CHECKS ---
    is_photo_video = bool(message.photo or message.video or message.video_note)
    is_sticker_emoji = bool(message.sticker or message.animation)
    is_doc_audio = bool(message.document or message.audio or message.voice)

    if is_photo_video and (user_id not in PHOTO_VIDEO_APPROVED):
        await handle_restricted_media(message, context, user_id, user_name, "Photo/Video", is_business, business_conn_id)
        return

    if is_sticker_emoji and (user_id not in STICKER_EMOJI_APPROVED):
        await handle_restricted_media(message, context, user_id, user_name, "Sticker/Emoji/GIF", is_business, business_conn_id)
        return

    if is_doc_audio and (user_id not in DOCUMENT_AUDIO_APPROVED):
        await handle_restricted_media(message, context, user_id, user_name, "Document/Audio/Voice", is_business, business_conn_id)
        return

    # Text Content Check
    text_content = (message.text or message.caption or "").lower()
    has_banned_content = any(banned in text_content for banned in BANNED_WORDS)

    if has_banned_content:
        try:
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
                response_text = "I'm doing well, but I don't really do random chats with unknown people unless there's a specific reason or work involved. It's enough here."
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


# --- HELPER FOR RESTRICTED MEDIA ALERT ---
async def handle_restricted_media(message, context, user_id, user_name, media_type, is_business, business_conn_id):
    try:
        await message.delete()
        alert_header = (
            f"🚨 **STEALTH BLOCKED {media_type.upper()}**\n\n"
            f"👤 **Sender:** {user_name} (ID: `{user_id}`)\n"
            f"💡 **Quick Action:** `/approve {user_id}`"
        )
        alert_msg = await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=alert_header, parse_mode="Markdown")
        
        forwarded_media = None
        if is_business and business_conn_id:
            forwarded_media = await context.bot.copy_message(chat_id=ADMIN_CHAT_ID, from_chat_id=message.chat_id, message_id=message.message_id)
        else:
            forwarded_media = await message.forward(chat_id=ADMIN_CHAT_ID)

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


# --- DELETE COMMAND (.del / /del) ---
async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message and update.message.reply_to_message:
            await update.message.reply_to_message.delete()
        if update.message:
            await update.message.delete()
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
        BotCommand("status", "Bot system status aur health dekhein"),
        BotCommand("datastore", "Sabhi approved aur banned lists dekhein"),
        BotCommand("manual", "Manual chat handling mode toggle karein"),
        BotCommand("help", "Commands ki list dekhein"),
        BotCommand("check", "User status check karein"),
        BotCommand("approve", "User fully approve karein"),
        BotCommand("restrict", "User restrict karein"),
        BotCommand("restart", "Bot restart karein"),
        BotCommand("del", "Message delete karein (.del)")
    ])
    await application.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="🔐 **Advanced Bot Online with Granular Categorized Lists & Manual Pause Mode!** 🚀",
        parse_mode="Markdown"
    )


def main():
    try:
        request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
        app = ApplicationBuilder().token(BOT_TOKEN).request(request).post_init(post_init).build()

        app.add_handler(CommandHandler("status", status_cmd))
        app.add_handler(CommandHandler("datastore", datastore_cmd))
        app.add_handler(CommandHandler("manual", manual_mode_cmd))
        app.add_handler(CommandHandler("restart", restart_cmd))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("check", check_user_cmd))
        app.add_handler(CommandHandler("approve", approve_user))
        app.add_handler(CommandHandler("restrict", restrict_user))
        app.add_handler(CommandHandler("photoapprove", photo_approve_cmd))
        app.add_handler(CommandHandler("photorestrict", photo_restrict_cmd))
        app.add_handler(CommandHandler("stickerapprove", sticker_approve_cmd))
        app.add_handler(CommandHandler("stickerrestrict", sticker_restrict_cmd))
        app.add_handler(CommandHandler("docapprove", doc_approve_cmd))
        app.add_handler(CommandHandler("docrestrict", doc_restrict_cmd))
        app.add_handler(CommandHandler("del", delete_cmd))
        
        # Message Handlers
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_incoming_dm))

        app.add_error_handler(error_handler)

        print("Advanced Bot is running smoothly...")
        app.run_polling(poll_interval=1.0, timeout=30, drop_pending_updates=True)
        
    except Exception as e:
    
        print(f"Bot start error: {e}")


if __name__ == "__main__":
    main()
