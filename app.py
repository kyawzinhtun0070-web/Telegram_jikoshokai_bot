import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- Config ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = 6131831207 
STORAGE_CHANNEL_ID = -1003649365692 
MAIN_CHANNEL = '@linktovideodownloadermm'

logging.basicConfig(level=logging.INFO)

# --- Channel Join ထားခြင်း ရှိ/မရှိ စစ်ဆေးခြင်း ---
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        # Status က member, administrator သို့မဟုတ် creator ဖြစ်ရမယ်
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Force Join Check Error: {e}")
        return False

# --- /start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_joined(user_id, context):
        text = (
            "👋 မင်္ဂလာပါ!\n\n"
            "ကျွန်တော်တို့ Bot ကို အသုံးပြုရန် အောက်က Channel ကို အရင် Join ပေးပါ။\n"
            "Join ပြီးပါက /start ကို ပြန်နှိပ်ပါ ခင်ဗျာ။"
        )
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL.replace('@','')}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await update.message.reply_text("📥 ဒေါင်းလုဒ်ဆွဲလိုသော Video Link ကို ဒီမှာ ပို့ပေးလိုက်ပါ ခင်ဗျာ။")

# --- Link လက်ခံရရှိခြင်း ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text

    if not url.startswith("http"):
        return

    # Force Join ထပ်စစ်မယ် (လုံခြုံရေးအတွက်)
    if not await check_joined(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL.replace('@','')}")]]
        await update.message.reply_text("⚠️ အရင် Join ပေးပါဦးခင်ဗျာ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    context.user_data['last_url'] = url
    keyboard = [[
        InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
        InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")
    ]]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ?", reply_markup=InlineKeyboardMarkup(keyboard))

# --- ဒေါင်းလုဒ်လုပ်ပြီး တိုက်ရိုက်ပို့ပေးခြင်း ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    url = context.user_data.get('last_url')
    
    if not url:
        await query.edit_message_text("❌ Link ပြန်ပို့ပေးပါ။")
        return

    status_msg = await query.edit_message_text("⏳ ဒေါင်းလုဒ်ဆွဲနေပါပြီ။ ခဏစောင့်ပါ။...")

    try:
        m_type = 'video' if query.data == 'dl_video' else 'audio'
        file_path = f'dl_{user_id}_{m_type}.mp4'
        
        ydl_opts = {
            'format': 'best' if m_type == 'video' else 'bestaudio/best',
            'outtmpl': file_path,
            'quiet': True,
            'nocheckcertificate': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # ဖိုင်ကို Storage ထဲအရင်ပို့ပြီး User ဆီ Copy ပြန်ကူးပေးမယ် (ဒါမှ Bot ပိုမြန်မယ်)
        with open(file_path, 'rb') as f:
            if m_type == 'video':
                sent = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            else:
                sent = await context.bot.send_audio(chat_id=STORAGE_CHANNEL_ID, audio=f)
            
            # User ဆီကို တိုက်ရိုက် Copy ပို့မယ်
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=sent.message_id,
                caption="✅ ဒေါင်းလုဒ်လုပ်ပြီးပါပြီ။"
            )

        # ပြီးရင် ဖုန်း/Server ထဲက ဖိုင်ဖျက်မယ်
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        logging.error(f"Error: {e}")
        await query.edit_message_text("❌ ဒေါင်းလုဒ်ဆွဲလို့ မရပါ။ Link ပြန်စစ်ပါ။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("Bot is running without Ads...")
    app.run_polling()
