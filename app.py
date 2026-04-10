"""
Yay Zat Zodiac Bot — Simple & Clean (STABLE VERSION)
Fixed: Profile save issue, Channel check removed, Timeout handling, Auto-restart
"""
import telebot
import sqlite3
import threading
import traceback
import time
import requests as _req
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)

# ══════════════════════════════════════════
# ⚙️ CONFIG
# ══════════════════════════════════════════
TOKEN        = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID   = -1003641016541          # ← သိမ်းထားသာ (check ဖြုတ်ထား)
CHANNEL_LINK = "https://t.me/yayzatofficial"
ADMIN_ID     = 6131831207
BOT_USERNAME = "YayZatBot"
HEART_STICKER = "CAACAgIAAxkBAAEBmjFnQ_example"  # ← သင့် heart sticker file_id ထည့်ပါ

ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

# ══════════════════════════════════════════
# 🌐 REQUESTS SESSION — Retry + Timeout
# ══════════════════════════════════════════
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_retry_session():
    session = _req.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

_retry_session = create_retry_session()
# ══════════════════════════════════════════
# 🤖 BOT INIT
# ══════════════════════════════════════════
# Timeout တန်ဖိုးများ တိုးထား
import telebot.apihelper
telebot.apihelper.REQ_TIMEOUT = 90
telebot.apihelper.session = _retry_session

bot = telebot.TeleBot(TOKEN, threaded=True, skip_pending=True)

# ══════════════════════════════════════════
# 🗄️ DATABASE — Thread-safe + Stable
# ══════════════════════════════════════════
DB   = 'yayzat.db'
_lk  = threading.Lock()
_db  = None

