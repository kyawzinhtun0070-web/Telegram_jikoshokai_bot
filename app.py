import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- Config (မင်းပေးထားတဲ့ အချက်အလက်များ) ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = 6131831207 
STORAGE_CHANNEL_ID = -1003649365692 # ID မှန်မမှန် ပြန်စစ်ပါ
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Force Join စစ်ဆေးခြင်း ---
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        # အခြေအနေ ၃ ခုလုံးကို လက်ခံရမယ်
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Check Join Error: {e}")
        return False

# --- /start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_joined = await check_joined(user_id, context)
    
    if not is_joined:
        text = (
            "👋 မင်္ဂလာပါ!\n\n"
            "ကျွန်တော်တို့ Bot ကို အသုံးပြုရန် အောက်က Channel ကို အရင် Join ပေးပါ။\n"
            "Join ပြီးပါက /start ကို ပြန်နှိပ်ပါခင်ဗျာ။"
        )
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL.replace('@','')}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    welcome_text = (
        "👋 မင်္ဂလာပါ!\n\n"
        "ကျွန်တော်က Social Media ဗီဒီယိုတွေကို ဒေါင်းလုဒ်ဆွဲပေးမယ့် Bot ပါ။\n\n"
        "📥 ဒေါင်းလုဒ်ဆွဲလိုသော Video Link ကို ဒီမှာ ပို့ပေးလိုက်ပါ ခင်ဗျာ။"
    )
    await update.message.reply_text(welcome_text)

# --- Link လက်ခံရရှိခြင်း ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    url = update.message.text

    if not url.startswith("http"):
        return

    # Force Join ထပ်စစ်မယ်
    if not await check_joined(user.id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL.replace('@','')}")]]
        await update.message.reply_text("⚠️ ဗီဒီယိုဒေါင်းရန် Channel ကို အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Admin ဆီ Notification ပို့မယ်
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 User: {user.first_name}\n🆔 ID: {user.id}\n🔗 Link: {url}")
    except: pass

    context.user_data['last_url'] = url
    keyboard = [
        [
            InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
            InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")
        ]
    ]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ ရွေးပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

# --- ခလုတ်နှိပ်ခြင်း Handler ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Loading စက်ဝိုင်း ပျောက်သွားအောင် အရင်ဖြေရမယ်
    
    user_id = query.from_user.id
    data = query.data

    # ၁။ Ad ကြည့်ခိုင်းသည့် အပိုင်း
    if data.startswith("force_ad_"):
        _, m_type, msg_id = data.split("_")
        label = "ဗီဒီယို" if m_type == "video" else "အသံဖိုင်"
        
        await query.edit_message_text(
            f"📥 {label} ကို ပြင်ဆင်နေပါပြီ...\n\n"
            f"⚠️ **အဆင့် (၁):** အောက်ကကြော်ငြာလင့်ကို နှိပ်ပါ။\n"
            f"🔗 {AD_LINK}\n\n"
            f"⏳ ၇ စက္ကန့်အတွင်း {label} အလိုအလျောက် ပို့ပေးပါမည်။"
        )
        
        await asyncio.sleep(7) # အတင်းစောင့်ခိုင်းခြင်း
        
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=int(msg_id),
                caption=f"✅ {label} ရပါပြီ။ @linktovideodownloadermm"
            )
            await query.message.delete()
        except Exception as e:
            logging.error(f"Copy Error: {e}")
            await query.message.reply_text("❌ စနစ်ချို့ယွင်းချက်ရှိပါသည်။ ပြန်စမ်းကြည့်ပါ။")
        return

    # ၂။ ဒေါင်းလုဒ်စတင်သည့် အပိုင်း
    url = context.user_data.get('last_url')
    if not url:
        await query.edit_message_text("❌ Link မရှိတော့ပါ။ ပြန်ပို့ပေးပါ။")
        return

    status_msg = await query.edit_message_text("⏳ ဒေါင်းလုဒ်ဆွဲနေပါပြီ။ ခဏစောင့်ပေးပါ။...")

    try:
        m_type = 'video' if data == 'dl_video' else 'audio'
        label = "ဗီဒီယို" if m_type == "video" else "အသံဖိုင်"
        
        file_path = f'dl_{user_id}.mp4'
        ydl_opts = {
            'format': 'best' if m_type == 'video' else 'bestaudio/best',
            'outtmpl': file_path,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Storage ထဲပို့ပြီး Message ID ယူမယ်
        with open(file_path, 'rb') as f:
            if m_type == 'video':
                sent = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            else:
                sent = await context.bot.send_audio(chat_id=STORAGE_CHANNEL_ID, audio=f)
            storage_msg_id = sent.message_id
        
        if os.path.exists(file_path): os.remove(file_path)

        # ကြော်ငြာကြည့်ရန် ခလုတ်ပြောင်းမယ်
        keyboard = [[InlineKeyboardButton(f"🚀 ကြော်ငြာကြည့်ပြီး {label} ရယူရန်", callback_data=f"force_ad_{m_type}_{storage_msg_id}")]]
        await status_msg.edit_text(
            f"✅ {label} အဆင်သင့်ဖြစ်ပါပြီ။\nအောက်ကခလုတ်ကိုနှိပ်ပြီး {label} ကို ရယူပါ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(f"Download Error: {e}")
        await query.edit_message_text("❌ ဒေါင်းလုဒ်ဆွဲမရပါ။ Link မှန်မမှန် ပြန်စစ်ပါ။")

# --- Main Logic ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("Bot is running...")
    app.run_polling()
