import os
import telebot
from telebot import types

# Koyeb ကနေ Token ကို လှမ်းယူမယ့်အပိုင်း
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# ယာယီ Data သိမ်းရန် Dictionary
user_data = {}

# ရွေးချယ်စရာ Dictionaries များ (Combination အတွက်)
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
    "အားကစားလုပ်ခြင်း": {"jp": "趣味はスポーツをすることです。", "mm": "ဝါသနာကတော့ အားကစားလုပ်ခြင်း ဖြစ်ပါတယ်။"}
}

FIELDS = {
    "စိုက်ပျိုးရေး": {"jp": "農業", "mm": "စိုက်ပျိုးရေးလုပ်ငန်း"},
    "သက်ကြီးစောင့်ရှောက်ရေး (Kaigo)": {"jp": "介護", "mm": "သက်ကြီးရွယ်အိုစောင့်ရှောက်ရေးလုပ်ငန်း"},
    "စားသောက်ဆိုင် (Gaisyoku)": {"jp": "外食産業", "mm": "စားသောက်ဆိုင်လုပ်ငန်း"},
    "အစားအသောက်ထုတ်လုပ်ရေး": {"jp": "飲食料品製造業", "mm": "အစားအသောက်ထုတ်လုပ်ရေးလုပ်ငန်း"},
    "ဆောက်လုပ်ရေး": {"jp": "建設業", "mm": "ဆောက်လုပ်ရေးလုပ်ငန်း"}
}

