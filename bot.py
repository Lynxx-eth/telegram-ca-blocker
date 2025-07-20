import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime, timedelta
import re

from keep_alive import keep_alive

# Load .env values
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Block logic
block_until = None
base58_pattern = r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'
eth_pattern = r'\b0x[a-fA-F0-9]{40}\b'

def is_ca_message(text):
    return re.search(base58_pattern, text) or re.search(eth_pattern, text)

def is_blocking_active():
    return block_until is not None and datetime.now() < block_until

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = message.from_user

    if not message or not message.text:
        return

    chat_member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
    if chat_member.status in ["administrator", "creator"]:
        return

    if is_blocking_active() and is_ca_message(message.text):
        await message.delete()
        await message.reply_text("🚫 Sharing CAs is restricted right now.")
    else:
        pass

async def set_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global block_until
    chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if chat_member.status not in ["administrator", "creator"]:
        await update.message.reply_text("Only admins can use this command.")
        return

    try:
        duration_str = ' '.join(context.args)
        amount, unit = duration_str.split()
        amount = int(amount)

        if unit in ['minute', 'minutes']:
            block_until = datetime.now() + timedelta(minutes=amount)
        elif unit in ['hour', 'hours']:
            block_until = datetime.now() + timedelta(hours=amount)
        elif unit in ['day', 'days']:
            block_until = datetime.now() + timedelta(days=amount)
        else:
            raise ValueError("Invalid unit")

        await update.message.reply_text(f"✅ CA sharing blocked for {amount} {unit}.")

        pinned_text = (
            "🚫 *Attention Everyone!*\n\n"
            "CA (Crypto Addresses) sharing has been *temporarily blocked* in this group.\n\n"
            f"⏳ Duration: {amount} {unit}\n"
            "👮 Only admins are allowed to share addresses during this time.\n\n"
            "Please refrain from posting any wallet addresses until the restriction is lifted.\n"
            "Thank you for understanding!"
        )

        sent = await update.message.reply_markdown(pinned_text)
        await update.effective_chat.pin_message(sent.message_id, disable_notification=True)

    except:
        await update.message.reply_text("Usage: /blockca <amount> <unit>\nExample: /blockca 2 hours")

async def unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global block_until
    chat_member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if chat_member.status not in ["administrator", "creator"]:
        await update.message.reply_text("Only admins can unblock.")
        return

    block_until = None
    await update.message.reply_text("✅ CA sharing is now allowed.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 *CA Blocker Bot Help*\n\n"
        "Use these commands to manage CA sharing in the group:\n"
        "• /blockca <amount> <unit> - Block CA sharing for a time period.\n"
        "   Example: /blockca 30 minutes\n"
        "• /unblockca - Unblock CA sharing immediately.\n"
        "• /statusca - Check if blocking is active.\n"
        "• /helpca - Show this help message.\n\n"
        "🚨 Note: Only admins can use /blockca and /unblockca."
    )
    await update.message.reply_markdown(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_blocking_active():
        remaining = block_until - datetime.now()
        minutes = int(remaining.total_seconds() // 60)
        await update.message.reply_text(f"🚫 CA sharing is currently blocked.\n🕒 Time remaining: {minutes} minutes.")
    else:
        await update.message.reply_text("✅ CA sharing is currently allowed.")


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("blockca", set_block))
    app.add_handler(CommandHandler("unblockca", unblock))
    app.add_handler(CommandHandler("helpca", help_command))
    app.add_handler(CommandHandler("statusca", status_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 Bot is running...")
    keep_alive()
    app.run_polling()
