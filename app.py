import telebot
import sqlite3
import os
import time
import traceback
import threading
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)

# ═══════════════════════════════════════════════════════════════
# 🔑  CONFIG
# ═══════════════════════════════════════════════════════════════
TOKEN        = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID   = -1003641016541
CHANNEL_LINK = "https://t.me/yayzatofficial"
ADMIN_ID     = 6131831207
BOT_USERNAME = "YayZatBot"   # ← သင့် bot username ပြောင်းထည့်ပါ

bot = telebot.TeleBot(TOKEN)

# Share gate — ဘယ်နှစ်ယောက်ဖိတ်ကြားမှ match ရသည်
SHARE_REQUIRED = 7

ZODIACS = [
    'Aries','Taurus','Gemini','Cancer','Leo','Virgo',
    'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'
]

# ═══════════════════════════════════════════════════════════════
# 💾  SQLite — Thread-safe single connection
# ═══════════════════════════════════════════════════════════════
DB_FILE = 'yayzat.db'
_db_lock = threading.Lock()

def get_db():
    db = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    return db

_db = get_db()

def db_exec(sql, params=()):
    with _db_lock:
        try:
            cur = _db.execute(sql, params)
            _db.commit()
            return cur
        except sqlite3.OperationalError:
            # connection died — reconnect
            global _db
            _db = get_db()
            cur = _db.execute(sql, params)
            _db.commit()
            return cur

def db_query(sql, params=()):
    with _db_lock:
        try:
            return _db.execute(sql, params)
        except sqlite3.OperationalError:
            global _db
            _db = get_db()
            return _db.execute(sql, params)

def init_db():
    db_exec('''CREATE TABLE IF NOT EXISTS users (
        user_id        INTEGER PRIMARY KEY,
        name           TEXT,
        age            TEXT,
        zodiac         TEXT,
        city           TEXT,
        hobby          TEXT,
        job            TEXT,
        song           TEXT,
        bio            TEXT,
        gender         TEXT,
        looking_gender TEXT,
        looking_zodiac TEXT,
        looking_type   TEXT,
        photo          TEXT,
        share_unlocked INTEGER DEFAULT 0,
        created_at     TEXT DEFAULT (datetime('now','localtime')),
        updated_at     TEXT DEFAULT (datetime('now','localtime'))
    )''')
    db_exec('''CREATE TABLE IF NOT EXISTS seen (
        user_id INTEGER, seen_id INTEGER,
        PRIMARY KEY (user_id, seen_id)
    )''')
    db_exec('''CREATE TABLE IF NOT EXISTS reports (
        reporter_id INTEGER, reported_id INTEGER,
        reported_at TEXT DEFAULT (datetime('now','localtime')),
        PRIMARY KEY (reporter_id, reported_id)
    )''')
    db_exec('''CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER,
        referred_id INTEGER,
        joined      INTEGER DEFAULT 0,
        created_at  TEXT DEFAULT (datetime('now','localtime')),
        PRIMARY KEY (referrer_id, referred_id)
    )''')
    # future-proof: add missing columns safely
    existing = {r[1] for r in db_query("PRAGMA table_info(users)")}
    for col,typ in [
        ('bio','TEXT'),('song','TEXT'),('looking_type','TEXT'),
        ('share_unlocked','INTEGER DEFAULT 0')
    ]:
        col_name = col.split()[0]
        if col_name not in existing:
            try: db_exec(f"ALTER TABLE users ADD COLUMN {col_name} {typ}")
            except: pass

init_db()

# ── CRUD ──────────────────────────────────────────────────────
FIELDS = ['name','age','zodiac','city','hobby','job','song','bio',
          'gender','looking_gender','looking_zodiac','looking_type',
          'photo','share_unlocked']

