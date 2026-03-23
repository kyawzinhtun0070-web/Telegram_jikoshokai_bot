import os
import telebot
from telebot import types

# --- Bot Setup ---
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# --- Admin Setup (ဆရာ့ ID) ---
ADMIN_ID = "6131831207"

# --- ယာယီ Data သိမ်းရန် ---
user_data = {}
SKIP_BTN = "⏭ မပြင်ပါ (Skip)"

# --- Data Dictionaries ---
LEVELS = {
    "JLPT N3 အောင်ထားပါတယ်": {"jp": "JLPTのN3に合格しました。", "mm": "JLPT N3 ကို အောင်မြင်ထားပါတယ်။"},
    "JLPT N4 အောင်ထားပါတယ်": {"jp": "JLPTのN4に合格しました。", "mm": "JLPT N4 ကို အောင်မြင်ထားပါတယ်။"},
    "N4 လေ့လာနေဆဲပါ": {"jp": "現在はN4レベルの日本語を勉強中です。", "mm": "လက်ရှိ N4 အဆင့် ဂျပန်စာကို လေ့လာနေဆဲပါ။"},
    "N5 အောင်ထားပါတယ်": {"jp": "JLPTのN5に合格しました。", "mm": "JLPT N5 ကို အောင်မြင်ထားပါတယ်။"}
}

HOBBIES = {
    "ရုပ်ရှင်ကြည့်ခြင်း": {"jp": "趣味は映画を見ることです。", "mm": "ဝါသနာကတော့ ရုပ်ရှင်ကြည့်ခြင်း ဖြစ်ပါတယ်။"},
    "သီချင်းနားထောင်ခြင်း": {"jp": "趣味は音楽を聴くことです。", "mm": "ဝါသနာကတော့ သီချင်းနားထောင်ခြင်း ဖြစ်ပါတယ်။"},
    "စာဖတ်ခြင်း": {"jp": "趣味は本を読むことです。", "mm": "ဝါသနာကတော့ စာဖတ်ခြင်း ဖြစ်ပါတယ်။"},
    "အားကစားလုပ်ခြင်း": {"jp": "趣味はスポーツをすることです。", "mm": "ဝါသနာကတော့ အားကစားလုပ်ခြင်း ဖြစ်ပါတယ်။"},
    "ခရီးသွားခြင်း": {"jp": "趣味は旅行することです。", "mm": "ဝါသနာကတော့ ခရီးသွားခြင်း ဖြစ်ပါတယ်။"},
    "ဟင်းချက်ခြင်း": {"jp": "趣味は料理を作ることです。", "mm": "ဝါသနာကတော့ ဟင်းချက်ခြင်း ဖြစ်ပါတယ်။"},
    "ဂိမ်းကစားခြင်း": {"jp": "趣味はゲームကိုすることです。", "mm": "ဝါသနာကတော့ ဂိမ်းကစားခြင်း ဖြစ်ပါတယ်။"},
    "ဓာတ်ပုံရိုက်ခြင်း": {"jp": "趣味は写真を撮ることです。", "mm": "ဝါသနာကတော့ ဓာတ်ပုံရိုက်ခြင်း ဖြစ်ပါတယ်။"},
    "ပန်းချီဆွဲခြင်း": {"jp": "趣味は絵を描くことです。", "mm": "ဝါသနာကတော့ ပန်းချီဆွဲခြင်း ဖြစ်ပါတယ်။"},
    "ဘာသာစကားလေ့လာခြင်း": {"jp": "趣味は外国語を勉強することです。", "mm": "ဝါသနာကတော့ ဘာသာစကားလေ့လာခြင်း ဖြစ်ပါတယ်။"}
}

FIELDS = {
    "စိုက်ပျိုးရေး": {"jp": "農業", "mm": "စိုက်ပျိုးရေးလုပ်ငန်း"},
    "သက်ကြီးစောင့်ရှောက်ရေး (Kaigo)": {"jp": "介護", "mm": "သက်ကြီးရွယ်အိုစောင့်ရှောက်ရေးလုပ်ငန်း"},
    "စားသောက်ဆိုင် (Gaishoku)": {"jp": "外食産業", "mm": "စားသောက်ဆိုင်လုပ်ငန်း"},
    "အစားအသောက်ထုတ်လုပ်ရေး": {"jp": "飲食料品製造業", "mm": "အစားအသောက်ထုတ်လုပ်ရေးလုပ်ငန်း"},
    "ဆောက်လုပ်ရေး": {"jp": "建設業", "mm": "ဆောက်လုပ်ရေးလုပ်ငန်း"},
    "ဟိုတယ်လုပ်ငန်း (Shukuhaku)": {"jp": "宿泊業", "mm": "ဟိုတယ်လုပ်ငန်း"},
    "အဆောက်အအုံသန့်ရှင်းရေး (Birukuri)": {"jp": "ビルクリーニング", "mm": "အဆောက်အအုံသန့်ရှင်းရေးလုပ်ငန်း"}
}

