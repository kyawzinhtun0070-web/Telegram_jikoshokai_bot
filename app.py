import os
import asyncio
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- ခင်ဗျား၏ အချက်အလက်များ ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = '6131831207'
STORAGE_CHANNEL_ID = '-1003649365692'
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Force Join စစ်ဆေးသည့် Function ---
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except:
        return True

# --- Start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_text = (
        f"👋 မင်္ဂလာပါ {user_name}။\n\n"
        "ကျွန်တော်က Social Media များမှ ဗီဒီယိုနှင့် အသံများကို "
        "ဒေါင်းလုဒ်ဆွဲပေးမည့် Bot ဖြစ်ပါတယ်။\n\n"
        "📥 ဒေါင်းလုဒ်ဆွဲလိုသော Link ကို ပို့ပေးနိုင်ပါပြီ။"
    )
    keyboard = [[InlineKeyboardButton("👑 Premium ဝယ်ယူရန်", url="https://t.me/kyawzinhtun0070")]]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- Link ပို့လာလျှင် အလုပ်လုပ်မည့် Function ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    url = update.message.text

    if not url.startswith("http"):
        await update.message.reply_text("❌ ကျေးဇူးပြု၍ မှန်ကန်သော Link ကိုသာ ပို့ပေးပါ။")
        return

    # Admin ထံ Noti ပို့ခြင်း
    admin_msg = f"🔔 **User Activity**\n👤 အမည်: {user.first_name}\n🆔 ID: `{user.id}`\n🔗 Link: {url}"
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except: pass

    # Force Join စစ်ဆေးခြင်း
    if not await check_joined(user.id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text("ဗီဒီယိုဒေါင်းရန် ကျွန်တော်တို့၏ Channel ကို အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    context.user_data['last_url'] = url
    keyboard = [
        [
            InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
            InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")
        ]
    ]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ ရွေးပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

# --- ဒေါင်းလုဒ်ဆွဲမည့် Core Function ---
def download_media(url, user_id, media_type):
    ydl_opts = {
        'format': 'best' if media_type == 'video' else 'bestaudio/best',
        'outtmpl': f'dl_{user_id}_{media_type}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

# --- ခလုတ်နှိပ်ခြင်းအား တုံ့ပြန်ခြင်း ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    url = context.user_data.get('last_url')
    user_id = query.from_user.id

    if action.startswith("get_"):
        file_id = action.split("_")[2]
        m_type = action.split("_")[1]
        if m_type == "video":
            await query.message.reply_video(video=file_id, caption="ဗီဒီယို ရပါပြီ။ ကျေးဇူးတင်ပါသည်။")
        else:
            await query.message.reply_audio(audio=file_id, caption="အသံဖိုင် ရပါပြီ။ ကျေးဇူးတင်ပါသည်။")
        return

    if not url:
        await query.edit_message_text("❌ အချိန်ကြာသွားသဖြင့် Link ကို ပြန်ပို့ပေးပါ။")
        return

    status = await query.edit_message_text("⏳ ခဏစောင့်ပါ။ ပြင်ဆင်နေပါသည်။...")

    try:
        media_type = 'video' if action == 'dl_video' else 'audio'
        file_path = await asyncio.to_thread(download_media, url, user_id, media_type)

        # Storage Channel သို့ ပို့ပြီး ID ယူခြင်း
        with open(file_path, 'rb') as f:
            if media_type == 'video':
                sent = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
                file_id = sent.video.file_id
            else:
                sent = await context.bot.send_audio(chat_id=STORAGE_CHANNEL_ID, audio=f)
                file_id = sent.audio.file_id
        
        os.remove(file_path)

        # ကြော်ငြာနှင့် ရယူရန်ခလုတ်ပြခြင်း
        keyboard = [
            [InlineKeyboardButton("📺 ကြော်ငြာကြည့်ရန် (၅ စက္ကန့်)", web_app=WebAppInfo(url=AD_LINK))],
            [InlineKeyboardButton("✅ ဖိုင်ရယူရန်", callback_data=f"get_{media_type}_{file_id}")]
        ]
        
        await status.edit_text(
            "✅ အဆင်သင့်ဖြစ်ပါပြီ။\n\n"
            "၁။ 'ကြော်ငြာကြည့်ရန်' ကိုနှိပ်ပြီး ၅ စက္ကန့်ခန့် ကြည့်ပေးပါ။\n"
            "၂။ ပြီးနောက် 'ဖိုင်ရယူရန်' ကိုနှိပ်ပြီး ဒေါင်းလုဒ်ရယူပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception:
        err = traceback.format_exc()
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ **Error Detail:**\n`{err[:3000]}`")
        await status.edit_text("❌ ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။ Link ပြန်စစ်ပေးပါ။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    print("Bot is successfully running...")
    app.run_polling()