def db_get(uid):
    row = db_query('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone()
    return dict(row) if row else None

def db_save(uid, data):
    existing = db_get(uid)
    # preserve photo if not provided
    if existing and not data.get('photo') and existing.get('photo'):
        data['photo'] = existing['photo']
    # preserve share_unlocked
    if existing:
        data.setdefault('share_unlocked', existing.get('share_unlocked', 0))
    cols = ','.join(FIELDS)
    ph   = ','.join(['?']*len(FIELDS))
    vals = [data.get(f) for f in FIELDS]
    upd  = ','.join([f"{f}=excluded.{f}" for f in FIELDS])
    db_exec(
        f"INSERT INTO users (user_id,{cols},updated_at) "
        f"VALUES (?,{ph},datetime('now','localtime')) "
        f"ON CONFLICT(user_id) DO UPDATE SET {upd},"
        f"updated_at=datetime('now','localtime')",
        [uid]+vals
    )

def db_update(uid, field, value):
    if field.split()[0] not in set(FIELDS): return
    db_exec(f"UPDATE users SET {field}=?,updated_at=datetime('now','localtime') "
            f"WHERE user_id=?", (value, uid))

def db_delete(uid):
    db_exec('DELETE FROM users WHERE user_id=?',(uid,))
    db_exec('DELETE FROM seen WHERE user_id=? OR seen_id=?',(uid,uid))

def db_all():
    return [dict(r) for r in db_query('SELECT * FROM users').fetchall()]

def db_all_ids():
    return [r[0] for r in db_query('SELECT user_id FROM users').fetchall()]

def db_count():
    return db_query('SELECT COUNT(*) FROM users').fetchone()[0]

def db_seen_add(uid,sid):
    try: db_exec('INSERT OR IGNORE INTO seen VALUES (?,?)',(uid,sid))
    except: pass

def db_seen_get(uid):
    return {r[0] for r in db_query('SELECT seen_id FROM seen WHERE user_id=?',(uid,))}

def db_seen_clear(uid):
    db_exec('DELETE FROM seen WHERE user_id=?',(uid,))

def db_report_add(a,b):
    try: db_exec('INSERT OR IGNORE INTO reports VALUES (?,?,datetime("now","localtime"))',(a,b))
    except: pass

def db_reported_by(uid):
    return {r[0] for r in db_query(
        'SELECT reported_id FROM reports WHERE reporter_id=?',(uid,))}

def db_ref_add(referrer, referred):
    try: db_exec('INSERT OR IGNORE INTO referrals (referrer_id,referred_id) VALUES (?,?)',
                 (referrer,referred))
    except: pass

def db_ref_joined(uid):
    """ဘယ်နှစ်ယောက် join ပြီးဆိုတာ"""
    return db_query(
        'SELECT COUNT(*) FROM referrals WHERE referrer_id=?',(uid,)).fetchone()[0]

def db_is_unlocked(uid):
    """Admin ကို အမြဲ unlock"""
    if uid == ADMIN_ID: return True
    row = db_get(uid)
    return bool(row and row.get('share_unlocked'))

def db_unlock(uid):
    db_exec('UPDATE users SET share_unlocked=1 WHERE user_id=?',(uid,))

def db_stats():
    total  = db_query('SELECT COUNT(*) FROM users').fetchone()[0]
    male   = db_query("SELECT COUNT(*) FROM users WHERE gender='Male'").fetchone()[0]
    female = db_query("SELECT COUNT(*) FROM users WHERE gender='Female'").fetchone()[0]
    photo  = db_query("SELECT COUNT(*) FROM users WHERE photo IS NOT NULL").fetchone()[0]
    refs   = db_query("SELECT COUNT(*) FROM referrals").fetchone()[0]
    unlocked = db_query("SELECT COUNT(*) FROM users WHERE share_unlocked=1").fetchone()[0]
    return {'total':total,'male':male,'female':female,
            'photo':photo,'refs':refs,'unlocked':unlocked}

# ═══════════════════════════════════════════════════════════════
# ⌨️  KEYBOARDS
# ═══════════════════════════════════════════════════════════════
def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(KeyboardButton("🔍 ဖူးစာရှာမည်"), KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    m.row(KeyboardButton("ℹ️ အကူအညီ"),      KeyboardButton("🔄 Profile ပြန်လုပ်"))
    return m

def admin_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(KeyboardButton("🔍 ဖူးစာရှာမည်"), KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    m.row(KeyboardButton("ℹ️ အကူအညီ"),      KeyboardButton("🔄 Profile ပြန်လုပ်"))
    m.row(KeyboardButton("📊 စာရင်းအင်း"),   KeyboardButton("🛠 Admin Panel"))
    return m

def kb(uid): return admin_kb() if uid==ADMIN_ID else main_kb()

# ═══════════════════════════════════════════════════════════════
# 🔧  UTILITIES
# ═══════════════════════════════════════════════════════════════
def safe(d, key, fallback='—'):
    v = (d or {}).get(key)
    if isinstance(v, str): v = v.strip()
    return v if v else fallback

def check_channel(uid):
    try:
        return bot.get_chat_member(CHANNEL_ID,uid).status in (
            'member','creator','administrator')
    except: return False

def notify_admin(text):
    try: bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except: pass

def report_error(context, err, uid=None):
    """Error ဖြစ်ရင် Admin ထံ အသိပေး"""
    tb = traceback.format_exc()
    msg = (
        f"🔴 *Bot Error*\n\n"
        f"📍 Context : `{context}`\n"
        f"👤 User ID : `{uid}`\n"
        f"❌ Error   : `{type(err).__name__}: {err}`\n"
        f"⏰ Time    : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        f"```\n{tb[-500:]}```"
    )
    notify_admin(msg)

def fmt_profile(tp, title='👤 *ပရိုဖိုင်*', show_count=False):
    bio_line  = f"\n📝 အကြောင်း  : {safe(tp,'bio')}" if (tp or {}).get('bio') else ''
    ltype     = safe(tp,'looking_type','')
    ltype_line= f"\n🎯 ရှာဖွေရန်  : {ltype}" if ltype!='—' else ''
    count_line= f"\n👥 အသုံးပြုသူ : *{db_count()}* ယောက်" if show_count else ''
    return (
        f"{title}{count_line}\n\n"
        f"📛 နာမည်   : {safe(tp,'name')}\n"
        f"🎂 အသက်   : {safe(tp,'age')} နှစ်\n"
        f"🔮 ရာသီ   : {safe(tp,'zodiac')}\n"
        f"📍 မြို့    : {safe(tp,'city')}\n"
        f"🎨 ဝါသနာ  : {safe(tp,'hobby')}\n"
        f"💼 အလုပ်   : {safe(tp,'job')}\n"
        f"🎵 သီချင်း  : {safe(tp,'song')}"
        f"{bio_line}"
        f"{ltype_line}\n"
        f"⚧ လိင်    : {safe(tp,'gender')}\n"
        f"💑 ရှာဖွေ  : {safe(tp,'looking_gender')} / {safe(tp,'looking_zodiac','Any')}"
    )

def stats_text():
    s = db_stats()
    return (
        f"📊 *Yay Zat Bot — စာရင်းအင်း*\n\n"
        f"👥 စုစုပေါင်း       : *{s['total']}* ယောက်\n"
        f"♂️ ကျား            : {s['male']} ယောက်\n"
        f"♀️ မ               : {s['female']} ယောက်\n"
        f"📸 ဓာတ်ပုံပါ       : {s['photo']} ယောက်\n"
        f"🔓 Unlock ပြီး     : {s['unlocked']} ယောက်\n"
        f"🔗 Referral        : {s['refs']} ခု\n"
        f"⏰ Update          : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

def invite_link(uid):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

def share_keyboard(uid):
    link = invite_link(uid)
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton(
        "📤 မိတ်ဆွေများကို Share လုပ်မည်",
        url=f"https://t.me/share/url?url={link}"
            f"&text=✨+Yay+Zat+Zodiac+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
    m.row(InlineKeyboardButton("✅ Share ပြီးပြီ — စစ်ဆေးမည်",
                               callback_data="check_share"))
    return m

user_reg = {}

# ═══════════════════════════════════════════════════════════════
# 🚀  /start
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def start_bot(message):
    uid  = message.chat.id
    args = message.text.split()
    try:
        # referral tracking
        if len(args)>1 and args[1].startswith('ref_'):
            referrer = int(args[1][4:])
            if referrer!=uid and db_get(referrer):
                db_ref_add(referrer, uid)
                # check if referrer now has enough refs
                check_and_unlock(referrer)
    except Exception as e:
        report_error('start/referral', e, uid)

    if db_get(uid):
        bot.send_message(uid,
            "✨ *ကြိုဆိုပါတယ်!* ✨\n\nအောက်ပါ ခလုတ်များကို နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇",
            parse_mode="Markdown", reply_markup=kb(uid))
        return

    try:
        tg=message.from_user.username or message.from_user.first_name or str(uid)
        fn=message.from_user.first_name or ''
        ln=message.from_user.last_name  or ''
    except: tg=fn=ln=str(uid)

    notify_admin(
        f"🆕 *အသုံးပြုသူသစ်*\n👤 {fn} {ln}\n🔗 @{tg}\n"
        f"🆔 `{uid}`\n👥 {db_count()} ယောက်\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    user_reg[uid] = {}
    bot.send_message(uid,
        f"✨ *Yay Zat Zodiac မှ ကြိုဆိုပါတယ်!* ✨\n\n"
        f"ဖူးစာရှင်/မိတ်ဆွေကို ရှာဖွေဖို့ မေးခွန်းလေးတွေ ဖြေပေးပါ 🙏\n"
        f"_( /skip — ကျော်ချင်ရင် )_\n\n"
        f"📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_name)

def check_and_unlock(uid):
    """Referral ၇ ယောက်ပြည့်ရင် unlock"""
    if db_is_unlocked(uid): return
    count = db_ref_joined(uid)
    if count >= SHARE_REQUIRED:
        db_unlock(uid)
        try:
            bot.send_message(uid,
                f"🎉 *ဂုဏ်ယူပါတယ်!* မိတ်ဆွေ *{SHARE_REQUIRED}* ယောက် "
                f"join ဖြစ်သွားပြီ!\n\n"
                f"✅ ဖူးစာရှာခွင့် unlock ရပါပြီ! "
                f"*🔍 ဖူးစာရှာမည်* ကိုနှိပ်ပြီး ရှာနိုင်ပါပြီ 💖",
                parse_mode="Markdown", reply_markup=kb(uid))
        except: pass

# ═══════════════════════════════════════════════════════════════
# 📝  REGISTRATION STEPS
# ═══════════════════════════════════════════════════════════════
def _skip(msg): return not msg.text or msg.text.strip()=='/skip'

def _reg_safe(fn):
    """Registration step wrapper — error ဖြစ်ရင် catch"""
    def wrapper(message):
        try:
            fn(message)
        except Exception as e:
            report_error(f'reg/{fn.__name__}', e, message.chat.id)
            bot.send_message(message.chat.id,
                "⚠️ တစ်ခုခု မှားသွားပါသည်။ /start ကိုနှိပ်ပြီး ပြန်စကြည့်ပါ။")
    return wrapper

@_reg_safe
def reg_name(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['name']=message.text.strip()
    bot.send_message(uid,"🎂 အသက် ဘယ်လောက်လဲ? (/skip)-")
    bot.register_next_step_handler(message,reg_age)

@_reg_safe
def reg_age(message):
    uid=message.chat.id
    if not _skip(message):
        if message.text.strip().isdigit():
            user_reg.setdefault(uid,{})['age']=message.text.strip()
        else:
            bot.send_message(uid,"⚠️ ဂဏန်းသာ ရိုက်ပါ (ဥပမာ 25)- (/skip)")
            bot.register_next_step_handler(message,reg_age); return
    m=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    for z in ZODIACS: m.add(z)
    m.add('/skip')
    bot.send_message(uid,"🔮 ရာသီခွင်ကို ရွေးပါ-",reply_markup=m)
    bot.register_next_step_handler(message,reg_zodiac)

@_reg_safe
def reg_zodiac(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['zodiac']=message.text.strip()
    bot.send_message(uid,"📍 နေထိုင်တဲ့ မြို့ (ဥပမာ Mandalay)- (/skip)",
                     reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message,reg_city)

@_reg_safe
def reg_city(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['city']=message.text.strip()
    bot.send_message(uid,"🎨 ဝါသနာ ဘာပါလဲ? (ဥပမာ ခရီးသွား, ဂီတ)- (/skip)")
    bot.register_next_step_handler(message,reg_hobby)

@_reg_safe
def reg_hobby(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['hobby']=message.text.strip()
    bot.send_message(uid,"💼 အလုပ်အကိုင်?- (/skip)")
    bot.register_next_step_handler(message,reg_job)

@_reg_safe
def reg_job(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['job']=message.text.strip()
    bot.send_message(uid,"🎵 အကြိုက်ဆုံး သီချင်း တစ်ပုဒ်?- (/skip)")
    bot.register_next_step_handler(message,reg_song)

@_reg_safe
def reg_song(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['song']=message.text.strip()
    bot.send_message(uid,
        "📝 *မိမိအကြောင်း အတိုချုံး* ရေးပြပါ\n"
        "_(ဥပမာ: ဆေးကျောင်းသား, ဂီတကိုနှစ်သက်သူ, ခရီးသွားချင်သူ)_- (/skip)",
        parse_mode="Markdown")
    bot.register_next_step_handler(message,reg_bio)

@_reg_safe
def reg_bio(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['bio']=message.text.strip()
    m=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    m.row('💑 ဖူးစာရှာနေသူ','🤝 မိတ်ဆွေဖွဲ့ချင်သူ')
    m.add('/skip')
    bot.send_message(uid,"🎯 သင် ဘာရှာနေပါသလဲ?",reply_markup=m)
    bot.register_next_step_handler(message,reg_looking_type)

@_reg_safe
def reg_looking_type(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['looking_type']=message.text.strip()
    m=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    m.add('Male','Female','/skip')
    bot.send_message(uid,"⚧ သင့်လိင်ကို ရွေးပါ-",reply_markup=m)
    bot.register_next_step_handler(message,reg_gender)

@_reg_safe
def reg_gender(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['gender']=message.text.strip()
    m=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    m.add('Male','Female','Both','/skip')
    bot.send_message(uid,"💑 ရှာဖွေနေတဲ့ လိင်ကို ရွေးပါ-",reply_markup=m)
    bot.register_next_step_handler(message,reg_looking_gender)

@_reg_safe
def reg_looking_gender(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['looking_gender']=message.text.strip()
    m=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    for z in ZODIACS: m.add(z)
    m.add('Any','/skip')
    bot.send_message(uid,"🔮 ရှာဖွေနေတဲ့ ရာသီခွင်ကို ရွေးပါ-",reply_markup=m)
    bot.register_next_step_handler(message,reg_looking_zodiac)

@_reg_safe
def reg_looking_zodiac(message):
    uid=message.chat.id
    if not _skip(message): user_reg.setdefault(uid,{})['looking_zodiac']=message.text.strip()
    bot.send_message(uid,
        "📸 Profile ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက /skip)_",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message,reg_photo)

@_reg_safe
def reg_photo(message):
    uid    = message.chat.id
    is_new = db_get(uid) is None
    if _skip(message):
        existing = db_get(uid)
        if existing and existing.get('photo'):
            user_reg.setdefault(uid,{})['photo'] = existing['photo']
    else:
        if message.content_type!='photo':
            bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ (သို့) /skip ဟုရိုက်ပါ-")
            bot.register_next_step_handler(message,reg_photo); return
        user_reg.setdefault(uid,{})['photo']=message.photo[-1].file_id

    data=user_reg.pop(uid,{})
    db_save(uid,data)

    bot.send_message(uid,
        f"✅ Profile {'တည်ဆောက်' if is_new else 'ပြင်ဆင်'} ပြီးပါပြီ! 🎉\n\n"
        f"ခလုတ်များ နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇",
        parse_mode="Markdown", reply_markup=kb(uid))

    if is_new:
        notify_admin(
            f"🎉 *မှတ်ပုံတင် ပြီးမြောက်ပါပြီ!*\n"
            f"🆔 `{uid}` — 📛 {safe(data,'name')}\n"
            f"👥 {db_count()} ယောက်\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

# ═══════════════════════════════════════════════════════════════
# 🔒  SHARE GATE — match မရှာခင် ၇ ယောက် ဖိတ်ကြားရမည်
# ═══════════════════════════════════════════════════════════════
def show_share_gate(uid):
    joined = db_ref_joined(uid)
    remaining = max(0, SHARE_REQUIRED - joined)
    link = invite_link(uid)
    bot.send_message(uid,
        f"🔒 *ဖူးစာရှာရန် Unlock လိုအပ်ပါသည်*\n\n"
        f"မိတ်ဆွေ *{SHARE_REQUIRED}* ယောက် Bot ကိုသုံးစေပြီးမှ\n"
        f"ဖူးစာရှာခွင့် ရမည်ဖြစ်ပါသည် 🙏\n\n"
        f"📊 လက်ရှိ : *{joined}/{SHARE_REQUIRED}* ယောက်\n"
        f"🎯 ကျန်    : *{remaining}* ယောက်\n\n"
        f"🔗 သင့် Link : `{link}`\n\n"
        f"Link ကို မိတ်ဆွေများထံ Share လုပ်ပြီး\n"
        f"သူများ join ဖြစ်ရင် စစ်ဆေးပေးပါ 👇",
        parse_mode="Markdown", reply_markup=share_keyboard(uid))

# ═══════════════════════════════════════════════════════════════
# 👤  MY PROFILE
# ═══════════════════════════════════════════════════════════════
def show_my_profile(message):
    uid=message.chat.id
    tp=db_get(uid)
    if not tp:
        bot.send_message(uid,"Profile မရှိသေးပါ။ /start ကိုနှိပ်ပါ。",reply_markup=kb(uid)); return

    refs    = db_ref_joined(uid)
    unlocked= db_is_unlocked(uid)
    status  = f"🔓 Unlock ပြီး" if unlocked else f"🔒 {refs}/{SHARE_REQUIRED} ဖိတ်ပြီး"

    # profile မှာ user count ပြမည်မဟုတ် — admin ပဲပြ
    text = fmt_profile(tp, show_count=(uid==ADMIN_ID))
    text += f"\n\n{status}"

    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📛 နာမည်",  callback_data="edit_name"),
          InlineKeyboardButton("🎂 အသက်",   callback_data="edit_age"))
    m.row(InlineKeyboardButton("🔮 ရာသီ",   callback_data="edit_zodiac"),
          InlineKeyboardButton("📍 မြို့",   callback_data="edit_city"))
    m.row(InlineKeyboardButton("🎨 ဝါသနာ", callback_data="edit_hobby"),
          InlineKeyboardButton("💼 အလုပ်",  callback_data="edit_job"))
    m.row(InlineKeyboardButton("🎵 သီချင်း",callback_data="edit_song"),
          InlineKeyboardButton("📝 Bio",    callback_data="edit_bio"))
    m.row(InlineKeyboardButton("📸 ဓာတ်ပုံ",callback_data="edit_photo"))
    m.row(InlineKeyboardButton("🔄 အကုန်ပြန်လုပ်", callback_data="edit_all"))
    m.row(InlineKeyboardButton("🔗 Invite Link ကြည့်",callback_data="my_invite"),
          InlineKeyboardButton("🗑 Profile ဖျက်",  callback_data="delete_profile"))

    if tp.get('photo'):
        bot.send_photo(uid,tp['photo'],caption=text,reply_markup=m,parse_mode="Markdown")
    else:
        bot.send_message(uid,text,reply_markup=m,parse_mode="Markdown")

# ═══════════════════════════════════════════════════════════════
# 🔍  FIND MATCH
# ═══════════════════════════════════════════════════════════════
def run_find_match(message):
    uid=message.chat.id
    me=db_get(uid)
    if not me:
        bot.send_message(uid,"/start ကိုနှိပ်ပြီး Profile အရင်တည်ဆောက်ပါ。",
                         reply_markup=kb(uid)); return

    # Share gate check
    if not db_is_unlocked(uid):
        show_share_gate(uid); return

    if not check_channel(uid):
        m=InlineKeyboardMarkup()
        m.add(InlineKeyboardButton("📢 Channel Join မည်",url=CHANNEL_LINK))
        bot.send_message(uid,"⚠️ Channel ကို အရင် Join ပေးပါ。",reply_markup=m); return

    seen     = db_seen_get(uid)
    reported = db_reported_by(uid)
    exclude  = seen|reported|{uid}

    looking_g=(me.get('looking_gender') or '').strip()
    looking_z=(me.get('looking_zodiac')  or '').strip()

    all_users=db_all()
    eligible=[]
    for u in all_users:
        if u['user_id'] in exclude: continue
        if looking_g and looking_g not in ('Both','Any'):
            if (u.get('gender') or '').strip()!=looking_g: continue
        eligible.append(u)

    if not eligible:
        if seen:
            db_seen_clear(uid)
            bot.send_message(uid,"🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ...")
            run_find_match(message)
        else:
            bot.send_message(uid,
                "😔 လောလောဆယ် သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ。\n"
                "ဖော်ဆွေကိုဖိတ်ကြားပြီး Bot ကိုပြောဆိုပေးပါ 😊",
                reply_markup=kb(uid))
        return

    if looking_z and looking_z not in ('Any',''):
        pref=[u for u in eligible if (u.get('zodiac') or '')==looking_z]
        fall=[u for u in eligible if (u.get('zodiac') or '')!=looking_z]
        ordered=pref+fall
    else:
        ordered=eligible

    target=ordered[0]
    tid=target['user_id']
    db_seen_add(uid,tid)

    note=''
    if looking_z and looking_z not in ('Any','') and (target.get('zodiac') or '')!=looking_z:
        note=f"\n_( {looking_z} မတွေ့သောကြောင့် အနီးစပ်ဆုံးပြပေးနေပါသည် )_"

    text=fmt_profile(target,title=f"🎯 *မိတ်ဆွေနဲ့ ကိုက်ညီနိုင်မယ့်သူ*{note}")
    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("❤️ Like",  callback_data=f"like_{tid}"),
          InlineKeyboardButton("⏭ Skip",  callback_data="skip"),
          InlineKeyboardButton("🚩 Report",callback_data=f"report_{tid}"))

    if target.get('photo'):
        bot.send_photo(uid,target['photo'],caption=text,reply_markup=m,parse_mode="Markdown")
    else:
        bot.send_message(uid,text,reply_markup=m,parse_mode="Markdown")

def send_match_msg(uid, partner_id):
    try:
        bot.send_message(uid,
            f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
            f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner_id}) စကားပြောနိုင်ပါပြီ 🎉",
            parse_mode="Markdown",reply_markup=kb(uid))
    except: pass

# ═══════════════════════════════════════════════════════════════
# 🔄  RESET / ℹ️ HELP / 📊 STATS / 🛠 ADMIN
# ═══════════════════════════════════════════════════════════════
def run_reset(message):
    uid=message.chat.id
    existing=db_get(uid)
    user_reg[uid]=dict(existing) if existing else {}
    bot.send_message(uid,
        "🔄 *Profile ပြန်လုပ်မည်*\n\n"
        "/skip — ကျော်နိုင်ပါသည်\n\n"
        "📛 နာမည် ရိုက်ထည့်ပါ-",
        parse_mode="Markdown",reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message,reg_name)

def show_help(message):
    bot.send_message(message.chat.id,
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ဖူးစာရှာမည်* — ကိုက်ညီနိုင်မယ့်သူ ရှာပါ\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
        "🔄 *Profile ပြန်လုပ်* — Profile အသစ်ပြန်ဖြည့်ပါ\n\n"
        "*Commands*\n"
        "/start — စတင်မှတ်ပုံတင်ပါ\n"
        "/reset — Profile ပြန်လုပ်ပါ\n"
        "/deleteprofile — Profile ဖျက်ပါ\n\n"
        "ပြဿနာများ Admin ကို ဆက်သွယ်ပါ。",
        parse_mode="Markdown",reply_markup=kb(message.chat.id))

def show_stats(message):
    uid=message.chat.id
    if uid!=ADMIN_ID:
        bot.send_message(uid,"⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်。"); return
    bot.send_message(ADMIN_ID,stats_text(),parse_mode="Markdown",reply_markup=admin_kb())

def show_admin_panel(message):
    if message.chat.id!=ADMIN_ID: return
    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📊 Full Stats",    callback_data="adm_stats"),
          InlineKeyboardButton("👥 User List",     callback_data="adm_userlist"))
    m.row(InlineKeyboardButton("📢 Broadcast",     callback_data="adm_broadcast"),
          InlineKeyboardButton("🗑 User ဖျက်",     callback_data="adm_deluser"))
    m.row(InlineKeyboardButton("🔓 User Unlock",   callback_data="adm_unlock"))
    bot.send_message(ADMIN_ID,"🛠 *Admin Panel*",parse_mode="Markdown",reply_markup=m)

def _broadcast_step(message):
    if message.text=='/cancel': bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    ok=fail=0
    for uid in db_all_ids():
        try: bot.send_message(uid,f"📢 *Admin မှ သတင်းစကား*\n\n{message.text}",
                              parse_mode="Markdown"); ok+=1
        except: fail+=1
    bot.send_message(ADMIN_ID,f"✅ Broadcast ပြီး!\n✔️ {ok} ရောက် / ❌ {fail} မရောက်")

def _deluser_step(message):
    if message.text=='/cancel': bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    try:
        uid=int(message.text.strip())
        if db_get(uid): db_delete(uid); bot.send_message(ADMIN_ID,f"✅ `{uid}` ဖျက်ပြီး",parse_mode="Markdown")
        else: bot.send_message(ADMIN_ID,"⚠️ ထို ID မတွေ့ပါ。")
    except ValueError: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ ရိုက်ပါ。")

def _unlock_step(message):
    if message.text=='/cancel': bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    try:
        uid=int(message.text.strip())
        if db_get(uid):
            db_unlock(uid)
            bot.send_message(ADMIN_ID,f"✅ `{uid}` unlock ပြီး",parse_mode="Markdown")
            try: bot.send_message(uid,"✅ Admin က သင့်အကောင့်ကို unlock လုပ်ပေးပြီးပါပြီ!\n"
                                  "🔍 ဖူးစာရှာနိုင်ပါပြီ 💖",reply_markup=kb(uid))
            except: pass
        else: bot.send_message(ADMIN_ID,"⚠️ ထို ID မတွေ့ပါ。")
    except ValueError: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ ရိုက်ပါ。")

def save_field(message,field):
    uid=message.chat.id
    try:
        if field=='photo':
            if message.content_type!='photo':
                bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ。"); return
            db_update(uid,'photo',message.photo[-1].file_id)
        else:
            if not message.text or not message.text.strip():
                bot.send_message(uid,"⚠️ ဗလာမထားပါနဲ့-")
                bot.register_next_step_handler(message,save_field,field); return
            db_update(uid,field,message.text.strip())
        bot.send_message(uid,"✅ ပြင်ဆင်မှု အောင်မြင်ပါသည်!",reply_markup=kb(uid))
    except Exception as e:
        report_error(f'save_field/{field}',e,uid)
        bot.send_message(uid,"⚠️ တစ်ခုခုမှားသွားပါသည်。ထပ်ကြိုးစားကြည့်ပါ。")

# ═══════════════════════════════════════════════════════════════
# 🔘  MENU ROUTER
# ═══════════════════════════════════════════════════════════════
MENU = {
    "🔍 ဖူးစာရှာမည်"     : run_find_match,
    "👤 ကိုယ့်ပရိုဖိုင်"  : show_my_profile,
    "ℹ️ အကူအညီ"          : show_help,
    "🔄 Profile ပြန်လုပ်"  : run_reset,
    "📊 စာရင်းအင်း"       : show_stats,
    "🛠 Admin Panel"       : show_admin_panel,
}

@bot.message_handler(func=lambda m: m.text in MENU)
def menu_router(message):
    try: MENU[message.text](message)
    except Exception as e:
        report_error(f'menu/{message.text}', e, message.chat.id)
        bot.send_message(message.chat.id,
            "⚠️ တစ်ခုခု မှားသွားပါသည်。နောက်မှ ထပ်ကြိုးစားကြည့်ပါ。")

@bot.message_handler(commands=['reset'])
def cmd_reset(m): run_reset(m)

@bot.message_handler(commands=['stats'])
def cmd_stats(m): show_stats(m)

@bot.message_handler(commands=['myprofile'])
def cmd_myprofile(m): show_my_profile(m)

@bot.message_handler(commands=['deleteprofile'])
def cmd_deleteprofile(message):
    uid=message.chat.id
    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("✅ ဟုတ်တယ် ဖျက်မည်",callback_data="confirm_delete"),
          InlineKeyboardButton("❌ မဖျက်တော့ပါ",     callback_data="cancel_delete"))
    bot.send_message(uid,"⚠️ Profile ကို ဖျက်မှာ သေချာပါသလား?",reply_markup=m)

# ═══════════════════════════════════════════════════════════════
# 📞  CALLBACK QUERY
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda call: True)
def on_callback(call):
    uid=call.message.chat.id
    d=call.data
    try:
        _handle_callback(call, uid, d)
    except Exception as e:
        report_error(f'callback/{d}', e, uid)
        try: bot.answer_callback_query(call.id,"⚠️ တစ်ခုခုမှားသွားပါသည်。",show_alert=True)
        except: pass

def _handle_callback(call, uid, d):

    # ── Share gate check ──────────────────────────────────────
    if d=="check_share":
        count = db_ref_joined(uid)
        if count >= SHARE_REQUIRED:
            db_unlock(uid)
            bot.answer_callback_query(call.id,"🎉 Unlock ဖြစ်ပါပြီ!",show_alert=True)
            try: bot.delete_message(uid,call.message.message_id)
            except: pass
            bot.send_message(uid,
                f"✅ *ဖူးစာရှာခွင့် Unlock ရပါပြီ!* 🎉\n\n"
                f"🔍 ဖူးစာရှာမည် ကိုနှိပ်ပြီး ရှာနိုင်ပါပြီ 💖",
                parse_mode="Markdown",reply_markup=kb(uid))
        else:
            remaining=SHARE_REQUIRED-count
            bot.answer_callback_query(call.id,
                f"ကျန်သေးသည် {remaining} ယောက်。ဆက်ဖိတ်ကြားပါ!",show_alert=True)

    # ── Edit ─────────────────────────────────────────────────
    elif d.startswith("edit_"):
        field=d[5:]
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        if field=="all":
            existing=db_get(uid)
            user_reg[uid]=dict(existing) if existing else {}
            bot.send_message(uid,"🔄 Profile ပြန်တည်ဆောက်မည်\n📛 နာမည် ရိုက်ထည့်ပါ- (/skip)",
                             reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(call.message,reg_name)
        elif field=="photo":
            msg=bot.send_message(uid,"📸 ဓာတ်ပုံအသစ် ပေးပို့ပါ-",reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg,save_field,'photo')
        else:
            labels={
                'name':'နာမည်','age':'အသက်','zodiac':'ရာသီ','city':'မြို့',
                'hobby':'ဝါသနာ','job':'အလုပ်','song':'သီချင်း','bio':'Bio',
                'looking_type':'ရှာဖွေမည့်အမျိုးအစား',
                'gender':'လိင်','looking_gender':'ရှာဖွေမည့်လိင်',
                'looking_zodiac':'ရှာဖွေမည့်ရာသီ'
            }
            msg=bot.send_message(uid,f"📝 {labels.get(field,field)} အသစ် ရိုက်ထည့်ပါ-",
                                 reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg,save_field,field)

    # ── Invite ────────────────────────────────────────────────
    elif d=="my_invite":
        link=invite_link(uid)
        count=db_ref_joined(uid)
        unlocked=db_is_unlocked(uid)
        status=f"🔓 Unlock ပြီး" if unlocked else f"🔒 {count}/{SHARE_REQUIRED}"
        m=InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("📤 Share လုပ်မည်",
              url=f"https://t.me/share/url?url={link}&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
        bot.send_message(uid,
            f"🔗 *သင့် Invite Link*\n\n`{link}`\n\n"
            f"👥 Join ဖြစ်သူ : *{count}/{SHARE_REQUIRED}* ယောက်\n"
            f"📊 အခြေအနေ : {status}",
            parse_mode="Markdown",reply_markup=m)

    # ── Delete profile ────────────────────────────────────────
    elif d=="delete_profile":
        m=InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("✅ ဟုတ်တယ် ဖျက်မည်",callback_data="confirm_delete"),
              InlineKeyboardButton("❌ မဖျက်တော့ပါ",     callback_data="cancel_delete"))
        try: bot.edit_message_reply_markup(uid,call.message.message_id,reply_markup=m)
        except: pass

    elif d=="confirm_delete":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        db_delete(uid)
        bot.send_message(uid,"🗑 Profile ဖျက်ပြီးပါပြီ。\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်。",
                         reply_markup=ReplyKeyboardRemove())

    elif d=="cancel_delete":
        bot.answer_callback_query(call.id,"မဖျက်တော့ပါ。")
        try: bot.delete_message(uid,call.message.message_id)
        except: pass

    # ── Skip match ────────────────────────────────────────────
    elif d=="skip":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        run_find_match(call.message)

    # ── Like ─────────────────────────────────────────────────
    elif d.startswith("like_"):
        tid=int(d[5:])
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        if not check_channel(uid):
            bot.answer_callback_query(call.id,"⚠️ Channel ကို Join ပါ!",show_alert=True); return
        me_data=db_get(uid) or {}
        liker_name=safe(me_data,'name','တစ်ယောက်')
        like_m=InlineKeyboardMarkup()
        like_m.row(InlineKeyboardButton("✅ လက်ခံမည်",callback_data=f"accept_{uid}"),
                   InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline"))
        caption=(
            f"💌 *'{liker_name}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n"
            + fmt_profile(me_data,title='👤 *သူ/သူမ ရဲ့ Profile*')
        )
        try:
            if me_data.get('photo'):
                bot.send_photo(tid,me_data['photo'],caption=caption,
                               reply_markup=like_m,parse_mode="Markdown")
            else:
                bot.send_message(tid,caption,reply_markup=like_m,parse_mode="Markdown")
            bot.send_message(uid,
                "❤️ Like လုပ်လိုက်ပါပြီ!\nတစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊",
                reply_markup=kb(uid))
        except:
            bot.send_message(uid,"⚠️ တစ်ဖက်လူမှာ Bot ကို Block ထားသဖြင့် ပေးပို့မရပါ。",
                             reply_markup=kb(uid))

    # ── Accept ────────────────────────────────────────────────
    elif d.startswith("accept_"):
        liker_id=int(d[7:])
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        notify_admin(
            f"💖 *New Match!*\n[A](tg://user?id={uid}) + [B](tg://user?id={liker_id})\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        send_match_msg(uid, liker_id)
        send_match_msg(liker_id, uid)

    # ── Decline ───────────────────────────────────────────────
    elif d=="decline":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        bot.send_message(uid,"❌ ငြင်းဆန်လိုက်ပါပြီ。",reply_markup=kb(uid))

    # ── Report ───────────────────────────────────────────────
    elif d.startswith("report_"):
        tid=int(d[7:])
        db_report_add(uid,tid)
        bot.answer_callback_query(call.id,"🚩 Report လုပ်ပြီးပါပြီ。",show_alert=True)
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        notify_admin(
            f"🚩 *User Report*\n"
            f"Reporter : `{uid}` {safe(db_get(uid),'name')}\n"
            f"Reported : `{tid}` {safe(db_get(tid),'name')}\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

    # ── Admin ─────────────────────────────────────────────────
    elif d=="adm_stats" and uid==ADMIN_ID:
        bot.send_message(ADMIN_ID,stats_text(),parse_mode="Markdown")

    elif d=="adm_broadcast" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"📢 Message ကို ရိုက်ထည့်ပါ (/cancel-ပယ်ဖျက်)-")
        bot.register_next_step_handler(msg,_broadcast_step)

    elif d=="adm_userlist" and uid==ADMIN_ID:
        rows=db_all()[:30]
        lines=[f"{i}. {safe(u,'name')} `{u['user_id']}` {'🔓' if u.get('share_unlocked') else '🔒'}"
               for i,u in enumerate(rows,1)]
        bot.send_message(ADMIN_ID,
            "👥 *User List (ပထမ 30)*\n\n"+("\n".join(lines) if lines else "မရှိသေး"),
            parse_mode="Markdown")

    elif d=="adm_deluser" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"🗑 ဖျက်မည့် User ID (/cancel-ပယ်ဖျက်)-")
        bot.register_next_step_handler(msg,_deluser_step)

    elif d=="adm_unlock" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"🔓 Unlock မည့် User ID (/cancel-ပယ်ဖျက်)-")
        bot.register_next_step_handler(msg,_unlock_step)

    try: bot.answer_callback_query(call.id)
    except: pass

# ═══════════════════════════════════════════════════════════════
# 🔁  AUTO-RESTART POLLING LOOP — bot မရပ်အောင်
# ═══════════════════════════════════════════════════════════════

# Re-register bot instance (already done above, this line just reassures)
print(f"✅ Yay Zat Bot စတင်နေပါပြီ... [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
notify_admin(f"🟢 *Bot Online ဖြစ်ပါပြီ!*\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

while True:
    try:
        bot.polling(
            none_stop=True,
            interval=0,
            timeout=30,
            long_polling_timeout=30
        )
    except Exception as e:
        err_msg = f"🔴 *Bot Polling Error — Restarting...*\n\n`{type(e).__name__}: {e}`\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        print(err_msg)
        try:
            import requests
            requests.get(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                params={"chat_id": ADMIN_ID, "text": err_msg, "parse_mode": "Markdown"},
                timeout=10
            )
        except: pass
        time.sleep(5)   # 5 sec စောင့်ပြီး ပြန်စသည်
        continue
