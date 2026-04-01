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

# --- Force Join စစ်ဆေးခြင်း (Strict Check) ---
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

# --- Greeting (Force Join ပါပြီးသား) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_joined = await check_joined(user_id, context)
    
    if not is_joined:
        text = (
            "👋 မင်္ဂလာပါ!\n\n"
            "ကျွန်တော်တို့ Bot ကို အသုံးပြုရန် အောက်က Channel ကို အရင် Join ပေးပါ။\n"
            "Join ပြီးပါက /start ကို ပြန်နှိပ်ပါခင်ဗျာ။"
        )
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url="https://t.me/linktovideodownloadermm")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    welcome_text = (
        "👋 မင်္ဂလာပါ!\n\n"
        "ကျွန်တော်က Social Media များမှ ဗီဒီယိုနှင့် အသံ (Audio) များကို "
        "အလွယ်တကူ ဒေါင်းလုဒ်ဆွဲပေးမည့် Bot ပါ။\n\n"
        "📥 ဒေါင်းလုဒ်ဆွဲလိုသော Video Link ကို ဒီမှာ ပို့ပေးလိုက်ပါ ခင်ဗျာ။"
    )
    await update.message.reply_text(welcome_text)

# --- Link ပို့လာလျှင် (Force Join ထပ်စစ်သည်) ---
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

# --- ခလုတ်နှိပ်ခြင်း (Force Ad စနစ် - Bypass လုံးဝမရ) ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # 🛑 Sensei အလိုရှိသော "ကြော်ငြာကိုပဲ အရင်ကြည့်ခိုင်းမည့်စနစ်"
    if query.data.startswith("force_ad_"):
        _, m_type, msg_id = query.data.split("_")
        label = "ဗီဒီယို" if m_type == "video" else "အသံဖိုင်"
        
        # ၁။ User ဆီကို ကြော်ငြာလင့် အရင်ပြမယ်
        await query.edit_message_text(
            f"📥 {label}ကို ထုတ်ပေးနေပါပြီ...\n\n"
            f"⚠️ **အဆင့် (၁):** အောက်ကကြော်ငြာလင့်ကို နှိပ်ပါ။\n"
            f"🔗 {AD_LINK}\n\n"
            f"⏳ ကြည့်ပြီး ၇ စက္ကန့်အတွင်း {label} အလိုအလျောက် ရောက်လာပါလိမ့်မည်။"
        )
        
        # ၂။ ၇ စက္ကန့် အတင်းစောင့်ခိုင်းမယ် (Bypass လုပ်မရအောင် Timer အသေပိတ်ထားသည်)
        await asyncio.sleep(7)
        
        # ၃။ ဖိုင်ကို Storage ထဲကနေ ဆွဲထုတ်ပြီး အလိုအလျောက် ပို့ပေးမယ်
        try:
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=int(msg_id),
                caption=f"✅ {label} ရပါပြီ။ ကျေးဇူးတင်ပါသည်။"
            )
            await query.message.delete()
        except Exception:
            await query.message.reply_text("❌ စနစ်ချို့ယွင်းချက်ရှိပါသည်။ Link ပြန်ပို့ပေးပါ။")
        return

    # ဒေါင်းလုဒ်လုပ်သည့် အပိုင်း
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

        # ✅ ဒေါင်းလုဒ်ခလုတ် လုံးဝမပါပါ (ကြော်ငြာကြည့်ရန် ခလုတ်တစ်ခုတည်းသာ)
        keyboard = [[InlineKeyboardButton(f"🚀 ကြော်ငြာကြည့်ပြီး {label}ရယူရန်", callback_data=f"force_ad_{m_type}_{storage_msg_id}")]]
        await status.edit_text(
            f"✅ {label} အဆင်သင့်ဖြစ်ပါပြီ။\nအောက်ကခလုတ်ကို နှိပ်ပြီး ကြော်ငြာကြည့်ကာ {label}ကို ရယူပါ။", 
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
