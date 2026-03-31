import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 မင်္ဂလာပါ!\n\n"
        "ကျွန်တော်က Social Media များမှ ဗီဒီယိုနှင့် အသံ (Audio) များကို "
        "အလွယ်တကူ ဒေါင်းလုဒ်ဆွဲပေးမယ့် Bot ပါ။\n\n"
        "📥 ဒေါင်းလုဒ်ဆွဲလိုသော Video Link ကို ဒီမှာ ပို့ပေးလိုက်ပါ ခင်ဗျာ။\n\n"
        "👑 ကြော်ငြာမကြည့်လိုပါက Premium (တစ်လ ၅၀၀၀ ကျပ်) ဝယ်ယူနိုင်ပါတယ်။"
    )
    keyboard = [[InlineKeyboardButton("👑 Premium ဝယ်ယူရန်", url="https://t.me/kyawzinhtun0070")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Link ပို့လာလျှင် ရွေးချယ်ခိုင်းမည့် Function
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text

    if not url.startswith("http"):
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ မှန်ကန်သော Video Link ကိုသာ ပို့ပေးပါ။")
        return

    # User ပို့လိုက်တဲ့ Link ကို မှတ်ထားမယ်
    context.user_data['last_url'] = url

    # ခလုတ်များ ဖန်တီးခြင်း
    keyboard = [
        [
            InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
            InlineKeyboardButton("🎵 အသံ (Audio) ပဲယူမယ်", callback_data="dl_audio")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👇 ဘယ်လို ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ ရွေးပေးပါခင်ဗျာ။", reply_markup=reply_markup)

# ဒေါင်းလုဒ်ဆွဲမည့် Core Function
def download_media(url, chat_id, media_type):
    if media_type == 'video':
        ydl_opts = {
            'format': 'best[filesize<50M]/bestvideo[filesize<50M]+bestaudio/best',
            'outtmpl': f'media_{chat_id}_%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }
    else: # Audio အတွက်
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': f'media_{chat_id}_%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
        }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# ခလုတ်နှိပ်လိုက်လျှင် အလုပ်လုပ်မည့် Function
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    url = context.user_data.get('last_url')
    chat_id = query.message.chat_id

    if not url:
        await query.edit_message_text("❌ အချိန်ကြာသွားသဖြင့် Link ကို ပြန်ပို့ပေးပါ။")
        return

    await query.edit_message_text("⏳ ခဏစောင့်ပါ... ဒေါင်းလုဒ်ဆွဲနေပါတယ်...")

    try:
        media_type = 'video' if action == 'dl_video' else 'audio'
        file_path = await asyncio.to_thread(download_media, url, chat_id, media_type)

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 49:
            await query.edit_message_text("❌ ဖိုင်ဆိုဒ် ကြီးလွန်းနေပါသည် (Telegram limit: 50MB)။")
            os.remove(file_path)
            return

        # ကြော်ငြာစာသား
        ad_caption = (
            "✅ ရပါပြီခင်ဗျာ!\n\n"
            "🙏 Bot လေး ရေရှည်ရပ်တည်နိုင်ဖို့ ကြော်ငြာလေးကို ကြည့်ပေးပါဦး။\n"
            "👉 [သင့်ကြော်ငြာ နေရာ]\n\n"
            "🚫 Premium KPay ၅၀၀၀ ဖြင့် ကြော်ငြာဖျောက်ရန် အောက်တွင်နှိပ်ပါ။"
        )
        keyboard = [[InlineKeyboardButton("👑 Premium ပြောင်းရန်", url="https://t.me/kyawzinhtun0070")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Video လား Audio လား ခွဲပြီး ပို့ခြင်း
        with open(file_path, 'rb') as media_file:
            if media_type == 'video':
                await context.bot.send_video(chat_id=chat_id, video=media_file, caption=ad_caption, reply_markup=reply_markup)
            else:
                await context.bot.send_audio(chat_id=chat_id, audio=media_file, caption=ad_caption, reply_markup=reply_markup)

        os.remove(file_path)
        await query.message.delete()

    except Exception as e:
        logging.error(f"Error: {e}")
        await query.edit_message_text("❌ ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။ Link မှားနေခြင်း သို့မဟုတ် Private ဖြစ်နေနိုင်ပါသည်။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click)) # ခလုတ်များအတွက် Handler အသစ်
    
    print("Bot is successfully running...")
    app.run_polling()
