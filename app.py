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
STORAGE_CHANNEL_ID = -1003649365692  # Channel ID ကို ကိန်းဂဏန်းအဖြစ်ပဲ ထားပါ
MAIN_CHANNEL = '@linktovideodownloadermm'
AD_LINK = 'https://www.profitablecpmratenetwork.com/iea7hf0n?key=3f50007692900d40cca3bb9bc6aee189'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def check_joined(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user_id)
        return member.status not in ['left', 'kicked']
    except: return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"မင်္ဂလာပါ {update.effective_user.first_name}။ ဗီဒီယို Link ပို့ပေးပါ။")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    url = update.message.text
    if not url.startswith("http"): return

    # Admin Noti
    try: await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 User: {user.first_name}\n🔗 Link: {url}")
    except: pass

    if not await check_joined(user.id, context):
        keyboard = [[InlineKeyboardButton("📢 Channel Join ရန်", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text("Channel အရင် Join ပေးပါ။", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ဒေါင်းလုဒ်ဆွဲရန် ရွေးခိုင်းခြင်း
    context.user_data['last_url'] = url
    keyboard = [[InlineKeyboardButton("📹 ဗီဒီယို ယူမယ်", callback_data="dl_video"),
                 InlineKeyboardButton("🎵 အသံ (Audio) ယူမယ်", callback_data="dl_audio")]]
    await update.message.reply_text("👇 ဘယ်လိုပုံစံ ဒေါင်းလုဒ်ဆွဲချင်ပါသလဲ?", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    # ၁-ကလစ်ဖြင့် ဖိုင်ထုတ်ပေးခြင်း
    if query.data.startswith("send_"):
        storage_msg_id = query.data.split("_")[1]
        try:
            # ၁။ ဖိုင်ကို User ဆီ ပို့ပေးမယ်
            await context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=STORAGE_CHANNEL_ID,
                message_id=int(storage_msg_id),
                caption="✅ ဒေါင်းလုဒ် ရပါပြီ။\n\n🙏 Bot ရေရှည်ရပ်တည်နိုင်ဖို့ အောက်ကကြော်ငြာကို ၅ စက္ကန့်ကြည့်ပေးပါ။",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📺 ကြော်ငြာကြည့်ရန်", url=AD_LINK)]])
            )
            await query.message.delete()
            await query.answer("ဖိုင်ကို ပို့ပေးလိုက်ပါပြီ။", show_alert=False)
        except Exception as e:
            await query.message.reply_text("❌ အမှားအယွင်းရှိသွားပါသည်။ Link ပြန်ပို့ပေးပါ။")
        return

    # ဒေါင်းလုဒ်လုပ်သည့်အပိုင်း
    url = context.user_data.get('last_url')
    if not url:
        await query.answer("Link သက်တမ်းကုန်သွားပါပြီ။ ပြန်ပို့ပေးပါ။", show_alert=True)
        return

    await query.edit_message_text("⏳ ခဏစောင့်ပါ။ ဒေါင်းလုဒ်ဆွဲနေပါသည်...")

    try:
        m_type = 'video' if query.data == 'dl_video' else 'audio'
        ydl_opts = {
            'format': 'best' if m_type == 'video' else 'bestaudio/best',
            'outtmpl': f'dl_{user_id}.%(ext)s',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        # Storage Channel သို့ ပို့ခြင်း
        with open(file_path, 'rb') as f:
            if m_type == 'video':
                sent = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            else:
                sent = await context.bot.send_audio(chat_id=STORAGE_CHANNEL_ID, audio=f)
            
            storage_msg_id = sent.message_id
        
        if os.path.exists(file_path): os.remove(file_path)

        # User ဆီသို့ ခလုတ်တစ်ခုတည်းဖြင့် ပြန်စာပို့ခြင်း
        keyboard = [[InlineKeyboardButton("🚀 ဖိုင်ရယူရန် (၁-ကလစ်)", callback_data=f"send_{storage_msg_id}")]]
        await query.edit_message_text(
            "✅ ဗီဒီယို အဆင်သင့်ဖြစ်ပါပြီ။\n\nအောက်ကခလုတ်ကို နှိပ်ပြီး ရယူလိုက်ပါ။", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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
