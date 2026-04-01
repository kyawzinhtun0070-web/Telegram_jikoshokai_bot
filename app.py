import os
import asyncio
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- Config ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = 6131831207 
STORAGE_CHANNEL_ID = -1003649365692
MAIN_CHANNEL = '@linktovideodownloadermm' # Force Join လုပ်ခိုင်းမည့် Channel
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Force Join စစ်ဆေးခြင်း (အမှန်တကယ် Join မှ ရမည်) ---
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        # member, administrator, creator ဖြစ်မှ Join တယ်လို့ သတ်မှတ်မယ်
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# --- Greeting ပုံစံအဟောင်း (Premium လုံးဝမပါ) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    url = update.message.text
    if not url.startswith("http"): return

    # Force Join Check (မ Join ရင် ဒီမှာတင် ရပ်မယ်)
    is_joined = await check_joined(user.id, context)
    if not is_joined:
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text(
            "ဗီဒီယိုဒေါင်းရန် ကျွန်တော်တို့၏ Channel ကို အရင် Join ပေးပါ။\n"
            "Join ပြီးပါက Link ကို ပြန်ပို့ပေးပါခင်ဗျာ။", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Admin Noti
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 User: {user.first_name}\n🆔 ID: {user.id}\n🔗 Link: {url}")
    except: pass

    context.user_data['last_url'] = url
    keyboard = [[InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")]]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ ရွေးပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))

# --- ခလုတ်နှိပ်ခြင်း (Force Ad စနစ်) ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # ၁။ ခလုတ်ဖွင့်ရန် (ကြော်ငြာနှိပ်ပြီးမှ နှိပ်ရမည့်အဆင့်)
    if query.data.startswith("ad_"):
        _, m_type, msg_id = query.data.split("_")
        label = "ဗီဒီယို" if m_type == "video" else "အသံဖိုင်"
        
        await query.answer("ကြော်ငြာကြည့်ပေးသည့်အတွက် ကျေးဇူးတင်ပါသည်။")
        
        new_keyboard = [[InlineKeyboardButton(f"🚀 {label}ရယူရန် (Download)", callback_data=f"get_{m_type}_{msg_id}")]]
        await query.edit_message_text(
            f"✅ ယခု အောက်ကခလုတ်ကို နှိပ်ပြီး {label}ကို ရယူနိုင်ပါပြီ။",
            reply_markup=InlineKeyboardMarkup(new_keyboard)
        )
        return

    # ၂။ ဗီဒီယို/အသံ အစစ်အမှန် ပို့ပေးသည့်အပိုင်း
    if query.data.startswith("get_"):
        _, m_type, msg_id = query.data.split("_")
        label = "ဗီဒီယို" if m_type == "video" else "အသံဖိုင်"
        
        await query.answer(f"{label}ကို ပို့ပေးနေပါပြီ...")
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

    # ၃။ ဒေါင်းလုဒ်ဆွဲသည့် အပိုင်း
    url = context.user_data.get('last_url')
    if not url: return

    await query.edit_message_text("⏳ ခဏစောင့်ပါ။ ပြင်ဆင်နေပါသည်။...")

    try:
        m_type = 'video' if query.data == 'dl_video' else 'audio'
        label = "ဗီဒီယို" if m_type == "video" else "အသံဖိုင်"
        
        ydl_opts = {
            'format': 'best' if m_type == 'video' else 'bestaudio/best',
            'outtmpl': f'dl_{user_id}.%(ext)s',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        with open(file_path, 'rb') as f:
            if m_type == 'video':
                sent = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            else:
                sent = await context.bot.send_audio(chat_id=STORAGE_CHANNEL_ID, audio=f)
            storage_msg_id = sent.message_id
        
        if os.path.exists(file_path): os.remove(file_path)

        # Force Ad Gate (ကြော်ငြာနှိပ်ပြီးမှ ဒေါင်းလုဒ်ခလုတ် ပွင့်မည်)
        keyboard = [
            [InlineKeyboardButton(f"📺 ကြော်ငြာကြည့်ပြီး {label}ယူရန်", url=AD_LINK)],
            [InlineKeyboardButton("🔓 ခလုတ်ဖွင့်ရန် (ကြော်ငြာနှိပ်ပြီးမှနှိပ်ပါ)", callback_data=f"ad_{m_type}_{storage_msg_id}")]
        ]
        
        await query.edit_message_text(
            f"✅ {label} အဆင်သင့်ဖြစ်ပါပြီ။\n\n၁။ အပေါ်က 'ကြော်ငြာကြည့်ရန်' ကို အရင်နှိပ်ပါ။\n၂။ ပြီးမှ 'ခလုတ်ဖွင့်ရန်' ကို နှိပ်ပါ။", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception:
        err = traceback.format_exc()
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ **Error Detail:**\n`{err[:3000]}`")
        await query.edit_message_text("❌ ဒေါင်းလုဒ်ဆွဲ၍ မရပါ။ Link ပြန်စစ်ပေးပါ။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

