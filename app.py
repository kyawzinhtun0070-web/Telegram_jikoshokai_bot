import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- Config ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = '6131831207'
STORAGE_CHANNEL_ID = '-1003649365692'
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except: return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"မင်္ဂလာပါ {update.effective_user.first_name}။ ဗီဒီယို Link ပို့ပေးပါ။ Watermark မပါဘဲ ဒေါင်းလုဒ်ဆွဲပေးပါမည်။")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    url = update.message.text
    if not url.startswith("http"): return

    # Admin Noti
    admin_msg = f"🔔 **User Activity**\n👤 အမည်: {user.first_name}\n🆔 ID: `{user.id}`\n🔗 Link: {url}"
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except: pass

    if not await check_joined(user.id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text("ဗီဒီယိုဒေါင်းရန် Channel ကို အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_msg = await update.message.reply_text("ခဏစောင့်ပါ။ ဗီဒီယိုကို ပြင်ဆင်နေပါသည်။ ⏳")

    try:
        # ဒေါင်းလုဒ် Options (TikTok အတွက် ပိုကောင်းအောင် ပြင်ထားသည်)
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'file_{user.id}.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        
        # Storage ထဲပို့ပြီး ID ယူခြင်း (အမျိုးအစားစုံ စစ်ဆေးခြင်း)
        with open(file_path, 'rb') as f:
            sent_msg = await context.bot.send_document(chat_id=STORAGE_CHANNEL_ID, document=f)
            file_id = sent_msg.document.file_id

        if os.path.exists(file_path): os.remove(file_path)

        keyboard = [
            [InlineKeyboardButton("📺 ကြော်ငြာကြည့်ရန် (၅ စက္ကန့်)", web_app=WebAppInfo(url=AD_LINK))],
            [InlineKeyboardButton("✅ ဖိုင်ရယူရန်", callback_data=f"get_{file_id}")]
        ]
        await status_msg.edit_text("ပြင်ဆင်ပြီးပါပြီ။\n\n၁။ ကြော်ငြာကြည့်ရန် ကိုနှိပ်ပါ။\n၂။ ပြီးနောက် ဖိုင်ရယူရန် ကိုနှိပ်ပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        logging.error(f"Download Error: {e}")
        await status_msg.edit_text("ဒေါင်းလုဒ်ဆွဲရာတွင် အခက်အခဲရှိနေပါသည်။ Link ပြန်စစ်ပေးပါ။")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("get_"):
        file_id = query.data.split("_")[1]
        try:
            await query.message.reply_document(document=file_id, caption="ဒေါင်းလုဒ် ရပါပြီ။ ကျေးဇူးတင်ပါသည်။")
            await query.message.delete()
        except Exception as e:
            logging.error(f"Send Error: {e}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()
