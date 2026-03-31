import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- ခင်ဗျားရဲ့ လျှို့ဝှက်ကုဒ်များ (အသင့်ထည့်ထားပြီးပါပြီ) ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = '6131831207'
STORAGE_CHANNEL_ID = '-1003649365692'
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Force Join စစ်ဆေးသည့် Function ---
async def check_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        if member.status in ['left', 'kicked']:
            return False
        return True
    except Exception as e:
        logging.error(f"Force Join Error (Bot ကို Admin ပေးထားရန်): {e}")
        return True # Error တက်လျှင် User အဆင်ပြေအောင် ဝင်ပြီးသားဟု ယူဆမည်

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 မင်္ဂလာပါ! ဗီဒီယို Link ပို့ပေးပါ။ ကြော်ငြာခဏကြည့်ပြီးတာနဲ့ ဗီဒီယိုကို အလွယ်တကူ ရယူနိုင်ပါပြီ။")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"): return

    # ၁။ Force Join အရင်စစ်မယ်
    is_joined = await check_joined(update, context)
    if not is_joined:
        join_text = "❌ ဗီဒီယို ဒေါင်းလုဒ်ဆွဲရန် ကျွန်ုပ်တို့၏ ပင်မ Channel ကို အရင် Join ပေးပါခင်ဗျာ။"
        keyboard = [[InlineKeyboardButton("📢 Channel သို့ Join ရန် နှိပ်ပါ", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text(join_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_msg = await update.message.reply_text("⏳ ဗီဒီယိုကို ရှာဖွေနေပါသည်...")

    try:
        # ၂။ ဗီဒီယိုကို ဒေါင်းလုဒ်ဆွဲခြင်း
        ydl_opts = {'format': 'best[filesize<50M]/bestvideo[filesize<50M]+bestaudio/best', 'outtmpl': f'vid_{update.effective_user.id}.%(ext)s', 'quiet': True}
        def download_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info)
        
        file_path = await asyncio.to_thread(download_sync)
        
        # ၃။ Storage Channel ထဲပို့ပြီး File ID ယူခြင်း
        with open(file_path, 'rb') as f:
            sent_msg = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            file_id = sent_msg.video.file_id
        
        os.remove(file_path) # Storage ပြည့်မှာစိုးလို့ ချက်ချင်းဖျက်မယ်

        # ၄။ User ကို ကြော်ငြာ Web App ပြမယ်
        keyboard = [
            [InlineKeyboardButton("📺 ကြော်ငြာကြည့်ရန် (ခဏစောင့်ပါ)", web_app=WebAppInfo(url=AD_LINK))],
            [InlineKeyboardButton("✅ ဗီဒီယို ရယူရန်", callback_data=f"get_{file_id}")]
        ]
        
        await status_msg.edit_text(
            "🚀 ဗီဒီယို အဆင်သင့်ဖြစ်ပါပြီ!\n\n"
            "၁။ အပေါ်ခလုတ်ကိုနှိပ်ပြီး ကြော်ငြာ ၅ စက္ကန့်ကြည့်ပါ။\n"
            "၂။ ပြီးလျှင် အောက်ခလုတ်ကိုနှိပ်ပြီး ဗီဒီယိုကို ယူလိုက်ပါဗျာ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # ၅။ Admin ထံ Noti ပို့ခြင်း
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 User {update.effective_user.first_name} က ဗီဒီယို လာဒေါင်းသွားပါတယ်။\n🔗 Link: {url}")

    except Exception as e:
        logging.error(e)
        await status_msg.edit_text("❌ ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("get_"):
        file_id = query.data.split("_")[1]
        # User ဆီ ဗီဒီယို တိုက်ရိုက်ပို့ခြင်း
        await query.message.reply_video(video=file_id, caption="✅ သင့်ဗီဒီယို ရပါပြီ! ကျေးဇူးတင်ပါတယ်။")
        await query.message.delete()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    print("Bot is successfully running with Automated Revenue System...")
    app.run_polling()
