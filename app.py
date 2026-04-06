import telebot
import json
import os
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)

# ═══════════════════════════════════════════════
# 🔑  Bot Config
# ═══════════════════════════════════════════════
TOKEN      = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID   = -1003641016541
CHANNEL_LINK = "https://t.me/yayzatofficial"
ADMIN_ID     = 6131831207

bot     = telebot.TeleBot(TOKEN)
DB_FILE = 'users_db.json'

# ═══════════════════════════════════════════════
# 💾  Database helpers
# ═══════════════════════════════════════════════
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return {int(k): v for k, v in json.load(f).items()}
    return {}

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_db, f, ensure_ascii=False, indent=4)

users_db        = load_db()
user_registration = {}   # registration temp state
seen_profiles   = {}     # { user_id: set(seen_uids) }  skip ဆွဲပြီးသားမှတ်
reported_users  = {}     # { reporter_id: set(reported_ids) }

# ═══════════════════════════════════════════════
# ⌨️  Keyboards
# ═══════════════════════════════════════════════
def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("🔍 ဖူးစာရှာမည်"),
        KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်")
    )
    markup.row(
        KeyboardButton("📊 စာရင်းအင်း"),
        KeyboardButton("ℹ️ အကူအညီ")
    )
    return markup

def admin_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("🔍 ဖူးစာရှာမည်"),
        KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်")
    )
    markup.row(
        KeyboardButton("📊 စာရင်းအင်း"),
        KeyboardButton("ℹ️ အကူအညီ")
    )
    markup.row(
        KeyboardButton("🛠 Admin Panel")
    )
    return markup

def get_keyboard(user_id):
    return admin_menu_keyboard() if user_id == ADMIN_ID else main_menu_keyboard()