# --- 1. Start & Admin Alert ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user = message.from_user
        alert_msg = (
            "👤 **ကျောင်းသားအသစ် ရောက်ရှိလာပါပြီ**\n\n"
            f"🏷 နာမည်: {user.first_name} {user.last_name if user.last_name else ''}\n"
            f"🆔 User ID: `{user.id}`\n"
            f"🔗 Username: @{user.username if user.username else 'မရှိပါ'}"
        )
        bot.send_message(ADMIN_ID, alert_msg, parse_mode="Markdown")
    except:
        pass
    
    welcome_text = "🎉 မင်္ဂလာပါ၊ **J.F.Y MYANMAR** မှ ကြိုဆိုပါတယ်။ မိမိကိုယ်ကိုယ်မိတ်ဆက်နည်း ရေးပေးရမလားခင်ဗျာ✨"
    show_main_menu(message.chat.id, welcome_text)

def show_main_menu(chat_id, text):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("📝 Jikoshokai ဖန်တီးမယ် / ပြင်မယ်", "📢 Main channel ကို join မယ်", "💬 သင်တန်းစုံစမ်းမယ်")
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ["📝 Jikoshokai ဖန်တီးမယ် / ပြင်မယ်", "📢 Main channel ကို join မယ်", "💬 သင်တန်းစုံစမ်းမယ်", "🏠 ပင်မစာမျက်နှာသို့", "Short Version", "Long Version"])
def handle_main_menu(message):
    chat_id = message.chat.id
    text = message.text

    if text == "📢 Main channel ကို join မယ်":
        bot.send_message(chat_id, "👉 https://t.me/jfytokuteiquiz")
    elif text == "💬 သင်တန်းစုံစမ်းမယ်":
        bot.send_message(chat_id, "👉 @kyawzinhtun0070")
    elif text == "🏠 ပင်မစာမျက်နှာသို့":
        show_main_menu(chat_id, "🏠 ပင်မစာမျက်နှာသို့ ပြန်ရောက်ပါပြီ။")
    elif text == "📝 Jikoshokai ဖန်တီးမယ် / ပြင်မယ်":
        if chat_id not in user_data:
            user_data[chat_id] = {}
        ask_name(chat_id)
    elif text in ["Short Version", "Long Version"]:
        if chat_id in user_data and 'field' in user_data[chat_id]:
            generate_result(chat_id, text)
        else:
            bot.send_message(chat_id, "⚠️ အချက်အလက်များ မဖြည့်ရသေးပါ။ ကျေးဇူးပြု၍ '📝 Jikoshokai ဖန်တီးမယ်' ကို အရင်နှိပ်ပါ။")

