import os
import sys
import json
import asyncio
import logging
import threading
import urllib.request
import time
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

# --- DUMMY HTTP SERVER & AUTO-PING KEEP ALIVE FOR FLY.IO ---
PORT = int(os.environ.get("PORT", 8080))

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def start_dummy_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_dummy_server, daemon=True).start()

def self_ping_loop():
    while True:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}")
        except Exception:
            pass
        time.sleep(180)

# --- SMART FRIENDLY AI ASSISTANT FOR DMS (UNRESTRICTED) ---
async def dm_ai_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Agar chat Private (DM) nahi hai, toh yeh function yahi se return ho jayega
    # (Taki groups ki moderation restrictions par koi asar na pade)
    if update.effective_chat.type != "private":
        return

    # User ka message capture karein
    user_message = update.message.text
    if not user_message:
        return

    user_text_lower = user_message.lower()

    # Friendly, warm, aur smart conversational responses
    if any(word in user_text_lower for word in ["hello", "hi", "hey", "hii", "namaste"]):
        reply = "Hey there! 👋 Main aapka safety aur moderation assistant hoon. Bataiye, aaj main aapki kya madad kar sakta hoon?"
    elif any(word in user_text_lower for word in ["help", "features", "commands", "kya kar sakte ho"]):
        reply = "Main aapke chats aur groups ko spam se safe rakhne mein madad karta hoon! 🛡️ Aap mujhse kisi bhi cheez ke baare mein pooch sakte hain, DM mein yahan koi restrictions nahi hain."
    elif any(word in user_text_lower for word in ["kaise ho", "how are you"]):
        reply = "Main ekdum 24/7 active aur badiya hoon! 🚀 Aap bataiye, sab kaisa chal raha hai?"
    else:
        # General friendly fallback jo aapki guidelines (warm, polite, smart) match kare
        reply = f"Aapne bilkul theek kaha! Main aapki baatein sun raha hoon. Agar aapko bot ke features ya commands ke baare mein kuch janna hai, toh bejhijhak pooch sakte hain. 😊"

    await update.message.reply_text(reply)

threading.Thread(target=self_ping_loop, daemon=True).start()
# -------------------------------------------------------------------------

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

ADMIN_CHAT_ID = 1448151744  # Owner ID
DATA_FILE = "bot_data.json"
KEY_FILE = "secret.key"

# --- Built-in HTTP Server Keep-Alive for Fly.io ---
def run_server():
    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    httpd.serve_forever()

# Background thread mein server start karein taaki bot band na ho
threading.Thread(target=run_server, daemon=True).start()


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
        # --- English Slang & Profanity ---
        "abuse", "badword", "idiot", "sex", "porn", "adult", "fuck", "shit", 
        "bitch", "bastard", "asshole", "cunt", "dick", "pussy", "slut", "whore",
        "crap", "damn", "cock", "piss",
        # --- Hindi / Hinglish Abusive Words ---
        "bhadwa", "chutiya", "randi", "gali", "madarchod", "behanchod", 
        "bhenchod", "bhosdike", "gandu", "harami", "kamine", "kamin", 
        "lauda", "loda", "lund", "choot", "chuut", "saala", "saali", 
        "kamina", "randwa", "tatta", "jhant"
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
                    set(data.get("media_approved_users", [1448151744]))
                )
        except Exception as e:
            print(f"Data Load/Decrypt Error: {e}")
    return (
        default_banned,
        {1448151744},
        {1448151744}
    )

def save_data():
    try:
        data = {
            "banned_words": list(BANNED_WORDS),
            "approved_users": list(APPROVED_USERS),
            "media_approved_users": list(MEDIA_APPROVED_USERS)
        }
        json_str = json.dumps(data)
        encrypted_data = cipher.encrypt(json_str.encode("utf-8"))
        with open(DATA_FILE, "wb") as f:
            f.write(encrypted_data)
    except Exception as e:
        print(f"Data Save/Encrypt Error: {e}")

# Load initial data
BANNED_WORDS, APPROVED_USERS, MEDIA_APPROVED_USERS = load_data()
NOTIFIED_USERS = set()
last_error_state = None


