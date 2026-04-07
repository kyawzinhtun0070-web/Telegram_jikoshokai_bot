"""
Yay Zat Zodiac Bot — Full Production Version
✅ Fixed: Syntax, Skip Flow, Match-Triggered Unlock, Referral Count
"""
import telebot
import sqlite3
import threading
import time
import traceback
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
BOT_USERNAME = "YayZatBot"
SHARE_NEEDED = 7

ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

bot = telebot.TeleBot(TOKEN, threaded=True, skip_pending=True)

# ═══════════════════════════════════════════════════════════════
# 💾  DATABASE (Thread-Safe & Auto-Fix)
# ═══════════════════════════════════════════════════════════════
DB_FILE = 'yayzat.db'
_db_lock = threading.Lock()
_db = None

def get_db():
    global _db
    if _db is None:
        _db = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=15)
        _db.row_factory = sqlite3.Row
        _db.execute("PRAGMA journal_mode=WAL")
        _db.execute("PRAGMA busy_timeout=10000")
    return _db

def execute_query(sql, params=(), commit=False):
    with _db_lock:
        db = get_db()
        try:            cur = db.execute(sql, params)
            if commit: db.commit()
            return cur
        except sqlite3.OperationalError:
            global _db
            _db = None
            db = get_db()
            cur = db.execute(sql, params)
            if commit: db.commit()
            return cur

