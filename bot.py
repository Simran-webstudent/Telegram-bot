import os
import sys
import asyncio
import logging
from telegram import Update, BotCommand
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Configuration
BOT_TOKEN = "8525088862:AAHOITECNV8zLJOcZaX8LS-jno1SzPeC_g"
ADMIN_CHAT_ID = 1448151744  # Owner ID

# Strict Banned words
BANNED_WORDS = [
    "abuse", "badword", "idiot", "sex", "porn", "adult", "bhadwa", "chutiya", "randi", "gali"
]

APPROVED_USERS = {1448151744}
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
        "1️⃣ **/check** — Kisi user ki details aur history check karne ke liye:\n"
        "   • `/check 123456789` ya `/check @username` (Ya user ke message par reply karke `/check` likhein)\n\n"
        "2️⃣ **/approve** — User ko unrestricted chat dene ke liye:\n"
        "   • `/approve 123456789` / `/approve @username` / Reply to message\n\n"
        "3️⃣ **/restrict** — Approved user ko wapas restrict/block karne ke liye:\n"
        "   • `/restrict 123456789` / `/restrict @username` / Reply to message\n\n"
        "4️⃣ **/restart** — Bot ko instantly DM se reboot karne ke liye.\n"
        "5️⃣ **.del** — Message turant delete karne ke liye.\n\n"
        "💡 *Note:* Sabhi actions bot ke DM mein turant (real-time) execute hote hain!"
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
        is_approved = target_id in APPROVED_USERS
        status_str = "✨ Approved & Unrestricted" if is_approved else "🔒 Restricted / Stranger"
        
        report_text = (
            f"🔍 **USER CHECK REPORT**\n\n"
            f"👤 **Target:** {target_identifier}\n"
            f"📊 **Current Status:** {status_str}\n\n"
            f"💡 *Quick Actions:* \n"
            f"• `/approve {target_id}`\n"
            f"• `/restrict {target_id}`"
        )
        await update.message.reply_text(report_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "⚠️ **Sahi tareeka use karein:**\n"
            "• `/check <USER_ID>`\n"
            "• `/check @username`\n"
            "• User ke message par reply karke `/check` likhein.",
            parse_mode="Markdown"
        )


# --- APPROVE COMMAND ---
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
        await update.message.reply_text(
            f"✨ **Success!** {target_name} (ID: `{target_id}`) ko successfully approve kar diya gaya hai.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "⚠️ **Usage:** `/approve <USER_ID>` / `/approve @username` ya message par reply karein.",
            parse_mode="Markdown"
        )


# --- RESTRICT COMMAND ---
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

    if target_id and target_id in APPROVED_USERS:
        if target_id == ADMIN_CHAT_ID:
            await update.message.reply_text("⚠️ Aap owner ko restrict nahi kar sakte!")
            return
        APPROVED_USERS.remove(target_id)
        await update.message.reply_text(f"🔒 User (`{target_id}`) ko successfully restrict kar diya gaya hai!", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "⚠️ **Usage:** `/restrict <USER_ID>` / `/restrict @username` ya approved user ke message par reply karein.",
            parse_mode="Markdown"
        )


# --- CONTACT CARD APPROVER ---
async def handle_contact_share(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    contact = update.message.contact
    if contact and contact.user_id:
        APPROVED_USERS.add(contact.user_id)
        await update.message.reply_text(f"✨ Contact **{contact.first_name}** approved!")


# --- SMART AI CONVERSATION ENGINE ---
def generate_ai_response(user_text: str, user_name: str) -> str:
    txt = user_text.lower().strip()
    if any(greet in txt for greet in ["hello", "hii", "hi", "hey"]):
        return f"Hello {user_name}! 👋 Main yahan owner ki assistant ki tarah help kar rahi hun. Aap bataiye, kya baat karni thi?"
    elif "kaise ho" in txt or "how are you" in txt:
        return "Main ekdum badhiya aur active hun! 😊 Aap kaise hain?"
    else:
        return f"Aapka message mil gaya hai {user_name}. Main owner ko notify kar doongi, wo free ho kar aapse contact kar lenge! 👍"


# --- UNIFIED DM & BUSINESS MESSAGE HANDLER ---
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

    # Owner / Approved Users Bypass
    if sender.id in APPROVED_USERS or sender.id == context.bot.id or getattr(message, "out", False):
        return

    user_name = sender.first_name or "Dear"
    user_id = sender.id

    # 1. Restrict All Kinds of Media
    has_restricted_media = (
        message.animation or 
        message.photo or 
        message.video or 
        message.video_note or 
        message.document or 
        message.audio or 
        message.voice
    )

    # 2. Strict Abusive/Adult Content Check
    text_content = (message.text or message.caption or "").lower()
    has_banned_content = any(banned in text_content for banned in BANNED_WORDS)

    if has_restricted_media or has_banned_content:
        try:
            await message.delete()
            
            rejection_text = "Hello, can i know why are you messaging me? Don't message me! Why are you messaging me? I am not interested."
            if is_business and business_conn_id:
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=rejection_text,
                    business_connection_id=business_conn_id
                )
            else:
                await message.reply_text(rejection_text)
                
            media_type_desc = "Video / Video Note" if (message.video or message.video_note) else ("Photo / Image" if message.photo else "Media / Document")
            
            alert_header = (
                f"🚨 **BLOCKED MEDIA / SPAM PREVIEW**\n\n"
                f"👤 **Sender:** {user_name} (ID: `{user_id}`)\n"
                f"📁 **Type:** {media_type_desc}\n"
                f"💬 **Caption:** `{message.text or message.caption or 'None'}`\n\n"
                f"💡 **Quick Action:** `/approve {user_id}` ya `/check {user_id}`\n"
                f"⏳ *Yeh preview 10 minutes mein auto-delete ho jayega.*"
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
            print(f"❌ Restriction/Forward Error: {e}")
        return

    # 3. Smart AI Conversational Reply for Normal Text
    if message.text:
        ai_reply = generate_ai_response(message.text, user_name)
        try:
            if is_business and business_conn_id:
                await context.bot.send_message(
                    chat_id=message.chat_id,
                    text=ai_reply,
                    business_connection_id=business_conn_id
                )
            else:
                await message.reply_text(ai_reply)
        except Exception as e:
            print(f"❌ Reply Error: {e}")


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
    # Set Native Bot Commands Menu in Telegram DM
    await application.bot.set_my_commands([
        BotCommand("help", "Saari commands ki list aur details dekhein"),
        BotCommand("check", "Kisi user ki details aur history check karein"),
        BotCommand("approve", "User ko approve / unrestrict karein"),
        BotCommand("restrict", "User ko restrict / block karein"),
        BotCommand("restart", "Bot ko instantly restart karein"),
        BotCommand("del", "Message delete karein")
    ])
    
    await application.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text="✅ **Bot is online with full command suite active!** 🚀",
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
        app.add_handler(CommandHandler("del", delete_cmd))
        app.add_handler(MessageHandler(filters.CONTACT, handle_contact_share))
        
        app.add_handler(TypeHandler(Update, process_incoming_dm))

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

