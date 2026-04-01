import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- Config ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = 6131831207 
STORAGE_CHANNEL_ID = -1003649365692
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(level=logging.INFO)

# --- Force Join စစ်ဆေးခြင်း ---
async def check_joined(user_id, context):
    try:
        # Bot ကို Channel မှာ Admin ခန့်ထားမှ ဒါက အလုပ်လုပ်မှာပါ
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

# --- Greeting & Force Join ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_joined(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url="https://t.me/linktovideodownloadermm")]]
        await update.message.reply_text(
            "👋 မင်္ဂလာပါ! ကျွန်တော်တို့ Bot ကို အသုံးပြုရန် Channel ကို အရင် Join ပေးပါ။\n\n"
            "Join ပြီးပါက /start ကို ပြန်နှိပ်ပါခင်ဗျာ။", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    welcome_text = (
        "👋 မင်္ဂလာပါ!\n\n"
        "ကျွန်တော်က Social Media များမှ ဗီဒီယိုနှင့် အသံ (Audio) များကို "
        "အလွယ်တကူ ဒေါင်းလုဒ်ဆွဲပေးမည့် Bot ပါ။\n\n"
        "📥 ဒေါင်းလုဒ်ဆွဲလိုသော Video Link ကို ဒီမှာ ပို့ပေးလိုက်ပါ ခင်ဗျာ။"
    )
    await update.message.reply_text(welcome_text)

# --- Link ပို့လာလျှင် ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await check_joined(user.id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url="https://t.me/linktovideodownloadermm")]]
        await update.message.reply_text("⚠️ ဗီဒီယိုဒေါင်းရန် Channel ကို အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    url = update.message.text
    if not url.startswith("http"): return

    # Admin Noti
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 User: {user.first_name}\n🆔 ID: {user.id}\n🔗 Link: {url}")
    except: pass

    context.user_data['last_url'] = url
    keyboard = [[InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")]]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ ရွေးပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

# --- ခလုတ်နှိပ်ခြင်း (Sensei အလိုရှိသော Strict Ad-Gate) ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data.startswith("force_"):
        _, m_type, msg_id = query.data.split("_")
        label = "ဗီဒီယို" if m_type == "video" else "အသံဖိုင်"
        
        # ၁။ User ဆီကို ကြော်ငြာလင့် အရင်ပို့မယ်
        await query.edit_message_text(
            f"📥 {label}ကို ထုတ်ပေးနေပါပြီ...\n\n"
            f"⚠️ **အရေးကြီးသည်:** ဖိုင်မပို့မီ အောက်ကကြော်ငြာလင့်ကို အရင်နှိပ်ပေးပါ။\n\n"
            f"🔗 {AD_LINK}\n\n"
            f"⏳ ၅ စက္ကန့်အတွင်း {label} ရောက်လာပါလိမ့်မည်။"
        )
        
        # ၂။ ၅ စက္ကန့် အတင်းစောင့်ခိုင်းမယ် (Bypass လုပ်မရအောင်)
        await asyncio.sleep(6)
        
        # ၃။ ဖိုင်ကို အလိုအလျောက် ပို့ပေးမယ်
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=int(msg_id),
                caption=f"✅ {label} ရပါပြီ။ ကျေးဇူးတင်ပါသည်။"
            )
            await query.message.delete()
        except:
            await query.message.reply_text("❌ စနစ်ချို့ယွင်းချက်ရှိပါသည်။ Link ပြန်ပို့ပေးပါ။")
        return

    url = context.user_data.get('last_url')
    if not url: return

    status = await query.edit_message_text("⏳ ခဏစောင့်ပါ။ ပြင်ဆင်နေပါသည်။...")

    try:
        m_type = 'video' if query.data == 'dl_video' else 'audio'
        label = "ဗီဒီယို" if m_type == "video" else "အသံဖိုင်"
        
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

        # ✅ ခလုတ်တစ်ခုတည်းပဲ ပြမယ် (ဒေါင်းလုဒ်ခလုတ် လုံးဝမပါ)
        keyboard = [[InlineKeyboardButton(f"🚀 ကြော်ငြာကြည့်ပြီး {label}ရယူရန်", callback_data=f"force_{m_type}_{storage_msg_id}")]]
        await status.edit_text(
            f"✅ {label} ဒေါင်းလုဒ်ဆွဲပြီးပါပြီ။\nအောက်ကခလုတ်ကို နှိပ်ပြီး ကြော်ငြာကြည့်ကာ ဖိုင်ရယူပါ။", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except:
        await query.edit_message_text("❌ ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။ Link ပြန်စစ်ပေးပါ။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()
