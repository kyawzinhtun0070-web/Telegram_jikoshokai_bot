import telebot
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton

# 🔑 Bot Tokens & IDs
TOKEN = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID = -1003641016541
CHANNEL_LINK = "https://t.me/yayzatofficial"

# ⚠️ အောက်က 123456789 နေရာမှာ မိတ်ဆွေရဲ့ Telegram ID ပြောင်းထည့်ရန် မမေ့ပါနဲ့!
ADMIN_ID = 8101049053 

bot = telebot.TeleBot(TOKEN)
DB_FILE = 'users_db.json'

# --- Database Load/Save ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return {int(k): v for k, v in json.load(f).items()}
    return {}

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_db, f, ensure_ascii=False, indent=4)

users_db = load_db()
user_registration = {}

# --- Persistent Menu Buttons ---
def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🔍 ဖူးစာရှာမည်"), KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    return markup

def check_channel(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

# --- Registration Flow (With Skip Logic) ---
@bot.message_handler(commands=['start'])
def start_bot(message):
    user_id = message.chat.id
    if user_id in users_db:
        bot.send_message(user_id, "✨ ရေစက်ရှာဖွေဖို့ အသင့်ပါပဲ! အောက်ပါ Menu ကိုသုံးပါ။", reply_markup=main_menu_keyboard())
        return
        
    user_registration[user_id] = {}
    user_count = len(users_db)
    greeting = f"✨ *Yay Zat Zodiac မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်!* ✨\n\n📊 လက်ရှိအသုံးပြုသူ: {user_count} ယောက်\n\nသင်နဲ့ ရေစက်ပါတဲ့ ဖူးစာရှင်ကို ရှာဖွေဖို့ အောက်က မေးခွန်းလေးတွေကို ဖြေပေးပါနော်။\n\nသင့်ရဲ့ *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ (မပြင်လိုပါက /skip ဟုရိုက်ပါ)-"
    bot.send_message(user_id, greeting, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_name)

def process_name(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['name'] = message.text
    bot.send_message(user_id, "အသက် ဘယ်လောက်လဲဗျ? (မပြင်လိုပါက /skip)-")
    bot.register_next_step_handler(message, process_age)

def process_age(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['age'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    zodiacs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces', '/skip']
    for z in zodiacs: markup.add(z)
    bot.send_message(user_id, "သင့်ရဲ့ ရာသီခွင်ကို ရွေးချယ်ပါ-", reply_markup=markup)
    bot.register_next_step_handler(message, process_zodiac)

def process_zodiac(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['zodiac'] = message.text
    bot.send_message(user_id, "နေထိုင်တဲ့ မြို့ကို ရိုက်ထည့်ပါ (ဥပမာ - Mandalay) (မပြင်လိုပါက /skip)-", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_city)

def process_city(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['city'] = message.text
    bot.send_message(user_id, "ဝါသနာ ဘာပါလဲ? (ဥပမာ - ခရီးသွား၊ ဂီတ) (မပြင်လိုပါက /skip)-")
    bot.register_next_step_handler(message, process_hobby)

def process_hobby(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['hobby'] = message.text
    bot.send_message(user_id, "အလုပ်အကိုင် ဘာလုပ်ပါသလဲ? (မပြင်လိုပါက /skip)-")
    bot.register_next_step_handler(message, process_job)

def process_job(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['job'] = message.text
    bot.send_message(user_id, "အကြိုက်ဆုံး သီချင်း တစ်ပုဒ်လောက် ပြောပြပါ? 🎵 (မပြင်လိုပါက /skip)-")
    bot.register_next_step_handler(message, process_song)

def process_song(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['song'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Male', 'Female', '/skip')
    bot.send_message(user_id, "သင့်လိင်အမျိုးအစားကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(message, process_gender)

def process_gender(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['gender'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Male', 'Female', 'Both', '/skip')
    bot.send_message(user_id, "သင်ရှာဖွေနေတဲ့ လိင်အမျိုးအစားကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(message, process_looking_gender)

def process_looking_gender(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['looking_gender'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    zodiacs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces', 'Any', '/skip']
    for z in zodiacs: markup.add(z)
    bot.send_message(user_id, "သင်ရှာဖွေနေတဲ့ ရာသီခွင်ကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(message, process_looking_zodiac)

def process_looking_zodiac(message):
    user_id = message.chat.id
    if message.text != '/skip': user_registration[user_id]['looking_zodiac'] = message.text
    bot.send_message(user_id, "နောက်ဆုံးအနေနဲ့ သင့်ရဲ့ ဓာတ်ပုံတစ်ပုံ (Profile Picture) ကို ပေးပို့ပါ 📸 (မပြင်လိုပါက /skip ဟုရိုက်ပါ)-", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_photo)

def process_photo(message):
    user_id = message.chat.id
    if message.text != '/skip':
        if message.content_type != 'photo':
            bot.send_message(user_id, "ကျေးဇူးပြု၍ ဓာတ်ပုံသာ ပေးပို့ပါ။ အစကပြန်စရန် /start ကိုနှိပ်ပါ။")
            return
        user_registration[user_id]['photo'] = message.photo[-1].file_id
        
    users_db[user_id] = user_registration[user_id]
    save_db() # သိမ်းဆည်းခြင်း
    
    bot.send_message(user_id, "✅ ပရိုဖိုင် အောင်မြင်စွာ တည်ဆောက်/ပြင်ဆင် ပြီးပါပြီ!\n\nအောက်က ခလုတ်များကို နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇", reply_markup=main_menu_keyboard())

# --- Menu Handler ---
@bot.message_handler(func=lambda message: message.text in ["🔍 ဖူးစာရှာမည်", "👤 ကိုယ့်ပရိုဖိုင်"])
def handle_menu_buttons(message):
    if message.text == "🔍 ဖူးစာရှာမည်":
        find_match(message)
    elif message.text == "👤 ကိုယ့်ပရိုဖိုင်":
        my_profile(message)

# --- Profile View & Edit ---
@bot.message_handler(commands=['myprofile'])
def my_profile(message):
    user_id = message.chat.id
    if user_id not in users_db:
        bot.send_message(user_id, "ပရိုဖိုင် မရှိသေးပါ။ /start ကိုနှိပ်ပါ။")
        return
    
    tp = users_db[user_id]
    user_count = len(users_db)
    song = tp.get('song', 'မဖြည့်ရသေးပါ') # အဟောင်းတွေအတွက် Fallback
    
    profile_text = f"📊 လက်ရှိ ရေစက်ရှာဖွေနေသူပေါင်း: {user_count} ယောက်\n\n👤 *သင့်ရဲ့ ပရိုဖိုင်*\n\nနာမည်: {tp['name']} ({tp['age']} နှစ်)\nရာသီခွင်: {tp['zodiac']}\nမြို့: {tp['city']}\nဝါသနာ: {tp['hobby']}\n💼 အလုပ်အကိုင်: {tp['job']}\n🎵 အကြိုက်ဆုံး သီချင်း: {song}\nရှာဖွေနေသည်: {tp['looking_gender']} ({tp['looking_zodiac']})"
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("📝 နာမည်ပြင်မည်", callback_data="edit_name"), InlineKeyboardButton("📍 မြို့ပြင်မည်", callback_data="edit_city"))
    markup.row(InlineKeyboardButton("🎵 သီချင်းပြင်မည်", callback_data="edit_song"), InlineKeyboardButton("📸 ဓာတ်ပုံပြင်မည်", callback_data="edit_photo"))
    markup.row(InlineKeyboardButton("🔄 အကုန်ပြန်လုပ်မည်", callback_data="edit_all"))
    
    if 'photo' in tp:
        bot.send_photo(user_id, photo=tp['photo'], caption=profile_text, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(user_id, profile_text, reply_markup=markup, parse_mode="Markdown")

def save_single_edit(message, field):
    user_id = message.chat.id
    if field == 'photo':
        if message.content_type != 'photo':
            bot.send_message(user_id, "⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။")
            return
        users_db[user_id]['photo'] = message.photo[-1].file_id
    else:
        users_db[user_id][field] = message.text
        
    save_db() 
    bot.send_message(user_id, "✅ ပြင်ဆင်မှု အောင်မြင်ပါသည်။ အောက်ပါ Menu မှတဆင့် ဆက်လက်အသုံးပြုပါ။", reply_markup=main_menu_keyboard())

# --- Match Logic ---
@bot.message_handler(commands=['match'])
def find_match(message):
    user_id = message.chat.id
    
    if user_id not in users_db:
        bot.send_message(user_id, "/start ကိုနှိပ်ပြီး ပရိုဖိုင် အရင်တည်ဆောက်ပါ။")
        return
    
    if not check_channel(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 Channel ကို Join ပါ", url=CHANNEL_LINK))
        bot.send_message(user_id, "⚠️ ဖူးစာရှာရန်အတွက် ကျေးဇူးပြု၍ ကျွန်ုပ်တို့ရဲ့ Channel ကို အရင် Join ပေးပါ။", reply_markup=markup)
        return

    user_data = users_db[user_id]
    user_city = user_data['city'].lower()
    
    candidates = []
    for uid, data in users_db.items():
        if uid == user_id: continue
        if user_data['looking_gender'] != 'Both' and user_data['looking_gender'] != 'Any':
            if data['gender'] != user_data['looking_gender']:
                continue
        candidates.append((uid, data))
    
    if not candidates:
        bot.send_message(user_id, "😔 လောလောဆယ် သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ။ နောက်မှ ပြန်ကြိုးစားကြည့်ပါ။")
        return

    candidates.sort(key=lambda x: 0 if user_city in x[1]['city'].lower() or x[1]['city'].lower() in user_city else 1)
    
    target_id = candidates[0][0]
    tp = candidates[0][1]
    song = tp.get('song', 'မဖြည့်ရသေးပါ')
    
    profile_text = f"🎯 *မိတ်ဆွေနဲ့ ကိုက်ညီနိုင်မယ့်သူ*\n\n👤 {tp['name']}, {tp['age']} နှစ်\n🔮 ရာသီခွင်: {tp['zodiac']}\n📍 မြို့: {tp['city']}\n🎨 ဝါသနာ: {tp['hobby']}\n💼 အလုပ်အကိုင်: {tp['job']}\n🎵 သီချင်း: {song}"
    
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("❤️ Like", callback_data=f"like_{target_id}"), InlineKeyboardButton("⏭ Skip", callback_data="skip"))
    
    if 'photo' in tp:
        bot.send_photo(user_id, photo=tp['photo'], caption=profile_text, reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(user_id, profile_text, reply_markup=markup, parse_mode="Markdown")

# --- Callbacks Handler ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    
    if call.data.startswith("edit_"):
        field = call.data.split("_")[1]
        bot.delete_message(user_id, call.message.message_id)
        if field == "all":
            user_registration[user_id] = users_db[user_id].copy() # 🌟 အဟောင်းတွေကို ကြိုထည့်ထားပေးမည်
            bot.send_message(user_id, "ပရိုဖိုင် အသစ်ပြန်လုပ်ပါမည်။\n\nသင့်နာမည်ကို ရိုက်ထည့်ပါ- (မပြင်လိုပါက /skip ဟုရိုက်ပါ)", reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(call.message, process_name)
        elif field == "photo":
            msg = bot.send_message(user_id, "📸 ဓာတ်ပုံအသစ်ကို ပေးပို့ပါ-", reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_single_edit, field)
        else:
            msg = bot.send_message(user_id, f"📝 အချက်အလက်အသစ်ကို ရိုက်ထည့်ပါ-", reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_single_edit, field)

    elif call.data == "skip":
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(user_id, "ကျော်သွားပါပြီ။ အခြားသူကို ဆက်ရှာနေပါတယ်...")
        find_match(call.message)
        
    elif call.data.startswith("like_"):
        target_id = int(call.data.split("_")[1])
        if not check_channel(user_id):
            bot.answer_callback_query(call.id, "⚠️ ကျေးဇူးပြု၍ Channel ကို အရင် Join ပါ!", show_alert=True)
            return

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{user_id}"), InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline"))
        liker_name = users_db[user_id]['name']
        
        try:
            bot.send_message(target_id, f"🎉 သတင်းကောင်း! '{liker_name}' က သင့်ကို သဘောကျနေပါတယ်။ လက်ခံမလား?", reply_markup=markup)
            bot.send_message(user_id, "❤️ Like လုပ်လိုက်ပါပြီ! တစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ်။")
        except:
            bot.send_message(user_id, "⚠️ တစ်ဖက်လူမှာ Bot ကို Block ထားသဖြင့် ပို့၍မရပါ။")
        
    elif call.data.startswith("accept_"):
        liker_id = int(call.data.split("_")[1])
        
        # 🔔 Admin Notification (Admin ထံ သတင်းပို့ခြင်း)
        try:
            admin_noti = f"🔔 *New Match Alert!*\n\n[User 1](tg://user?id={user_id}) နှင့် [User 2](tg://user?id={liker_id}) တို့ Match ဖြစ်သွားပါပြီ! 💖"
            bot.send_message(ADMIN_ID, admin_noti, parse_mode="Markdown")
        except:
            pass

        bot.send_message(user_id, f"💖 *Match ဖြစ်သွားပါပြီ!*\n\nသူ့ရဲ့ Telegram အကောင့်ကို [ဒီမှာနှိပ်ပြီး](tg://user?id={liker_id}) စကားသွားပြောလို့ ရပါပြီ။", parse_mode="Markdown")
        try:
            bot.send_message(liker_id, f"💖 *Match ဖြစ်သွားပါပြီ!*\n\nသူ့ရဲ့ Telegram အကောင့်ကို [ဒီမှာနှိပ်ပြီး](tg://user?id={user_id}) စကားသွားပြောလို့ ရပါပြီ။", parse_mode="Markdown")
        except:
            pass
        bot.delete_message(user_id, call.message.message_id)

    elif call.data == "decline":
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(user_id, "❌ ပယ်ချလိုက်ပါပြီ။")

bot.polling(none_stop=True)