# --- HELP COMMAND ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    
    help_text = (
        "🤖 **SECURE BOT COMMANDS GUIDE** 🚀\n\n"
        "1️⃣ **/check** — User ki details aur approval status check karein\n"
        "2️⃣ **/approve** — User ko text chat ke liye approve karein\n"
        "3️⃣ **/restrict** — User ko text chat se restrict karein\n"
        "4️⃣ **/mediaapprove** — User ko media bhejne ki permission dein\n"
        "5️⃣ **/mediarestrict** — User ki media sharing permission wapas lein\n"
        "6️⃣ 📝 **BANNED WORDS MANAGEMENT:**\n"
        "   • `/addword <word>` — Naya banned word add karein\n"
        "   • `/delword <word>` — Banned word hatayein\n"
        "   • `/listwords` — Active banned words ki list dekhein\n"
        "7️⃣ **.del** — Message delete karne ke liye."
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
        elif arg.startswith("@"):
            target_username = arg.replace("@", "").lower()
            target_id = context.bot_data.get(f"user_{target_username}")
            target_identifier = f"Username: @{target_username} (ID: `{target_id}`)"

    if target_id:
        is_text_approved = target_id in APPROVED_USERS
        is_media_approved = target_id in MEDIA_APPROVED_USERS
        
        text_status = "✨ Approved (Text Allowed)" if is_text_approved else "🔒 Restricted"
        media_status = "🖼️ Allowed (Media Permitted)" if is_media_approved else "🚫 Restricted (Media Blocked)"
        
        report_text = (
            f"🔍 **USER CHECK REPORT**\n\n"
            f"👤 **Target:** {target_identifier}\n"
            f"💬 **Text Status:** {text_status}\n"
            f"📁 **Media Status:** {media_status}"
        )
        await update.message.reply_text(report_text, parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/check <USER_ID>` ya message par reply karein.", parse_mode="Markdown")


# --- APPROVE COMMAND (TEXT CHAT) ---
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    target_id = None
    target_name = "User"

    if update.message and update.message.reply_to_message:
        replied = update.message.reply_to_message
        if replied.from_user:
            target_id = replied.from_user.id
            target_name = replied.from_user.first_name or "User"

    elif context.args:
        arg = context.args[0]
        if arg.isdigit():
            target_id = int(arg)
            target_name = f"ID `{target_id}`"
        elif arg.startswith("@"):
            target_username = arg.replace("@", "").lower()
            target_id = context.bot_data.get(f"user_{target_username}")
            target_name = arg

    if target_id:
        APPROVED_USERS.add(target_id)
        if target_id in NOTIFIED_USERS:
            NOTIFIED_USERS.remove(target_id)
        save_data()
        await update.message.reply_text(
            f"✨ **Success!** {target_name} (ID: `{target_id}`) approved and saved securely!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⚠️ **Usage:** `/approve <USER_ID>`", parse_mode="Markdown")


# --- RESTRICT COMMAND (TEXT CHAT) ---
async def restrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    target_id = None
    if update.message and update.message.reply_to_message:
        replied = update.message.reply_to_message
        if replied.from_user:
            target_id = replied.from_user.id

    elif context.args:
        arg = context.args[0]
        if arg.isdigit():
            target_id = int(arg)
        elif arg.startswith("@"):
            target_username = arg.replace("@", "").lower()
            target_id = context.bot_data.get(f"user_{target_username}")

    if target_id:
        if target_id == ADMIN_CHAT_ID:
            await update.message.reply_text("⚠️ Aap owner ko restrict nahi kar sakte!")
            return
        
        if target_id in APPROVED_USERS:
            APPROVED_USERS.remove(target_id)
            save_data()
        
        await update.message.reply_text(f"🔒 **Success!** User (`{target_id}`) restricted securely!", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/restrict <USER_ID>`", parse_mode="Markdown")


# --- MEDIA APPROVE COMMAND ---
async def media_approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    target_id = None
    target_name = "User"

    if update.message and update.message.reply_to_message:
        replied = update.message.reply_to_message
        if replied.from_user:
            target_id = replied.from_user.id
            target_name = replied.from_user.first_name or "User"

    elif context.args:
        arg = context.args[0]
        if arg.isdigit():
            target_id = int(arg)
            target_name = f"ID `{target_id}`"

    if target_id:
        MEDIA_APPROVED_USERS.add(target_id)
        save_data()
        await update.message.reply_text(f"🖼️ **Success!** {target_name} media approved securely!", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/mediaapprove <USER_ID>`", parse_mode="Markdown")


# --- MEDIA RESTRICT COMMAND ---
async def media_restrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    target_id = None
    if update.message and update.message.reply_to_message:
        replied = update.message.reply_to_message
        if replied.from_user:
            target_id = replied.from_user.id

    elif context.args:
        arg = context.args[0]
        if arg.isdigit():
            target_id = int(arg)

    if target_id:
        if target_id == ADMIN_CHAT_ID:
            return
        if target_id in MEDIA_APPROVED_USERS:
            MEDIA_APPROVED_USERS.remove(target_id)
            save_data()
        await update.message.reply_text(f"🔒 **Success!** User media restricted securely!", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ **Usage:** `/mediarestrict <USER_ID>`", parse_mode="Markdown")


# --- CONTACT CARD APPROVER ---
async def handle_contact_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    contact = update.message.contact
    if contact and contact.user_id:
        APPROVED_USERS.add(contact.user_id)
        MEDIA_APPROVED_USERS.add(contact.user_id)
        save_data()
        await update.message.reply_text(f"✨ Contact **{contact.first_name}** approved and encrypted successfully!")


# --- UNIFIED DM & SEPARATE MEDIA RESTRICTION HANDLER ---
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

    if sender.username:
        context.bot_data[f"user_{sender.username.lower()}"] = sender.id

    if sender.id == ADMIN_CHAT_ID or sender.id == context.bot.id or getattr(message, "out", False):
        return

    user_name = sender.first_name or "Dear"
    user_id = sender.id

    # Media Check
    has_restricted_media = bool(
        message.animation or message.photo or message.video or 
        message.video_note or message.document or message.audio or message.voice
    )

    if has_restricted_media and (user_id not in MEDIA_APPROVED_USERS):
        try:
            await message.delete()
            alert_header = (
                f"🚨 **STEALTH BLOCKED MEDIA FILE**\n\n"
                f"👤 **Sender:** {user_name} (ID: `{user_id}`)\n"
                f"💡 **Quick Action:** `/mediaapprove {user_id}`"
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
            print(f"Media Error: {e}")
        return

    # Text Content Check
    text_content = (message.text or message.caption or "").lower()
    has_banned_content = any(banned in text_content for banned in BANNED_WORDS)

    if has_banned_content or (user_id not in APPROVED_USERS):
        try:
            await message.delete()
            if user_id not in NOTIFIED_USERS:
                NOTIFIED_USERS.add(user_id)
                rejection_text = "Hello, can i know why are you messaging me? Don't message me! Why are you messaging me? I am not interested."
                if is_business and business_conn_id:
                    await context.bot.send_message(chat_id=message.chat_id, text=rejection_text, business_connection_id=business_conn_id)
                else:
                    await message.reply_text(rejection_text)
            
            alert_header = (
                f"🚨 **STEALTH BLOCKED SPAM MESSAGE**\n\n"
                f"👤 **Sender:** {user_name} (ID: `{user_id}`)\n"
                f"💬 **Content:** `{message.text or 'None'}`\n"
                f"💡 **Quick Action:** `/approve {user_id}`"
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
            print(f"Text Error: {e}")
        return


# --- DELETE COMMAND (.del) ---
async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
        BotCommand("help", "Commands ki list dekhein"),
        BotCommand("check", "User status check karein"),
        BotCommand("approve", "Text chat approve karein"),
        BotCommand("restrict", "Text chat restrict karein"),
        BotCommand("mediaapprove", "Media sharing approve karein"),
        BotCommand("mediarestrict", "Media sharing restrict karein"),
        BotCommand("addword", "Naya banned word add karein"),
        BotCommand("delword", "Banned word hatayein"),
        BotCommand("listwords", "Banned words ki list dekhein"),
        BotCommand("del", "Message delete karein")
    ])
    await application.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="🔐 **Bot is online with AES Fernet Encryption & Secure Storage!** 🚀",
        parse_mode="Markdown"
    )


def main():
    try:
        request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0, write_timeout=30.0, pool_timeout=30.0)
        app = ApplicationBuilder().token(BOT_TOKEN).request(request).post_init(post_init).build()

        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("check", check_user_cmd))
        app.add_handler(CommandHandler("approve", approve_user))
        app.add_handler(CommandHandler("restrict", restrict_user))
        app.add_handler(CommandHandler("mediaapprove", media_approve_user))
        app.add_handler(CommandHandler("mediarestrict", media_restrict_user))
        app.add_handler(CommandHandler("addword", add_word_cmd))
        app.add_handler(CommandHandler("delword", del_word_cmd))
        app.add_handler(CommandHandler("listwords", list_words_cmd))
        app.add_handler(CommandHandler("del", delete_cmd))
        app.add_handler(MessageHandler(filters.CONTACT, handle_contact_share))
        
        # --- DM AI Assistant Handler (Unrestricted DMs) ---
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, dm_ai_assistant))
        
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_incoming_dm))

        app.add_error_handler(error_handler)

        print("Secure Bot is running smoothly...")
        app.run_polling(poll_interval=1.0, timeout=30, drop_pending_updates=True)
        
    except Exception as e:
        print(f"Bot start error: {e}")


if __name__ == "__main__":
    main()
