import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup

TOKEN = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_USERNAME = '@yayzatofficial'
bot = telebot.TeleBot(TOKEN)

users_db = {} 
user_registration = {}

def check_channel(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

@bot.message_handler(commands=['start'])
def start_bot(message):
    user_id = message.chat.id
    bot.send_message(user_id, "🌟 Yay Zat Zodiac မှ ကြိုဆိုပါတယ်။ သင့်ရဲ့ နာမည်ကို ရိုက်ထည့်ပါ-")
    bot.register_next_step_handler(message, process_name)

def process_name(message):
    user_id = message.chat.id
    user_registration[user_id] = {'name': message.text}
    bot.send_message(user_id, "အသက် ဘယ်လောက်လဲဗျ?")
    bot.register_next_step_handler(message, process_age)

def process_age(message):
    user_id = message.chat.id
    user_registration[user_id]['age'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    zodiacs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    for z in zodiacs: markup.add(z)
    msg = bot.send_message(user_id, "သင့်ရဲ့ ရာသီခွင်ကို ရွေးချယ်ပါ-", reply_markup=markup)
    bot.register_next_step_handler(msg, process_zodiac)

def process_zodiac(message):
    user_id = message.chat.id
    user_registration[user_id]['zodiac'] = message.text
    bot.send_message(user_id, "နေထိုင်တဲ့ မြို့ကို ရိုက်ထည့်ပါ-", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_city)

def process_city(message):
    user_id = message.chat.id
    user_registration[user_id]['city'] = message.text
    bot.send_message(user_id, "ဝါသနာ ဘာပါလဲ?")
    bot.register_next_step_handler(message, process_hobby)

def process_hobby(message):
    user_id = message.chat.id
    user_registration[user_id]['hobby'] = message.text
    bot.send_message(user_id, "အလုပ်အကိုင် ဘာလုပ်ပါသလဲ?")
    bot.register_next_step_handler(message, process_job)

def process_job(message):
    user_id = message.chat.id
    user_registration[user_id]['job'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Male', 'Female')
    msg = bot.send_message(user_id, "သင့်လိင်အမျိုးအစားကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(msg, process_gender)

def process_gender(message):
    user_id = message.chat.id
    user_registration[user_id]['gender'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Male', 'Female', 'Both')
    msg = bot.send_message(user_id, "သင်ရှာဖွေနေတဲ့ လိင်အမျိုးအစားကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(msg, process_looking_gender)

def process_looking_gender(message):
    user_id = message.chat.id
    user_registration[user_id]['looking_gender'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    zodiacs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces', 'Any']
    for z in zodiacs: markup.add(z)
    msg = bot.send_message(user_id, "သင်ရှာဖွေနေတဲ့ ရာသီခွင်ကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(msg, process_looking_zodiac)

def process_looking_zodiac(message):
    user_id = message.chat.id
    user_registration[user_id]['looking_zodiac'] = message.text
    users_db[user_id] = user_registration[user_id]
    bot.send_message(user_id, "✅ ပရိုဖိုင် အောင်မြင်ပါသည်။ /match ကို နှိပ်ပြီး ရှာဖွေနိုင်ပါပြီ။", reply_markup=telebot.types.ReplyKeyboardRemove())

@bot.message_handler(commands=['match'])
def find_match(message):
    user_id = message.chat.id
    if user_id not in users_db:
        bot.send_message(user_id, "/start ကိုနှိပ်ပြီး ပရိုဖိုင် အရင်တည်ဆောက်ပါ။")
        return
    target_id = next((uid for uid in users_db if uid != user_id), None)
    if not target_id:
        bot.send_message(user_id, "လောလောဆယ် ကိုက်ညီသူ မရှိသေးပါ။")
        return
    tp = users_db[target_id]
    profile_text = f"🔮 ရာသီခွင်: {tp['zodiac']}\n🎯 ရှာနေတာ: {tp['looking_zodiac']}\n👤 {tp['name']}, {tp['age']} နှစ်\n📍 {tp['city']}\n🎨 {tp['hobby']}\n💼 {tp['job']}"
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("❤️ Like", callback_data=f"like_{target_id}"), InlineKeyboardButton("⏭ Skip", callback_data="skip"))
    bot.send_message(user_id, profile_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    if call.data == "skip":
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(user_id, "ကျော်သွားပါပြီ။ /match ပြန်နှိပ်ပါ။")
    elif call.data.startswith("like_"):
        target_id = int(call.data.split("_")[1])
        bot.send_message(user_id, "❤️ Like လုပ်လိုက်ပါပြီ!")
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{user_id}"), InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline"))
        bot.send_message(target_id, f"🎉 {users_db[user_id]['zodiac']} က လူတစ်ယောက်က သင့်ကို သဘောကျနေပါတယ်။ လက်ခံမလား?", reply_markup=markup)
    elif call.data.startswith("accept_"):
        liker_id = int(call.data.split("_")[1])
        if not check_channel(user_id):
            bot.send_message(user_id, f"⚠️ Match ဖြစ်ဖို့ Channel Join ပါ -> {CHANNEL_USERNAME}")
            return
        bot.send_message(user_id, "✅ Match ဖြစ်သွားပါပြီ!")
        bot.send_message(liker_id, "💖 Match ဖြစ်သွားပါပြီ!")

bot.polling(none_stop=True)
