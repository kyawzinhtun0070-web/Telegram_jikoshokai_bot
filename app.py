import os
import asyncio
import logging
import traceback
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
    welcome_text = (
        "👋 မင်္ဂလာပါ!\n\n"
        "Social Media များမှ ဗီဒီယိုနှင့် အသံများကို ဒေါင်းလုဒ်ဆွဲပေးမည့် Bot ပါ။\n"
        "📥 ဒေါင်းလုဒ်ဆွဲလိုသော Link ကို ပို့ပေးလိုက်ပါ ခင်ဗျာ။"
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    url = update.message.text
    if not url.startswith("http"): return

    # Admin Noti (ဘယ်သူသုံးနေလဲ သိရအောင်)
    admin_msg = f"🔔 **User Activity**\n👤 အမည်: {user.first_name}\n🆔 ID: `{user.id}`\n🔗 Link: {url}"
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    except: pass

    # Force Join စစ်ဆေးခြင်း
    if not await check_joined(user.id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text("ဗီဒီယိုဒေါင်းရန် ကျွန်တော်တို့၏ Channel ကို အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    context.user_data['last_url'] = url
    keyboard = [[InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")]]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ ရွေးပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    user_id = query.from_user.id

    # ဖိုင်ပြန်ထုတ်ပေးသည့်အပိုင်း
    if action == "get_file":
        file_id = context.user_data.get('temp_id')
        media_type = context.user_data.get('temp_type')
        
        if not file_id:
            await query.message.reply_text("❌ စနစ်ကြောင့် ဖိုင်မှတ်ဉာဏ် ပျောက်သွားပါသည်။ Link ကို ပြန်ပို့ပေးပါ။")
            return

        try:
            if media_type == "video": await query.message.reply_video(video=file_id, caption="ဗီဒီယို ရပါပြီ။")
            else: await query.message.reply_audio(audio=file_id, caption="အသံဖိုင် ရပါပြီ။")
            await query.message.delete()
        except:
            await query.message.reply_document(document=file_id, caption="ဖိုင် ရပါပြီ။")
            await query.message.delete()
        return

    url = context.user_data.get('last_url')
    if not url:
        await query.edit_message_text("❌ Link ပြန်ပို့ပေးပါ။")
        return

    await query.edit_message_text("⏳ ခဏစောင့်ပါ။ ပြင်ဆင်နေပါသည်။...")

    try:
        m_type = 'video' if action == 'dl_video' else 'audio'
        ydl_opts = {
            'format': 'best' if m_type == 'video' else 'bestaudio/best',
            'outtmpl': f'dl_{user_id}.%(ext)s',
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        with open(file_path, 'rb') as f:
            if m_type == 'video':
                sent = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
                file_id = sent.video.file_id
            else:
                sent = await context.bot.send_audio(chat_id=STORAGE_CHANNEL_ID, audio=f)
                file_id = sent.audio.file_id
        
        if os.path.exists(file_path): os.remove(file_path)

        # File ID ကို ခဏသိမ်းထားမယ်
        context.user_data['temp_id'] = file_id
        context.user_data['temp_type'] = m_type

        keyboard = [
            [InlineKeyboardButton("📺 ကြော်ငြာကြည့်ရန် (၅ စက္ကန့်)", web_app=WebAppInfo(url=AD_LINK))],
            [InlineKeyboardButton("✅ ဖိုင်ရယူရန်", callback_data="get_file")]
        ]
        await query.edit_message_text("✅ အဆင်သင့်ဖြစ်ပါပြီ။\n\n၁။ ကြော်ငြာကြည့်ရန် ကိုနှိပ်ပါ။\n၂။ ပြီးနောက် ဖိုင်ရယူရန် ကိုနှိပ်ပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception:
        err = traceback.format_exc()
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ **Error:**\n`{err[:3000]}`")
        await query.edit_message_text("❌ ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။ Link ပြန်စစ်ပေးပါ။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()
