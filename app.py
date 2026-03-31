import os
import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# --- ခင်ဗျားရဲ့ အချက်အလက်များ (အသင့်ထည့်ပေးထားပါသည်) ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = '6131831207' # ခင်ဗျားရဲ့ Telegram ID
STORAGE_CHANNEL_ID = '-1003649365692' # Storage Channel ID
MAIN_CHANNEL = '@linktovideodownloadermm' # Force Join လုပ်မည့် Channel
AD_API_KEY = '4fad161fd60063e4e82a32386258dabc907ede8f' # ⚠️ ShrinkMe API Key ထည့်ရန်

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
        logging.error(f"Force Join Error: {e}")
        return True

# --- ShrinkMe မှ ကြော်ငြာလင့်ခ် ပြောင်းသည့် Function ---
def get_short_link(long_url):
    api_url = f"https://shrinkme.io/api?api={AD_API_KEY}&url={long_url}"
    try:
        r = requests.get(api_url).json()
        if r['status'] == 'success':
            return r['shortenedUrl']
    except Exception as e:
        logging.error(f"ShrinkMe API Error: {e}")
    return long_url # Error တက်ခဲ့လျှင် မူလလင့်ခ်ကိုသာ ပြန်ပေးမည်

# --- /start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args # Deep Link Payload ကို စစ်ဆေးခြင်း
    user_id = update.effective_user.id

    # အကယ်၍ User က ကြော်ငြာကြည့်ပြီး ဗီဒီယိုယူရန် ပြန်ရောက်လာခြင်းဖြစ်လျှင်
    if args:
        file_id = args[0]
        await update.message.reply_text("✅ ကြော်ငြာကြည့်ပေးတဲ့အတွက် ကျေးဇူးတင်ပါတယ်။ သင့်ဗီဒီယို လာပါပြီ 🚀")
        try:
            # Storage မှ ဗီဒီယိုကို User ထံ တိုက်ရိုက်ပို့ပေးခြင်း
            await context.bot.send_video(chat_id=user_id, video=file_id)
        except Exception as e:
            await update.message.reply_text("❌ ဗီဒီယို ရှာမတွေ့ပါ။ Link အဟောင်း ဖြစ်နေနိုင်ပါသည်။")
        return

    # ရိုးရိုး /start နှိပ်လျှင် ပြမည့်စာသား
    welcome_text = (
        "👋 မင်္ဂလာပါ! ကျွန်တော်က Video များကို အလွယ်တကူ ဒေါင်းလုဒ်ဆွဲပေးမယ့် Bot ပါ။\n\n"
        "📥 ဒေါင်းလုဒ်ဆွဲလိုသော Video Link ကို ဒီမှာ ပို့ပေးလိုက်ပါ။\n"
        "(မှတ်ချက် - Bot ရေရှည်ရပ်တည်နိုင်ရန် ဗီဒီယိုရယူရာတွင် ကြော်ငြာ ၅ စက္ကန့်ခန့် ကြည့်ပေးရပါမည်)"
    )
    await update.message.reply_text(welcome_text)

# --- Link ပို့လာလျှင် အလုပ်လုပ်မည့် Function ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    url = update.message.text
    
    # 1. Force Join စစ်ဆေးခြင်း
    is_joined = await check_joined(update, context)
    if not is_joined:
        join_text = "❌ ဗီဒီယို ဒေါင်းလုဒ်ဆွဲရန် ကျွန်ုပ်တို့၏ ပင်မ Channel ကို အရင် Join ပေးပါခင်ဗျာ။"
        keyboard = [[InlineKeyboardButton("📢 Channel သို့ Join ရန် နှိပ်ပါ", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text(join_text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if not url.startswith("http"):
        return

    status_msg = await update.message.reply_text("⏳ ခဏစောင့်ပါ... ဗီဒီယိုကို ရှာဖွေနေပါသည်...")

    try:
        # 2. ဗီဒီယို ဒေါင်းလုဒ်ဆွဲခြင်း (50MB Limit)
        ydl_opts = {'format': 'best[filesize<50M]/bestvideo[filesize<50M]+bestaudio/best', 'outtmpl': f'vid_{user.id}.%(ext)s', 'quiet': True}
        file_path = await asyncio.to_thread(download_video_sync, url, ydl_opts)

        if not file_path:
            await status_msg.edit_text("❌ ဗီဒီယို ဖိုင်ဆိုဒ် ကြီးလွန်းနေပါသည် (Telegram limit: 50MB)။")
            return

        # 3. Storage Channel သို့ ပို့၍ File ID ယူခြင်း
        with open(file_path, 'rb') as f:
            sent_msg = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            file_id = sent_msg.video.file_id # Telegram ပေါ်ရှိ ဗီဒီယို၏ မှတ်ပုံတင်နံပါတ်

        # 4. Server ပေါ်မှ ဖိုင်ကို ချက်ချင်းဖျက်ခြင်း (Storage မပြည့်စေရန်)
        os.remove(file_path)

        # 5. Bot ဆီ ပြန်လာမည့် Deep Link ဖန်တီး၍ ကြော်ငြာလင့်ခ် ပြောင်းခြင်း
        bot_username = (await context.bot.get_me()).username
        deep_link = f"https://t.me/{bot_username}?start={file_id}"
        ad_link = get_short_link(deep_link)

        # 6. User ဆီသို့ ကြော်ငြာလင့်ခ် ပို့ခြင်း
        keyboard = [[InlineKeyboardButton("▶️ ကြော်ငြာကြည့်ပြီး ဗီဒီယိုရယူရန် နှိပ်ပါ", url=ad_link)]]
        await status_msg.edit_text(
            "🚀 ဗီဒီယို အဆင်သင့်ဖြစ်ပါပြီ!\n\n"
            "အောက်ကခလုတ်ကိုနှိပ်ပြီး ကြော်ငြာ ၅ စက္ကန့်ကြည့်ပေးပါခင်ဗျာ။ "
            "ကြည့်ပြီးလျှင် သင့်ဗီဒီယို အလိုလို ကျလာပါလိမ့်မည်။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # 7. Admin (ခင်ဗျား) ထံ Noti ပို့ခြင်း
        noti = f"🔔 User: {user.first_name}\n🔗 Link: {url}\n💰 Ad Link ဖန်တီးပြီးပါပြီ!"
        await context.bot.send_message(chat_id=ADMIN_ID, text=noti)

    except Exception as e:
        logging.error(f"Download Error: {e}")
        await status_msg.edit_text("❌ ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။ Link မှားနေခြင်း သို့မဟုတ် Private ဖြစ်နေနိုင်ပါသည်။")

def download_video_sync(url, ydl_opts):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except:
        return None

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Bot is successfully running with Ad-Revenue System...")
    app.run_polling()