# --- 2. Information Gathering (Step-by-Step) ---
def ask_name(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    old_val = user_data[chat_id].get('name')
    if old_val:
        markup.add(SKIP_BTN)
        msg = f"၁။ သင့်နာမည် ဘယ်လိုခေါ်ပါသလဲ？ (ဥပမာ - Kyaw Kyaw)\n\n*(ယခင်: {old_val})*"
    else:
        markup = types.ReplyKeyboardRemove()
        msg = "၁။ သင့်နာမည် ဘယ်လိုခေါ်ပါသလဲ？ (ဥပမာ - Kyaw Kyaw)"
    bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler_by_chat_id(chat_id, process_name)

def process_name(message):
    chat_id = message.chat.id
    if message.text != SKIP_BTN:
        user_data[chat_id]['name'] = message.text
    ask_age(chat_id)

def ask_age(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    old_val = user_data[chat_id].get('age')
    if old_val:
        markup.add(SKIP_BTN)
        msg = f"၂။ အသက် ဘယ်လောက်ပါလဲ？ (ဥပမာ - 25)\n\n*(ယခင်: {old_val})*"
    else:
        markup = types.ReplyKeyboardRemove()
        msg = "၂။ အသက် ဘယ်လောက်ပါလဲ？ (ဥပမာ - 25)"
    bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler_by_chat_id(chat_id, process_age)

def process_age(message):
    chat_id = message.chat.id
    if message.text != SKIP_BTN:
        user_data[chat_id]['age'] = message.text
    ask_city(chat_id)

def ask_city(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    old_val = user_data[chat_id].get('city')
    if old_val:
        markup.add(SKIP_BTN)
        msg = f"၃။ မြန်မာနိုင်ငံရဲ့ ဘယ်မြို့မှာ နေထိုင်ပါသလဲ？ (ဥပမာ - Yangon)\n\n*(ယခင်: {old_val})*"
    else:
        markup = types.ReplyKeyboardRemove()
        msg = "၃။ မြန်မာနိုင်ငံရဲ့ ဘယ်မြို့မှာ နေထိုင်ပါသလဲ？ (ဥပမာ - Yangon)"
    bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler_by_chat_id(chat_id, process_city)

def process_city(message):
    chat_id = message.chat.id
    if message.text != SKIP_BTN:
        user_data[chat_id]['city'] = message.text
    ask_level(chat_id)

def ask_level(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    buttons = list(LEVELS.keys())
    if user_data[chat_id].get('level'): buttons.insert(0, SKIP_BTN)
    markup.add(*buttons)
    bot.send_message(chat_id, "၄။ လက်ရှိ ဂျပန်စာ Level ကို ရွေးပေးပါ👇", reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, process_level)

def process_level(message):
    chat_id = message.chat.id
    if message.text in LEVELS:
        user_data[chat_id]['level'] = message.text
    ask_hobby(chat_id)

def ask_hobby(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = list(HOBBIES.keys())
    if user_data[chat_id].get('hobby'): markup.add(SKIP_BTN)
    markup.add(*buttons)
    bot.send_message(chat_id, "၅။ သင့်ရဲ့ ဝါသနာကို ရွေးပေးပါ👇", reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, process_hobby)

def process_hobby(message):
    chat_id = message.chat.id
    if message.text in HOBBIES:
        user_data[chat_id]['hobby'] = message.text
    ask_field(chat_id)

def ask_field(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = list(FIELDS.keys())
    if user_data[chat_id].get('field'): markup.add(SKIP_BTN)
    markup.add(*buttons)
    bot.send_message(chat_id, "၆။ သွားရောက်လုပ်ကိုင်မည့် အလုပ်အမျိုးအစားကို ရွေးပေးပါ👇", reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(chat_id, process_field)

def process_field(message):
    chat_id = message.chat.id
    if message.text in FIELDS:
        user_data[chat_id]['field'] = message.text
    ask_version(chat_id)

def ask_version(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Short Version", "Long Version")
    bot.send_message(chat_id, "✅ အချက်အလက်များ ပြည့်စုံသွားပါပြီ။ မည်သည့် Version ကို လိုချင်ပါသလဲ？👇", reply_markup=markup)

# --- 3. Final Result ---
def generate_result(chat_id, version):
    data = user_data.get(chat_id, {})
    n, a, c = data.get('name',''), data.get('age',''), data.get('city','')
    l_jp = LEVELS.get(data.get('level'), {}).get('jp', '')
    l_mm = LEVELS.get(data.get('level'), {}).get('mm', '')
    h_jp = HOBBIES.get(data.get('hobby'), {}).get('jp', '')
    h_mm = HOBBIES.get(data.get('hobby'), {}).get('mm', '')
    f_jp = FIELDS.get(data.get('field'), {}).get('jp', '')
    f_mm = FIELDS.get(data.get('field'), {}).get('mm', '')

    if version == "Short Version":
        res = f"📝 **Short Version (အမြန်မိတ်ဆက်ခြင်း)**\n━━━━━━━━━━━━━━━━━━━━━\n\n🇯🇵 **日本語**\nはじめまして。✨\n{n}と申します।👤\n年齢は{a}歳です।🎂\nミャンマーの{c}に住んでいます।🇲🇲\nどうぞよろしくお願いいたします।🙇‍♂️\n\n🇲🇲 **မြန်မာအဓိပ္ပာယ်**\nတွေ့ရတာ ဝမ်းသာပါတယ်။ ကျွန်တော်ကတော့ {n} လို့ ခေါ်ပါတယ်။ အသက် {a} နှစ်ဖြစ်ပြီး {c} မြို့မှာ နေထိုင်ပါတယ်။"
    else:
        res = f"📝 **Long Version (အပြည့်အစုံမိတ်ဆက်ခြင်း)**\n━━━━━━━━━━━━━━━━━━━━━\n\n🇯🇵 **日本語**\nはじめまして।✨\n{n}と申します।👤\n年齢は{a}歳です।🎂\nミャンマーの{c}に住んでいます।🇲🇲\n{l_jp} 🎓\n{h_jp} 🎬\n日本の高い技術を学びたいと思い、{f_jp}に興味を持っています।🌱\n本日は面接の機会をいただき、誠にありがとうございます।🙏\n採用していただきましたら၊ 一生懸命頑張ります।💪\nどうぞよろしくお願いいたします।🙇‍♂️\n\n🇲🇲 **မြန်မာအဓိပ္ပာယ်**\n{l_mm} {h_mm} ဂျပန်ရဲ့ {f_mm} ကို စိတ်ဝင်စားပါတယ်။ အင်တာဗျူးခွင့်ရလို့ ကျေးဇူးတင်ပါတယ်။ အစွမ်းကုန် ကြိုးစားပါမယ်။"

    bot.send_message(chat_id, res, parse_mode="Markdown")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Long Version" if version == "Short Version" else "Short Version", "📝 Jikoshokai ဖန်တီးမယ် / ပြင်မယ်", "🏠 ပင်မစာမျက်နှာသို့")
    bot.send_message(chat_id, "👇 အောက်ပါခလုတ်များကို အသုံးပြုနိုင်ပါတယ်။", reply_markup=markup)

if __name__ == "__main__":
    bot.infinity_polling()
