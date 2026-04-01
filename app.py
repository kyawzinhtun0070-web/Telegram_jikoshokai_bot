import os
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = '6131831207'
STORAGE_CHANNEL_ID = '-1003649365692'
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(level=logging.INFO)

async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except: return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"မင်္ဂလာပါ {update.effective_user.first_name}။ ဗီဒီယို Link ပို့ပေးပါ။")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    url = update.message.text
    if not url.startswith("http"): return

    # Admin Noti (ဘယ်သူသုံးလဲ သိရအောင်)
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 User: {user.first_name}\n🔗 Link: {url}")

    if not await check_joined(user.id, context):
        keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text("Channel Join ပေးပါဦး။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status = await update.message.reply_text("ပြင်ဆင်နေပါသည်... ⏳")

    try:
        # TikTok နှင့် အဆင်ပြေအောင် Option များ ပြင်ဆင်ထားသည်
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'dl_{user.id}.mp4',
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        file_path = f'dl_{user.id}.mp4'
        with open(file_path, 'rb') as f:
            msg = await context.bot.send_document(chat_id=STORAGE_CHANNEL_ID, document=f)
            file_id = msg.document.file_id
        os.remove(file_path)

        keyboard = [[InlineKeyboardButton("📺 Ad ကြည့်ရန်", web_app=WebAppInfo(url=AD_LINK))],
                    [InlineKeyboardButton("✅ ရယူရန်", callback_data=f"get_{file_id}")]]
        await status.edit_text("ဗီဒီယို အဆင်သင့်ဖြစ်ပါပြီ။ အောက်ကခလုတ်များကို နှိပ်ပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception:
        err = traceback.format_exc()
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ **Error Detail:**\n`{err[:3000]}`", parse_mode="Markdown")
        await status.edit_text("အမှားအယွင်းရှိနေပါသည်။ Link ပြန်စစ်ပေးပါ။")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("get_"):
        await query.message.reply_document(document=query.data.split("_")[1], caption="ရပါပြီ။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()
