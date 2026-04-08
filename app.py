"""
Yay Zat Zodiac Bot — Stable Release (Share After Match Flow)
"""
import telebot
import sqlite3
import threading
import traceback
import time
import requests as _req
from datetime import datetime
from urllib.parse import quote
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)

# ═══════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════
TOKEN        = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID   = -1003641016541
CHANNEL_LINK = "https://t.me/yayzatofficial"
ADMIN_ID     = 6131831207
BOT_USERNAME = "YayZatBot"
SHARE_NEEDED = 7  # Match ဖြစ်မှ unlock လုပ်ရမည့် အရေအတွက်

ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

bot = telebot.TeleBot(TOKEN, threaded=True)

# ═══════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════
DB_FILE  = 'yayzat.db'
_lock    = threading.Lock()
_db      = None

def open_db():
    global _db
    c = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    _db = c
    return c

open_db()

def xq(sql, p=()):    global _db
    with _lock:
        for attempt in range(3):
            try:
                cur = _db.execute(sql, p)
                _db.commit()
                return cur
            except sqlite3.OperationalError:
                try: open_db()
                except: pass
                time.sleep(0.3 * (attempt + 1))
        raise RuntimeError(f"Write query failed: {sql}")

def xr(sql, p=()):
    global _db
    with _lock:
        for attempt in range(3):
            try:
                return _db.execute(sql, p)
            except sqlite3.OperationalError:
                try: open_db()
                except: pass
                time.sleep(0.3 * (attempt + 1))
        raise RuntimeError(f"Read query failed: {sql}")

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
    xq('''CREATE TABLE IF NOT EXISTS reports (        reporter_id INTEGER, reported_id INTEGER,
        PRIMARY KEY (reporter_id, reported_id)
    )''')
    xq('''CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER, referred_id INTEGER,
        PRIMARY KEY (referrer_id, referred_id)
    )''')
    xq('''CREATE TABLE IF NOT EXISTS pending_match (
        user_id INTEGER PRIMARY KEY, partner_id INTEGER,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    try:
        ex = {r[1] for r in xr("PRAGMA table_info(users)")}
        for col, typ in [('bio','TEXT'),('song','TEXT'),
                         ('looking_type','TEXT'),('stars','INTEGER DEFAULT 0')]:
            if col not in ex:
                try: xq(f"ALTER TABLE users ADD COLUMN {col} {typ}")
                except: pass
    except: pass

init_db()

UFIELDS = ['name','age','zodiac','city','hobby','job','song','bio',
           'gender','looking_gender','looking_zodiac','looking_type','photo','stars']

def db_get(uid):
    r = xr('SELECT * FROM users WHERE user_id=?',(uid,))
    row = r.fetchone() if r else None
    return dict(row) if row else None

def db_save(uid, data):
    old = db_get(uid)
    if old:
        if not data.get('photo') and old.get('photo'):
            data['photo'] = old['photo']
        data['stars'] = old.get('stars', 0)
    else:
        data.setdefault('stars', 0)
    cols = ','.join(UFIELDS)
    ph   = ','.join(['?']*len(UFIELDS))
    vals = [data.get(f) for f in UFIELDS]
    upd  = ','.join([f"{f}=excluded.{f}" for f in UFIELDS])
    xq(f"INSERT INTO users (user_id,{cols},updated_at) "
       f"VALUES(?,{ph},datetime('now','localtime')) "
       f"ON CONFLICT(user_id) DO UPDATE SET {upd},"
       f"updated_at=datetime('now','localtime')",
       [uid]+vals)

def db_update(uid, field, val):
    if field not in set(UFIELDS): return    xq(f"UPDATE users SET {field}=?,updated_at=datetime('now','localtime') "
       f"WHERE user_id=?", (val, uid))

def db_delete(uid):
    xq('DELETE FROM users WHERE user_id=?',(uid,))
    xq('DELETE FROM seen WHERE user_id=? OR seen_id=?',(uid,uid))
    xq('DELETE FROM pending_match WHERE user_id=? OR partner_id=?',(uid,uid))

def db_all_ids(): return [r[0] for r in xr('SELECT user_id FROM users')]

def db_seen_add(u,s): xq('INSERT OR IGNORE INTO seen VALUES(?,?)',(u,s))
def db_seen_get(uid):
    r = xr('SELECT seen_id FROM seen WHERE user_id=?',(uid,))
    return {x[0] for x in r} if r else set()
def db_seen_clear(uid): xq('DELETE FROM seen WHERE user_id=?',(uid,))

def db_report(a,b): xq('INSERT OR IGNORE INTO reports VALUES(?,?)',(a,b))

def db_ref_add(referrer, referred):
    xq('INSERT OR IGNORE INTO referrals(referrer_id,referred_id) VALUES(?,?)',
       (referrer, referred))
    xq('UPDATE users SET stars=stars+1 WHERE user_id=?',(referrer,))

def db_ref_count(uid):
    r = xr('SELECT COUNT(*) FROM referrals WHERE referrer_id=?',(uid,))
    return r.fetchone()[0] if r else 0

def db_is_unlocked(uid):
    """✅ Match ဖြစ်ပြီးမှ စစ်ဆေးမည့် function"""
    if uid == ADMIN_ID: return True
    return db_ref_count(uid) >= SHARE_NEEDED

def pm_set(uid, pid):
    """Match ဖြစ်သွားသော စုံတွဲကို သိမ်းဆည်း"""
    xq('INSERT OR REPLACE INTO pending_match VALUES(?,?,datetime(\'now\'))',(uid,pid))

def pm_get(uid):
    r = xr('SELECT partner_id FROM pending_match WHERE user_id=?',(uid,))
    row = r.fetchone() if r else None
    return row[0] if row else None

def pm_clear(uid): xq('DELETE FROM pending_match WHERE user_id=?',(uid,))
def pm_clear_pair(uid1, uid2):
    xq('DELETE FROM pending_match WHERE (user_id=? AND partner_id=?) OR (user_id=? AND partner_id=?)',
       (uid1, uid2, uid2, uid1))

def db_stats():
    def n(q): r=xr(q); return r.fetchone()[0] if r else 0
    unlocked = sum(1 for uid in db_all_ids() if db_ref_count(uid) >= SHARE_NEEDED)
    return {        'total'   : n('SELECT COUNT(*) FROM users'),
        'male'    : n("SELECT COUNT(*) FROM users WHERE gender='Male'"),
        'female'  : n("SELECT COUNT(*) FROM users WHERE gender='Female'"),
        'photo'   : n('SELECT COUNT(*) FROM users WHERE photo IS NOT NULL'),
        'refs'    : n('SELECT COUNT(*) FROM referrals'),
        'unlocked': unlocked,
    }

# ═══════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════
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

# ═══════════════════════════════════════
# UTILS
# ═══════════════════════════════════════
def sf(d, k, fb='—'):
    v = (d or {}).get(k)
    if isinstance(v, str): v = v.strip()
    return v if v else fb

def is_cmd(text): return text and text.startswith('/')

def check_ch(uid):
    try:
        return bot.get_chat_member(CHANNEL_ID,uid).status in ('member','creator','administrator')
    except: return False

def notify_admin(txt):
    try: bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")
    except: pass

def err_notify(ctx, e, uid=None):
    tb = traceback.format_exc()[-1000:]
    msg = (f"🔴 *Bot Error*\n📍 `{ctx}`\n👤 `{uid}`\n❌ `{type(e).__name__}: {e}`\n"
           f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n```\n{tb}```")
    try:        _req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"}, timeout=8)
    except: pass

def fmt(tp, title='👤 *ပရိုဖိုင်*'):
    lines = [f"{title}\n\n", f"📛 နာမည်   : {sf(tp,'name')}\n", f"🎂 အသက်   : {sf(tp,'age')} နှစ်\n",
             f"🔮 ရာသီ   : {sf(tp,'zodiac')}\n", f"📍 မြို့    : {sf(tp,'city')}\n",
             f"🎨 ဝါသနာ  : {sf(tp,'hobby')}\n", f"💼 အလုပ်   : {sf(tp,'job')}\n",
             f"🎵 သီချင်း  : {sf(tp,'song')}"]
    if (tp or {}).get('bio'): lines.append(f"\n📝 အကြောင်း  : {sf(tp,'bio')}")
    if (tp or {}).get('looking_type'): lines.append(f"\n🎯 ရှာဖွေရန်  : {sf(tp,'looking_type')}")
    lines.extend([f"\n⚧ လိင်    : {sf(tp,'gender')}\n",
                  f"💑 ရှာဖွေ  : {sf(tp,'looking_gender')} / {sf(tp,'looking_zodiac','Any')}"])
    return ''.join(lines)

def stars_str(n):
    n = max(0, min(int(n or 0), 10))
    return ('⭐' * n) if n > 0 else 'မရှိသေး'

def inv_link(uid): return f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

def _make_share_link(link, text):
    safe_link = quote(link, safe='')
    safe_text = quote(text, safe='')
    return f"https://t.me/share/url?url={safe_link}&text={safe_text}"

# ═══════════════════════════════════════
# SHARE GATE — Match ဖြစ်မှ ပြသမည်
# ═══════════════════════════════════════
def share_gate_for_match(uid, partner_id, context="match"):
    """
    Match ဖြစ်ပြီးမှ Contact ရဖို့ Share ခိုင်းသော function
    context: "match" | "pending"
    """
    cnt = db_ref_count(uid)
    need = max(0, SHARE_NEEDED - cnt)
    link = inv_link(uid)
    share_text = f"✨ Yay Zat Zodiac Bot မှာ ဖူးစာရှာနိုင်ပါတယ် 💖"
    share_url = _make_share_link(link, share_text)
    
    # Message ကို အခြေအနေပေါ်မူတည်ပြီး ပြောင်းလဲပြသ
    if context == "match" and db_is_unlocked(partner_id):
        # Partner က unlock ဖြစ်နေရင် ပိုဆွဲဆောင်မှုရှိအောင်ရေး
        title = "🔓 ဖူးစာရှင်ရဲ့ ဆက်သွယ်ရန် လင့်ရယူမည်"
        desc = f"ဖူးစာရှင်က သင့်ကို လက်ခံလိုက်ပါပြီ! 🎉\nသူ/သူမရဲ့ Telegram link ကိုရဖို့ အောက်ပါအတိုင်း လုပ်ဆောင်ပါ။"
    else:
        title = "🔒 ဖူးစာရှင်ရဲ့ ဆက်သွယ်ရန် လင့်ရယူမည်"
        desc = f"Match ဖြစ်သွားပါပြီ! 💖\nဖူးစာရှင်ရဲ့ Telegram link ကိုရဖို့ မိတ်ဆွေ {SHARE_NEEDED} ယောက်ကို ဖိတ်ကြားပေးပါ။"
    
    m = InlineKeyboardMarkup()    m.row(InlineKeyboardButton("📤 မိတ်ဆွေများကို Share လုပ်မည်", url=share_url))
    m.row(InlineKeyboardButton("✅ Share ပြီးပြီ — စစ်ဆေးမည်", callback_data=f"chk_match_{partner_id}"))
    m.row(InlineKeyboardButton("⏭ နောက်မှလုပ်မည်", callback_data="match_later"))
    
    bot.send_message(uid,
        f"{title}\n\n"
        f"{desc}\n\n"
        f"📊 ဖိတ်ကြားပြီးသူ : *{cnt} / {SHARE_NEEDED}*\n"
        f"🎯 ကျန်သေးသည်   : *{need}* ယောက်\n\n"
        f"🔗 `{link}`\n\n✅ ကိုနှိပ်ပြီး စစ်ဆေးပေးပါ 👇",
        parse_mode="Markdown", reply_markup=m)

def try_deliver_match(me, partner, force=False):
    """
    Match ဖြစ်ပြီးနောက် Contact ပေးပို့ရန် စစ်ဆေးသော function
    force=True ဖြစ်လျှင် unlock မစစ်ဘဲ ပေးပို့မည် (Admin အတွက်)
    """
    if force or db_is_unlocked(me):
        pd = db_get(partner)
        pname = sf(pd, 'name', 'ဖူးစာရှင်')
        try:
            bot.send_message(me,
                f"💖 *Match အောင်မြင်သွားပါပြီ!* 🎉\n\n"
                f"[👉 ဒီမှာနှိပ်ပြီး {pname} နဲ့ စကားပြောမည်](tg://user?id={partner})\n\n"
                f"💡 Tip: သူ/သူမကို ပထမဆုံး စကားပြောဖို့ မမေ့ပါနဲ့! 😊",
                parse_mode="Markdown", reply_markup=kb(me))
            # Successfully delivered — clear pending
            pm_clear(me)
            return True
        except Exception as e:
            err_notify('deliver_match', e, me)
            return False
    else:
        # Still locked — show share gate
        pm_set(me, partner)  # Ensure pending is saved
        share_gate_for_match(me, partner, context="match")
        return False

# ═══════════════════════════════════════
# REGISTRATION (unchanged but optimized)
# ═══════════════════════════════════════
_reg = {}

def clear_reg(uid):
    _reg.pop(uid, None)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass

def reg_set(uid, k, v): _reg.setdefault(uid, {})[k] = v
def _step(fn):
    def w(msg):
        uid = msg.chat.id
        if is_cmd(msg.text) and msg.text.split()[0] not in ('/skip',):
            clear_reg(uid)
            bot.send_message(uid, "⚠️ မှတ်ပုံတင်ခြင်း ရပ်တန့်ပြီးပါပြီ။\nပြန်စရန် /start ကိုနှိပ်ပါ။", reply_markup=kb(uid))
            return
        try: fn(msg)
        except Exception as e:
            err_notify(f'reg/{fn.__name__}', e, uid)
            bot.send_message(uid, "⚠️ တစ်ခုခုမှားသွားပါသည်။/start ကိုနှိပ်ပြီး ပြန်စပါ။")
    return w

def ask(uid, text, markup=None, parse_mode="Markdown"):
    bot.send_message(uid, text, reply_markup=markup, parse_mode=parse_mode) if markup else bot.send_message(uid, text, parse_mode=parse_mode)

@_step
def s_name(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'name',m.text.strip())
    ask(uid, "🎂 အသက် ဘယ်လောက်လဲ? (/skip)-")
    bot.register_next_step_handler(m, s_age)

@_step
def s_age(m):
    uid = m.chat.id
    if m.text and m.text != '/skip':
        if m.text.strip().isdigit(): reg_set(uid,'age',m.text.strip())
        else:
            ask(uid,"⚠️ ဂဏန်းသာ ရိုက်ပါ (ဥပမာ 25)   (/skip)-")
            bot.register_next_step_handler(m, s_age)
            return
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('/skip')
    bot.send_message(uid, "🔮 ရာသီခွင်?", reply_markup=mk)
    bot.register_next_step_handler(m, s_zodiac)

@_step
def s_zodiac(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'zodiac',m.text.strip())
    bot.send_message(uid,"📍 မြို့ (ဥပမာ Mandalay)? (/skip)-", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m, s_city)

@_step
def s_city(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'city',m.text.strip())
    ask(uid,"🎨 ဝါသနာ (ဥပမာ ခရီးသွား, ဂီတ)? (/skip)-")    bot.register_next_step_handler(m, s_hobby)

@_step
def s_hobby(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'hobby',m.text.strip())
    ask(uid,"💼 အလုပ်? (/skip)-")
    bot.register_next_step_handler(m, s_job)

@_step
def s_job(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'job',m.text.strip())
    ask(uid,"🎵 အကြိုက်ဆုံး သီချင်း? (/skip)-")
    bot.register_next_step_handler(m, s_song)

@_step
def s_song(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'song',m.text.strip())
    ask(uid, "📝 *မိမိအကြောင်း အတိုချုံး* (/skip)-\n_(ဥပမာ: ဆေးကျောင်းသား, ဂီတကိုနှစ်သက်သူ)_")
    bot.register_next_step_handler(m, s_bio)

@_step
def s_bio(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'bio',m.text.strip())
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.row('💑 ဖူးစာရှာနေသူ','🤝 မိတ်ဆွေဖွဲ့ချင်သူ')
    mk.add('/skip')
    bot.send_message(uid,"🎯 ဘာရှာနေပါသလဲ?", reply_markup=mk)
    bot.register_next_step_handler(m, s_ltype)

@_step
def s_ltype(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'looking_type',m.text.strip())
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add('Male','Female','/skip')
    bot.send_message(uid,"⚧ သင့်လိင်?", reply_markup=mk)
    bot.register_next_step_handler(m, s_gender)

@_step
def s_gender(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'gender',m.text.strip())
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add('Male','Female','Both','/skip')
    bot.send_message(uid,"💑 ရှာဖွေနေတဲ့ လိင်?", reply_markup=mk)
    bot.register_next_step_handler(m, s_lgender)
@_step
def s_lgender(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'looking_gender',m.text.strip())
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('Any','/skip')
    bot.send_message(uid,"🔮 ရှာဖွေနေတဲ့ ရာသီ?", reply_markup=mk)
    bot.register_next_step_handler(m, s_lzodiac)

@_step
def s_lzodiac(m):
    uid = m.chat.id
    if m.text and m.text != '/skip': reg_set(uid,'looking_zodiac',m.text.strip())
    bot.send_message(uid, "📸 Profile ဓာတ်ပုံ ပေးပို့ပါ\n_(မလိုပါက /skip)_", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m, s_photo)

@_step
def s_photo(m):
    uid = m.chat.id
    old = db_get(uid)
    is_new = old is None
    if m.text == '/skip':
        if old and old.get('photo'): reg_set(uid,'photo', old['photo'])
    elif m.content_type == 'photo':
        reg_set(uid,'photo', m.photo[-1].file_id)
    else:
        ask(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ  (သို့)  /skip ဟုရိုက်ပါ-")
        bot.register_next_step_handler(m, s_photo)
        return
    data = _reg.pop(uid, {})
    db_save(uid, data)
    bot.send_message(uid, f"✅ Profile {'တည်ဆောက်' if is_new else 'ပြင်ဆင်'} ပြီးပါပြီ! 🎉\n\nခလုတ်များ နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇", parse_mode="Markdown", reply_markup=kb(uid))
    if is_new:
        notify_admin(f"🎉 *မှတ်ပုံတင် ပြီးမြောက်!*\n🆔 `{uid}` — {sf(data,'name')}\n👥 {len(db_all_ids())} ယောက်\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ═══════════════════════════════════════
# /start
# ═══════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.chat.id
    args = message.text.split()
    clear_reg(uid)
    try:
        if len(args) > 1 and args[1].startswith('ref_'):
            referrer = int(args[1][4:])
            if referrer != uid and db_get(referrer) and not db_get(uid):
                db_ref_add(referrer, uid)                # Check if referrer has pending match and just unlocked
                if db_is_unlocked(referrer):
                    pid = pm_get(referrer)
                    if pid:
                        pm_clear(referrer)
                        try_deliver_match(referrer, pid)
    except Exception as e:
        err_notify('start/ref', e, uid)
    if db_get(uid):
        bot.send_message(uid, "✨ *ကြိုဆိုပါတယ်!* ✨\n\nခလုတ်များနှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇", parse_mode="Markdown", reply_markup=kb(uid))
        return
    try:
        tg = message.from_user.username or str(uid)
        fn = message.from_user.first_name or ''
        ln = message.from_user.last_name or ''
    except: tg = fn = ln = str(uid)
    notify_admin(f"🆕 *User သစ်*\n👤 {fn} {ln} @{tg}\n🆔 `{uid}`\n👥 {len(db_all_ids())} ယောက်\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    _reg[uid] = {}
    bot.send_message(uid, "✨ *Yay Zat Zodiac မှ ကြိုဆိုပါတယ်!* ✨\n\nဖူးစာရှင်/မိတ်ဆွေကို ရှာဖွေဖို့ မေးခွန်းလေးတွေ ဖြေပေးပါ 🙏\n_(/skip ရိုက်ပြီး ကျော်နိုင်ပါသည်)_\n\n📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, s_name)

# ═══════════════════════════════════════
# MY PROFILE
# ═══════════════════════════════════════
def show_profile(message):
    uid = message.chat.id
    tp = db_get(uid)
    if not tp:
        bot.send_message(uid,"Profile မရှိသေးပါ။ /start ကိုနှိပ်ပါ။", reply_markup=kb(uid)); return
    stars = tp.get('stars') or 0
    refs = db_ref_count(uid)
    # Show share progress even if not unlocked yet
    progress = f"📊 Share Progress: {refs}/{SHARE_NEEDED} ⭐"
    if db_is_unlocked(uid):
        progress += " ✅ (Unlock ပြီး)"
    else:
        progress += f" 🔒 ({SHARE_NEEDED-refs} ကျန်)"
    text = fmt(tp) + f"\n\n⭐ ကြယ်ပွင့် : {stars_str(stars)} ({stars} ခု)\n🔗 {progress}"
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📛 နာမည်", callback_data="e_name"), InlineKeyboardButton("🎂 အသက်", callback_data="e_age"))
    m.row(InlineKeyboardButton("🔮 ရာသီ", callback_data="e_zodiac"), InlineKeyboardButton("📍 မြို့", callback_data="e_city"))
    m.row(InlineKeyboardButton("🎨 ဝါသနာ", callback_data="e_hobby"), InlineKeyboardButton("💼 အလုပ်", callback_data="e_job"))
    m.row(InlineKeyboardButton("🎵 သီချင်း",callback_data="e_song"), InlineKeyboardButton("📝 Bio", callback_data="e_bio"))
    m.row(InlineKeyboardButton("📸 ဓာတ်ပုံ",callback_data="e_photo"))
    m.row(InlineKeyboardButton("🔗 Invite Link", callback_data="my_invite"))
    m.row(InlineKeyboardButton("🔄 Profile ပြန်လုပ်", callback_data="do_reset"), InlineKeyboardButton("🗑 Profile ဖျက်", callback_data="do_delete"))
    if tp.get('photo'):
        try:
            bot.send_photo(uid, tp['photo'], caption=text, reply_markup=m, parse_mode="Markdown")
            return        except Exception as e: err_notify('show_profile/photo', e, uid)
    bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")

# ═══════════════════════════════════════
# FIND MATCH — NO SHARE GATE HERE! ✅
# ═══════════════════════════════════════
def find_match_candidate(uid, me):
    seen = db_seen_get(uid)
    excl = list(seen | {uid})
    if not excl: excl = [uid]
    lg = (me.get('looking_gender') or '').strip()
    lz = (me.get('looking_zodiac') or '').strip()
    query = '''SELECT * FROM users WHERE user_id NOT IN ({excl_placeholders}) AND user_id != ?'''.format(excl_placeholders=','.join('?'*len(excl)))
    params = excl + [uid]
    if lg and lg not in ('Both','Any',''):
        query += " AND (gender = ? OR gender IS NULL)"
        params.append(lg)
    query += ''' ORDER BY CASE WHEN ? != '' AND ? NOT IN ('Any','') AND zodiac = ? THEN 0 ELSE 1 END, stars DESC, RANDOM() LIMIT 1'''
    params.extend([lz, lz, lz])
    try:
        r = xr(query, params)
        return r.fetchone() if r else None
    except: return None

def find_match(message):
    uid = message.chat.id
    me = db_get(uid)
    if not me:
        bot.send_message(uid,"/start ကိုနှိပ်ပြီး Profile ဦးတည်ဆောက်ပါ။", reply_markup=kb(uid)); return
    
    # ✅ NO SHARE CHECK HERE — Users can browse freely!
    # Only check channel membership
    if not check_ch(uid):
        mk = InlineKeyboardMarkup()
        mk.add(InlineKeyboardButton("📢 Channel Join မည်",url=CHANNEL_LINK))
        bot.send_message(uid,"⚠️ Channel ကို အရင် Join ပေးပါ။",reply_markup=mk); return

    tgt_row = find_match_candidate(uid, me)
    if not tgt_row:
        if db_seen_get(uid):
            db_seen_clear(uid)
            bot.send_message(uid,"🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ...")
            find_match(message)
        else:
            bot.send_message(uid, "😔 သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ。\nဖော်ဆွေများကို ဖိတ်ကြားပါ 😊",reply_markup=kb(uid))
        return

    tgt = dict(tgt_row)
    tid = tgt['user_id']
    db_seen_add(uid, tid)    lz = (me.get('looking_zodiac') or '').strip()
    note = ''
    if lz and lz not in ('Any','') and (tgt.get('zodiac') or '') != lz:
        note = f"\n_({lz} မတွေ့သောကြောင့် အနီးစပ်ဆုံးပြပေးနေပါသည်)_"
    text = fmt(tgt, title=f"🎯 *မိတ်ဆွေနဲ့ ကိုက်ညီနိုင်မယ့်သူ*{note}")
    mk = InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("❤️ Like", callback_data=f"like_{tid}"),
           InlineKeyboardButton("⏭ Skip", callback_data="skip"),
           InlineKeyboardButton("🚩 Report", callback_data=f"rpt_{tid}"))
    if tgt.get('photo'):
        try:
            bot.send_photo(uid, tgt['photo'], caption=text, reply_markup=mk, parse_mode="Markdown")
            return
        except Exception as e: err_notify('find_match/photo', e, uid)
    bot.send_message(uid, text, reply_markup=mk, parse_mode="Markdown")

# ═══════════════════════════════════════
# OTHER HANDLERS
# ═══════════════════════════════════════
def do_reset(message):
    uid = message.chat.id
    clear_reg(uid)
    old = db_get(uid)
    _reg[uid] = dict(old) if old else {}
    bot.send_message(uid, "🔄 *Profile ပြန်လုပ်မည်*\n\n/skip — ကျော်နိုင်ပါသည် (ဟောင်းတန်ဖိုးများ ထိန်းသိမ်းမည်)\n\n📛 နာမည်-", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, s_name)

def show_help(message):
    bot.send_message(message.chat.id,
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ဖူးစာရှာမည်* — ကိုက်ညီနိုင်မယ့်သူ ရှာပါ (အခမဲ့)\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
        "🔄 *Profile ပြန်လုပ်* — Profile ပြန်ဖြည့်ပါ\n"
        "💡 *Match ဖြစ်မှ* — ဖူးစာရှင်ရဲ့ Telegram link ရဖို့ မိတ်ဆွေ ၇ ယောက် ဖိတ်ကြားရပါမည်။\n\n"
        "⚠️ ပြဿနာများ Admin ထံ ဆက်သွယ်ပါ။",
        parse_mode="Markdown", reply_markup=kb(message.chat.id))

def show_stats(message):
    uid = message.chat.id
    if uid != ADMIN_ID: bot.send_message(uid,"⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်။"); return
    s = db_stats()
    bot.send_message(ADMIN_ID, f"📊 *Admin Stats*\n\n👥 စုစုပေါင်း : *{s['total']}* ယောက်\n♂️ ကျား : {s['male']}\n♀️ မ : {s['female']}\n📸 ဓာတ်ပုံပါ : {s['photo']}\n🔓 Unlock ပြီး : {s['unlocked']}\n🔗 Referral : {s['refs']}\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}", parse_mode="Markdown", reply_markup=admin_kb())

def show_admin(message):
    if message.chat.id != ADMIN_ID: return
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📊 Stats", callback_data="adm_stats"), InlineKeyboardButton("👥 Users", callback_data="adm_users"))
    m.row(InlineKeyboardButton("📢 Broadcast", callback_data="adm_bcast"), InlineKeyboardButton("🗑 User ဖျက်", callback_data="adm_del"))
    m.row(InlineKeyboardButton("🔓 Manual Unlock", callback_data="adm_unlock"))
    bot.send_message(ADMIN_ID,"🛠 *Admin Panel*",parse_mode="Markdown",reply_markup=m)
def _bcast(m):
    if is_cmd(m.text): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး။"); return
    ok=fail=0
    for uid in db_all_ids():
        try: bot.send_message(uid,f"📢 *Admin မှ*\n\n{m.text}", parse_mode="Markdown"); ok+=1
        except: fail+=1
    bot.send_message(ADMIN_ID,f"✅ {ok} ရောက် / ❌ {fail} မရောက်")

def _del_u(m):
    if is_cmd(m.text): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး။"); return
    try:
        uid = int(m.text.strip())
        if db_get(uid): db_delete(uid); bot.send_message(ADMIN_ID,f"✅ `{uid}` ဖျက်ပြီး",parse_mode="Markdown")
        else: bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ။")
    except: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ။")

def _unlock_u(m):
    if is_cmd(m.text): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး။"); return
    try:
        uid = int(m.text.strip())
        if db_get(uid):
            for i in range(SHARE_NEEDED):
                xq('INSERT OR IGNORE INTO referrals(referrer_id,referred_id) VALUES(?,?)', (uid, -(i+1)))
            xq('UPDATE users SET stars=stars+? WHERE user_id=?',(SHARE_NEEDED,uid))
            bot.send_message(ADMIN_ID,f"✅ `{uid}` unlock ပြီး",parse_mode="Markdown")
            try: bot.send_message(uid, "✅ Admin က unlock လုပ်ပေးပြီးပါပြီ!\n🔍 ဖူးစာရှာနိုင်ပါပြီ 💖", reply_markup=kb(uid))
            except: pass
            pid = pm_get(uid)
            if pid: pm_clear(uid); try_deliver_match(uid, pid)
        else: bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ။")
    except: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ။")

def save_edit(message, field):
    uid = message.chat.id
    if is_cmd(message.text) and message.text != '/skip':
        bot.send_message(uid,"⚠️ ပြင်ဆင်မှု ရပ်တန့်ပြီးပါပြီ။",reply_markup=kb(uid)); return
    try:
        if field == 'photo':
            if message.content_type != 'photo': bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။"); return
            db_update(uid,'photo',message.photo[-1].file_id)
        else:
            if not message.text or not message.text.strip() or message.text=='/skip':
                bot.send_message(uid,"✅ ပြောင်းလဲမှု မလုပ်ဘဲ ထိန်းသိမ်းပြီး။",reply_markup=kb(uid)); return
            db_update(uid, field, message.text.strip())
        bot.send_message(uid,"✅ ပြင်ဆင်မှု အောင်မြင်!",reply_markup=kb(uid))
    except Exception as e:
        err_notify(f'save_edit/{field}',e,uid)
        bot.send_message(uid,"⚠️ မှားသွားပါသည်။ထပ်ကြိုးစားပါ။")
# ═══════════════════════════════════════
# MENU ROUTER
# ═══════════════════════════════════════
MENU = {
    "🔍 ဖူးစာရှာမည်"     : find_match,
    "👤 ကိုယ့်ပရိုဖိုင်"  : show_profile,
    "ℹ️ အကူအညီ"          : show_help,
    "🔄 Profile ပြန်လုပ်"  : lambda m: ask_reset(m),
    "📊 စာရင်းအင်း"       : show_stats,
    "🛠 Admin Panel"       : show_admin,
}

def ask_reset(message):
    uid = message.chat.id
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့ ပြန်လုပ်မည်", callback_data="reset_go"), InlineKeyboardButton("❌ မလုပ်တော့ပါ", callback_data="reset_no"))
    bot.send_message(uid, "⚠️ Profile ကို ပြန်လုပ်မှာ သေချာပါသလား?\n_(/skip ကျော်ပြီး ဟောင်းတန်ဖိုးများ ထိန်းသိမ်းနိုင်ပါသည်)_", parse_mode="Markdown", reply_markup=m)

@bot.message_handler(func=lambda m: m.text in MENU)
def menu_router(message):
    clear_reg(message.chat.id)
    try: MENU[message.text](message)
    except Exception as e:
        err_notify(f'menu/{message.text}',e,message.chat.id)
        bot.send_message(message.chat.id,"⚠️ မှားသွားပါသည်။နောက်မှ ထပ်ကြိုးစားပါ။")

@bot.message_handler(commands=['reset'])
def cmd_reset(m): clear_reg(m.chat.id); ask_reset(m)

@bot.message_handler(commands=['myprofile'])
def cmd_profile(m): show_profile(m)

@bot.message_handler(commands=['stats'])
def cmd_stats(m): show_stats(m)

@bot.message_handler(commands=['deleteprofile'])
def cmd_del(message):
    uid = message.chat.id
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့ ဖျက်မည်", callback_data="do_delete"), InlineKeyboardButton("❌ မဖျက်တော့ပါ", callback_data="del_no"))
    bot.send_message(uid,"⚠️ Profile ဖျက်မှာ သေချာပါသလား?",reply_markup=m)

# ═══════════════════════════════════════
# CALLBACK HANDLER — UPDATED FOR NEW FLOW
# ═══════════════════════════════════════
EDIT_LABELS = {
    'name':'နာမည်','age':'အသက်','zodiac':'ရာသီ','city':'မြို့',
    'hobby':'ဝါသနာ','job':'အလုပ်','song':'သီချင်း','bio':'Bio',
    'looking_type':'ရှာဖွေမည့်အမျိုးအစား',
    'gender':'လိင်','looking_gender':'ရှာဖွေမည့်လိင်',    'looking_zodiac':'ရှာဖွေမည့်ရာသီ'
}

@bot.callback_query_handler(func=lambda c: True)
def on_cb(call):
    uid = call.message.chat.id
    d = call.data
    try: _handle(call, uid, d)
    except Exception as e:
        err_notify(f'cb/{d}',e,uid)
        try: bot.answer_callback_query(call.id,"⚠️ မှားသွားပါသည်။",show_alert=True)
        except: pass

def _handle(call, uid, d):
    # Check share status for match delivery
    if d.startswith("chk_match_"):
        partner_id = int(d[10:])
        cnt = db_ref_count(uid)
        if cnt >= SHARE_NEEDED:
            bot.answer_callback_query(call.id,"🎉 Unlock ဖြစ်ပါပြီ!",show_alert=True)
            try: bot.delete_message(uid,call.message.message_id)
            except: pass
            bot.send_message(uid, f"✅ *{SHARE_NEEDED} ယောက် ပြည့်ပါပြီ! Unlock ဖြစ်ပါပြီ!* 🎉\n\nဖူးစာရှင်ရဲ့ Telegram link ကို ပေးပို့နေပါပြီ... 💖", parse_mode="Markdown")
            # Try to deliver match now
            if try_deliver_match(uid, partner_id):
                pm_clear_pair(uid, partner_id)
        else:
            bot.answer_callback_query(call.id, f"ကျန်သေးသည် {SHARE_NEEDED-cnt} ယောက်။ဆက်ဖိတ်ကြားပါ!", show_alert=True)
        return
    
    # User wants to skip share for now
    elif d == "match_later":
        bot.answer_callback_query(call.id,"✅ နောက်မှ ပြန်လုပ်နိုင်ပါတယ်! 👍", show_alert=True)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        bot.send_message(uid, "💡 သတိပေးချက်: ဖူးစာရှင်ရဲ့ Telegram link ကိုရဖို့ ပြန်လာပြီး Share လုပ်ပေးပါ။", reply_markup=kb(uid))
        return

    # Original share check (for profile page invite)
    elif d == "chk_share":
        cnt = db_ref_count(uid)
        if cnt >= SHARE_NEEDED:
            bot.answer_callback_query(call.id,"🎉 Unlock ဖြစ်ပါပြီ!",show_alert=True)
            try: bot.delete_message(uid,call.message.message_id)
            except: pass
            bot.send_message(uid, f"✅ *{SHARE_NEEDED} ယောက် ပြည့်ပါပြီ! Unlock ဖြစ်ပါပြီ!* 🎉\n\n🔍 ဖူးစာရှာမည် ကိုနှိပ်ပြီး ရှာနိုင်ပါပြီ 💖", parse_mode="Markdown", reply_markup=kb(uid))
            # Check if there's a pending match to deliver
            pid = pm_get(uid)
            if pid:
                pm_clear(uid)                try_deliver_match(uid, pid)
        else:
            bot.answer_callback_query(call.id, f"ကျန်သေးသည် {SHARE_NEEDED-cnt} ယောက်။ဆက်ဖိတ်ကြားပါ!", show_alert=True)
        return

    # reset callbacks
    elif d == "do_reset":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        ask_reset(call.message)
        return
    elif d == "reset_go":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        do_reset(call.message)
        return
    elif d == "reset_no":
        bot.answer_callback_query(call.id,"မလုပ်တော့ပါ 👍")
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        return

    # delete callbacks
    elif d == "do_delete":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့ ဖျက်မည်",callback_data="del_yes"), InlineKeyboardButton("❌ မဖျက်တော့ပါ", callback_data="del_no"))
        bot.send_message(uid,"⚠️ Profile ဖျက်မှာ သေချာပါသလား?",reply_markup=mk)
        return
    elif d == "del_yes":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        clear_reg(uid)
        db_delete(uid)
        bot.send_message(uid, "🗑 Profile ဖျက်ပြီးပါပြီ。\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်။", reply_markup=ReplyKeyboardRemove())
        return
    elif d == "del_no":
        bot.answer_callback_query(call.id,"မဖျက်တော့ပါ 👍")
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        return

    # edit field callbacks
    elif d.startswith("e_"):
        field = d[2:]
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        clear_reg(uid)
        if field == 'photo':            msg = bot.send_message(uid,"📸 ဓာတ်ပုံအသစ် ပေးပို့ပါ-", reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, lambda m: save_edit(m, 'photo'))
        else:
            label = EDIT_LABELS.get(field, field)
            msg = bot.send_message(uid, f"📝 *{label}* အသစ် ရိုက်ထည့်ပါ-\n_(/skip — မပြောင်းဘဲ ကျော်ရန်)_", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, lambda m: save_edit(m, field))
        return

    # invite link — with URL encoding fix
    elif d == "my_invite":
        cnt = db_ref_count(uid)
        link = inv_link(uid)
        share_text = f"✨ Yay Zat Bot မှာ ဖူးစာရှာနိုင်ပါတယ် 💖"
        share_url = _make_share_link(link, share_text)
        mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("📤 Share လုပ်မည်", url=share_url))
        progress = f"👥 Join ဖြစ်သူ : *{cnt}/{SHARE_NEEDED}*"
        if db_is_unlocked(uid):
            progress += "\n✅ Unlock ပြီး — Match ဖြစ်ရင် Contact ရပြီ!"
        else:
            progress += f"\n🔒 {SHARE_NEEDED-cnt} ယောက် ထပ်ဖိတ်ပါ"
        bot.send_message(uid, f"🔗 *Invite Link*\n\n`{link}`\n\n{progress}", parse_mode="Markdown", reply_markup=mk)
        return

    # skip match
    elif d == "skip":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        find_match(call.message)
        return

    # like — Send notification to target user
    elif d.startswith("like_"):
        tid = int(d[5:])
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        if not check_ch(uid):
            bot.answer_callback_query(call.id,"⚠️ Channel ကို Join ပါ!",show_alert=True); return
        me = db_get(uid) or {}
        lnm = sf(me,'name','တစ်ယောက်')
        am = InlineKeyboardMarkup()
        am.row(InlineKeyboardButton("✅ လက်ခံမည်",callback_data=f"accept_{uid}"), InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline"))
        cap = (f"💌 *'{lnm}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n" + fmt(me, title='👤 *သူ/သူမ ရဲ့ Profile*'))
        try:
            if me.get('photo'):
                bot.send_photo(tid, me['photo'], caption=cap, reply_markup=am, parse_mode="Markdown")
            else:
                bot.send_message(tid, cap, reply_markup=am, parse_mode="Markdown")
            bot.send_message(uid, "❤️ Like လုပ်လိုက်ပါပြီ!\nတစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊", reply_markup=kb(uid))
        except Exception as e:            err_notify('like/send',e,uid)
            bot.send_message(uid,"⚠️ တစ်ဖက်လူမှာ Bot Block ထားသဖြင့် ပေးပို့မရပါ။", reply_markup=kb(uid))
        return

    # accept — MUTUAL MATCH! Now check unlock status
    elif d.startswith("accept_"):
        liker = int(d[7:])
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        notify_admin(f"💖 *Match!* [A](tg://user?id={uid}) + [B](tg://user?id={liker})\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        # Save the match as pending for both users
        pm_set(uid, liker)
        pm_set(liker, uid)
        
        # Try to deliver to both — if either is locked, they'll see share gate
        delivered_a = try_deliver_match(uid, liker)
        delivered_b = try_deliver_match(liker, uid)
        
        # If both delivered, clear pending
        if delivered_a and delivered_b:
            pm_clear_pair(uid, liker)
        return

    # decline
    elif d == "decline":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        bot.send_message(uid,"❌ ငြင်းဆန်လိုက်ပါပြီ။",reply_markup=kb(uid))
        return

    # report
    elif d.startswith("rpt_"):
        tid = int(d[4:])
        db_report(uid,tid)
        bot.answer_callback_query(call.id,"🚩 Report လုပ်ပြီး။",show_alert=True)
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        notify_admin(f"🚩 *Report*\n`{uid}` {sf(db_get(uid),'name')} → `{tid}` {sf(db_get(tid),'name')}")
        return

    # admin callbacks
    elif d == "adm_stats" and uid == ADMIN_ID: show_stats(call.message); return
    elif d == "adm_users" and uid == ADMIN_ID:
        rows = [dict(r) for r in xr('SELECT * FROM users LIMIT 30')]
        lines = [f"{i}. {sf(u,'name')} `{u['user_id']}` ⭐{u.get('stars',0)} {'🔓' if db_is_unlocked(u['user_id']) else '🔒'}" for i,u in enumerate(rows,1)]
        bot.send_message(ADMIN_ID, "👥 *User List*\n\n"+("\n".join(lines) or "မရှိသေး"), parse_mode="Markdown"); return
    elif d == "adm_bcast" and uid == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID,"📢 Message (/cancel)-")
        bot.register_next_step_handler(msg,_bcast); return    elif d == "adm_del" and uid == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID,"🗑 User ID (/cancel)-")
        bot.register_next_step_handler(msg,_del_u); return
    elif d == "adm_unlock" and uid == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID,"🔓 Unlock မည့် User ID (/cancel)-")
        bot.register_next_step_handler(msg,_unlock_u); return

    try: bot.answer_callback_query(call.id)
    except: pass

# ═══════════════════════════════════════
# AUTO-RESTART POLLING
# ═══════════════════════════════════════
print(f"✅ Yay Zat Bot [{datetime.now().strftime('%d/%m/%Y %H:%M')}] — Share After Match Flow")
notify_admin(f"🟢 *Bot Online*\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n🔄 Flow: Share AFTER Match")

while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=40, long_polling_timeout=40)
    except Exception as e:
        msg = (f"🔴 *Polling Error — Restarting...*\n`{type(e).__name__}: {e}`\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print(msg)
        try:
            _req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"}, timeout=8)
        except: pass
        time.sleep(5)
