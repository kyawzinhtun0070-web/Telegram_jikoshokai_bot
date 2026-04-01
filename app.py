import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- Config ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = '6131831207'
STORAGE_CHANNEL_ID = -1003649365692
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Force Join စစ်ဆေးခြင်း
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except: return True

# Sensei စိတ်ကြိုက် Greeting ပုံစံ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 မင်္ဂလာပါ!\n\n"
        "ကျွန်တော်က Social Media များမှ ဗီဒီယိုနှင့် အသံ (Audio) များကို "
        "အလွယ်တကူ ဒေါင်းလုဒ်ဆွဲပေးမည့် Bot ပါ။\n\n"
        "📥 ဒေါင်းလုဒ်ဆွဲလိုသော Video Link ကို ဒီမှာ ပို့ပေးလိုက်ပါ ခင်ဗျာ။\n\n"
        "👑 ကြော်ငြာမကြည့်လိုပါက Premium ဝယ်ယူနိုင်ပါတယ်။"
    )
    await update.message.reply_text(welcome_text)

# Link ပို့လာလျှင်
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    url = update.message.text
    if not url.startswith("http"): return

    # Admin Noti
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 User: {user.first_name}\n🔗 Link: {url}")
    except: pass

    # Force Join
    if not await check_joined(user.id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text("ဗီဒီယိုဒေါင်းရန် Channel ကို အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    context.user_data['last_url'] = url
    keyboard = [[InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")]]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ ရွေးပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

# ခလုတ်နှိပ်ခြင်း (အဓိက အပိုင်း)
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # "ဗီဒီယိုရယူရန်" ခလုတ်ကို နှိပ်လိုက်လျှင်
    if query.data.startswith("get_"):
        msg_id = query.data.split("_")[1]
        
        # ၁။ ကြော်ငြာ Link ကို Popup အနေနဲ့ တန်းပွင့်ခိုင်းမယ် (ဒါမှ ဝင်ငွေရမှာပါ)
        await query.answer(url=AD_LINK) 
        
        # ၂။ ဗီဒီယိုကို User ဆီ တန်းပို့ပေးမယ်
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=int(msg_id),
                caption="✅ ဒေါင်းလုဒ် ရပါပြီ။ ကျေးဇူးတင်ပါသည်။"
            )
            await query.message.delete()
        except:
            await query.message.reply_text("❌ အမှားအယွင်းရှိပါသည်။ Link ကို ပြန်ပို့ပေးပါ။")
        return

    # ဒေါင်းလုဒ်ဆွဲသည့်အပိုင်း
    url = context.user_data.get('last_url')
    if not url: return

    await query.edit_message_text("⏳ ခဏစောင့်ပါ။ ပြင်ဆင်နေပါသည်။...")

    try:
        m_type = 'video' if query.data == 'dl_video' else 'audio'
        ydl_opts = {
            'format': 'best' if m_type == 'video' else 'bestaudio/best',
            'outtmpl': f'dl_{user_id}.%(ext)s', 'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        with open(file_path, 'rb') as f:
            if m_type == 'video': sent = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            else: sent = await context.bot.send_audio(chat_id=STORAGE_CHANNEL_ID, audio=f)
            storage_msg_id = sent.message_id
        
        if os.path.exists(file_path): os.remove(file_path)

        # ခလုတ်တစ်ခုတည်း ပေါင်းပေးလိုက်ခြင်း
        # နှိပ်လိုက်တာနဲ့ query.answer(url=AD_LINK) ကြောင့် ကြော်ငြာဆီသွားဖို့ မေးပါလိမ့်မယ်
        keyboard = [[InlineKeyboardButton("🚀 ဗီဒီယိုရယူရန် (ကြော်ငြာကြည့်ပေးပါ)", callback_data=f"get_{storage_msg_id}")]]
        await query.edit_message_text("✅ အဆင်သင့်ဖြစ်ပါပြီ။ အောက်ကခလုတ်ကို နှိပ်ပြီး ရယူပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        await query.edit_message_text("❌ ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။ Link ပြန်စစ်ပေးပါ။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