def open_db():
    global _db
    try:
        if _db:
            try: _db.close()
            except: pass
        c = sqlite3.connect(DB, check_same_thread=False, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=15000")
        c.execute("PRAGMA synchronous=NORMAL")
        _db = c
    except Exception as e:
        print(f"❌ DB open error: {e}")
        raise

open_db()

def xq(sql, p=()):  # write
    global _db
    with _lk:
        for attempt in range(3):
            try:
                r = _db.execute(sql, p)
                _db.commit()
                return r
            except sqlite3.OperationalError as e:
                if attempt == 2: raise
                open_db()
                time.sleep(0.3)

def xr(sql, p=()):  # read
    global _db    with _lk:
        for attempt in range(3):
            try:
                return _db.execute(sql, p)
            except sqlite3.OperationalError as e:
                if attempt == 2: raise
                open_db()
                time.sleep(0.3)
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
        bio            TEXT,
        gender         TEXT,
        looking_gender TEXT,
        looking_zodiac TEXT,
        photo          TEXT,
        created_at     TEXT DEFAULT (datetime('now','localtime'))
    )''')
    xq('''CREATE TABLE IF NOT EXISTS seen (
        user_id INTEGER, seen_id INTEGER,
        PRIMARY KEY(user_id, seen_id)
    )''')
    xq('''CREATE TABLE IF NOT EXISTS reports (
        reporter_id INTEGER, reported_id INTEGER,
        PRIMARY KEY(reporter_id, reported_id)
    )''')

init_db()

UF = ['name','age','zodiac','city','hobby','job','bio',
      'gender','looking_gender','looking_zodiac','photo']

def db_get(uid):
    try:
        r = xr('SELECT * FROM users WHERE user_id=?', (uid,))
        row = r.fetchone() if r else None
        return dict(row) if row else None
    except Exception as e:
        err_log('db_get', e, uid)
        return None

def db_save(uid, data):    try:
        old = db_get(uid)
        if old and not data.get('photo') and old.get('photo'):
            data['photo'] = old['photo']
        cols = ','.join(UF)
        ph = ','.join(['?']*len(UF))
        vals = [data.get(f) for f in UF]
        upd = ','.join([f"{f}=excluded.{f}" for f in UF])
        xq(f"INSERT INTO users (user_id,{cols}) VALUES(?,{ph}) "
           f"ON CONFLICT(user_id) DO UPDATE SET {upd}", [uid]+vals)
        return True
    except Exception as e:
        err_log('db_save', e, uid)
        return False

def db_update(uid, field, val):
    if field not in set(UF): return
    try: xq(f"UPDATE users SET {field}=? WHERE user_id=?", (val, uid))
    except Exception as e: err_log(f'db_update/{field}', e, uid)

def db_delete(uid):
    try:
        xq('DELETE FROM users WHERE user_id=?', (uid,))
        xq('DELETE FROM seen WHERE user_id=? OR seen_id=?', (uid, uid))
    except Exception as e: err_log('db_delete', e, uid)

def db_all():
    try: return [dict(r) for r in (xr('SELECT * FROM users') or [])]
    except: return []

def db_ids():
    try: return [r[0] for r in (xr('SELECT user_id FROM users') or [])]
    except: return []

def db_count():
    try:
        r = xr('SELECT COUNT(*) FROM users')
        return r.fetchone()[0] if r else 0
    except: return 0

def db_seen_add(u, s):
    try: xq('INSERT OR IGNORE INTO seen VALUES(?,?)', (u, s))
    except: pass

def db_seen_get(uid):
    try:
        r = xr('SELECT seen_id FROM seen WHERE user_id=?', (uid,))
        return {x[0] for x in r} if r else set()
    except: return set()
def db_seen_clear(uid):
    try: xq('DELETE FROM seen WHERE user_id=?', (uid,))
    except: pass

def db_report(a, b):
    try: xq('INSERT OR IGNORE INTO reports VALUES(?,?)', (a, b))
    except: pass

def db_reported_by(uid):
    try:
        r = xr('SELECT reported_id FROM reports WHERE reporter_id=?', (uid,))
        return {x[0] for x in r} if r else set()
    except: return set()

def db_stats():
    def n(q):
        try: r=xr(q); return r.fetchone()[0] if r else 0
        except: return 0
    return {
        'total' : n('SELECT COUNT(*) FROM users'),
        'male'  : n("SELECT COUNT(*) FROM users WHERE gender='Male'"),
        'female': n("SELECT COUNT(*) FROM users WHERE gender='Female'"),
        'photo' : n('SELECT COUNT(*) FROM users WHERE photo IS NOT NULL'),
    }

# ══════════════════════════════════════════
# ⌨️ KEYBOARDS
# ══════════════════════════════════════════
def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(KeyboardButton("🔍 ရှာမည်"), KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    m.row(KeyboardButton("ℹ️ အကူအညီ"), KeyboardButton("🔄 ပြန်လုပ်"))
    return m

def admin_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(KeyboardButton("🔍 ရှာမည်"), KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    m.row(KeyboardButton("ℹ️ အကူအညီ"), KeyboardButton("🔄 ပြန်လုပ်"))
    m.row(KeyboardButton("📊 Admin Stats"), KeyboardButton("🛠 Admin Panel"))
    return m

def kb(uid): return admin_kb() if uid == ADMIN_ID else main_kb()

# ══════════════════════════════════════════
# 🔧 UTILS
# ══════════════════════════════════════════
def sf(d, k, fb='—'):
    v = (d or {}).get(k)
    if isinstance(v, str): v = v.strip()
    return v if v else fb
# Channel check ကို ဖြုတ်ထားပြီ — အောက်ပါ function ကို သိမ်းထားသာ
# def check_ch(uid): ...

def admin_msg(txt):
    try:
        bot.send_message(ADMIN_ID, txt, parse_mode="Markdown", timeout=30)
    except: pass

def err_log(ctx, e, uid=None):
    tb = traceback.format_exc()[-400:]
    msg = (f"🔴 *Error* `{ctx}`\n👤 `{uid}`\n"
           f"`{type(e).__name__}: {str(e)[:100]}`\n```\n{tb}```")
    try:
        _retry_session.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"},
            timeout=15
        )
    except: pass

def fmt(tp, title='👤 *ပရိုဖိုင်*'):
    bio = f"\n📝 Bio      : {sf(tp,'bio')}" if (tp or {}).get('bio') else ''
    return (
        f"{title}\n\n"
        f"📛 နာမည်   : {sf(tp,'name')}\n"
        f"🎂 အသက်   : {sf(tp,'age')} နှစ်\n"
        f"🔮 ရာသီ   : {sf(tp,'zodiac')}\n"
        f"📍 မြို့    : {sf(tp,'city')}\n"
        f"🎨 ဝါသနာ  : {sf(tp,'hobby')}\n"
        f"💼 အလုပ်   : {sf(tp,'job')}"
        f"{bio}\n"
        f"⚧ လိင်    : {sf(tp,'gender')}\n"
        f"🔍 ရှာဖွေ  : {sf(tp,'looking_gender')} / {sf(tp,'looking_zodiac','Any')}"
    )

def send_safe(uid, photo, caption, markup):
    if photo:
        try:
            bot.send_photo(uid, photo, caption=caption,
                          reply_markup=markup, parse_mode="Markdown", timeout=30)
            return
        except Exception as e:
            err_log('send_photo', e, uid)
    bot.send_message(uid, caption, reply_markup=markup, parse_mode="Markdown", timeout=30)

def share_prompt(uid):
    link = f"https://t.me/{BOT_USERNAME}?start=s"
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton(        "📤 မိတ်ဆွေ ၇ ယောက်ကို Share လုပ်မည်",
        url=f"https://t.me/share/url?url={link}"
            f"&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာ+ရှာနိုင်ပါတယ်+💖"))
    m.row(InlineKeyboardButton("🔍 ဆက်ရှာမည်", callback_data="continue_find"))
    bot.send_message(uid,
        "💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
        "🙏 Bot ကို မိတ်ဆွေ *၇ ယောက်* ကို Share ပေးပါ!\n"
        "Share မြဲ Bot ကြီးထွားပြီး သင့်အတွက် ရှာဖွေမှု ပိုကောင်းလာမည် 😊",
        parse_mode="Markdown", reply_markup=m, timeout=30)

# ══════════════════════════════════════════
# 🔄 SAFE STEP HANDLER — Registration မရပ်အောင်
# ══════════════════════════════════════════
def safe_next_handler(msg, handler_func, *args):
    try:
        bot.register_next_step_handler(msg, handler_func, *args)
    except Exception as e:
        uid = msg.chat.id if hasattr(msg, 'chat') else None
        err_log('safe_next_handler', e, uid)
        if uid:
            bot.send_message(uid, "⚠️ ခေတ္တပြဿနာဖြစ်နေပါတယ်။ /start နှိပ်ပြီး ပြန်စကြည့်ပါ။",
                           reply_markup=kb(uid), timeout=30)

# ══════════════════════════════════════════
# 📝 REGISTRATION STATE
# ══════════════════════════════════════════
_reg  = {}
_step = {}

def _is_start(msg):
    if msg.text and msg.text.strip().lower().startswith('/start'):
        uid = msg.chat.id
        _reg.pop(uid, None); _step.pop(uid, None)
        try: bot.clear_step_handler_by_chat_id(uid)
        except: pass
        cmd_start(msg)
        return True
    return False

def _sk(msg): return msg.text and msg.text.strip() == '/skip'
def _sv(uid, k, msg):
    if msg.text: _reg.setdefault(uid, {})[k] = msg.text.strip()

def begin_reg(uid, msg, prefill=None):
    _reg[uid] = dict(prefill) if prefill else {}
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass
    bot.send_message(uid,
        "📋 *မှတ်ပုံတင်မည်*\n\n"
        "_(/skip — ကျော်ချင်ရင်)_\n\n"        "📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(), timeout=30)
    safe_next_handler(msg, r_name)

def r_name(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'name', m)
        bot.send_message(uid, "🎂 အသက်? (/skip)-", timeout=30)
        safe_next_handler(m, r_age)
    except Exception as e:
        err_log('r_name', e, m.chat.id if hasattr(m,'chat') else None)
        bot.send_message(m.chat.id, "⚠️ မှားသွားပါသည်။ /start နှိပ်ပြီး ပြန်စပါ။",
                        reply_markup=kb(m.chat.id), timeout=30)

def r_age(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m):
            if m.text and m.text.strip().isdigit():
                _sv(uid, 'age', m)
            else:
                bot.send_message(uid, "⚠️ ဂဏန်းသာ (/skip)-", timeout=30)
                safe_next_handler(m, r_age); return
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for z in ZODIACS: mk.add(z)
        mk.add('/skip')
        bot.send_message(uid, "🔮 ရာသီ?", reply_markup=mk, timeout=30)
        safe_next_handler(m, r_zodiac)
    except Exception as e:
        err_log('r_age', e, m.chat.id if hasattr(m,'chat') else None)

def r_zodiac(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'zodiac', m)
        bot.send_message(uid, "📍 မြို့? (/skip)-", reply_markup=ReplyKeyboardRemove(), timeout=30)
        safe_next_handler(m, r_city)
    except Exception as e:
        err_log('r_zodiac', e, m.chat.id if hasattr(m,'chat') else None)

def r_city(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'city', m)
        bot.send_message(uid, "🎨 ဝါသနာ? (/skip)-", timeout=30)        safe_next_handler(m, r_hobby)
    except Exception as e:
        err_log('r_city', e, m.chat.id if hasattr(m,'chat') else None)

def r_hobby(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'hobby', m)
        bot.send_message(uid, "💼 အလုပ်? (/skip)-", timeout=30)
        safe_next_handler(m, r_job)
    except Exception as e:
        err_log('r_hobby', e, m.chat.id if hasattr(m,'chat') else None)

def r_job(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'job', m)
        bot.send_message(uid,
            "📝 *မိမိအကြောင်း အတိုချုံး* (/skip)-\n"
            "_(ဥပမာ: ဆေးကျောင်းသား, ဂီတကိုနှစ်သက်သူ)_",
            parse_mode="Markdown", timeout=30)
        safe_next_handler(m, r_bio)
    except Exception as e:
        err_log('r_job', e, m.chat.id if hasattr(m,'chat') else None)

def r_bio(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'bio', m)
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.add('Male', 'Female', '/skip')
        bot.send_message(uid, "⚧ သင့်လိင်?", reply_markup=mk, timeout=30)
        safe_next_handler(m, r_gender)
    except Exception as e:
        err_log('r_bio', e, m.chat.id if hasattr(m,'chat') else None)

def r_gender(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'gender', m)
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.add('Male', 'Female', 'Both', '/skip')
        bot.send_message(uid, "💑 ရှာဖွေနေတဲ့ လိင်?", reply_markup=mk, timeout=30)
        safe_next_handler(m, r_lgender)
    except Exception as e:
        err_log('r_gender', e, m.chat.id if hasattr(m,'chat') else None)
def r_lgender(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'looking_gender', m)
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for z in ZODIACS: mk.add(z)
        mk.add('Any', '/skip')
        bot.send_message(uid, "🔮 ရှာဖွေနေတဲ့ ရာသီ?", reply_markup=mk, timeout=30)
        safe_next_handler(m, r_lzodiac)
    except Exception as e:
        err_log('r_lgender', e, m.chat.id if hasattr(m,'chat') else None)

def r_lzodiac(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        if not _sk(m): _sv(uid, 'looking_zodiac', m)
        bot.send_message(uid,
            "📸 ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက /skip)_",
            parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(), timeout=30)
        safe_next_handler(m, r_photo)
    except Exception as e:
        err_log('r_lzodiac', e, m.chat.id if hasattr(m,'chat') else None)

def r_photo(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        is_new = db_get(uid) is None

        if _sk(m):
            old = db_get(uid)
            if old and old.get('photo'):
                _reg.setdefault(uid, {})['photo'] = old['photo']
        elif m.content_type == 'photo':
            _reg.setdefault(uid, {})['photo'] = m.photo[-1].file_id
        else:
            bot.send_message(uid, "⚠️ ဓာတ်ပုံ ပေးပို့ပါ (သို့) /skip-", timeout=30)
            safe_next_handler(m, r_photo); return

        data = _reg.pop(uid, {})
        db_save(uid, data)

        bot.send_message(uid,
            f"✅ Profile {'တည်ဆောက်' if is_new else 'ပြင်ဆင်'} ပြီးပါပြီ! 🎉\n\n"
            "👇 ခလုတ်များနှိပ်ပြီး သုံးနိုင်ပါပြီ",
            parse_mode="Markdown", reply_markup=kb(uid), timeout=30)
        if is_new:
            admin_msg(f"🆕 *User သစ် မှတ်ပုံတင်ပြီး*\n"
                      f"🆔 `{uid}` — {sf(data,'name')}\n"
                      f"👥 {db_count()} ယောက်\n"
                      f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    except Exception as e:
        err_log('r_photo', e, m.chat.id if hasattr(m,'chat') else None)

# ══════════════════════════════════════════
# 🚀 /start
# ══════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(message):
    try:
        uid = message.chat.id
        _reg.pop(uid, None)
        try: bot.clear_step_handler_by_chat_id(uid)
        except: pass

        if db_get(uid):
            bot.send_message(uid,
                "✨ *ကြိုဆိုပါတယ်!* ✨\n\n👇 ခလုတ်များနှိပ်ပြီး သုံးနိုင်ပါပြီ",
                parse_mode="Markdown", reply_markup=kb(uid), timeout=30)
            return

        try:
            fn = message.from_user.first_name or ''
            ln = message.from_user.last_name  or ''
            tg = message.from_user.username or str(uid)
        except: fn=ln=tg=str(uid)

        admin_msg(f"🆕 *User သစ် ဝင်ရောက်လာပြီ*\n"
                  f"👤 {fn} {ln} @{tg}\n🆔 `{uid}`\n"
                  f"👥 {db_count()} ယောက်\n"
                  f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        begin_reg(uid, message)
    except Exception as e:
        err_log('cmd_start', e, message.chat.id if hasattr(message,'chat') else None)

# ══════════════════════════════════════════
# 🔍 FIND MATCH — Channel check ဖြုတ်ထား
# ══════════════════════════════════════════
def find_match(message):
    try:
        uid = message.chat.id
        me  = db_get(uid)
        if not me:
            bot.send_message(uid, "/start နှိပ်ပြီး Profile အရင်တည်ဆောက်ပါ။",
                            reply_markup=kb(uid), timeout=30); return
        # ❌ Channel check ကို ဖြုတ်ထားပြီ — အောက်ပါအတိုင်း မှတ်ချက်ချထား
        # if not check_ch(uid):
        #     mk = InlineKeyboardMarkup()
        #     mk.add(InlineKeyboardButton("📢 Channel Join မည်", url=CHANNEL_LINK))
        #     bot.send_message(uid, "⚠️ Channel ကို အရင် Join ပေးပါ။", reply_markup=mk, timeout=30); return

        seen  = db_seen_get(uid)
        rptd  = db_reported_by(uid)
        excl  = seen | rptd | {uid}
        lg    = (me.get('looking_gender') or '').strip()
        lz    = (me.get('looking_zodiac')  or '').strip()

        pool = []
        for u in db_all():
            if u['user_id'] in excl: continue
            if lg and lg not in ('Both','Any'):
                if (u.get('gender') or '').strip() != lg: continue
            pool.append(u)

        if not pool:
            if seen:
                db_seen_clear(uid)
                bot.send_message(uid, "🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ...", timeout=30)
                find_match(message); return
            bot.send_message(uid,
                "😔 သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ。\n"
                "ဖော်ဆွေများကို ဖိတ်ကြားပါ 😊", reply_markup=kb(uid), timeout=30); return

        if lz and lz not in ('Any', ''):
            pref = [u for u in pool if (u.get('zodiac') or '') == lz]
            rest = [u for u in pool if (u.get('zodiac') or '') != lz]
            pool = pref + rest

        tgt = pool[0]
        tid = tgt['user_id']
        db_seen_add(uid, tid)

        note = ''
        if lz and lz not in ('Any','') and (tgt.get('zodiac') or '') != lz:
            note = f"\n_({lz} မတွေ့သောကြောင့် အနီးစပ်ဆုံးပြပေးနေပါသည်)_"

        text = fmt(tgt, title=f"✨ *ရှာတွေ့ပြီ!*{note}")
        mk = InlineKeyboardMarkup()
        mk.row(
            InlineKeyboardButton("❤️", callback_data=f"like_{tid}"),
            InlineKeyboardButton("👎", callback_data=f"nope_{tid}")
        )

        send_safe(uid, tgt.get('photo'), text, mk)    except Exception as e:
        err_log('find_match', e, message.chat.id if hasattr(message,'chat') else None)
        bot.send_message(message.chat.id, "⚠️ ရှာဖွေရာတွင် အဆင်မပြေဖြစ်နေပါတယ်။", 
                        reply_markup=kb(message.chat.id), timeout=30)

# ══════════════════════════════════════════
# 👤 MY PROFILE
# ══════════════════════════════════════════
def show_profile(message):
    try:
        uid = message.chat.id
        tp  = db_get(uid)
        if not tp:
            bot.send_message(uid, "Profile မရှိသေးပါ။ /start နှိပ်ပါ။",
                            reply_markup=kb(uid), timeout=30); return

        m = InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("📛 နာမည်",  callback_data="e_name"),
              InlineKeyboardButton("🎂 အသက်",   callback_data="e_age"))
        m.row(InlineKeyboardButton("🔮 ရာသီ",   callback_data="e_zodiac"),
              InlineKeyboardButton("📍 မြို့",   callback_data="e_city"))
        m.row(InlineKeyboardButton("🎨 ဝါသနာ", callback_data="e_hobby"),
              InlineKeyboardButton("💼 အလုပ်",  callback_data="e_job"))
        m.row(InlineKeyboardButton("📝 Bio",    callback_data="e_bio"),
              InlineKeyboardButton("📸 ဓာတ်ပုံ",callback_data="e_photo"))
        m.row(InlineKeyboardButton("⚧ လိင်",   callback_data="e_gender"),
              InlineKeyboardButton("💑 ရှာဖွေ",  callback_data="e_looking_gender"))
        m.row(InlineKeyboardButton("🔄 Profile ပြန်လုပ်", callback_data="do_reset"),
              InlineKeyboardButton("🗑 ဖျက်",            callback_data="do_delete"))

        send_safe(uid, tp.get('photo'), fmt(tp), m)
    except Exception as e:
        err_log('show_profile', e, message.chat.id if hasattr(message,'chat') else None)

# ══════════════════════════════════════════
# ℹ️ HELP
# ══════════════════════════════════════════
def show_help(message):
    try:
        bot.send_message(message.chat.id,
            "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
            "🔍 *ရှာမည်* — ကိုက်ညီမယ့်သူ ရှာပါ\n"
            "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
            "🔄 *ပြန်လုပ်* — Profile ပြန်ဖြည့်ပါ\n\n"
            "ပြဿနာများ Admin ထံ ဆက်သွယ်ပါ။",
            parse_mode="Markdown", reply_markup=kb(message.chat.id), timeout=30)
    except Exception as e:
        err_log('show_help', e, message.chat.id if hasattr(message,'chat') else None)

# ══════════════════════════════════════════# 🛠 ADMIN
# ══════════════════════════════════════════
def show_stats(message):
    try:
        if message.chat.id != ADMIN_ID:
            bot.send_message(message.chat.id, "⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်။", timeout=30); return
        s = db_stats()
        bot.send_message(ADMIN_ID,
            f"📊 *Admin Stats*\n\n"
            f"👥 စုစုပေါင်း : *{s['total']}* ယောက်\n"
            f"♂️ ကျား      : {s['male']}\n"
            f"♀️ မ         : {s['female']}\n"
            f"📸 ဓာတ်ပုံပါ : {s['photo']}\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            parse_mode="Markdown", reply_markup=admin_kb(), timeout=30)
    except Exception as e:
        err_log('show_stats', e, message.chat.id if hasattr(message,'chat') else None)

def show_admin(message):
    try:
        if message.chat.id != ADMIN_ID: return
        m = InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("📊 Stats",     callback_data="adm_stats"),
              InlineKeyboardButton("👥 Users",      callback_data="adm_users"))
        m.row(InlineKeyboardButton("📢 Broadcast",  callback_data="adm_bcast"),
              InlineKeyboardButton("🗑 User ဖျက်", callback_data="adm_del"))
        bot.send_message(ADMIN_ID, "🛠 *Admin Panel*", parse_mode="Markdown", reply_markup=m, timeout=30)
    except Exception as e:
        err_log('show_admin', e, message.chat.id if hasattr(message,'chat') else None)

def _bcast(m):
    try:
        if m.text and m.text.startswith('/'): 
            bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး။", timeout=30); return
        ok=fail=0
        for uid in db_ids():
            try: 
                bot.send_message(uid,f"📢 *Yay Zat*\n\n{m.text}",parse_mode="Markdown", timeout=30)
                ok+=1
            except: fail+=1
        bot.send_message(ADMIN_ID,f"✅ {ok} ရောက် / ❌ {fail} မရောက်", timeout=30)
    except Exception as e:
        err_log('_bcast', e, ADMIN_ID)

def _del_u(m):
    try:
        if m.text and m.text.startswith('/'): 
            bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး။", timeout=30); return
        uid=int(m.text.strip())
        if db_get(uid):             db_delete(uid)
            bot.send_message(ADMIN_ID,f"✅ `{uid}` ဖျက်ပြီး",parse_mode="Markdown", timeout=30)
        else: 
            bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ။", timeout=30)
    except: 
        bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ။", timeout=30)

def save_edit(message, field):
    try:
        uid = message.chat.id
        if _is_start(message): return
        if field == 'photo':
            if message.content_type != 'photo':
                bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။", timeout=30); return
            db_update(uid,'photo',message.photo[-1].file_id)
        else:
            if not message.text or message.text.strip() == '/skip':
                bot.send_message(uid,"✅ မပြောင်းဘဲ ထိန်းသိမ်းပြီး။",reply_markup=kb(uid), timeout=30); return
            db_update(uid,field,message.text.strip())
        bot.send_message(uid,"✅ ပြင်ဆင်မှု အောင်မြင်!",reply_markup=kb(uid), timeout=30)
    except Exception as e:
        err_log(f'edit/{field}',e,uid)
        bot.send_message(uid,"⚠️ မှားသွားပါသည်။", timeout=30)

# ══════════════════════════════════════════
# 🧭 MENU ROUTER
# ══════════════════════════════════════════
MENU = {
    "🔍 ရှာမည်"           : find_match,
    "👤 ကိုယ့်ပရိုဖိုင်"  : show_profile,
    "ℹ️ အကူအညီ"           : show_help,
    "🔄 ပြန်လုပ်"          : lambda m: ask_reset(m),
    "📊 Admin Stats"       : show_stats,
    "🛠 Admin Panel"       : show_admin,
}

def ask_reset(message):
    try:
        m = InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့",  callback_data="reset_go"),
              InlineKeyboardButton("❌ မလုပ်တော့", callback_data="reset_no"))
        bot.send_message(message.chat.id,
            "⚠️ Profile ကို ပြန်လုပ်မှာ သေချာပါသလား?", reply_markup=m, timeout=30)
    except Exception as e:
        err_log('ask_reset', e, message.chat.id if hasattr(message,'chat') else None)

@bot.message_handler(func=lambda m: m.text in MENU)
def menu_router(message):
    try:
        uid = message.chat.id        _reg.pop(uid, None)
        try: bot.clear_step_handler_by_chat_id(uid)
        except: pass
        MENU[message.text](message)
    except Exception as e:
        err_log(f'menu/{message.text}',e,uid)

@bot.message_handler(commands=['reset'])
def cmd_reset(m): ask_reset(m)
@bot.message_handler(commands=['myprofile'])
def cmd_profile(m): show_profile(m)

# ══════════════════════════════════════════
# ⚡ CALLBACK HANDLER
# ══════════════════════════════════════════
EDIT_LABELS = {
    'name':'နာမည်','age':'အသက်','zodiac':'ရာသီ','city':'မြို့',
    'hobby':'ဝါသနာ','job':'အလုပ်','bio':'Bio','gender':'လိင်',
    'looking_gender':'ရှာဖွေမည့်လိင်','looking_zodiac':'ရှာဖွေမည့်ရာသီ'
}

@bot.callback_query_handler(func=lambda c: True)
def on_cb(call):
    try:
        uid = call.message.chat.id
        d   = call.data
        _cb(call, uid, d)
    except Exception as e:
        err_log(f'cb/{call.data if hasattr(call,"data") else "unknown"}',e,call.message.chat.id if hasattr(call.message,'chat') else None)
        try: bot.answer_callback_query(call.id,"⚠️ မှားသွားပါသည်။",show_alert=True, timeout=30)
        except: pass

def _cb(call, uid, d):
    try:
        # ── Like ──────────────────────────────
        if d.startswith("like_"):
            tid = int(d[5:])
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            try: bot.send_sticker(uid, HEART_STICKER, timeout=30)
            except: bot.send_message(uid, "❤️", timeout=30)
            me  = db_get(uid) or {}
            lnm = sf(me,'name','တစ်ယောက်')
            mk  = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{uid}"),
                   InlineKeyboardButton("❌ ငြင်းမည်",  callback_data="decline"))
            cap = (f"💌 *'{lnm}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n"
                   + fmt(me, title='👤 *သူ/သူမ ရဲ့ Profile*'))
            try:
                send_safe(tid, me.get('photo'), cap, mk)                bot.send_message(uid,
                    "❤️ Like လုပ်လိုက်ပါပြီ!\n"
                    "တစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊",
                    reply_markup=kb(uid), timeout=30)
            except Exception as e:
                err_log('like/send',e,uid)
                bot.send_message(uid,"⚠️ တစ်ဖက်လူမှာ Bot Block ထားသဖြင့် မပို့နိုင်ပါ။",
                                 reply_markup=kb(uid), timeout=30)

        # ── Nope ──────────────────────────────
        elif d.startswith("nope_"):
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            find_match(call.message)

        # ── Accept ────────────────────────────
        elif d.startswith("accept_"):
            liker = int(d[7:])
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            admin_msg(f"💖 *Match!*\n"
                      f"[A](tg://user?id={uid}) + [B](tg://user?id={liker})\n"
                      f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            for me, partner in [(uid, liker),(liker, uid)]:
                pd = db_get(partner)
                try:
                    bot.send_message(me,
                        f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
                        f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner}) "
                        f"{sf(pd,'name','ဖူးစာရှင်')} နဲ့ စကားပြောနိုင်ပါပြီ 🎉",
                        parse_mode="Markdown", reply_markup=kb(me), timeout=30)
                except: pass
            try: share_prompt(uid)
            except: pass
            try: share_prompt(liker)
            except: pass

        # ── Decline ───────────────────────────
        elif d == "decline":
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            bot.send_message(uid,"❌ ငြင်းဆန်လိုက်ပါပြီ။",reply_markup=kb(uid), timeout=30)

        # ── Continue find ─────────────────────
        elif d == "continue_find":
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            find_match(call.message)

        # ── Reset ─────────────────────────────        elif d == "reset_go":
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            old = db_get(uid)
            begin_reg(uid, call.message, prefill=old)
        elif d == "reset_no":
            bot.answer_callback_query(call.id,"မလုပ်တော့ပါ 👍", timeout=30)
            try: bot.delete_message(uid, call.message.message_id)
            except: pass

        # ── Delete ────────────────────────────
        elif d == "do_delete":
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            mk = InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့",  callback_data="del_yes"),
                   InlineKeyboardButton("❌ မဖျက်တော့", callback_data="del_no"))
            bot.send_message(uid,"⚠️ Profile ဖျက်မှာ သေချာပါသလား?",reply_markup=mk, timeout=30)
        elif d == "del_yes":
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            _reg.pop(uid,None)
            db_delete(uid)
            bot.send_message(uid,
                "🗑 Profile ဖျက်ပြီးပါပြီ。\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်။",
                reply_markup=ReplyKeyboardRemove(), timeout=30)
        elif d == "del_no":
            bot.answer_callback_query(call.id,"မဖျက်တော့ပါ 👍", timeout=30)
            try: bot.delete_message(uid, call.message.message_id)
            except: pass

        # ── do_reset ──────────────────────────
        elif d == "do_reset":
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            ask_reset(call.message)

        # ── Edit fields ───────────────────────
        elif d.startswith("e_"):
            field = d[2:]
            try: bot.delete_message(uid, call.message.message_id)
            except: pass
            _reg.pop(uid,None)
            try: bot.clear_step_handler_by_chat_id(uid)
            except: pass
            if field == 'photo':
                msg = bot.send_message(uid,"📸 ဓာတ်ပုံအသစ် ပေးပို့ပါ-",
                                       reply_markup=ReplyKeyboardRemove(), timeout=30)
                safe_next_handler(msg, save_edit, 'photo')
            else:                label = EDIT_LABELS.get(field, field)
                msg = bot.send_message(uid,
                    f"📝 *{label}* အသစ် ရိုက်ထည့်ပါ-\n_(/skip — မပြောင်းဘဲ ကျော်)_",
                    parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(), timeout=30)
                safe_next_handler(msg, save_edit, field)

        # ── Admin callbacks ───────────────────
        elif d == "adm_stats" and uid == ADMIN_ID:
            show_stats(call.message)
        elif d == "adm_users" and uid == ADMIN_ID:
            rows = db_all()[:30]
            lines = [f"{i}. {sf(u,'name')} `{u['user_id']}`"
                     for i,u in enumerate(rows,1)]
            bot.send_message(ADMIN_ID,
                "👥 *User List (ပထမ 30)*\n\n"+("\n".join(lines) or "မရှိသေး"),
                parse_mode="Markdown", timeout=30)
        elif d == "adm_bcast" and uid == ADMIN_ID:
            msg = bot.send_message(ADMIN_ID,"📢 Message (/cancel)-", timeout=30)
            safe_next_handler(msg, _bcast)
        elif d == "adm_del" and uid == ADMIN_ID:
            msg = bot.send_message(ADMIN_ID,"🗑 User ID (/cancel)-", timeout=30)
            safe_next_handler(msg, _del_u)

        try: bot.answer_callback_query(call.id, timeout=30)
        except: pass
    except Exception as e:
        err_log('_cb/main', e, uid)

# ══════════════════════════════════════════
# 🔄 AUTO-RESTART POLLING — Stable Loop
# ══════════════════════════════════════════
print(f"✅ Yay Zat Bot [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
admin_msg(f"🟢 *Bot Online*\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

while True:
    try:
        bot.polling(
            none_stop=True, 
            interval=2,           # ← ပိုတည်ငြိမ်အောင် 2s
            timeout=90,           # ← 45s → 90s
            long_polling_timeout=80  # ← 40s → 80s
        )
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user")
        break
    except Exception as e:
        err_name = type(e).__name__
        err_msg = str(e)[:300]
        
        # 🔁 Network errors ကို သီးသန့်ကိုင်တွယ်        if err_name in ('ReadTimeout', 'TimeoutError', 'ConnectionError', 'ConnectionResetError'):
            print(f"⚠️ Network issue: {err_msg} — Retrying in 5s...")
            time.sleep(5)
            continue
            
        msg = (f"🔴 *Polling Error*\n`{err_name}: {err_msg}`\n"
               f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\n🔄 Restarting...")
        print(msg)
        try:
            _retry_session.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"},
                timeout=15
            )
        except: pass
        time.sleep(5)