def init_db():
    execute_query('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, name TEXT, age TEXT, zodiac TEXT,
        city TEXT, hobby TEXT, job TEXT, song TEXT, bio TEXT,
        gender TEXT, looking_gender TEXT, looking_zodiac TEXT,
        looking_type TEXT, photo TEXT, stars INTEGER DEFAULT 0,
        created_at TEXT, updated_at TEXT)''', commit=True)
    execute_query('CREATE TABLE IF NOT EXISTS seen (user_id INTEGER, seen_id INTEGER, PRIMARY KEY (user_id, seen_id))', commit=True)
    execute_query('CREATE TABLE IF NOT EXISTS reports (reporter_id INTEGER, reported_id INTEGER, PRIMARY KEY (reporter_id, reported_id))', commit=True)
    execute_query('CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, PRIMARY KEY (referrer_id, referred_id))', commit=True)
    execute_query('CREATE TABLE IF NOT EXISTS pending_match (user_id INTEGER PRIMARY KEY, partner_id INTEGER, created_at TEXT)', commit=True)

    # Auto-add missing columns
    db = get_db()
    cols = [row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()]
    for col, typ in [('bio','TEXT'), ('song','TEXT'), ('looking_type','TEXT'), ('stars','INTEGER DEFAULT 0')]:
        if col not in cols:
            try: execute_query(f"ALTER TABLE users ADD COLUMN {col} {typ}", commit=True)
            except: pass
init_db()

# ═══════════════════════════════════════════════════════════════
# 🔧  HELPERS
# ═══════════════════════════════════════════════════════════════
user_reg = {}

def safe(d, k, fb='—'):
    v = (d or {}).get(k)
    return str(v).strip() if v else fb

def get_user(uid):
    try:
        r = execute_query("SELECT * FROM users WHERE user_id=?", (uid,))
        row = r.fetchone()
        return dict(row) if row else None
    except: return None

def save_user(uid, data):
    old = get_user(uid)    if old and 'photo' not in data:
        data['photo'] = old.get('photo')
    data['stars'] = old.get('stars', 0) if old else 0
    cols = list(data.keys())
    vals = list(data.values())
    placeholders = ','.join(['?']*len(cols))
    updates = ','.join([f"{c}=excluded.{c}" for c in cols])
    sql = f"INSERT INTO users (user_id,{','.join(cols)},updated_at) VALUES (?,{placeholders},datetime('now')) ON CONFLICT(user_id) DO UPDATE SET {updates},updated_at=datetime('now')"
    execute_query(sql, [uid]+vals, commit=True)

def delete_user(uid):
    execute_query("DELETE FROM users WHERE user_id=?", (uid,), commit=True)
    execute_query("DELETE FROM seen WHERE user_id=? OR seen_id=?", (uid, uid), commit=True)

def get_ref_count(uid):
    r = execute_query("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,))
    return r.fetchone()[0] if r else 0

def is_unlocked(uid):
    return uid == ADMIN_ID or get_ref_count(uid) >= SHARE_NEEDED

# ═══════════════════════════════════════════════════════════════
# ⌨️  KEYBOARDS
# ═══════════════════════════════════════════════════════════════
def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(KeyboardButton("🔍 ဖူးစာရှာမည်"), KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    m.row(KeyboardButton("ℹ️ အကူအညီ"), KeyboardButton("🔄 Profile ပြန်လုပ်"))
    return m

# ═══════════════════════════════════════════════════════════════
# 🚀  START & REFERRAL
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(m):
    uid = m.chat.id
    parts = m.text.split()
    if len(parts) > 1 and parts[1].startswith('ref_'):
        try:
            ref_uid = int(parts[1][4:])
            if ref_uid != uid and get_user(ref_uid) and not get_user(uid):
                execute_query("INSERT OR IGNORE INTO referrals VALUES(?,?)", (ref_uid, uid), commit=True)
        except: pass

    if get_user(uid):
        bot.send_message(uid, "✨ ကြိုဆိုပါတယ်! ခလုတ်များနှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇", reply_markup=main_kb())
    else:
        user_reg[uid] = {}
        bot.send_message(uid, "✨ Yay Zat Zodiac မှ ကြိုဆိုပါတယ်! ✨\n\nဖူးစာရှင်ရှာဖို့ မေးခွန်းလေးတွေ ဖြေပေးပါ 🙏\n_( /skip — ကျော်ချင်ရင် )_\n\n📛 နာမည် -", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(m, reg_name)
# ═══════════════════════════════════════════════════════════════
# 📝  REGISTRATION FLOW (Robust Skip Handling)
# ═══════════════════════════════════════════════════════════════
def next_step(m, func, prompt, kb=None):
    try:
        bot.send_message(m.chat.id, prompt, reply_markup=kb, parse_mode="Markdown")
        bot.register_next_step_handler(m, func)
    except Exception as e:
        print(f"Reg step error: {e}")
        bot.send_message(m.chat.id, "⚠️ အဆင်မပြေပါ။ /start ထပ်နှိပ်ပါ")

def reg_name(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['name'] = m.text.strip()
    next_step(m, reg_age, "🎂 အသက်? `(/skip)`-")

def reg_age(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip':
        if m.text.strip().isdigit(): user_reg.setdefault(uid,{})['age'] = m.text.strip()
        else:
            bot.send_message(uid, "⚠️ ဏန်းသာ ထည့်ပါ (သို့) `/skip`-")
            bot.register_next_step_handler(m, reg_age); return
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add(*ZODIACS); mk.add('/skip')
    next_step(m, reg_zodiac, "🔮 ရာသီခွင်?", mk)

def reg_zodiac(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['zodiac'] = m.text.strip()
    next_step(m, reg_city, "📍 မြို့ (ဥပမာ Mandalay)? `(/skip)`-")

def reg_city(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['city'] = m.text.strip()
    next_step(m, reg_hobby, "🎨 ဝါသနာ (ဥပမာ ခရီးသွား,ဂီတ)? `(/skip)`-")

def reg_hobby(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['hobby'] = m.text.strip()
    next_step(m, reg_job, "💼 အလုပ်? `(/skip)`-")

def reg_job(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['job'] = m.text.strip()
    next_step(m, reg_song, "🎵 အကြိုက်ဆုံး သီချင်း? `(/skip)`-")

def reg_song(m):
    uid = m.chat.id    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['song'] = m.text.strip()
    next_step(m, reg_bio, "📝 *မိမိအကြောင်း အတိုချုံး* `(/skip)`-\n_(ဥပမာ: ဆေးကျောင်းသား, ဂီတကိုနှစ်သက်သူ)_")

def reg_bio(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['bio'] = m.text.strip()
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.row('💑 ဖူးစာရှာနေသူ','🤝 မိတ်ဆွေဖွဲ့ချင်သူ')
    mk.add('/skip')
    next_step(m, reg_ltype, "🎯 ဘာရှာနေပါသလဲ?", mk)

def reg_ltype(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['looking_type'] = m.text.strip()
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add('Male','Female','/skip')
    next_step(m, reg_gender, "⚧ သင့်လိင်?", mk)

def reg_gender(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['gender'] = m.text.strip()
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add('Male','Female','Both','/skip')
    next_step(m, reg_lgender, "💑 ရှာဖွေနေတဲ့ လိင်?", mk)

def reg_lgender(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['looking_gender'] = m.text.strip()
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add(*ZODIACS)
    mk.add('Any','/skip')
    next_step(m, reg_lzodiac, "🔮 ရှာဖွေနေတဲ့ ရာသီ?", mk)

def reg_lzodiac(m):
    uid = m.chat.id
    if m.text and m.text.strip() != '/skip': user_reg.setdefault(uid,{})['looking_zodiac'] = m.text.strip()
    next_step(m, reg_photo, "📸 Profile ာတ်ပုံ ပေးပို့ပါ _(မလိုပါက `/skip`)_")

def reg_photo(m):
    uid = m.chat.id
    if m.content_type == 'photo':
        user_reg.setdefault(uid,{})['photo'] = m.photo[-1].file_id
    try:
        save_user(uid, user_reg.pop(uid, {}))
        bot.send_message(uid, "✅ Profile တည်ဆောက် ပြီးပါပြီ! 🎉\n\nခလုတ်များ နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇", parse_mode="Markdown", reply_markup=main_kb())
    except Exception as e:
        print(f"Save error: {e}")
        bot.send_message(uid, "⚠️ Error ဖြစ်သွားပါသည်။ /start ထပ်နှိပ်ပါ")

# ═══════════════════════════════════════════════════════════════# 👤  PROFILE & 🔍  MATCH
# ═══════════════════════════════════════════════════════════════
def fmt_profile(u):
    if not u: return "Profile မရှိပါ"
    return (f"📛 *နာမည်*: {safe(u, 'name')}\n🎂 *အသက်*: {safe(u, 'age')} | 🔮 *ရာသီ*: {safe(u, 'zodiac')}\n"
            f"📍 *မြို့*: {safe(u, 'city')} | 💼 *အလုပ်*: {safe(u, 'job')}\n🎵 *သီချင်း*: {safe(u, 'song')}\n"
            f"📝 *Bio*: {safe(u, 'bio')}\n⚧ *လိင်*: {safe(u, 'gender')} | 💑 *ရှာဖွေ*: {safe(u, 'looking_gender')}")

@bot.message_handler(func=lambda m: m.text == "👤 ကိုယ့်ပရိုဖိုင်")
def show_profile(m):
    uid = m.chat.id
    user = get_user(uid)
    if not user:
        bot.send_message(uid, "Profile မရှိသေးပါ။ /start ကိုနှိပ်ပါ။", reply_markup=main_kb()); return
    refs = get_ref_count(uid)
    stars = safe(user, 'stars', '0')
    # Fixed bracket here
    unlock_status = ' ✅ Unlock ပြီး' if is_unlocked(uid) else f' 🔒 ({SHARE_NEEDED-refs} ကျန်)'
    text = fmt_profile(user) + f"\n\n⭐ ကြယ်ပွင့်: {stars} ခု\n ဖိတ်ကြားမှု: {refs}/{SHARE_NEEDED}{unlock_status}"
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🔄 ပြန်လုပ်မည်", callback_data="reset_profile"), InlineKeyboardButton("🔗 Invite Link", callback_data="my_invite"))
    if user.get('photo'):
        try: bot.send_photo(uid, user['photo'], caption=text, parse_mode="Markdown", reply_markup=kb)
        except: bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🔍 ဖူးစာရှာမည်")
def find_match(m):
    uid = m.chat.id
    user = get_user(uid)
    if not user:
        bot.send_message(uid, "/start ကိုနှိပ်ပြီး Profile ဦးတည်ဆောက်ပါ။", reply_markup=main_kb()); return
    # ✅ UNLOCK CHECK REMOVED FROM HERE
    
    r = execute_query("SELECT seen_id FROM seen WHERE user_id=?", (uid,))
    seen = [row[0] for row in r] if r else []
    seen.append(uid)
    r = execute_query("SELECT reported_id FROM reports WHERE reporter_id=?", (uid,))
    reported = [row[0] for row in r] if r else []
    excl = list(set(seen + reported))
    lg = safe(user, 'looking_gender', '')
    lz = safe(user, 'looking_zodiac', '')
    filters = [f"user_id NOT IN ({','.join(['?']*len(excl))})"] if excl else ["1=1"]
    params = excl[:]
    if lg and lg not in ('Both', 'Any'):
        filters.append("(gender=? OR gender IS NULL)")
        params.append(lg)
    order = f"CASE WHEN zodiac='{lz}' THEN 0 ELSE 1 END, stars DESC, RANDOM()" if lz and lz not in ('Any','') else "stars DESC, RANDOM()"
    query = f"SELECT * FROM users WHERE {' AND '.join(filters)} ORDER BY {order} LIMIT 1"    r = execute_query(query, params)
    p_row = r.fetchone() if r else None
    if not p_row:
        if len(seen) > 1:
            execute_query("DELETE FROM seen WHERE user_id=?", (uid,), commit=True)
            bot.send_message(uid, "🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ...")
            find_match(m)
        else:
            bot.send_message(uid, "😔 ကိုက်ညီသူ မရှိသေးပါ။", reply_markup=main_kb())
        return
    p = dict(p_row)
    execute_query("INSERT OR IGNORE INTO seen VALUES(?,?)", (uid, p['user_id']), commit=True)
    note = f"\n_({lz} မတွေ့သောကြောင့် အနီးစပ်ဆုံးပြပေးနေပါသည်)_" if lz and lz not in ('Any','') and safe(p,'zodiac','') != lz else ''
    text = fmt_profile(p) + note
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("❤️ Like", callback_data=f"like_{p['user_id']}"), InlineKeyboardButton("⏭ Skip", callback_data="skip_match"), InlineKeyboardButton("🚩 Report", callback_data=f"report_{p['user_id']}"))
    if p.get('photo'):
        try: bot.send_photo(uid, p['photo'], caption=text, parse_mode="Markdown", reply_markup=kb)
        except: bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    else:
        bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)

# ═══════════════════════════════════════════════════════════════
# 🔘  CALLBACKS (Match Logic & Unlock Gate)
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def on_cb(c):
    uid = c.message.chat.id
    data = c.data
    try:
        if data == "my_invite":
            link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
            refs = get_ref_count(uid)
            kb = InlineKeyboardMarkup()
            kb.row(InlineKeyboardButton("📤 Share လုပ်မည်", url=f"https://t.me/share/url?url={link}&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
            bot.send_message(uid, f"🔗 *Invite Link*\n\n`{link}`\n\n👥 Join ဖြစ်သူ: *{refs}/{SHARE_NEEDED}*\n{'✅ Unlock ပြီး' if is_unlocked(uid) else f'🔒 {SHARE_NEEDED-refs} ကျန်'}", parse_mode="Markdown", reply_markup=kb)

        elif data == "reset_profile":
            try: bot.delete_message(uid, c.message.message_id)
            except: pass
            user_reg[uid] = {}
            bot.send_message(uid, "🔄 Profile ပြန်လုပ်မည်\n\n📛 နာမည် -", reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(c.message, reg_name)

        elif data == "skip_match":
            try: bot.delete_message(uid, c.message.message_id)
            except: pass
            find_match(c.message)

        elif data.startswith("like_"):            tid = int(data[5:])
            try: bot.delete_message(uid, c.message.message_id)
            except: pass
            me = get_user(uid)
            if not me: return
            kb = InlineKeyboardMarkup()
            kb.row(InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{uid}"), InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline"))
            cap = f"💌 *'{safe(me,'name','တစ်ယောက်')}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n" + fmt_profile(me)
            try:
                if me.get('photo'): bot.send_photo(tid, me['photo'], caption=cap, parse_mode="Markdown", reply_markup=kb)
                else: bot.send_message(tid, cap, parse_mode="Markdown", reply_markup=kb)
                bot.send_message(uid, "❤️ Like ပို့လိုက်ပါပြီ! တစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊", reply_markup=main_kb())
            except: bot.send_message(uid, "⚠️ တစ်ဖက်လူက Bot Block ထားလို့ မပို့နိုင်ပါ။", reply_markup=main_kb())

        elif data.startswith("accept_"):
            liker_id = int(data[7:])
            try: bot.delete_message(uid, c.message.message_id)
            except: pass
            liker = get_user(liker_id)
            me = get_user(uid)

            def deliver_match(to_uid, partner_uid, partner_name):
                if is_unlocked(to_uid):
                    try: bot.send_message(to_uid, f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n[ဒီမှာနှိပ်ပြီး](tg://user?id={partner_uid}) {partner_name} နဲ့ စကားပြောနိုင်ပါပြီ 🎉\n\n✅ သင် Unlock ဖြစ်ပြီးပါပြီ", parse_mode="Markdown", reply_markup=main_kb())
                    except: pass
                else:
                    link = f"https://t.me/{BOT_USERNAME}?start=ref_{to_uid}"
                    kb = InlineKeyboardMarkup()
                    kb.row(InlineKeyboardButton("📤 Share လုပ်မည်", url=f"https://t.me/share/url?url={link}&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
                    kb.row(InlineKeyboardButton("✅ စစ်ဆေးမည်", callback_data="check_unlock"))
                    execute_query("INSERT OR REPLACE INTO pending_match VALUES(?,?,datetime('now'))", (to_uid, partner_uid), commit=True)
                    try: bot.send_message(to_uid, f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n🔒 *ဖူးစာရှင်ရဲ့ Link ကိုရဖို့ Unlock လုပ်ပါ*\n\nမိတ်ဆွေ *{SHARE_NEEDED}* ယောက် Bot ကိုသုံးစေပြီးမှ Link ရပါမည် 🙏\n\n📊 ဖိတ်ပြီး Join ဖြစ်သူ: *{get_ref_count(to_uid)}/{SHARE_NEEDED}*\n🎯 ကျန်: *{SHARE_NEEDED - get_ref_count(to_uid)}* ယောက်\n\n🔗 `{link}`\n\nLink ကို Share လုပ်ပြီး စစ်ဆေးပေးပါ 👇", parse_mode="Markdown", disable_web_page_preview=True, reply_markup=kb)
                    except: pass

            deliver_match(uid, liker_id, safe(liker,'name','ဖူးစာရှင်'))
            deliver_match(liker_id, uid, safe(me,'name','ဖူးစာရှင်'))
            bot.answer_callback_query(c.id, "🎉 လက်ခံလိုက်ပါပြီ!")

        elif data == "decline":
            try: bot.delete_message(uid, c.message.message_id)
            except: pass
            bot.send_message(uid, "❌ ငြင်းဆန်လိုက်ပါပြီ။", reply_markup=main_kb())

        elif data == "check_unlock":
            refs = get_ref_count(uid)
            if refs >= SHARE_NEEDED:
                bot.answer_callback_query(c.id, f"🎉 {refs} ယောက်ပြည့်ပါပြီ! Unlock ဖြစ်ပါပြီ!", show_alert=True)
                r = execute_query("SELECT partner_id FROM pending_match WHERE user_id=?", (uid,))
                row = r.fetchone() if r else None
                if row:                    pid = row[0]
                    execute_query("DELETE FROM pending_match WHERE user_id=?", (uid,), commit=True)
                    try: bot.send_message(uid, f"✅ *Unlock ဖြစ်သွားပါပြီ!*\n\n[ဒီမှာနှိပ်ပြီး](tg://user?id={pid}) ဖူးစာရှင်နဲ့ စကားပြောနိုင်ပါပြီ 🎉", parse_mode="Markdown", reply_markup=main_kb())
                    except: pass
                try: bot.delete_message(uid, c.message.message_id)
                except: pass
            else:
                bot.answer_callback_query(c.id, f"⚠️ ကျန်သေးသည် {SHARE_NEEDED - refs} ယောက်။ ဆက်ဖိတ်ကြားပါ!", show_alert=True)

        elif data.startswith("report_"):
            tid = int(data[7:])
            execute_query("INSERT OR IGNORE INTO reports VALUES(?,?)", (uid, tid), commit=True)
            bot.answer_callback_query(c.id, "🚩 Report လုပ်ပြီး", show_alert=True)
            try: bot.delete_message(uid, c.message.message_id)
            except: pass
            bot.send_message(uid, "✅ Report လုပ်ပြီးပါပြီ", reply_markup=main_kb())

    except Exception as e:
        print(f"Callback error: {e}")

# ═══════════════════════════════════════════════════════════════
# 🔁  MENU & POLLING
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "🔄 Profile ပြန်လုပ်")
def cmd_reset(m):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့", callback_data="reset_profile"), InlineKeyboardButton("❌ မဟုတ်ပါ", callback_data="cancel_cb"))
    bot.send_message(m.chat.id, "⚠️ Profile ကို ပြန်လုပ်မှာ သေချာပါသလား?\n_(ဟောင်းသွားပါမည်)_", parse_mode="Markdown", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "ℹ️ အကူအညီ")
def show_help(m):
    bot.send_message(m.chat.id, "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n🔍 *ဖူးစာရှာမည်* — ကိုက်ညီသူရှာပါ\n👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n🔄 *Profile ပြန်လုပ်* — Profile အသစ်စမည်\n\n*Unlock လုပ်နည်း*\nMatch ဖြစ်ရင် Link ရဖို့ မိတ်ဆွေများ ဖိတ်ပါ\n7 ဦးပြည့်ရင် အလိုအလျောက် Unlock ဖြစ်ပါမယ်", parse_mode="Markdown", reply_markup=main_kb())

@bot.callback_query_handler(func=lambda c: c.data == "cancel_cb")
def cancel_cb(c):
    try: bot.delete_message(c.message.chat.id, c.message.message_id)
    except: pass
    bot.answer_callback_query(c.id, "ပယ်ဖျက်ပြီး")

print("✅ Yay Zat Bot Started Successfully")
while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=30)
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"Polling Error: {e}")
        time.sleep(5)
