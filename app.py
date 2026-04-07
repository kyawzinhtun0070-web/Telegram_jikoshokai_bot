"""
Yay Zat Zodiac Bot — Full Rewrite
Fixes: photo, match flow, share gate, star priority, polling crash, error notify
"""
import telebot
import sqlite3
import threading
import traceback
import time
import requests as req_lib
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
BOT_USERNAME = "YayZatBot"      # ← သင့် bot username ပြောင်းထည့်ပါ (@ မပါ)
SHARE_NEEDED = 7                # ဘယ်နှစ်ယောက်ဖိတ်ကြားမှ match link ရမည်

ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

bot = telebot.TeleBot(TOKEN, threaded=True)

# ═══════════════════════════════════════════════════════════════
# 💾  DATABASE
# ═══════════════════════════════════════════════════════════════
DB_FILE  = 'yayzat.db'
_db_lock = threading.Lock()
_db      = None

def open_db():
    global _db
    _db = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=10)
    _db.row_factory = sqlite3.Row
    _db.execute("PRAGMA journal_mode=WAL")
    _db.execute("PRAGMA busy_timeout=5000")
    _db.execute("PRAGMA synchronous=NORMAL")
    return _db

open_db()

def xq(sql, params=()):
    """Execute + commit"""
    global _db
    with _db_lock:
        for attempt in range(3):
            try:
                cur = _db.execute(sql, params)
                _db.commit()
                return cur
            except sqlite3.OperationalError:
                try: open_db()
                except: pass
                time.sleep(0.2)
        return None

def xr(sql, params=()):
    """Read query"""
    global _db
    with _db_lock:
        for attempt in range(3):
            try:
                return _db.execute(sql, params)
            except sqlite3.OperationalError:
                try: open_db()
                except: pass
                time.sleep(0.2)
        return None

