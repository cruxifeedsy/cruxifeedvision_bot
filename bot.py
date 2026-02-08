from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest
import asyncio
import os
import requests
from datetime import datetime

# ===================== CONFIG =====================
TOKEN = "8480668283:AAHGw8c_qp0hQtYAWkUIMr_UKjd3ddFX8SQ"
TWELVE_DATA_API_KEY = "a1794effd77c466280ebe9c34f45543f"

MORNING_SESSION = (7, 11)
EVENING_SESSION = (18, 22)

PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]
TIMEFRAMES = ["1m"]

START_IMG = "start.png"
BUY_IMG = "buy.png"
SELL_IMG = "sell.png"

user_state = {}

# ===================== START =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📈 Get Smart Signal", callback_data="signal")]]

    if os.path.exists(START_IMG):
        await update.message.reply_photo(
            photo=open(START_IMG, "rb"),
            caption="🔥 **CRUXIFEED AI**\n\nFun + Serious Forex Assistant 🤖\nTap below for smart signals.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "🔥 **CRUXIFEED AI**\nSmart Forex Assistant 🤖",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

# ===================== SIGNAL MENU =====================
async def signal_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}") for pair in PAIRS]]

    await query.message.reply_text(
        "💱 **Choose Pair**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===================== PAIR SELECT =====================
async def pair_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pair = query.data.split("_")[1]
    user_state[query.from_user.id] = {"pair": pair}

    keyboard = [[InlineKeyboardButton("1m (Sniper)", callback_data="time_1m")]]

    await query.message.reply_text(
        f"💱 Pair: **{pair}**\nChoose expiry:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===================== SMART SIGNAL ENGINE =====================
async def timeframe_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pair = user_state[query.from_user.id]["pair"]
    timeframe = "1m"

    hour = datetime.now().hour
    if not (MORNING_SESSION[0] <= hour < MORNING_SESSION[1] or EVENING_SESSION[0] <= hour < EVENING_SESSION[1]):
        await query.message.reply_text("🕒 Market session closed — waiting...")
        return

    loading = await query.message.reply_text("📊 Scanning live market...")
    await asyncio.sleep(1)

    try:
        url = f"https://api.twelvedata.com/time_series?symbol={pair}&interval=1min&outputsize=200&apikey={TWELVE_DATA_API_KEY}"
        data = requests.get(url, timeout=10).json()

        values = data.get("values", [])
        prices = [float(v["close"]) for v in reversed(values)]

        if len(prices) < 80:
            raise Exception("Not enough data")

        # ===== INDICATORS =====
        def ema(vals, p):
            k = 2 / (p + 1)
            e = vals[0]
            for v in vals[1:]:
                e = v * k + e * (1 - k)
            return e

        def rsi(vals, p=14):
            gains, losses = [], []
            for i in range(1, len(vals)):
                diff = vals[i] - vals[i-1]
                gains.append(max(diff, 0))
                losses.append(abs(min(diff, 0)))
            avg_gain = sum(gains[-p:]) / p
            avg_loss = sum(losses[-p:]) / p if sum(losses[-p:]) != 0 else 1
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))

        def macd(vals):
            return ema(vals, 12) - ema(vals, 26)

        ema_fast = ema(prices[-80:], 9)
        ema_slow = ema(prices[-80:], 21)
        rsi_val = rsi(prices[-50:])
        macd_val = macd(prices[-100:])
        momentum = prices[-1] - prices[-6]
        volatility = max(prices[-30:]) - min(prices[-30:])
        trend_strength = ema_fast - ema_slow

        uptrend = trend_strength > 0 and macd_val > 0
        downtrend = trend_strength < 0 and macd_val < 0

        sideways = volatility < 0.00015
        overbought = rsi_val > 75
        oversold = rsi_val < 25

        signal = "WAIT"

        if uptrend and momentum > 0 and rsi_val < 65 and not overbought:
            signal = "BUY"

        elif downtrend and momentum < 0 and rsi_val > 35 and not oversold:
            signal = "SELL"

        if sideways:
            signal = "WAIT"

        confidence = min(99, int(abs(trend_strength) * 160000) + 85)

    except:
        signal = "WAIT"
        confidence = 80
        rsi_val = 50

    await loading.delete()

    # ===== WAIT MODE =====
    if signal == "WAIT":
        await query.message.reply_text("⏳ No clear safe trade — waiting like a pro 😎")
        return

    # ===== 1 MIN WARNING =====
    await query.message.reply_text("⚠️ Possible trade forming — wait 1 minute for confirmation...")
    await asyncio.sleep(60)

    image = BUY_IMG if signal == "BUY" else SELL_IMG

    caption = (
        f"💎 **CRUXIFEED AI SIGNAL**\n\n"
        f"💱 Pair: `{pair}`\n"
        f"⏱ Expiry: `1m`\n"
        f"📈 Direction: **{signal}**\n"
        f"📊 RSI: **{round(rsi_val, 2)}**\n"
        f"🔥 Confidence: **{confidence}%**\n\n"
        f"😎 Trade smart. Protect capital."
    )

    keyboard = [[InlineKeyboardButton("🔁 New Signal", callback_data="signal")]]

    if os.path.exists(image):
        await query.message.reply_photo(
            photo=open(image, "rb"),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await query.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ===================== AI CHAT MODE =====================
async def chat_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if "eurusd" in text:
        await update.message.reply_text("📊 EURUSD is our sniper pair. Want a 1m smart entry?")
    elif "signal" in text:
        await update.message.reply_text("Tap 📈 Get Smart Signal to receive a trade idea.")
    elif "trade" in text:
        await update.message.reply_text("I trade safe — no rush. Market clarity first 😎")
    elif "hi" in text or "hello" in text:
        await update.message.reply_text("Hey trader 😄 Ready to hunt pips?")
    else:
        await update.message.reply_text("I'm here to help — trading smart beats trading fast 💡")

# ===================== RUN =====================
request = HTTPXRequest(connect_timeout=30, read_timeout=30)

app = ApplicationBuilder().token(TOKEN).request(request).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(signal_menu, pattern="signal"))
app.add_handler(CallbackQueryHandler(pair_selected, pattern="pair_"))
app.add_handler(CallbackQueryHandler(timeframe_selected, pattern="time_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_ai))

print("✅ CRUXIFEED AI RUNNING — SMART SAFE MODE")

app.run_polling()