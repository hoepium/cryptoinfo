import requests
import json
import os
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from keep_alive import keep_alive

# ======================
# 🔧 CONFIG
# ======================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"   # put your bot token here
ADMIN_ID = 123456789                    # replace with your Telegram user ID
USERS_FILE = "users.json"

# ======================
# 📂 USER STORAGE
# ======================
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# ======================
# 📊 CRYPTO FUNCTIONS
# ======================
def get_price(symbol: str):
    symbol = symbol.upper()
    try:
        # Binance price + 24hr stats
        price_data = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT").json()
        stats_data = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT").json()

        usd_price = float(price_data["price"])
        change = stats_data.get("priceChangePercent", "N/A")
        high = stats_data.get("highPrice", "N/A")
        low = stats_data.get("lowPrice", "N/A")
        volume = stats_data.get("volume", "N/A")

        # USD → INR conversion
        forex = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        usd_to_inr = forex["rates"]["INR"]
        inr_price = usd_price * usd_to_inr

        return f"""
💰 <b>{symbol} Price</b>
USD: ${usd_price:,.2f}
INR: ₹{inr_price:,.2f}

📊 24h Change: {change}%
🔼 High: {high}
🔽 Low: {low}
📦 Volume: {volume}
"""
    except Exception as e:
        return "⚠️ Error: Invalid symbol or API issue."

def convert_crypto(amount: float, from_symbol: str, to_symbol: str):
    try:
        from_symbol = from_symbol.upper()
        to_symbol = to_symbol.upper()

        from_price = float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={from_symbol}USDT").json()["price"])
        to_price = float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={to_symbol}USDT").json()["price"])

        result = (amount * from_price) / to_price
        return f"🔄 {amount} {from_symbol} = {result:.6f} {to_symbol}"
    except:
        return "⚠️ Conversion failed. Check symbols."

# ======================
# 🤖 COMMAND HANDLERS
# ======================
def start(update: Update, context: CallbackContext):
    user_id = update.message.chat_id
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

    update.message.reply_text(
        "👋 Welcome to the Crypto Bot!\n\n"
        "Type /help to see what I can do."
    )

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        """
📖 <b>Commands</b>

/price BTC → Get live price of Bitcoin
/price ETH → Get live price of Ethereum
/convert 2 ETH BTC → Convert 2 ETH into BTC
/convert 100 DOGE USD → Convert Doge into USD

(Admin only)
/broadcast <msg> → Send message to all users
""",
        parse_mode=ParseMode.HTML,
    )

def price_command(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        update.message.reply_text("⚠️ Usage: /price BTC")
        return
    symbol = context.args[0]
    result = get_price(symbol)
    update.message.reply_text(result, parse_mode=ParseMode.HTML)

def convert_command(update: Update, context: CallbackContext):
    if len(context.args) < 3:
        update.message.reply_text("⚠️ Usage: /convert <amount> <from> <to>")
        return
    try:
        amount = float(context.args[0])
        from_symbol = context.args[1]
        to_symbol = context.args[2]
        result = convert_crypto(amount, from_symbol, to_symbol)
        update.message.reply_text(result)
    except ValueError:
        update.message.reply_text("⚠️ Amount must be a number.")

def broadcast(update: Update, context: CallbackContext):
    if update.message.chat_id != ADMIN_ID:
        update.message.reply_text("⛔ Not authorized.")
        return

    if not context.args:
        update.message.reply_text("⚠️ Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    users = load_users()

    sent = 0
    for user in users:
        try:
            context.bot.send_message(chat_id=user, text=f"📢 {message}")
            sent += 1
        except:
            pass

    update.message.reply_text(f"✅ Broadcast sent to {sent} users.")

# ======================
# 🚀 MAIN
# ======================
def main():
    keep_alive()  # keep bot alive on Replit
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("price", price_command))
    dp.add_handler(CommandHandler("convert", convert_command))
    dp.add_handler(CommandHandler("broadcast", broadcast, run_async=True))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