def init_db():
    xq('''CREATE TABLE IF NOT EXISTS users (
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
        stars          INTEGER DEFAULT 0,
        created_at     TEXT DEFAULT (datetime('now','localtime')),
        updated_at     TEXT DEFAULT (datetime('now','localtime'))
    )''')
    xq('''CREATE TABLE IF NOT EXISTS seen (
        user_id INTEGER, seen_id INTEGER,
        PRIMARY KEY (user_id, seen_id)
    )''')
    xq('''CREATE TABLE IF NOT EXISTS reports (
        reporter_id INTEGER, reported_id INTEGER,
        PRIMARY KEY (reporter_id, reported_id)
    )''')
    xq('''CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER, referred_id INTEGER,
        PRIMARY KEY (referrer_id, referred_id)
    )''')
    xq('''CREATE TABLE IF NOT EXISTS pending_match (
        user_id    INTEGER PRIMARY KEY,
        partner_id INTEGER,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    # safe column adds
    existing = {r[1] for r in xr("PRAGMA table_info(users)") or []}
    for col,typ in [('bio','TEXT'),('song','TEXT'),('looking_type','TEXT'),('stars','INTEGER DEFAULT 0')]:
        if col not in existing:
            try: xq(f"ALTER TABLE users ADD COLUMN {col} {typ}")
            except: pass

init_db()

# ── CRUD ──────────────────────────────────────────────────────
UFIELDS = ['name','age','zodiac','city','hobby','job','song','bio',
           'gender','looking_gender','looking_zodiac','looking_type','photo','stars']

def db_get(uid):
    r = xr('SELECT * FROM users WHERE user_id=?',(uid,))
    row = r.fetchone() if r else None
    return dict(row) if row else None

def db_save(uid, data):
    old = db_get(uid)
    # preserve photo if not in new data
    if old and not data.get('photo') and old.get('photo'):
        data['photo'] = old['photo']
    # preserve stars
    if old:
        data['stars'] = old.get('stars', 0)
    else:
        data.setdefault('stars', 0)
    cols = ','.join(UFIELDS)
    ph   = ','.join(['?']*len(UFIELDS))
    vals = [data.get(f) for f in UFIELDS]
    upd  = ','.join([f"{f}=excluded.{f}" for f in UFIELDS])
    xq(f"INSERT INTO users (user_id,{cols},updated_at) "
       f"VALUES (?,{ph},datetime('now','localtime')) "
       f"ON CONFLICT(user_id) DO UPDATE SET {upd},"
       f"updated_at=datetime('now','localtime')",
       [uid]+vals)

def db_update_field(uid, field, value):
    if field not in set(UFIELDS): return
    xq(f"UPDATE users SET {field}=?,updated_at=datetime('now','localtime') WHERE user_id=?",
       (value, uid))

def db_delete(uid):
    xq('DELETE FROM users WHERE user_id=?',(uid,))
    xq('DELETE FROM seen WHERE user_id=? OR seen_id=?',(uid,uid))
    xq('DELETE FROM pending_match WHERE user_id=? OR partner_id=?',(uid,uid))

def db_all(): return [dict(r) for r in (xr('SELECT * FROM users') or [])]
def db_ids(): return [r[0] for r in (xr('SELECT user_id FROM users') or [])]
def db_count():
    r = xr('SELECT COUNT(*) FROM users')
    return r.fetchone()[0] if r else 0

def db_seen_add(uid,sid): xq('INSERT OR IGNORE INTO seen VALUES(?,?)',(uid,sid))
def db_seen_get(uid):
    r = xr('SELECT seen_id FROM seen WHERE user_id=?',(uid,))
    return {row[0] for row in r} if r else set()
def db_seen_clear(uid): xq('DELETE FROM seen WHERE user_id=?',(uid,))

def db_report(a,b): xq('INSERT OR IGNORE INTO reports VALUES(?,?)',(a,b))
def db_reported_by(uid):
    r = xr('SELECT reported_id FROM reports WHERE reporter_id=?',(uid,))
    return {row[0] for row in r} if r else set()

def db_ref_add(referrer, referred):
    xq('INSERT OR IGNORE INTO referrals(referrer_id,referred_id) VALUES(?,?)',
       (referrer,referred))
    # +1 star to referrer
    xq('UPDATE users SET stars=stars+1 WHERE user_id=?',(referrer,))

def db_ref_count(uid):
    r = xr('SELECT COUNT(*) FROM referrals WHERE referrer_id=?',(uid,))
    return r.fetchone()[0] if r else 0

def db_is_unlocked(uid):
    if uid == ADMIN_ID: return True
    return db_ref_count(uid) >= SHARE_NEEDED

# pending match
def pm_set(uid, partner_id):
    xq('INSERT OR REPLACE INTO pending_match(user_id,partner_id) VALUES(?,?)',
       (uid,partner_id))

def pm_get(uid):
    r = xr('SELECT partner_id FROM pending_match WHERE user_id=?',(uid,))
    row = r.fetchone() if r else None
    return row[0] if row else None

def pm_clear(uid): xq('DELETE FROM pending_match WHERE user_id=?',(uid,))

def db_stats():
    def n(q): r=xr(q); return r.fetchone()[0] if r else 0
    return {
        'total'   : n('SELECT COUNT(*) FROM users'),
        'male'    : n("SELECT COUNT(*) FROM users WHERE gender='Male'"),
        'female'  : n("SELECT COUNT(*) FROM users WHERE gender='Female'"),
        'photo'   : n('SELECT COUNT(*) FROM users WHERE photo IS NOT NULL'),
        'refs'    : n('SELECT COUNT(*) FROM referrals'),
        'unlocked': n(f'SELECT COUNT(*) FROM users WHERE '
                      f'(SELECT COUNT(*) FROM referrals WHERE referrer_id=users.user_id)>={SHARE_NEEDED}'),
    }

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

def kb(uid): return admin_kb() if uid == ADMIN_ID else main_kb()

# ═══════════════════════════════════════════════════════════════
# 🔧  UTILITIES
# ═══════════════════════════════════════════════════════════════
def safe(d, k, fb='—'):
    v = (d or {}).get(k)
    if isinstance(v, str): v = v.strip()
    return v if v else fb

def check_channel(uid):
    try:
        return bot.get_chat_member(CHANNEL_ID,uid).status in (
            'member','creator','administrator')
    except: return False

def notify_admin(txt):
    try: bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")
    except: pass

def report_err(ctx, err, uid=None):
    tb = traceback.format_exc()[-600:]
    msg = (f"🔴 *Bot Error*\n📍 `{ctx}`\n👤 `{uid}`\n"
           f"❌ `{type(err).__name__}: {err}`\n"
           f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
           f"```\n{tb}```")
    try:
        req_lib.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"},
            timeout=8)
    except: pass

def stars_display(n):
    n = min(n, 10)
    return '⭐'*n if n > 0 else '—'

def invite_url(uid):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

def share_btn(uid):
    url = invite_url(uid)
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton(
        "📤 မိတ်ဆွေများကို Share လုပ်မည်",
        url=f"https://t.me/share/url?url={url}"
            f"&text=✨+Yay+Zat+Zodiac+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
    m.row(InlineKeyboardButton(
        "✅ Share ပြီးပြီ — Join စစ်မည်",
        callback_data="chk_share"))
    return m

def fmt_profile(tp, title='👤 *ပရိုဖိုင်*'):
    bio   = f"\n📝 အကြောင်း  : {safe(tp,'bio')}"  if (tp or {}).get('bio') else ''
    ltype = f"\n🎯 ရှာဖွေရန်  : {safe(tp,'looking_type')}" if (tp or {}).get('looking_type') else ''
    return (
        f"{title}\n\n"
        f"📛 နာမည်   : {safe(tp,'name')}\n"
        f"🎂 အသက်   : {safe(tp,'age')} နှစ်\n"
        f"🔮 ရာသီ   : {safe(tp,'zodiac')}\n"
        f"📍 မြို့    : {safe(tp,'city')}\n"
        f"🎨 ဝါသနာ  : {safe(tp,'hobby')}\n"
        f"💼 အလုပ်   : {safe(tp,'job')}\n"
        f"🎵 သီချင်း  : {safe(tp,'song')}"
        f"{bio}{ltype}\n"
        f"⚧ လိင်    : {safe(tp,'gender')}\n"
        f"💑 ရှာဖွေ  : {safe(tp,'looking_gender')} / "
        f"{safe(tp,'looking_zodiac','Any')}"
    )

# ═══════════════════════════════════════════════════════════════
# 🔒  SHARE GATE
# ═══════════════════════════════════════════════════════════════
def show_share_gate(uid):
    cnt  = db_ref_count(uid)
    need = max(0, SHARE_NEEDED - cnt)
    link = invite_url(uid)
    bot.send_message(uid,
        f"🔒 *ဖူးစာရှာရန် Unlock လိုအပ်ပါသည်*\n\n"
        f"မိတ်ဆွေ *{SHARE_NEEDED}* ယောက် Bot ကိုသုံးစေပြီးမှ\n"
        f"ဖူးစာရှင်ရဲ့ Telegram link ကို ပေးမည်ဖြစ်ပါသည် 🙏\n\n"
        f"📊 ဖိတ်ပြီး Join ဖြစ်သူ : *{cnt}/{SHARE_NEEDED}*\n"
        f"🎯 ကျန် : *{need}* ယောက်\n\n"
        f"🔗 `{link}`\n\n"
        f"Link ကို မိတ်ဆွေများထံ Share ပြီး စစ်ဆေးပေးပါ 👇",
        parse_mode="Markdown",
        reply_markup=share_btn(uid))

def process_unlock(uid):
    """Unlock ဖြစ်ပြီဆိုရင် pending match ရှိရင် link ပေး"""
    partner_id = pm_get(uid)
    if partner_id:
        pm_clear(uid)
        partner = db_get(partner_id)
        try:
            bot.send_message(uid,
                f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
                f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner_id}) "
                f"{safe(partner,'name')} နဲ့ စကားပြောနိုင်ပါပြီ 🎉",
                parse_mode="Markdown", reply_markup=kb(uid))
        except Exception as e:
            report_err('process_unlock/send', e, uid)

# ═══════════════════════════════════════════════════════════════
# 🚀  /start
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def start_bot(message):
    uid  = message.chat.id
    args = message.text.split()
    try:
        if len(args)>1 and args[1].startswith('ref_'):
            referrer = int(args[1][4:])
            if referrer != uid and db_get(referrer) and not db_get(uid):
                db_ref_add(referrer, uid)
                # auto-check unlock for referrer
                if db_is_unlocked(referrer):
                    process_unlock(referrer)
    except Exception as e:
        report_err('start/ref', e, uid)

    if db_get(uid):
        bot.send_message(uid,
            "✨ *ကြိုဆိုပါတယ်!* ✨\n\nခလုတ်များနှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇",
            parse_mode="Markdown", reply_markup=kb(uid))
        return

    try:
        tg = message.from_user.username or str(uid)
        fn = message.from_user.first_name or ''
        ln = message.from_user.last_name  or ''
    except: tg=fn=ln=str(uid)

    notify_admin(
        f"🆕 *User သစ်*\n👤 {fn} {ln} @{tg}\n🆔 `{uid}`\n"
        f"👥 {db_count()} ယောက်\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    user_reg[uid] = {}
    bot.send_message(uid,
        "✨ *Yay Zat Zodiac မှ ကြိုဆိုပါတယ်!* ✨\n\n"
        "ဖူးစာရှင်/မိတ်ဆွေကို ရှာဖွေဖို့ မေးခွန်းလေးတွေ ဖြေပေးပါ 🙏\n"
        "_( /skip — ကျော်ချင်ရင် )_\n\n"
        "📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_name)

# temp state
user_reg = {}

# ═══════════════════════════════════════════════════════════════
# 📝  REGISTRATION  (error-safe wrapper)
# ═══════════════════════════════════════════════════════════════
def safe_step(fn):
    def w(msg):
        try: fn(msg)
        except Exception as e:
            report_err(f'reg/{fn.__name__}', e, msg.chat.id)
            bot.send_message(msg.chat.id,
                "⚠️ တစ်ခုခုမှားသွားပါသည်。/start ကိုနှိပ်ပြီး ပြန်စကြည့်ပါ。")
    return w

@safe_step
def reg_name(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['name']=m.text.strip()
    bot.send_message(uid,"🎂 အသက်? (/skip)-")
    bot.register_next_step_handler(m,reg_age)

@safe_step
def reg_age(m):
    uid=m.chat.id
    if m.text and m.text!='/skip':
        if m.text.strip().isdigit(): user_reg.setdefault(uid,{})['age']=m.text.strip()
        else:
            bot.send_message(uid,"⚠️ ဂဏန်းသာ (/skip)—"); bot.register_next_step_handler(m,reg_age); return
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('/skip')
    bot.send_message(uid,"🔮 ရာသီခွင်?",reply_markup=mk)
    bot.register_next_step_handler(m,reg_zodiac)

@safe_step
def reg_zodiac(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['zodiac']=m.text.strip()
    bot.send_message(uid,"📍 မြို့ (ဥပမာ Mandalay)? (/skip)-",reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m,reg_city)

@safe_step
def reg_city(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['city']=m.text.strip()
    bot.send_message(uid,"🎨 ဝါသနာ (ဥပမာ ခရီးသွား,ဂီတ)? (/skip)-")
    bot.register_next_step_handler(m,reg_hobby)

@safe_step
def reg_hobby(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['hobby']=m.text.strip()
    bot.send_message(uid,"💼 အလုပ်? (/skip)-")
    bot.register_next_step_handler(m,reg_job)

@safe_step
def reg_job(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['job']=m.text.strip()
    bot.send_message(uid,"🎵 အကြိုက်ဆုံး သီချင်း? (/skip)-")
    bot.register_next_step_handler(m,reg_song)

@safe_step
def reg_song(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['song']=m.text.strip()
    bot.send_message(uid,
        "📝 *မိမိအကြောင်း အတိုချုံး* (/skip)-\n"
        "_(ဥပမာ: ဆေးကျောင်းသား, ဂီတကိုနှစ်သက်သူ)_",
        parse_mode="Markdown")
    bot.register_next_step_handler(m,reg_bio)

@safe_step
def reg_bio(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['bio']=m.text.strip()
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    mk.row('💑 ဖူးစာရှာနေသူ','🤝 မိတ်ဆွေဖွဲ့ချင်သူ')
    mk.add('/skip')
    bot.send_message(uid,"🎯 ဘာရှာနေပါသလဲ?",reply_markup=mk)
    bot.register_next_step_handler(m,reg_ltype)

@safe_step
def reg_ltype(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['looking_type']=m.text.strip()
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    mk.add('Male','Female','/skip')
    bot.send_message(uid,"⚧ သင့်လိင်?",reply_markup=mk)
    bot.register_next_step_handler(m,reg_gender)

@safe_step
def reg_gender(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['gender']=m.text.strip()
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    mk.add('Male','Female','Both','/skip')
    bot.send_message(uid,"💑 ရှာဖွေနေတဲ့ လိင်?",reply_markup=mk)
    bot.register_next_step_handler(m,reg_lgender)

@safe_step
def reg_lgender(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['looking_gender']=m.text.strip()
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('Any','/skip')
    bot.send_message(uid,"🔮 ရှာဖွေနေတဲ့ ရာသီ?",reply_markup=mk)
    bot.register_next_step_handler(m,reg_lzodiac)

@safe_step
def reg_lzodiac(m):
    uid=m.chat.id
    if m.text and m.text!='/skip': user_reg.setdefault(uid,{})['looking_zodiac']=m.text.strip()
    bot.send_message(uid,
        "📸 Profile ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက /skip)_",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m,reg_photo)

@safe_step
def reg_photo(m):
    uid    = m.chat.id
    is_new = db_get(uid) is None
    if m.text == '/skip':
        # preserve old photo
        old = db_get(uid)
        if old and old.get('photo'):
            user_reg.setdefault(uid,{})['photo'] = old['photo']
    elif m.content_type == 'photo':
        user_reg.setdefault(uid,{})['photo'] = m.photo[-1].file_id
    else:
        bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ (သို့) /skip ဟုရိုက်ပါ-")
        bot.register_next_step_handler(m,reg_photo); return

    data = user_reg.pop(uid, {})
    db_save(uid, data)

    bot.send_message(uid,
        f"✅ Profile {'တည်ဆောက်' if is_new else 'ပြင်ဆင်'} ပြီးပါပြီ! 🎉\n\n"
        f"ခလုတ်များ နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇",
        parse_mode="Markdown", reply_markup=kb(uid))

    if is_new:
        notify_admin(
            f"🎉 *မှတ်ပုံတင် ပြီးမြောက်!*\n🆔 `{uid}` — {safe(data,'name')}\n"
            f"👥 {db_count()} ယောက်\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ═══════════════════════════════════════════════════════════════
# 👤  MY PROFILE
# ═══════════════════════════════════════════════════════════════
def show_profile(message):
    uid = message.chat.id
    tp  = db_get(uid)
    if not tp:
        bot.send_message(uid,"Profile မရှိသေးပါ။ /start ကိုနှိပ်ပါ。",reply_markup=kb(uid)); return

    stars = tp.get('stars') or 0
    refs  = db_ref_count(uid)
    text  = (
        fmt_profile(tp) +
        f"\n\n⭐ ကြယ်ပွင့်  : {stars_display(stars)} ({stars} ခု)\n"
        f"🔗 ဖိတ်ကြားမှု: {refs}/{SHARE_NEEDED}"
        + (" ✅ Unlock ပြီး" if db_is_unlocked(uid) else f" 🔒 ({SHARE_NEEDED-refs} ကျန်)")
    )

    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📛 နာမည်",   cb("edit_name")),
          InlineKeyboardButton("🎂 အသက်",    cb("edit_age")))
    m.row(InlineKeyboardButton("🔮 ရာသီ",    cb("edit_zodiac")),
          InlineKeyboardButton("📍 မြို့",    cb("edit_city")))
    m.row(InlineKeyboardButton("🎨 ဝါသနာ",  cb("edit_hobby")),
          InlineKeyboardButton("💼 အလုပ်",   cb("edit_job")))
    m.row(InlineKeyboardButton("🎵 သီချင်း", cb("edit_song")),
          InlineKeyboardButton("📝 Bio",     cb("edit_bio")))
    m.row(InlineKeyboardButton("📸 ဓာတ်ပုံ",cb("edit_photo")))
    m.row(InlineKeyboardButton("🔗 Invite Link", cb("my_invite")))
    m.row(InlineKeyboardButton("🔄 အကုန်ပြန်လုပ်", cb("reset_confirm")),
          InlineKeyboardButton("🗑 ဖျက်",   cb("del_confirm")))

    if tp.get('photo'):
        try:
            bot.send_photo(uid, tp['photo'], caption=text, reply_markup=m, parse_mode="Markdown")
        except Exception as e:
            report_err('show_profile/photo', e, uid)
            bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")
    else:
        bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")

def cb(d): return d  # alias for readability

# ═══════════════════════════════════════════════════════════════
# 🔍  FIND MATCH  — star priority sort
# ═══════════════════════════════════════════════════════════════
def find_match(message):
    uid = message.chat.id
    me  = db_get(uid)
    if not me:
        bot.send_message(uid,"/start ကိုနှိပ်ပြီး Profile ဦးတည်ဆောက်ပါ。",reply_markup=kb(uid)); return

    if not db_is_unlocked(uid):
        show_share_gate(uid); return

    if not check_channel(uid):
        m=InlineKeyboardMarkup()
        m.add(InlineKeyboardButton("📢 Channel Join မည်",url=CHANNEL_LINK))
        bot.send_message(uid,"⚠️ Channel ကို အရင် Join ပေးပါ。",reply_markup=m); return

    seen     = db_seen_get(uid)
    reported = db_reported_by(uid)
    excl     = seen | reported | {uid}

    lg = (me.get('looking_gender') or '').strip()
    lz = (me.get('looking_zodiac')  or '').strip()

    pool = [u for u in db_all()
            if u['user_id'] not in excl
            and (not lg or lg in ('Both','Any') or (u.get('gender') or '').strip()==lg)]

    if not pool:
        if seen:
            db_seen_clear(uid)
            bot.send_message(uid,"🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ...")
            find_match(message)
        else:
            bot.send_message(uid,
                "😔 သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ。\nဖော်ဆွေများကို ဖိတ်ကြားပါ 😊",
                reply_markup=kb(uid))
        return

    # ── Sort: zodiac match first, then by stars desc ──────────
    def sort_key(u):
        zodiac_match = 0 if (lz and lz not in ('Any','') and (u.get('zodiac') or '')==lz) else 1
        stars = -(u.get('stars') or 0)   # negative = higher stars first
        return (zodiac_match, stars)

    pool.sort(key=sort_key)
    target = pool[0]
    tid    = target['user_id']
    db_seen_add(uid, tid)

    note = ''
    if lz and lz not in ('Any','') and (target.get('zodiac') or '') != lz:
        note = f"\n_({lz} မတွေ့သောကြောင့် အနီးစပ်ဆုံးပြပေးနေပါသည်)_"

    text = fmt_profile(target, title=f"🎯 *မိတ်ဆွေနဲ့ ကိုက်ညီနိုင်မယ့်သူ*{note}")
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("❤️ Like",   callback_data=f"like_{tid}"),
          InlineKeyboardButton("⏭ Skip",   callback_data="skip"),
          InlineKeyboardButton("🚩 Report", callback_data=f"report_{tid}"))

    if target.get('photo'):
        try:
            bot.send_photo(uid, target['photo'], caption=text,
                           reply_markup=m, parse_mode="Markdown")
        except Exception as e:
            report_err('find_match/photo', e, uid)
            bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")
    else:
        bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")

# ═══════════════════════════════════════════════════════════════
# 🔄 RESET / ℹ️ HELP / 📊 STATS / 🛠 ADMIN
# ═══════════════════════════════════════════════════════════════
def do_reset(message):
    uid = message.chat.id
    old = db_get(uid)
    user_reg[uid] = dict(old) if old else {}
    bot.send_message(uid,
        "🔄 *Profile ပြန်လုပ်မည်*\n\n/skip — ကျော်နိုင်ပါသည်\n\n📛 နာမည်-",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, reg_name)

def show_help(message):
    bot.send_message(message.chat.id,
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ဖူးစာရှာမည်* — ကိုက်ညီနိုင်မယ့်သူ ရှာပါ\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
        "🔄 *Profile ပြန်လုပ်* — Profile ပြန်ဖြည့်ပါ\n\n"
        "*Commands*\n/start /reset /deleteprofile\n\n"
        "⚠️ ပြဿနာများ Admin ထံ ဆက်သွယ်ပါ。",
        parse_mode="Markdown", reply_markup=kb(message.chat.id))

def show_stats(message):
    uid = message.chat.id
    if uid != ADMIN_ID:
        bot.send_message(uid,"⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်。"); return
    s = db_stats()
    bot.send_message(ADMIN_ID,
        f"📊 *Yay Zat — Admin Stats*\n\n"
        f"👥 စုစုပေါင်း   : *{s['total']}* ယောက်\n"
        f"♂️ ကျား        : {s['male']}\n"
        f"♀️ မ           : {s['female']}\n"
        f"📸 ဓာတ်ပုံပါ   : {s['photo']}\n"
        f"🔓 Unlock ပြီး : {s['unlocked']}\n"
        f"🔗 Referral    : {s['refs']}\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        parse_mode="Markdown", reply_markup=admin_kb())

def show_admin(message):
    if message.chat.id != ADMIN_ID: return
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📊 Stats",       callback_data="adm_stats"),
          InlineKeyboardButton("👥 Users",        callback_data="adm_users"))
    m.row(InlineKeyboardButton("📢 Broadcast",    callback_data="adm_bcast"),
          InlineKeyboardButton("🗑 User ဖျက်",   callback_data="adm_del"))
    m.row(InlineKeyboardButton("🔓 Manual Unlock",callback_data="adm_unlock"))
    bot.send_message(ADMIN_ID,"🛠 *Admin Panel*",parse_mode="Markdown",reply_markup=m)

def _bcast(m):
    if m.text=='/cancel': bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    ok=fail=0
    for uid in db_ids():
        try: bot.send_message(uid,f"📢 *Admin မှ*\n\n{m.text}",parse_mode="Markdown"); ok+=1
        except: fail+=1
    bot.send_message(ADMIN_ID,f"✅ {ok} ရောက် / ❌ {fail} မရောက်")

def _del_user(m):
    if m.text=='/cancel': bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    try:
        uid=int(m.text.strip())
        if db_get(uid): db_delete(uid); bot.send_message(ADMIN_ID,f"✅ `{uid}` ဖျက်ပြီး",parse_mode="Markdown")
        else: bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ。")
    except: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ。")

def _unlock_user(m):
    if m.text=='/cancel': bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    try:
        uid=int(m.text.strip())
        if db_get(uid):
            xq('UPDATE users SET stars=stars+? WHERE user_id=?',(SHARE_NEEDED,uid))
            xq(f'INSERT OR IGNORE INTO referrals(referrer_id,referred_id) '
               f'SELECT ?,? WHERE NOT EXISTS('
               f'SELECT 1 FROM referrals WHERE referrer_id=? AND referred_id=?)',
               (uid,0,uid,0))
            # manually insert enough ref rows to unlock
            for i in range(SHARE_NEEDED):
                xq('INSERT OR IGNORE INTO referrals(referrer_id,referred_id) VALUES(?,?)',
                   (uid, -(i+1)))
            bot.send_message(ADMIN_ID,f"✅ `{uid}` unlock ပြီး",parse_mode="Markdown")
            try: bot.send_message(uid,
                "✅ Admin က unlock လုပ်ပေးပြီးပါပြီ!\n🔍 ဖူးစာရှာနိုင်ပါပြီ 💖",
                reply_markup=kb(uid))
            except: pass
        else: bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ。")
    except: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ。")

# field edit save
def save_edit(message, field):
    uid = message.chat.id
    try:
        if field == 'photo':
            if message.content_type != 'photo':
                bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ。"); return
            db_update_field(uid,'photo',message.photo[-1].file_id)
        else:
            if not message.text or not message.text.strip():
                bot.send_message(uid,"⚠️ ဗလာမထားနဲ့-")
                bot.register_next_step_handler(message,save_edit,field); return
            db_update_field(uid,field,message.text.strip())
        bot.send_message(uid,"✅ ပြင်ဆင်မှု အောင်မြင်!",reply_markup=kb(uid))
    except Exception as e:
        report_err(f'save_edit/{field}',e,uid)
        bot.send_message(uid,"⚠️ မှားသွားပါသည်。ထပ်ကြိုးစားကြည့်ပါ。")

# ═══════════════════════════════════════════════════════════════
# 🔘  MENU ROUTER
# ═══════════════════════════════════════════════════════════════
MENU = {
    "🔍 ဖူးစာရှာမည်"     : find_match,
    "👤 ကိုယ့်ပရိုဖိုင်"  : show_profile,
    "ℹ️ အကူအညီ"          : show_help,
    "🔄 Profile ပြန်လုပ်"  : lambda m: confirm_reset(m),
    "📊 စာရင်းအင်း"       : show_stats,
    "🛠 Admin Panel"       : show_admin,
}

def confirm_reset(message):
    uid = message.chat.id
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("✅ ဟုတ်တယ် ပြန်လုပ်မည်", callback_data="reset_go"),
          InlineKeyboardButton("❌ မလုပ်တော့ပါ",          callback_data="reset_cancel"))
    bot.send_message(uid,
        "⚠️ Profile ကို ပြန်လုပ်မှာ သေချာပါသလား?\n"
        "_(skip ကျော်ပြီး ဟောင်းတွေ ထိန်းသိမ်းနိုင်ပါသည်)_",
        parse_mode="Markdown", reply_markup=m)

@bot.message_handler(func=lambda m: m.text in MENU)
def menu_router(message):
    try: MENU[message.text](message)
    except Exception as e:
        report_err(f'menu/{message.text}',e,message.chat.id)
        bot.send_message(message.chat.id,"⚠️ မှားသွားပါသည်。နောက်မှ ထပ်ကြိုးစားကြည့်ပါ。")

@bot.message_handler(commands=['reset'])
def cmd_reset(m):
    confirm_reset(m)

@bot.message_handler(commands=['myprofile'])
def cmd_profile(m): show_profile(m)

@bot.message_handler(commands=['stats'])
def cmd_stats(m): show_stats(m)

@bot.message_handler(commands=['deleteprofile'])
def cmd_delete(message):
    uid=message.chat.id
    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("✅ ဟုတ်တယ် ဖျက်မည်",callback_data="del_confirm"),
          InlineKeyboardButton("❌ မဖျက်တော့ပါ",     callback_data="del_cancel"))
    bot.send_message(uid,"⚠️ Profile ဖျက်မှာ သေချာပါသလား?",reply_markup=m)

# ═══════════════════════════════════════════════════════════════
# 📞  CALLBACK QUERY
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def on_cb(call):
    uid = call.message.chat.id
    d   = call.data
    try:
        _cb(call, uid, d)
    except Exception as e:
        report_err(f'cb/{d}',e,uid)
        try: bot.answer_callback_query(call.id,"⚠️ မှားသွားပါသည်。",show_alert=True)
        except: pass

def _cb(call, uid, d):

    # ── Share check ───────────────────────────────────────────
    if d == "chk_share":
        cnt = db_ref_count(uid)
        if cnt >= SHARE_NEEDED:
            bot.answer_callback_query(call.id,"🎉 Unlock ဖြစ်ပါပြီ!",show_alert=True)
            try: bot.delete_message(uid,call.message.message_id)
            except: pass
            bot.send_message(uid,
                f"✅ *{SHARE_NEEDED} ယောက် ပြည့်ပါပြီ! Unlock ဖြစ်ပါပြီ!* 🎉\n\n"
                f"🔍 ဖူးစာရှာမည် ကိုနှိပ်ပြီး ရှာနိုင်ပါပြီ 💖",
                parse_mode="Markdown",reply_markup=kb(uid))
            process_unlock(uid)
        else:
            need = SHARE_NEEDED - cnt
            bot.answer_callback_query(call.id,
                f"ကျန်သေးသည် {need} ယောက်。ဆက်ဖိတ်ကြားပါ!",show_alert=True)
        return

    # ── Reset confirm/go/cancel ───────────────────────────────
    elif d == "reset_confirm":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        confirm_reset(call.message)
        return

    elif d == "reset_go":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        do_reset(call.message)
        return

    elif d == "reset_cancel":
        bot.answer_callback_query(call.id,"မလုပ်တော့ပါ 👍")
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        return

    # ── Delete confirm ────────────────────────────────────────
    elif d == "del_confirm":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        db_delete(uid)
        bot.send_message(uid,
            "🗑 Profile ဖျက်ပြီးပါပြီ。\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်。",
            reply_markup=ReplyKeyboardRemove())
        return

    elif d == "del_cancel":
        bot.answer_callback_query(call.id,"မဖျက်တော့ပါ 👍")
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        return

    # ── Edit field ────────────────────────────────────────────
    elif d.startswith("edit_"):
        field = d[5:]
        try: bot.delete_message(uid,call.message.message_id)
        except: pass

        LABELS = {
            'name':'နာမည်','age':'အသက်','zodiac':'ရာသီ','city':'မြို့',
            'hobby':'ဝါသနာ','job':'အလုပ်','song':'သီချင်း','bio':'Bio',
            'looking_type':'ရှာဖွေမည့်အမျိုးအစား',
            'gender':'လိင်','looking_gender':'ရှာဖွေမည့်လိင်',
            'looking_zodiac':'ရှာဖွေမည့်ရာသီ'
        }
        if field == 'photo':
            msg = bot.send_message(uid,"📸 ဓာတ်ပုံအသစ် ပေးပို့ပါ-",
                                   reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_edit, 'photo')
        else:
            label = LABELS.get(field, field)
            msg = bot.send_message(uid, f"📝 *{label}* အသစ် ရိုက်ထည့်ပါ-\n"
                                   f"_( /skip — မပြင်ဘဲကျော်ရန် )_",
                                   parse_mode="Markdown",
                                   reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_edit, field)
        return

    # ── Invite link ───────────────────────────────────────────
    elif d == "my_invite":
        cnt  = db_ref_count(uid)
        link = invite_url(uid)
        m = InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("📤 Share လုပ်မည်",
              url=f"https://t.me/share/url?url={link}"
                  f"&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
        bot.send_message(uid,
            f"🔗 *Invite Link*\n\n`{link}`\n\n"
            f"👥 Join ဖြစ်သူ : *{cnt}/{SHARE_NEEDED}*\n"
            + ("✅ Unlock ပြီး" if db_is_unlocked(uid) else f"🔒 {SHARE_NEEDED-cnt} ကျန်"),
            parse_mode="Markdown", reply_markup=m)
        return

    # ── Skip match ────────────────────────────────────────────
    elif d == "skip":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        find_match(call.message)
        return

    # ── Like ─────────────────────────────────────────────────
    elif d.startswith("like_"):
        tid = int(d[5:])
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        if not check_channel(uid):
            bot.answer_callback_query(call.id,"⚠️ Channel ကို Join ပါ!",show_alert=True); return

        me  = db_get(uid) or {}
        lnm = safe(me,'name','တစ်ယောက်')
        accept_m = InlineKeyboardMarkup()
        accept_m.row(
            InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{uid}"),
            InlineKeyboardButton("❌ ငြင်းမည်",  callback_data="decline"))
        cap = (f"💌 *'{lnm}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n"
               + fmt_profile(me, title='👤 *သူ/သူမ ရဲ့ Profile*'))
        try:
            if me.get('photo'):
                bot.send_photo(tid, me['photo'], caption=cap,
                               reply_markup=accept_m, parse_mode="Markdown")
            else:
                bot.send_message(tid, cap, reply_markup=accept_m, parse_mode="Markdown")
            bot.send_message(uid,
                "❤️ Like လုပ်လိုက်ပါပြီ!\nတစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊",
                reply_markup=kb(uid))
        except Exception as e:
            report_err('like/send',e,uid)
            bot.send_message(uid,"⚠️ တစ်ဖက်လူမှာ Bot Block ထားသဖြင့် ပေးပို့မရပါ。",
                             reply_markup=kb(uid))
        return

    # ── Accept ────────────────────────────────────────────────
    elif d.startswith("accept_"):
        liker_id = int(d[7:])
        try: bot.delete_message(uid,call.message.message_id)
        except: pass

        notify_admin(
            f"💖 *Match!* [A](tg://user?id={uid}) + [B](tg://user?id={liker_id})\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        # ── deliver link or show gate ──────────────────────────
        def deliver(me, partner):
            partner_data = db_get(partner)
            pname = safe(partner_data or {},'name','ဖူးစာရှင်')
            if db_is_unlocked(me):
                try:
                    bot.send_message(me,
                        f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
                        f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner}) "
                        f"{pname} နဲ့ စကားပြောနိုင်ပါပြီ 🎉",
                        parse_mode="Markdown", reply_markup=kb(me))
                except: pass
            else:
                pm_set(me, partner)    # store pending match
                show_share_gate(me)
        
        deliver(uid, liker_id)
        deliver(liker_id, uid)
        return

    # ── Decline ───────────────────────────────────────────────
    elif d == "decline":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        bot.send_message(uid,"❌ ငြင်းဆန်လိုက်ပါပြီ。",reply_markup=kb(uid))
        return

    # ── Report ───────────────────────────────────────────────
    elif d.startswith("report_"):
        tid = int(d[7:])
        db_report(uid,tid)
        bot.answer_callback_query(call.id,"🚩 Report လုပ်ပြီး。",show_alert=True)
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        notify_admin(
            f"🚩 *Report*\n{safe(db_get(uid),'name')} `{uid}` → "
            f"{safe(db_get(tid),'name')} `{tid}`")
        return

    # ── Admin ─────────────────────────────────────────────────
    elif d=="adm_stats" and uid==ADMIN_ID:
        show_stats(call.message); return

    elif d=="adm_users" and uid==ADMIN_ID:
        rows = db_all()[:30]
        lines = [f"{i}. {safe(u,'name')} `{u['user_id']}` "
                 f"⭐{u.get('stars',0)} "
                 f"{'🔓' if db_is_unlocked(u['user_id']) else '🔒'}"
                 for i,u in enumerate(rows,1)]
        bot.send_message(ADMIN_ID,
            "👥 *User List*\n\n"+("\n".join(lines) or "မရှိသေး"),
            parse_mode="Markdown"); return

    elif d=="adm_bcast" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"📢 Message (/cancel)—")
        bot.register_next_step_handler(msg,_bcast); return

    elif d=="adm_del" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"🗑 User ID (/cancel)—")
        bot.register_next_step_handler(msg,_del_user); return

    elif d=="adm_unlock" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"🔓 Unlock မည့် User ID (/cancel)—")
        bot.register_next_step_handler(msg,_unlock_user); return

    try: bot.answer_callback_query(call.id)
    except: pass

# ═══════════════════════════════════════════════════════════════
# 🔁  AUTO-RESTART POLLING — bot မရပ်ပါ
# ═══════════════════════════════════════════════════════════════
print(f"✅ Yay Zat Bot on [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
notify_admin(f"🟢 *Bot Online*\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=40, long_polling_timeout=40)
    except Exception as e:
        msg = (f"🔴 *Polling Error — Restarting...*\n"
               f"`{type(e).__name__}: {e}`\n"
               f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print(msg)
        try:
            req_lib.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"},
                timeout=8)
        except: pass
        time.sleep(5)
