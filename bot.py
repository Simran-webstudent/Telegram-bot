import telebot

TOKEN = "8525088862:8525088862:AAHOITECNV8zLJOcZaX8LS-jno1SzPeC_g"
ADMIN_ID = 1448151744

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Hello! Bot is live and running.")

bot.infinity_polling()
