import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

# --- ခင်ဗျားရဲ့ အချက်အလက်များ ---
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
    except:
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_msg = (
        f"မင်္ဂလာပါ {user_name} လေးရေ... 🤗\n\n"
        "ဗီဒီယိုတွေကို Watermark မပါဘဲ အကောင်းဆုံး ဒေါင်းပေးဖို့ ကျွန်တော် အဆင်သင့်ရှိနေပါပြီ။\n"
        "ဒေါင်းလုဒ်ဆွဲချင်တဲ့ Link လေးကို အောက်မှာ ပို့ပေးလိုက်နော်။ 👇"
    )
    await update.message.reply_text(welcome_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text
    if not url.startswith("http"): return

    joined = await check_joined(user_id, context)
    if not joined:
        keyboard = [[InlineKeyboardButton("📢 Channel ကို Join ရန်", url=f"https://t.me/{MAIN_CHANNEL[1:]}")]]
        await update.message.reply_text("ဗီဒီယိုဒေါင်းဖို့အတွက် ကျွန်တော်တို့ရဲ့ Channel လေးကို အရင် Join ပေးပါဦးနော်။ 🙏", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    status_msg = await update.message.reply_text("ခဏလေးစောင့်ပေးပါနော်... ချစ်တို့အတွက် ဗီဒီယိုလေးကို ရှာဖွေပြီး ပြင်ဆင်ပေးနေပါတယ်... ⏳✨")

    try:
        # ဗီဒီယိုဒေါင်းလုဒ်ဆွဲခြင်း (Options ကို ပိုမိုကောင်းမွန်အောင် ပြင်ထားသည်)
        ydl_opts = {
            'format': 'best', 
            'outtmpl': f'vid_{user_id}.%(ext)s', 
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
        
        # Storage ထဲပို့ခြင်း
        with open(file_path, 'rb') as f:
            # ဗီဒီယိုအနေနဲ့ ပို့ကြည့်မယ်
            sent_msg = await context.bot.send_video(chat_id=STORAGE_CHANNEL_ID, video=f)
            
            # ဗီဒီယိုဖြစ်ဖြစ်၊ ဖိုင်ဖြစ်ဖြစ် file_id ကို ရအောင်ယူမယ် (ဒါက အဓိက အဖြေပဲ!)
            file_id = None
            if sent_msg.video:
                file_id = sent_msg.video.file_id
            elif sent_msg.document:
                file_id = sent_msg.document.file_id
            elif sent_msg.animation:
                file_id = sent_msg.animation.file_id
        
        if os.path.exists(file_path):
            os.remove(file_path)

        if not file_id:
            raise Exception("File ID not found")

        # ကြော်ငြာပြသခြင်း
        keyboard = [
            [InlineKeyboardButton("📺 ကြော်ငြာ ၅ စက္ကန့်ကြည့်ရန်", web_app=WebAppInfo(url=AD_LINK))],
            [InlineKeyboardButton("✅ ဗီဒီယို ရယူရန်", callback_data=f"get_{file_id}")]
        ]
        
        await status_msg.edit_text(
            "ကဲ... ဗီဒီယိုလေး အဆင်သင့်ဖြစ်ပါပြီရှင်! 😍\n\n"
            "၁။ ပထမဆုံး 'ကြော်ငြာကြည့်ရန်' ခလုတ်လေးကိုနှိပ်ပြီး ၅ စက္ကန့်လောက် ကြည့်ပေးပါနော်။ (ပြီးရင် Window လေးကို ပြန်ပိတ်လိုက်ပါ)\n"
            "၂။ ပြီးရင်တော့ 'ဗီဒီယို ရယူရန်' ကိုနှိပ်ပြီး ယူလို့ရပါပြီ။",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logging.error(f"Error detail: {e}")
        await status_msg.edit_text("စိတ်မကောင်းပါဘူး... ဗီဒီယိုဖိုင်က ကြီးလွန်းနေလို့ ဒါမှမဟုတ် Link မှားနေလို့ ဒေါင်းလို့မရဖြစ်နေပါတယ်ရှင်။ 😥")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("get_"):
        file_id = query.data.split("_")[1]
        try:
            # ဗီဒီယိုကို file_id နဲ့ ပြန်ပို့မယ်
            await query.message.reply_video(video=file_id, caption="ချစ်တို့အတွက် ဗီဒီယိုလေး ရပါပြီရှင်... ကျေးဇူးတင်ပါတယ်နော်! ❤️")
            await query.message.delete()
        except:
            # Video အနေနဲ့ မရရင် Document အနေနဲ့ ပို့မယ်
            await query.message.reply_document(document=file_id, caption="ချစ်တို့အတွက် ဖိုင်လေး ရပါပြီရှင်... ကျေးဇူးတင်ပါတယ်နော်! ❤️")
            await query.message.delete()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()
