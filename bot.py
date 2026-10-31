import os
import sys
import asyncio
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, BotCommand
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- DUMMY HTTP SERVER FOR CLOUD HOSTING (RENDER / FLY.IO HEALTH CHECK) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_dummy_server, daemon=True).start()
# -------------------------------------------------------------------------

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Configuration (Using parentheses to handle mobile screen line-wrapping safely)
BOT_TOKEN = (
    "8525088862:AAFif8rY3R-INyIsTjFpsqiECs99cgpS5v8"
)

ADMIN_CHAT_ID = 1448151744  # Owner ID

# Strict Banned words
BANNED_WORDS = [
    "abuse", "badword", "idiot", "sex", "porn", "adult", "bhadwa", "chutiya", "randi", "gali"
]

APPROVED_USERS = {1448151744}       # Normal text chat ke liye approved users
MEDIA_APPROVED_USERS = {1448151744}  # Sirf media sharing ke liye approved users
NOTIFIED_USERS = set()
last_error_state = None


# --- RESTART COMMAND ---
async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await update.message.reply_text("🔄 **Bot restart ho raha hai...** 🚀", parse_mode="Markdown")
    os.execv(sys.executable, ['python'] + sys.argv)


# --- HELP COMMAND ---
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    
    help_text = (
        "🤖 **BOT COMMANDS GUIDE & USAGE** 🚀\n\n"
        "1️⃣ **/check** — User ki details aur approval status check karne ke liye:\n"
        "   • `/check 123456789` ya `/check @username` (Ya message par reply karein)\n\n"
        "2️⃣ **/approve** — User ko normal text chat ke liye approve karne ke liye:\n"
        "   • `/approve <USER_ID>` / Reply to message\n\n"
        "3️⃣ **/restrict** — User ko text chat se restrict karne ke liye:\n"
        "   • `/restrict <USER_ID>` / Reply to message\n\n"
        "4️⃣ **🖼️ /mediaapprove** — User ko media (photo/video) bhejne ki permission dene ke liye:\n"
        "   • `/mediaapprove <USER_ID>` / Reply to message\n\n"
        "5️⃣ **🔒 /mediarestrict** — User ki media sharing permission wapas lene ke liye:\n"
        "   • `/mediarestrict <USER_ID>` / Reply to message\n\n"
        "6️⃣ **/restart** — Bot ko instantly restart karne ke liye.\n"
        "7️⃣ **.del** — Message delete karne ke liye."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


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
            f"📁 **Media Status:** {media_status}\n\n"
            f"💡 *Quick Actions:* \n"
            f"• `/approve {target_id}` | `/restrict {target_id}`\n"
            f"• `/mediaapprove {target_id}` | `/mediarestrict {target_id}`"
        )
        await update.message.reply_text(report_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "⚠️ **Sahi tareeka use karein:**\n"
            "• `/check <USER_ID>`\n"
            "• `/check @username`",
            parse_mode="Markdown"
        )


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
        await update.message.reply_text(
            f"✨ **Success!** {target_name} (ID: `{target_id}`) ab **Text Chat ke liye Approved** ho gaya hai! (Lekin media permissions ke liye alag se `/mediaapprove` use karein agar zaroorat ho)",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ **Usage:** `/approve <USER_ID>` / `/approve @username` ya message par reply karein.",
            parse_mode="Markdown"
        )


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
        
        await update.message.reply_text(
            f"🔒 **Success!** User (`{target_id}`) ko text chat se **Restrict** kar diya gaya hai!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ **Usage:** `/restrict <USER_ID>` / `/restrict @username` ya user ke message par reply karein.",
            parse_mode="Markdown"
        )


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
        elif arg.startswith("@"):
            target_username = arg.replace("@", "").lower()
            target_id = context.bot_data.get(f"user_{target_username}")
            target_name = arg

    if target_id:
        MEDIA_APPROVED_USERS.add(target_id)
        await update.message.reply_text(
            f"🖼️ **Success!** {target_name} (ID: `{target_id}`) ko **Media Sharing ke liye Approve** kar diya gaya hai! Ab yeh media files bhej sakta hai.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ **Usage:** `/mediaapprove <USER_ID>` / `/mediaapprove @username` ya message par reply karein.",
            parse_mode="Markdown"
        )


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
        elif arg.startswith("@"):
            target_username = arg.replace("@", "").lower()
            target_id = context.bot_data.get(f"user_{target_username}")

    if target_id:
        if target_id == ADMIN_CHAT_ID:
            await update.message.reply_text("⚠️ Aap owner ki media restrict nahi kar sakte!")
            return
        
        if target_id in MEDIA_APPROVED_USERS:
            MEDIA_APPROVED_USERS.remove(target_id)
        
        await update.message.reply_text(
            f"🔒 **Success!** User (`{target_id}`) ki **Media Sharing restrict** kar di gayi hai! Ab yeh koi media file nahi bhej payega.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ **Usage:** `/mediarestrict <USER_ID>` / `/mediarestrict @username` ya message par reply karein.",
            parse_mode="Markdown"
        )