# 1. /start Command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn1 = types.KeyboardButton("📝 Jikoshokai အသစ်ဖန်တီးမယ်")
    btn2 = types.KeyboardButton("📢 Main channel ကို join မယ်")
    btn3 = types.KeyboardButton("💬 သင်တန်းစုံစမ်းမယ်")
    markup.add(btn1, btn2, btn3)
    
    welcome_text = (
        "🎉 မင်္ဂလာပါ၊ **J.F.Y JIKOSHOKAI FOR YOU** Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "မိမိအချက်အလက်များကို ဖြည့်သွင်းပြီး အင်တာဗျူးအတွက် Jikoshokai ကို အလွယ်တကူ ဖန်တီးနိုင်ပါတယ်။ 👇"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# 2. Main Menu ခလုတ်များ နှိပ်လျှင်
@bot.message_handler(func=lambda message: message.text in ["📝 Jikoshokai အသစ်ဖန်တီးမယ်", "📢 Main channel ကို join မယ်", "💬 သင်တန်းစုံစမ်းမယ်"])
def handle_main_menu(message):
    if message.text == "📢 Main channel ကို join မယ်":
        bot.send_message(message.chat.id, "👉 https://t.me/japaneseforyoumyanmar")
    elif message.text == "💬 သင်တန်းစုံစမ်းမယ်":
        bot.send_message(message.chat.id, "👉 @kyawzinhtun0070")
    elif message.text == "📝 Jikoshokai အသစ်ဖန်တီးမယ်":
        user_data[message.chat.id] = {} # Data အဟောင်းများဖျက်ရန်
        markup = types.ReplyKeyboardRemove() # Keyboard ခဏဖျောက်ထားရန်
        bot.send_message(message.chat.id, "၁။ သင့်နာမည် ဘယ်လိုခေါ်ပါသလဲခင်ဗျာ？ (ဥပမာ - Kyaw Kyaw)", reply_markup=markup)
        bot.register_next_step_handler(message, get_name)

# 3. အချက်အလက်များ တစ်ဆင့်ချင်းစီ တောင်းခံခြင်း
def get_name(message):
    user_data[message.chat.id]['name'] = message.text
    bot.send_message(message.chat.id, "၂။ အသက် ဘယ်လောက်ပါလဲ？ (ဥပမာ - 25)")
    bot.register_next_step_handler(message, get_age)

def get_age(message):
    user_data[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "၃။ မြန်မာနိုင်ငံရဲ့ ဘယ်မြို့မှာ နေထိုင်ပါသလဲ？ (ဥပမာ - Yangon)")
    bot.register_next_step_handler(message, get_city)

def get_city(message):
    user_data[message.chat.id]['city'] = message.text
    
    # Level ရွေးရန် ခလုတ်များပြခြင်း
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(*LEVELS.keys())
    bot.send_message(message.chat.id, "၄။ လက်ရှိ ဂျပန်စာ အရည်အချင်း (Level) ကို ရွေးပေးပါ👇", reply_markup=markup)
    bot.register_next_step_handler(message, get_level)

def get_level(message):
    if message.text not in LEVELS:
        bot.send_message(message.chat.id, "ကျေးဇူးပြု၍ အောက်ပါခလုတ်ကိုသာ နှိပ်ပေးပါ။")
        bot.register_next_step_handler(message, get_level)
        return
        
    user_data[message.chat.id]['level'] = message.text
    
    # Hobby ရွေးရန် ခလုတ်များပြခြင်း
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(*HOBBIES.keys())
    bot.send_message(message.chat.id, "၅။ သင့်ရဲ့ ဝါသနာကို ရွေးပေးပါ👇", reply_markup=markup)
    bot.register_next_step_handler(message, get_hobby)

def get_hobby(message):
    if message.text not in HOBBIES:
        bot.send_message(message.chat.id, "ကျေးဇူးပြု၍ အောက်ပါခလုတ်ကိုသာ နှိပ်ပေးပါ။")
        bot.register_next_step_handler(message, get_hobby)
        return
        
    user_data[message.chat.id]['hobby'] = message.text
    
    # Field ရွေးရန် ခလုတ်များပြခြင်း
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(*FIELDS.keys())
    bot.send_message(message.chat.id, "၆။ သင်သွားရောက်လုပ်ကိုင်မည့် အလုပ်အမျိုးအစားကို ရွေးပေးပါ👇", reply_markup=markup)
    bot.register_next_step_handler(message, get_field)

def get_field(message):
    if message.text not in FIELDS:
        bot.send_message(message.chat.id, "ကျေးဇူးပြု၍ အောက်ပါခလုတ်ကိုသာ နှိပ်ပေးပါ။")
        bot.register_next_step_handler(message, get_field)
        return
        
    user_data[message.chat.id]['field'] = message.text
    
    # Version ရွေးရန်
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Short Version", "Long Version")
    bot.send_message(message.chat.id, "✅ အချက်အလက်များ ပြည့်စုံသွားပါပြီ။ မည်သည့် Version ကို လိုချင်ပါသလဲ？👇", reply_markup=markup)
    bot.register_next_step_handler(message, generate_result)

# 4. နောက်ဆုံးရလဒ် (Result) ထုတ်ပေးခြင်း
def generate_result(message):
    chat_id = message.chat.id
    if message.text not in ["Short Version", "Long Version"]:
        bot.send_message(chat_id, "ကျေးဇူးပြု၍ 'Short Version' သို့မဟုတ် 'Long Version' ခလုတ်ကို နှိပ်ပါ။")
        bot.register_next_step_handler(message, generate_result)
        return

    data = user_data.get(chat_id, {})
    
    name = data.get('name', '')
    age = data.get('age', '')
    city = data.get('city', '')
    
    level_jp = LEVELS[data['level']]['jp']
    level_mm = LEVELS[data['level']]['mm']
    
    hobby_jp = HOBBIES[data['hobby']]['jp']
    hobby_mm = HOBBIES[data['hobby']]['mm']
    
    field_jp = FIELDS[data['field']]['jp']
    field_mm = FIELDS[data['field']]['mm']

    if message.text == "Short Version":
        result_text = f"""📝 **Short Version (အမြန်မိတ်ဆက်ခြင်း)**
━━━━━━━━━━━━━━━━━━━━━

🇯🇵 **日本語**
はじめまして。✨
{name}と申します。👤
年齢は{age}歳です。🎂
ミャンマーの{city}に住んでいます。🇲🇲
どうぞよろしくお願いいたします。🙇‍♂️

🇲🇲 **မြန်မာအဓိပ္ပာယ်**
တွေ့ရတာ ဝမ်းသာပါတယ်။ ✨
ကျွန်တော်/ကျွန်မကတော့ {name} လို့ ခေါ်ပါတယ်။ 👤
အသက်ကတော့ {age} နှစ် ဖြစ်ပါတယ်။ 🎂
မြန်မာနိုင်ငံ၊ {city} မှာ နေထိုင်ပါတယ်။ 🇲🇲
ရှေ့ဆက်ပြီး ကူညီစောင့်ရှောက်ပေးဖို့ တောင်းဆိုအပ်ပါတယ်။ 🙇‍♂️"""

    else:
        result_text = f"""📝 **Long Version (အပြည့်အစုံမိတ်ဆက်ခြင်း)**
━━━━━━━━━━━━━━━━━━━━━

🇯🇵 **日本語**
はじめまして。✨
{name}と申します。👤
年齢は{age}歳です。🎂
ミャンマーの{city}に住んでいます。🇲🇲
{level_jp} 🎓
{hobby_jp} 🎬
日本の高い技術を学びたいと思い、{field_jp}に興味を持っています。🌱
本日は面接の機会をいただき、誠にありがとうございます。🙏
採用していただきましたら、一生懸命頑張ります。💪
どうぞよろしくお願いいたします。🙇‍♂️

🇲🇲 **မြန်မာအဓိပ္ပာယ်**
တွေ့ရတာ ဝမ်းသာပါတယ်။ ✨
ကျွန်တော်/ကျွန်မကတော့ {name} လို့ ခေါ်ပါတယ်။ 👤
အသက်ကတော့ {age} နှစ် ဖြစ်ပါတယ်။ 🎂
မြန်မာနိုင်ငံ၊ {city} မှာ နေထိုင်ပါတယ်။ 🇲🇲
{level_mm} 🎓
{hobby_mm} 🎬
ဂျပန်ရဲ့ အဆင့်မြင့်နည်းပညာတွေကို သင်ယူချင်တဲ့အတွက် {field_mm} ကို စိတ်ဝင်စားပါတယ်။ 🌱
ဒီနေ့ အင်တာဗျူး ဖြေဆိုခွင့်ရတဲ့အတွက် ကျေးဇူးအများကြီးတင်ပါတယ်။ 🙏
အလုပ်ရွေးချယ်ခံရရင် အစွမ်းကုန် ကြိုးစားသွားပါမယ်။ 💪
ကူညီစောင့်ရှောက်ပေးဖို့ တောင်းဆိုအပ်ပါတယ်။ 🙇‍♂️"""

    # ပြန်လည်စတင်ရန် Main Menu ခလုတ်များပြန်ခေါ်ခြင်း
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("📝 Jikoshokai အသစ်ဖန်တီးမယ်", "📢 Main channel ကို join မယ်", "💬 သင်တန်းစုံစမ်းမယ်")
    
    bot.send_message(chat_id, result_text, parse_mode="Markdown")
    bot.send_message(chat_id, "အခြားလိုအပ်သည်များ ရှိပါက အောက်ပါ Menu မှ ထပ်မံရွေးချယ်နိုင်ပါတယ်ခင်ဗျာ 👇", reply_markup=markup)

if __name__ == "__main__":
    bot.infinity_polling()
