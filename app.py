import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- Config ---
TOKEN = '8659166008:AAGEI5f61PsG6wd5ciKEazmqtiRiycDTYbI'
ADMIN_ID = 6131831207 
STORAGE_CHANNEL_ID = -1003649365692 # ဗီဒီယိုတွေ သိမ်းမယ့်နေရာ
FORCE_JOIN_CHANNEL = -1003894700479 # မင်းပေးတဲ့ Channel ID အသစ်

logging.basicConfig(level=logging.INFO)

# --- Force Join စစ်ဆေးခြင်း ---
async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_JOIN_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# --- Greeting (Professional Look) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_joined = await check_joined(user.id, context)
    
    if not is_joined:
        # Channel Link ကို Username မသိရင် ID ကနေ တိုက်ရိုက်သွားလို့မရလို့ Private Link သုံးပါ သို့မဟုတ် Username သိရင် ပြန်ပြင်ပါ
        text = (
            f"👋 မင်္ဂလာပါ {user.first_name}!\n\n"
            "ကျွန်တော်တို့ရဲ့ Bot ကို အသုံးပြုဖို့ အောက်က Channel ကို အရင် Join ပေးပါဦး။\n"
            "Join ပြီးမှ /start ကို ပြန်နှိပ်ပေးပါ ခင်ဗျာ။"
        )
        # အောက်က URL မှာ မင်း Channel ရဲ့ username ကို ထည့်ပေးပါ (ဥပမာ t.me/yourchannel)
        keyboard = [[InlineKeyboardButton("📢 Channel ကို Join ရန်", url="https://t.me/linktovideodownloadermm")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    welcome_text = (
        "🌟 **Social Media Video Downloader Bot** 🌟\n\n"
        "ကျွန်တော်က အောက်ပါ Platform တွေကနေ ဗီဒီယိုတွေကို အခမဲ့ ဒေါင်းလုဒ်ဆွဲပေးနိုင်ပါတယ်။\n"
        "✅ TikTok  ✅ Facebook\n"
        "✅ YouTube ✅ Instagram\n"
        "✅ X (Twitter)\n\n"
        "📥 ဒေါင်းလုဒ်ဆွဲဖို့ ဗီဒီယိုလင့်ခ် (Link) ကို ဒီမှာ ပို့ပေးလိုက်ပါ!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

# --- Message Handler ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text

    if not url.startswith("http"):
        return

    # Force Join စစ်မယ်
    if not await check_joined(user_id, context):
        await start(update, context)
        return

    # Link ကို user_data ထဲမှာ အသေအချာ သိမ်းမယ်
    context.user_data['last_url'] = url
    
    keyboard = [[
        InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
        InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")
    ]]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ?", reply_markup=InlineKeyboardMarkup(keyboard))

# --- Button Click Handler (Fixes: "လင့်ပြန်ပို့ပေးပါ" error) ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    # URL ရှိမရှိ သေချာစစ်မယ်
    url = context.user_data.get('last_url')
    
    if not url:
        await query.message.reply_text("❌ စနစ်ချို့ယွင်းမှုကြောင့် လင့်ခ် ပျောက်သွားပါတယ်။ ကျေးဇူးပြုပြီး လင့်ခ်ကို ပြန်ပို့ပေးပါ။")
        return

    status_msg = await query.edit_message_text("⏳ ဒေါင်းလုဒ်ဆွဲနေပါပြီ။ ခဏစောင့်ပေးပါ။...")

    try:
        m_type = 'video' if query.data == 'dl_video' else 'audio'
        # ဖိုင်နာမည်ကို User ID နဲ့ ခွဲထားမယ် (တခြား user နဲ့ မရောအောင်)
        file_path = f'dl_{user_id}_{m_type}.mp4'
        
        # Multi-platform Support ဖြစ်ဖို့ Option အစုံထည့်ထားတယ်
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if m_type == 'video' else 'bestaudio/best',
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'ignoreerrors': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(file_path):
            await query.edit_message_text("❌ ဒေါင်းလုဒ်ဆွဲလို့ မရပါ။ Link မှားနေတာ ဒါမှမဟုတ် ဗီဒီယိုက Private ဖြစ်နေတာ ဖြစ်နိုင်ပါတယ်။")
            return

        # ဖိုင်ပို့မယ်
        with open(file_path, 'rb') as f:
            if m_type == 'video':
                sent = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f, caption="✅ Success")
            else:
                sent = await context.bot.send_audio(chat_id=STORAGE_CHANNEL_ID, audio=f, caption="✅ Success")
            
            # User ဆီ Copy ပို့မယ်
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=sent.message_id
            )

        # Cleanup
        if os.path.exists(file_path): os.remove(file_path)
        await status_msg.delete()

    except Exception as e:
        logging.error(f"Error: {e}")
        await query.edit_message_text(f"❌ အခက်အခဲတစ်ခုရှိနေပါတယ်။ နောက်မှ ပြန်စမ်းကြည့်ပါ။")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("Bot is starting with Multi-platform support...")
    app.run_polling()
