import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from keep_alive import keep_alive

# --- Your Bot Token (from BotFather) ---
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# --- Your Telegram ID (find via @userinfobot) ---
ADMIN_ID = 123456789  # replace with your Telegram numeric ID

# Storage for chat IDs
USERS_FILE = "users.txt"

def save_user(chat_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            pass
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if str(chat_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")

def get_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return f.read().splitlines()

# Binance + Forex API
BINANCE_URL = "https://api.binance.com/api/v3"
FOREX_URL = "https://api.exchangerate.host/latest"

# --- Get Live Price + 24h Stats ---
def get_crypto_stats(symbol="BTCUSDT"):
    url = f"{BINANCE_URL}/ticker/24hr?symbol={symbol.upper()}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    
    data = r.json()
    return {
        "price": float(data["lastPrice"]),
        "change_percent": float(data["priceChangePercent"]),
        "high": float(data["highPrice"]),
        "low": float(data["lowPrice"]),
        "volume": float(data["volume"])
    }

# --- Crypto → Crypto Conversion ---
def convert_crypto(amount, from_coin, to_coin):
    pair = f"{from_coin.upper()}{to_coin.upper()}"
    url = f"{BINANCE_URL}/ticker/price?symbol={pair}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    rate = float(r.json()["price"])
    return amount * rate

# --- Crypto → USD ---
def crypto_to_usd(amount, coin):
    pair = f"{coin.upper()}USDT"
    url = f"{BINANCE_URL}/ticker/price?symbol={pair}"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    price = float(r.json()["price"])
    return amount * price

# --- Crypto → INR ---
def crypto_to_inr(amount, coin):
    usd_value = crypto_to_usd(amount, coin)
    if usd_value is None:
        return None
    r = requests.get(f"{FOREX_URL}?base=USD&symbols=INR")
    if r.status_code != 200:
        return None
    usd_inr = r.json()["rates"]["INR"]
    return usd_value * usd_inr


# --- Bot Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    save_user(chat_id)
    await update.message.reply_text("👋 Welcome! Use /price BTC or /convert 2 ETH BTC")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /price BTC")
        return
    
    coin = context.args[0].upper()
    stats = get_crypto_stats(f"{coin}USDT")
    if not stats:
        await update.message.reply_text("❌ Invalid symbol")
        return

    inr_value = crypto_to_inr(1, coin)
    msg = (
        f"💰 {coin}\n"
        f"Price: ${stats['price']:.2f} | ₹{inr_value:.2f}\n"
        f"24h: {stats['change_percent']}%\n"
        f"High: ${stats['high']:.2f} | Low: ${stats['low']:.2f}\n"
        f"Volume: {stats['volume']:.2f}"
    )
    await update.message.reply_text(msg)

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /convert 2 ETH BTC or /convert 1 ETH USD/INR")
        return
    
    try:
        amount = float(context.args[0])
    except:
        await update.message.reply_text("❌ Invalid amount")
        return

    from_coin = context.args[1].upper()
    to_coin = context.args[2].upper()

    if to_coin == "USD":
        result = crypto_to_usd(amount, from_coin)
    elif to_coin == "INR":
        result = crypto_to_inr(amount, from_coin)
    else:
        result = convert_crypto(amount, from_coin, to_coin)

    if result is None:
        await update.message.reply_text("❌ Conversion failed")
    else:
        await update.message.reply_text(f"🔄 {amount} {from_coin} = {result:.6f} {to_coin}")

# --- Admin Broadcast Command ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ You are not allowed to use this command.")
        return
    
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /broadcast Your message here")
        return
    
    message = " ".join(context.args)
    users = get_users()
    success, fail = 0, 0

    for user in users:
        try:
            await context.bot.send_message(chat_id=int(user), text=message)
            success += 1
        except:
            fail += 1
    
    await update.message.reply_text(f"✅ Sent to {success} users, ❌ Failed {fail}")

# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("broadcast", broadcast))  # admin only

    keep_alive()  # keep bot alive on Replit
    app.run_polling()

if __name__ == "__main__":
    main()
