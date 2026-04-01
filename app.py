import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- အချက်အလက်များ ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = '6131831207'
STORAGE_CHANNEL_ID = '-1003649365692'
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Channel Join စစ်ဆေးခြင်း ---
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except:
        return True

# --- ပုံမှန် နှုတ်ဆက်ခြင်း ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"မင်္ဂလာပါ {user_name}။\n\n"
        "ဗီဒီယို Link ကို ပို့ပေးပါ။ Watermark မပါဘဲ ဒေါင်းလုဒ်ဆွဲပေးပါမည်။"
    )

# --- ဗီဒီယို လုပ်ဆောင်ခြင်း ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text
    if not url.startswith("http"): return

    # Join စစ်ခြင်း
    joined = await check_joined(user_id, context)
    if not joined:
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text("ဗီဒီယိုဒေါင်းရန် Channel ကို အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_msg = await update.message.reply_text("ခဏစောင့်ပါ။ ဗီဒီယိုကို ပြင်ဆင်နေပါသည်။ ⏳")

    try:
        # ဒေါင်းလုဒ်လုပ်ခြင်း
        ydl_opts = {'format': 'best', 'outtmpl': f'vid_{user_id}.%(ext)s', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        
        # Storage ထဲပို့ပြီး ID ယူခြင်း
        with open(file_path, 'rb') as f:
            sent_msg = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            
            # ဗီဒီယို သို့မဟုတ် ဖိုင်မှ ID ကို ယူခြင်း
            file_id = None
            if sent_msg.video:
                file_id = sent_msg.video.file_id
            elif sent_msg.document:
                file_id = sent_msg.document.file_id
            elif sent_msg.animation:
                file_id = sent_msg.animation.file_id

        if os.path.exists(file_path):
            os.remove(file_path)

        if not file_id:
            raise Exception("File ID Not Found")

        # ကြော်ငြာနှင့် ခလုတ်ပြခြင်း
        keyboard = [
            [InlineKeyboardButton("📺 ကြော်ငြာကြည့်ရန် (၅ စက္ကန့်)", web_app=WebAppInfo(url=AD_LINK))],
            [InlineKeyboardButton("✅ ဗီဒီယို ရယူရန်", callback_data=f"get_{file_id}")]
        ]
        
        await status_msg.edit_text(
            "ဗီဒီယို အဆင်သင့်ဖြစ်ပါပြီ။\n\n"
            "၁။ 'ကြော်ငြာကြည့်ရန်' ကိုနှိပ်ပြီး ၅ စက္ကန့်ခန့် ကြည့်ပေးပါ။\n"
            "၂။ ပြီးနောက် 'ဗီဒီယို ရယူရန်' ကိုနှိပ်ပြီး ဒေါင်းလုဒ်ရယူနိုင်ပါပြီ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text("အမှားအယွင်းရှိနေပါသည်။ Link မှန်မမှန် ပြန်စစ်ပေးပါ။")

# --- ခလုတ်နှိပ်ခြင်းအား တုံ့ပြန်ခြင်း ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("get_"):
        file_id = query.data.split("_")[1]
        try:
            await query.message.reply_video(video=file_id, caption="ဗီဒီယို ရပါပြီ။ ကျေးဇူးတင်ပါသည်။")
            await query.message.delete()
        except:
            await query.message.reply_document(document=file_id, caption="ဖိုင် ရပါပြီ။ ကျေးဇူးတင်ပါသည်။")
            await query.message.delete()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()