# --- CONTACT CARD APPROVER ---
async def handle_contact_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    contact = update.message.contact
    if contact and contact.user_id:
        APPROVED_USERS.add(contact.user_id)
        MEDIA_APPROVED_USERS.add(contact.user_id)
        await update.message.reply_text(f"✨ Contact **{contact.first_name}** ko text aur media dono ke liye approve kar diya gaya hai!")


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

    # Owner Bypass
    if sender.id == ADMIN_CHAT_ID or sender.id == context.bot.id or getattr(message, "out", False):
        return

    user_name = sender.first_name or "Dear"
    user_id = sender.id

    # 1. Media Check: Agar user ne media bheji hai aur wo MEDIA_APPROVED_USERS mein nahi hai
    has_restricted_media = bool(
        message.animation or 
        message.photo or 
        message.video or 
        message.video_note or 
        message.document or 
        message.audio or 
        message.voice
    )

    if has_restricted_media and (user_id not in MEDIA_APPROVED_USERS):
        try:
            await message.delete()
            
            media_type_desc = "Video / Video Note" if (message.video or message.video_note) else ("Photo / Image" if message.photo else "Media / Document")
            
            alert_header = (
                f"🚨 **STEALTH BLOCKED MEDIA FILE**\n\n"
                f"👤 **Sender:** {user_name} (ID: `{user_id}`)\n"
                f"📁 **Type:** {media_type_desc}\n"
                f"💬 **Caption:** `{message.caption or 'None'}`\n\n"
                f"💡 **Quick Action:** `/mediaapprove {user_id}` ya `/check {user_id}`\n"
                f"⏳ *Yeh alert 10 minutes mein auto-delete ho jayega.*"
            )
            
            alert_msg = await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=alert_header,
                parse_mode="Markdown"
            )
            
            forwarded_media = None
            if is_business and business_conn_id:
                forwarded_media = await context.bot.copy_message(
                    chat_id=ADMIN_CHAT_ID,
                    from_chat_id=message.chat_id,
                    message_id=message.message_id
                )
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
            print(f"❌ Media Restriction Error: {e}")
        return

    # 2. Text Content & Banned Words / Unapproved User Check
    text_content = (message.text or message.caption or "").lower()
    has_banned_content = any(banned in text_content for banned in BANNED_WORDS)

    if has_banned_content or (user_id not in APPROVED_USERS):
        try:
            await message.delete()
            
            if user_id not in NOTIFIED_USERS:
                NOTIFIED_USERS.add(user_id)
                rejection_text = "Hello, can i know why are you messaging me? Don't message me! Why are you messaging me? I am not interested."
                if is_business and business_conn_id:
                    await context.bot.send_message(
                        chat_id=message.chat_id,
                        text=rejection_text,
                        business_connection_id=business_conn_id
                    )
                else:
                    await message.reply_text(rejection_text)
            
            alert_header = (
                f"🚨 **STEALTH BLOCKED SPAM MESSAGE**\n\n"
                f"👤 **Sender:** {user_name} (ID: `{user_id}`)\n"
                f"💬 **Content:** `{message.text or 'None'}`\n\n"
                f"💡 **Quick Action:** `/approve {user_id}` ya `/check {user_id}`\n"
                f"⏳ *Yeh alert 10 minutes mein auto-delete ho jayega.*"
            )
            
            alert_msg = await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=alert_header,
                parse_mode="Markdown"
            )

            async def delete_alert_later(chat_id, alert_id):
                await asyncio.sleep(600)
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=alert_id)
                except Exception:
                    pass
            
            asyncio.create_task(delete_alert_later(ADMIN_CHAT_ID, alert_msg.message_id))
        except Exception as e:
            print(f"❌ Text Restriction Error: {e}")
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
    
    ignored_errors = [
        "Business_peer_invalid",
        "httpx.ReadError",
        "httpx.ConnectError",
        "httpx.WriteError",
        "Timed out",
        "NetworkError"
    ]
    
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
        BotCommand("restart", "Bot restart karein"),
        BotCommand("del", "Message delete karein")
    ])
    
    await application.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="✅ **Bot is online with independent Media & Text restrictions active!** 🚀",
        parse_mode="Markdown"
    )


def main():
    try:
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0
        )

        app = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .request(request)
            .post_init(post_init)
            .build()
        )

        # Handlers Registration
        app.add_handler(CommandHandler("restart", restart_bot))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("check", check_user_cmd))
        app.add_handler(CommandHandler("approve", approve_user))
        app.add_handler(CommandHandler("restrict", restrict_user))
        app.add_handler(CommandHandler("mediaapprove", media_approve_user))
        app.add_handler(CommandHandler("mediarestrict", media_restrict_user))
        app.add_handler(CommandHandler("del", delete_cmd))
        app.add_handler(MessageHandler(filters.CONTACT, handle_contact_share))
        
        app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_incoming_dm))

        app.add_error_handler(error_handler)

        print("Bot is running smoothly...")
        app.run_polling(
            poll_interval=1.0,
            timeout=30,
            drop_pending_updates=True
        )
    except Exception as e:
        print(f"Bot start error: {e}")


if __name__ == "__main__":
    main()