# ═══════════════════════════════════════════════
# 🔧  Utilities
# ═══════════════════════════════════════════════
def check_channel(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except:
        return False

def notify_admin(text: str):
    """Admin ထံ notification ပေးပို့ (မအောင်မြင်ရင် ဆိတ်ဆိတ်နေ)"""
    try:
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except:
        pass

def safe(d: dict, key: str, fallback='မဖြည့်ရသေးပါ'):
    """KeyError မဖြစ်အောင် safe get"""
    val = d.get(key, '').strip() if isinstance(d.get(key), str) else d.get(key)
    return val if val else fallback

def format_profile(tp: dict, header='👤 *ပရိုဖိုင်*') -> str:
    return (
        f"{header}\n\n"
        f"📛 နာမည် : {safe(tp,'name')}\n"
        f"🎂 အသက်  : {safe(tp,'age')} နှစ်\n"
        f"🔮 ရာသီ  : {safe(tp,'zodiac')}\n"
        f"📍 မြို့   : {safe(tp,'city')}\n"
        f"🎨 ဝါသနာ : {safe(tp,'hobby')}\n"
        f"💼 အလုပ်  : {safe(tp,'job')}\n"
        f"🎵 သီချင်း : {safe(tp,'song')}\n"
        f"⚧ လိင်   : {safe(tp,'gender')}\n"
        f"💑 ရှာဖွေ  : {safe(tp,'looking_gender')} / {safe(tp,'looking_zodiac','Any')}"
    )

def get_stats_text() -> str:
    total     = len(users_db)
    with_photo = sum(1 for u in users_db.values() if u.get('photo'))
    male      = sum(1 for u in users_db.values() if u.get('gender') == 'Male')
    female    = sum(1 for u in users_db.values() if u.get('gender') == 'Female')
    return (
        f"📊 *Yay Zat Bot စာရင်းအင်း*\n\n"
        f"👥 စုစုပေါင်း အသုံးပြုသူ : *{total}* ယောက်\n"
        f"📸 ဓာတ်ပုံပါသော Profile   : {with_photo} ယောက်\n"
        f"♂️ ကျား                  : {male} ယောက်\n"
        f"♀️ မ                     : {female} ယောက်\n"
        f"⏰ နောက်ဆုံး Update      : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

# ═══════════════════════════════════════════════
# 🚀  /start  — Registration Flow
# ═══════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def start_bot(message):
    user_id    = message.chat.id
    user_count = len(users_db)

    # ── မှတ်ပုံတင်ပြီးသားဆိုရင် ────────────────
    if user_id in users_db:
        bot.send_message(
            user_id,
            f"✨ *ကြိုဆိုပါတယ်!* ✨\n\n"
            f"👥 လက်ရှိ အသုံးပြုသူ : *{user_count}* ယောက်\n\n"
            f"အောက်ပါ Menu ကိုသုံးနိုင်ပါပြီ 👇",
            parse_mode="Markdown",
            reply_markup=get_keyboard(user_id)
        )
        return

    # ── အသစ် ────────────────────────────────────
    # Admin notification
    try:
        tg_name = message.from_user.username or message.from_user.first_name or str(user_id)
    except:
        tg_name = str(user_id)

    notify_admin(
        f"🆕 *အသုံးပြုသူသစ် စတင်သုံးနေပါပြီ!*\n\n"
        f"👤 Name : {message.from_user.first_name or ''} {message.from_user.last_name or ''}\n"
        f"🔗 Username : @{tg_name}\n"
        f"🆔 ID : `{user_id}`\n"
        f"👥 စုစုပေါင်း (မှတ်ပုံတင်မပြီးသေး) : {user_count} ယောက်\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

    user_registration[user_id] = {}
    greeting = (
        f"✨ *Yay Zat Zodiac မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်!* ✨\n\n"
        f"👥 လက်ရှိ အသုံးပြုသူ : *{user_count}* ယောက်\n\n"
        f"သင်နဲ့ ရေစက်ပါတဲ့ ဖူးစာရှင်ကို ရှာဖွေဖို့\n"
        f"မေးခွန်းလေးတွေကို ဖြေပေးပါနော်။\n"
        f"_(မပြင်လိုသော မေးခွန်းများအတွက် /skip ရိုက်ပါ)_\n\n"
        f"📛 သင့်ရဲ့ *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-"
    )
    bot.send_message(user_id, greeting, parse_mode="Markdown",
                     reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_name)


# ── Registration steps ──────────────────────────
def process_name(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['name'] = message.text
    bot.send_message(user_id, "🎂 အသက် ဘယ်လောက်လဲဗျ? (/skip)-")
    bot.register_next_step_handler(message, process_age)

def process_age(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        if message.text.isdigit():
            user_registration[user_id]['age'] = message.text
        else:
            bot.send_message(user_id, "⚠️ ဂဏန်းသာ ရိုက်ထည့်ပါ (ဥပမာ 25)-")
            bot.register_next_step_handler(message, process_age)
            return

    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    zodiacs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
               'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces','/skip']
    for z in zodiacs:
        markup.add(z)
    bot.send_message(user_id, "🔮 သင့်ရဲ့ ရာသီခွင်ကို ရွေးချယ်ပါ-", reply_markup=markup)
    bot.register_next_step_handler(message, process_zodiac)

def process_zodiac(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['zodiac'] = message.text
    bot.send_message(user_id,
        "📍 နေထိုင်တဲ့ မြို့ကို ရိုက်ထည့်ပါ (ဥပမာ - Mandalay) (/skip)-",
        reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_city)

def process_city(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['city'] = message.text
    bot.send_message(user_id, "🎨 ဝါသနာ ဘာပါလဲ? (ဥပမာ - ခရီးသွား, ဂီတ) (/skip)-")
    bot.register_next_step_handler(message, process_hobby)

def process_hobby(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['hobby'] = message.text
    bot.send_message(user_id, "💼 အလုပ်အကိုင် ဘာလုပ်ပါသလဲ? (/skip)-")
    bot.register_next_step_handler(message, process_job)

def process_job(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['job'] = message.text
    bot.send_message(user_id, "🎵 အကြိုက်ဆုံး သီချင်း တစ်ပုဒ်လောက် ပြောပြပါ? (/skip)-")
    bot.register_next_step_handler(message, process_song)

def process_song(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['song'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Male', 'Female', '/skip')
    bot.send_message(user_id, "⚧ သင့်လိင်အမျိုးအစားကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(message, process_gender)

def process_gender(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['gender'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Male', 'Female', 'Both', '/skip')
    bot.send_message(user_id, "💑 သင်ရှာဖွေနေတဲ့ လိင်အမျိုးအစားကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(message, process_looking_gender)

def process_looking_gender(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['looking_gender'] = message.text
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    zodiacs = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra',
               'Scorpio','Sagittarius','Capricorn','Aquarius','Pisces','Any','/skip']
    for z in zodiacs:
        markup.add(z)
    bot.send_message(user_id, "🔮 သင်ရှာဖွေနေတဲ့ ရာသီခွင်ကို ရွေးပါ-", reply_markup=markup)
    bot.register_next_step_handler(message, process_looking_zodiac)

def process_looking_zodiac(message):
    user_id = message.chat.id
    if message.text and message.text != '/skip':
        user_registration[user_id]['looking_zodiac'] = message.text
    bot.send_message(
        user_id,
        "📸 သင့်ရဲ့ ဓာတ်ပုံတစ်ပုံ (Profile Picture) ကို ပေးပို့ပါ\n"
        "_(မပြင်လိုပါက /skip ဟုရိုက်ပါ)_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(message, process_photo)

def process_photo(message):
    user_id = message.chat.id
    if message.text == '/skip':
        pass  # ဓာတ်ပုံ မထည့်ဘဲ ကျော်
    elif message.content_type != 'photo':
        bot.send_message(user_id, "⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။ (/skip နဲ့ ကျော်လို့လည်းရသည်)")
        bot.register_next_step_handler(message, process_photo)
        return
    else:
        user_registration[user_id]['photo'] = message.photo[-1].file_id

    # ── Save ───────────────────────────────────
    is_new = user_id not in users_db
    users_db[user_id] = user_registration.pop(user_id, {})
    save_db()

    total = len(users_db)
    bot.send_message(
        user_id,
        f"✅ ပရိုဖိုင် အောင်မြင်စွာ {'တည်ဆောက်' if is_new else 'ပြင်ဆင်'} ပြီးပါပြီ!\n\n"
        f"👥 လက်ရှိ အသုံးပြုသူ : *{total}* ယောက်\n\n"
        f"အောက်က ခလုတ်များကို နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇",
        parse_mode="Markdown",
        reply_markup=get_keyboard(user_id)
    )

    # ── Admin noti (မှတ်ပုံတင်ပြီးမှ) ──────────
    if is_new:
        notify_admin(
            f"🎉 *မှတ်ပုံတင်ခြင်း ပြီးမြောက်ပါပြီ!*\n\n"
            f"🆔 ID : `{user_id}`\n"
            f"📛 နာမည် : {safe(users_db[user_id],'name')}\n"
            f"👥 စုစုပေါင်း : *{total}* ယောက်\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

# ═══════════════════════════════════════════════
# 📋  Profile View & Edit
# ═══════════════════════════════════════════════
@bot.message_handler(commands=['myprofile'])
@bot.message_handler(func=lambda m: m.text == "👤 ကိုယ့်ပရိုဖိုင်")
def my_profile(message):
    user_id = message.chat.id
    if user_id not in users_db:
        bot.send_message(user_id, "ပရိုဖိုင် မရှိသေးပါ။ /start ကိုနှိပ်ပါ။")
        return

    tp         = users_db[user_id]
    user_count = len(users_db)
    profile_text = (
        f"📊 လက်ရှိ ရေစက်ရှာဖွေနေသူပေါင်း: *{user_count}* ယောက်\n\n"
        + format_profile(tp)
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📛 နာမည်", callback_data="edit_name"),
        InlineKeyboardButton("🎂 အသက်",  callback_data="edit_age")
    )
    markup.row(
        InlineKeyboardButton("📍 မြို့",   callback_data="edit_city"),
        InlineKeyboardButton("🎨 ဝါသနာ", callback_data="edit_hobby")
    )
    markup.row(
        InlineKeyboardButton("💼 အလုပ်",  callback_data="edit_job"),
        InlineKeyboardButton("🎵 သီချင်း", callback_data="edit_song")
    )
    markup.row(
        InlineKeyboardButton("📸 ဓာတ်ပုံ", callback_data="edit_photo")
    )
    markup.row(
        InlineKeyboardButton("🔄 အကုန်ပြန်လုပ်မည်", callback_data="edit_all")
    )
    markup.row(
        InlineKeyboardButton("🗑 Profile ဖျက်မည်", callback_data="delete_profile")
    )

    if tp.get('photo'):
        bot.send_photo(user_id, photo=tp['photo'], caption=profile_text,
                       reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(user_id, profile_text, reply_markup=markup, parse_mode="Markdown")

# ── Single field edit save ──────────────────────
def save_single_edit(message, field):
    user_id = message.chat.id
    if field == 'photo':
        if message.content_type != 'photo':
            bot.send_message(user_id, "⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။")
            return
        users_db[user_id]['photo'] = message.photo[-1].file_id
    else:
        if not message.text or message.text.strip() == '':
            bot.send_message(user_id, "⚠️ ဗလာမထားပါနဲ့ ပြန်ရိုက်ထည့်ပါ-")
            bot.register_next_step_handler(message, save_single_edit, field)
            return
        users_db[user_id][field] = message.text.strip()

    save_db()
    bot.send_message(user_id,
        "✅ ပြင်ဆင်မှု အောင်မြင်ပါသည်!",
        reply_markup=get_keyboard(user_id))

# ═══════════════════════════════════════════════
# 📊  Stats
# ═══════════════════════════════════════════════
@bot.message_handler(commands=['stats'])
@bot.message_handler(func=lambda m: m.text == "📊 စာရင်းအင်း")
def stats_handler(message):
    bot.send_message(message.chat.id, get_stats_text(),
                     parse_mode="Markdown", reply_markup=get_keyboard(message.chat.id))

# ═══════════════════════════════════════════════
# ℹ️  Help
# ═══════════════════════════════════════════════
@bot.message_handler(commands=['help'])
@bot.message_handler(func=lambda m: m.text == "ℹ️ အကူအညီ")
def help_handler(message):
    text = (
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ဖူးစာရှာမည်* — သင်နဲ့ ကိုက်ညီနိုင်မယ့်သူများကို ရှာပါ\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
        "📊 *စာရင်းအင်း* — Bot သုံးစွဲသူ စာရင်းကြည့်ပါ\n\n"
        "📝 *Commands*\n"
        "/start — စတင်မှတ်ပုံတင်ပါ\n"
        "/myprofile — Profile ကြည့်ပါ\n"
        "/stats — စာရင်းအင်းကြည့်ပါ\n"
        "/reset — Profile ပြန်လုပ်ပါ\n"
        "/deleteprofile — Profile ဖျက်ပါ\n\n"
        "⚠️ မည်သည့်ပြဿနာမဆို Admin ကို ဆက်သွယ်ပါ။"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown",
                     reply_markup=get_keyboard(message.chat.id))

# ═══════════════════════════════════════════════
# 🔄  Reset / Delete Profile
# ═══════════════════════════════════════════════
@bot.message_handler(commands=['reset'])
def reset_profile(message):
    user_id = message.chat.id
    if user_id in users_db:
        user_registration[user_id] = users_db[user_id].copy()
    else:
        user_registration[user_id] = {}
    bot.send_message(
        user_id,
        "🔄 *Profile ပြန်လုပ်မည်*\n\n"
        "📛 နာမည် ရိုက်ထည့်ပါ- (/skip နဲ့ ကျော်နိုင်သည်)",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(message, process_name)

@bot.message_handler(commands=['deleteprofile'])
def delete_profile_cmd(message):
    user_id = message.chat.id
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ ဟုတ်တယ် ဖျက်မည်", callback_data="confirm_delete"),
        InlineKeyboardButton("❌ မဖျက်တော့ပါ",       callback_data="cancel_delete")
    )
    bot.send_message(user_id, "⚠️ Profile ကို အပြီးအပိုင် ဖျက်မှာ သေချာပါသလား?",
                     reply_markup=markup)

# ═══════════════════════════════════════════════
# 🔍  Match / Find
# ═══════════════════════════════════════════════
@bot.message_handler(commands=['match'])
@bot.message_handler(func=lambda m: m.text == "🔍 ဖူးစာရှာမည်")
def find_match(message):
    user_id = message.chat.id

    if user_id not in users_db:
        bot.send_message(user_id, "/start ကိုနှိပ်ပြီး Profile အရင်တည်ဆောက်ပါ။")
        return

    if not check_channel(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 Channel Join မည်", url=CHANNEL_LINK))
        bot.send_message(
            user_id,
            "⚠️ ဖူးစာရှာရန် ကျွန်ုပ်တို့ Channel ကို အရင် Join ပေးပါ။",
            reply_markup=markup
        )
        return

    user_data       = users_db[user_id]
    user_city       = safe(user_data, 'city', '').lower()
    looking_gender  = safe(user_data, 'looking_gender', '')
    looking_zodiac  = safe(user_data, 'looking_zodiac', 'Any')

    # ── seen list ──
    seen = seen_profiles.get(user_id, set())
    # ── reported list ──
    my_reports = reported_users.get(user_id, set())

    candidates = []
    for uid, data in users_db.items():
        if uid == user_id:             continue
        if uid in seen:                continue  # ပြပြီးသား ကျော်
        if uid in my_reports:          continue  # Report လုပ်ပြီးသား ကျော်

        # gender filter
        if looking_gender not in ('Both', 'Any', ''):
            if safe(data, 'gender', '') != looking_gender:
                continue

        # zodiac filter (Any ဆိုရင် အကုန်ကြည့်)
        if looking_zodiac not in ('Any', ''):
            if safe(data, 'zodiac', '') not in (looking_zodiac, ''):
                continue

        candidates.append((uid, data))

    # ── seen ကုန်ရင် reset ──
    if not candidates:
        if seen:
            seen_profiles[user_id] = set()
            bot.send_message(user_id,
                "🔄 ကြည့်ရှုပြီးသားသူများ ကုန်သွားသဖြင့် ပြန်စတင်ပါပြီ...\n"
                "ထပ်မံ ရှာဖွေပါ။")
            find_match(message)
        else:
            bot.send_message(user_id,
                "😔 လောလောဆယ် သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ။\n"
                "နောက်မှ ပြန်ကြိုးစားကြည့်ပါ။")
        return

    # ── Sort by city ──
    candidates.sort(key=lambda x:
        0 if user_city and (
            user_city in safe(x[1],'city','').lower() or
            safe(x[1],'city','').lower() in user_city
        ) else 1
    )

    target_id = candidates[0][0]
    tp        = candidates[0][1]

    # seen မှတ်
    seen_profiles.setdefault(user_id, set()).add(target_id)

    profile_text = (
        f"🎯 *မိတ်ဆွေနဲ့ ကိုက်ညီနိုင်မယ့်သူ*\n\n"
        + format_profile(tp, header='👤')
    )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("❤️ Like",        callback_data=f"like_{target_id}"),
        InlineKeyboardButton("⏭ Skip",         callback_data="skip"),
        InlineKeyboardButton("🚩 Report",      callback_data=f"report_{target_id}")
    )

    if tp.get('photo'):
        bot.send_photo(user_id, photo=tp['photo'], caption=profile_text,
                       reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(user_id, profile_text, reply_markup=markup, parse_mode="Markdown")

# ═══════════════════════════════════════════════
# 🛠  Admin Panel
# ═══════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel" and m.chat.id == ADMIN_ID)
def admin_panel(message):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📊 Full Stats",    callback_data="admin_stats"),
        InlineKeyboardButton("📢 Broadcast",     callback_data="admin_broadcast")
    )
    markup.row(
        InlineKeyboardButton("👥 User List",     callback_data="admin_userlist"),
        InlineKeyboardButton("🗑 User ဖျက်",     callback_data="admin_deleteuser")
    )
    bot.send_message(ADMIN_ID, "🛠 *Admin Panel*", parse_mode="Markdown", reply_markup=markup)

def admin_broadcast_send(message):
    if message.text == '/cancel':
        bot.send_message(ADMIN_ID, "ပယ်ဖျက်ပြီးပါပြီ။", reply_markup=get_keyboard(ADMIN_ID))
        return
    text    = message.text
    success = 0
    fail    = 0
    for uid in users_db:
        try:
            bot.send_message(uid, f"📢 *Admin မှ သတင်းစကား*\n\n{text}", parse_mode="Markdown")
            success += 1
        except:
            fail += 1
    bot.send_message(ADMIN_ID,
        f"✅ Broadcast ပြီးပါပြီ!\n✔️ အောင်မြင် : {success}\n❌ မရောက် : {fail}")

def admin_delete_user_step(message):
    if message.text == '/cancel':
        bot.send_message(ADMIN_ID, "ပယ်ဖျက်ပြီးပါပြီ။")
        return
    try:
        uid = int(message.text.strip())
        if uid in users_db:
            del users_db[uid]
            save_db()
            bot.send_message(ADMIN_ID, f"✅ User `{uid}` ကို ဖျက်လိုက်ပါပြီ။", parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, "⚠️ ထို User ID မတွေ့ပါ။")
    except ValueError:
        bot.send_message(ADMIN_ID, "⚠️ ID ဂဏန်းသာ ရိုက်ထည့်ပါ။")

# ═══════════════════════════════════════════════
# 📞  Callback Query Handler
# ═══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id

    # ── Profile Edit ───────────────────────────
    if call.data.startswith("edit_"):
        field = call.data.split("_", 1)[1]
        bot.delete_message(user_id, call.message.message_id)

        if field == "all":
            user_registration[user_id] = users_db.get(user_id, {}).copy()
            bot.send_message(
                user_id,
                "🔄 Profile ပြန်တည်ဆောက်မည်\n\n"
                "📛 နာမည် ရိုက်ထည့်ပါ- (/skip ကျော်နိုင်)",
                reply_markup=ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(call.message, process_name)

        elif field == "photo":
            msg = bot.send_message(user_id, "📸 ဓာတ်ပုံအသစ်ကို ပေးပို့ပါ-",
                                   reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_single_edit, field)

        elif field in ("name","age","city","hobby","job","song","zodiac",
                       "gender","looking_gender","looking_zodiac"):
            label_map = {
                'name':'နာမည်','age':'အသက်','city':'မြို့',
                'hobby':'ဝါသနာ','job':'အလုပ်','song':'သီချင်း',
                'zodiac':'ရာသီ','gender':'လိင်',
                'looking_gender':'ရှာဖွေမည့်လိင်','looking_zodiac':'ရှာဖွေမည့်ရာသီ'
            }
            msg = bot.send_message(user_id,
                f"📝 {label_map.get(field,field)} အသစ်ကို ရိုက်ထည့်ပါ-",
                reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_single_edit, field)

    # ── Delete Profile ─────────────────────────
    elif call.data == "delete_profile":
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ ဟုတ်တယ် ဖျက်မည်", callback_data="confirm_delete"),
            InlineKeyboardButton("❌ မဖျက်တော့ပါ",       callback_data="cancel_delete")
        )
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=markup)

    elif call.data == "confirm_delete":
        bot.delete_message(user_id, call.message.message_id)
        if user_id in users_db:
            del users_db[user_id]
            save_db()
        bot.send_message(user_id,
            "🗑 Profile ကို ဖျက်ပြီးပါပြီ။\n"
            "ပြန်မှတ်ပုံတင်လိုပါက /start ကိုနှိပ်ပါ။",
            reply_markup=ReplyKeyboardRemove())

    elif call.data == "cancel_delete":
        bot.answer_callback_query(call.id, "မဖျက်တော့ပါ။")
        bot.delete_message(user_id, call.message.message_id)

    # ── Skip ──────────────────────────────────
    elif call.data == "skip":
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(user_id, "⏭ ကျော်သွားပါပြီ...")
        find_match(call.message)

    # ── Like ──────────────────────────────────
    elif call.data.startswith("like_"):
        target_id = int(call.data.split("_")[1])
        bot.delete_message(user_id, call.message.message_id)

        if not check_channel(user_id):
            bot.answer_callback_query(call.id,
                "⚠️ Channel ကို အရင် Join ပါ!", show_alert=True)
            return

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{user_id}"),
            InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline")
        )
        liker_name = safe(users_db.get(user_id, {}), 'name', 'တစ်ယောက်')

        try:
            bot.send_message(
                target_id,
                f"🎉 *'{liker_name}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n"
                f"လက်ခံမလား? 💌",
                parse_mode="Markdown",
                reply_markup=markup
            )
            bot.send_message(user_id,
                "❤️ Like လုပ်လိုက်ပါပြီ!\n"
                "တစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ်။")
        except:
            bot.send_message(user_id,
                "⚠️ တစ်ဖက်လူမှာ Bot ကို Block ထားသဖြင့် ပေးပို့မရပါ။")

    # ── Accept ────────────────────────────────
    elif call.data.startswith("accept_"):
        liker_id = int(call.data.split("_")[1])
        bot.delete_message(user_id, call.message.message_id)

        notify_admin(
            f"💖 *New Match!*\n\n"
            f"[User A](tg://user?id={user_id}) နှင့် [User B](tg://user?id={liker_id})\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

        bot.send_message(
            user_id,
            f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
            f"[ဒီမှာနှိပ်ပြီး](tg://user?id={liker_id}) စကားပြောနိုင်ပါပြီ 🎉",
            parse_mode="Markdown"
        )
        try:
            bot.send_message(
                liker_id,
                f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
                f"[ဒီမှာနှိပ်ပြီး](tg://user?id={user_id}) စကားပြောနိုင်ပါပြီ 🎉",
                parse_mode="Markdown"
            )
        except:
            pass

    # ── Decline ───────────────────────────────
    elif call.data == "decline":
        bot.delete_message(user_id, call.message.message_id)
        bot.send_message(user_id, "❌ ငြင်းဆန်လိုက်ပါပြီ။")

    # ── Report ───────────────────────────────
    elif call.data.startswith("report_"):
        target_id = int(call.data.split("_")[1])
        reported_users.setdefault(user_id, set()).add(target_id)
        bot.answer_callback_query(call.id, "🚩 Report လုပ်ပြီးပါပြီ။ ကျေးဇူးတင်ပါသည်။",
                                  show_alert=True)
        bot.delete_message(user_id, call.message.message_id)
        # Admin ထံပို့
        reporter_name = safe(users_db.get(user_id,{}), 'name', str(user_id))
        target_name   = safe(users_db.get(target_id,{}), 'name', str(target_id))
        notify_admin(
            f"🚩 *User Report!*\n\n"
            f"Reporter : {reporter_name} (`{user_id}`)\n"
            f"Reported : {target_name} (`{target_id}`)\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

    # ── Admin callbacks ───────────────────────
    elif call.data == "admin_stats" and user_id == ADMIN_ID:
        bot.answer_callback_query(call.id)
        bot.send_message(ADMIN_ID, get_stats_text(), parse_mode="Markdown")

    elif call.data == "admin_broadcast" and user_id == ADMIN_ID:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID,
            "📢 ပေးပို့မည့် Message ကို ရိုက်ထည့်ပါ\n(/cancel — ပယ်ဖျက်)")
        bot.register_next_step_handler(msg, admin_broadcast_send)

    elif call.data == "admin_userlist" and user_id == ADMIN_ID:
        bot.answer_callback_query(call.id)
        lines = []
        for i, (uid, data) in enumerate(list(users_db.items())[:30], 1):
            lines.append(f"{i}. {safe(data,'name')} — `{uid}`")
        text = "👥 *User List (ပထမ 30)*\n\n" + "\n".join(lines) if lines else "User မရှိသေးပါ။"
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown")

    elif call.data == "admin_deleteuser" and user_id == ADMIN_ID:
        bot.answer_callback_query(call.id)
        msg = bot.send_message(ADMIN_ID,
            "🗑 ဖျက်မည့် User ID ကို ရိုက်ထည့်ပါ-\n(/cancel — ပယ်ဖျက်)")
        bot.register_next_step_handler(msg, admin_delete_user_step)

    # ── answer to avoid loading animation ─────
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

# ═══════════════════════════════════════════════
# 🚀  Polling
# ═══════════════════════════════════════════════
print("✅ Yay Zat Bot စတင်နေပါပြီ...")
bot.polling(none_stop=True)
