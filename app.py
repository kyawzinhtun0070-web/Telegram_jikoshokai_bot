"""
Yay Zat Zodiac Bot — Simple & Clean
"""
import telebot, sqlite3, threading, traceback, time, requests as _req
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)

# ══════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════
TOKEN        = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID   = -1003641016541
CHANNEL_LINK = "https://t.me/yayzatofficial"
ADMIN_ID     = 6131831207
BOT_USERNAME = "YayZatBot"          # @ မပါ
HEART_STICKER = "CAACAgIAAxkBAAEBmjFnQ_example"  # ← သင့် heart sticker file_id ထည့်ပါ

ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

bot = telebot.TeleBot(TOKEN, threaded=True)

# ══════════════════════════════════════════
# DATABASE — single connection, thread-safe
# ══════════════════════════════════════════
DB   = 'yayzat.db'
_lk  = threading.Lock()
_db  = None

def open_db():
    global _db
    c = sqlite3.connect(DB, check_same_thread=False, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    _db = c

open_db()

def xq(sql, p=()):                  # write
    global _db
    with _lk:
        for _ in range(3):
            try:
                r = _db.execute(sql, p); _db.commit(); return r
            except sqlite3.OperationalError:
                open_db(); time.sleep(0.2)

def xr(sql, p=()):                  # read
    global _db
    with _lk:
        for _ in range(3):
            try: return _db.execute(sql, p)
            except sqlite3.OperationalError:
                open_db(); time.sleep(0.2)
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
    r = xr('SELECT * FROM users WHERE user_id=?', (uid,))
    row = r.fetchone() if r else None
    return dict(row) if row else None

def db_save(uid, data):
    old = db_get(uid)
    # preserve photo if not in new data
    if old and not data.get('photo') and old.get('photo'):
        data['photo'] = old['photo']
    cols = ','.join(UF); ph = ','.join(['?']*len(UF))
    vals = [data.get(f) for f in UF]
    upd  = ','.join([f"{f}=excluded.{f}" for f in UF])
    xq(f"INSERT INTO users (user_id,{cols}) VALUES(?,{ph}) "
       f"ON CONFLICT(user_id) DO UPDATE SET {upd}", [uid]+vals)

def db_update(uid, field, val):
    if field not in set(UF): return
    xq(f"UPDATE users SET {field}=? WHERE user_id=?", (val, uid))

def db_delete(uid):
    xq('DELETE FROM users WHERE user_id=?', (uid,))
    xq('DELETE FROM seen WHERE user_id=? OR seen_id=?', (uid, uid))

def db_all():   return [dict(r) for r in (xr('SELECT * FROM users') or [])]
def db_ids():   return [r[0] for r in (xr('SELECT user_id FROM users') or [])]
def db_count():
    r = xr('SELECT COUNT(*) FROM users'); return r.fetchone()[0] if r else 0

def db_seen_add(u, s): xq('INSERT OR IGNORE INTO seen VALUES(?,?)', (u, s))
def db_seen_get(uid):
    r = xr('SELECT seen_id FROM seen WHERE user_id=?', (uid,))
    return {x[0] for x in r} if r else set()
def db_seen_clear(uid): xq('DELETE FROM seen WHERE user_id=?', (uid,))

def db_report(a, b): xq('INSERT OR IGNORE INTO reports VALUES(?,?)', (a, b))
def db_reported_by(uid):
    r = xr('SELECT reported_id FROM reports WHERE reporter_id=?', (uid,))
    return {x[0] for x in r} if r else set()

def db_stats():
    def n(q): r=xr(q); return r.fetchone()[0] if r else 0
    return {
        'total' : n('SELECT COUNT(*) FROM users'),
        'male'  : n("SELECT COUNT(*) FROM users WHERE gender='Male'"),
        'female': n("SELECT COUNT(*) FROM users WHERE gender='Female'"),
        'photo' : n('SELECT COUNT(*) FROM users WHERE photo IS NOT NULL'),
    }

# ══════════════════════════════════════════
# KEYBOARDS
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
# UTILS
# ══════════════════════════════════════════
def sf(d, k, fb='—'):
    v = (d or {}).get(k)
    if isinstance(v, str): v = v.strip()
    return v if v else fb

def check_ch(uid):
    try: return bot.get_chat_member(CHANNEL_ID,uid).status in (
        'member','creator','administrator')
    except: return False

def admin_msg(txt):
    try: bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")
    except: pass

def err_log(ctx, e, uid=None):
    tb = traceback.format_exc()[-400:]
    msg = (f"🔴 *Error* `{ctx}`\n👤 `{uid}`\n"
           f"`{type(e).__name__}: {e}`\n```\n{tb}```")
    try:
        _req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"},
                  timeout=6)
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
    """Send photo; fallback to text if photo fails"""
    if photo:
        try:
            bot.send_photo(uid, photo, caption=caption,
                           reply_markup=markup, parse_mode="Markdown")
            return
        except Exception as e:
            err_log('send_photo', e, uid)
    bot.send_message(uid, caption, reply_markup=markup, parse_mode="Markdown")

def share_prompt(uid):
    link = f"https://t.me/{BOT_USERNAME}?start=s"
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton(
        "📤 မိတ်ဆွေ ၇ ယောက်ကို Share လုပ်မည်",
        url=f"https://t.me/share/url?url={link}"
            f"&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာ+ရှာနိုင်ပါတယ်+💖"))
    m.row(InlineKeyboardButton("🔍 ဆက်ရှာမည်", callback_data="continue_find"))
    bot.send_message(uid,
        "💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
        "🙏 Bot ကို မိတ်ဆွေ *၇ ယောက်* ကို Share ပေးပါ!\n"
        "Share မြဲ Bot ကြီးထွားပြီး သင့်အတွက် ရှာဖွေမှု ပိုကောင်းလာမည် 😊",
        parse_mode="Markdown", reply_markup=m)

# ══════════════════════════════════════════
# REGISTRATION STATE
# ══════════════════════════════════════════
_reg  = {}      # uid -> data dict
_step = {}      # uid -> current step name (for debug)

def _is_start(msg):
    """If user types /start mid-flow → redirect"""
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
        "_(/skip — ကျော်ချင်ရင်)_\n\n"
        "📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, r_name)

def r_name(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'name', m)
    bot.send_message(uid, "🎂 အသက်? (/skip)-")
    bot.register_next_step_handler(m, r_age)

def r_age(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m):
        if m.text and m.text.strip().isdigit():
            _sv(uid, 'age', m)
        else:
            bot.send_message(uid, "⚠️ ဂဏန်းသာ (/skip)-")
            bot.register_next_step_handler(m, r_age); return
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('/skip')
    bot.send_message(uid, "🔮 ရာသီ?", reply_markup=mk)
    bot.register_next_step_handler(m, r_zodiac)

def r_zodiac(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'zodiac', m)
    bot.send_message(uid, "📍 မြို့? (/skip)-", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m, r_city)

def r_city(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'city', m)
    bot.send_message(uid, "🎨 ဝါသနာ? (/skip)-")
    bot.register_next_step_handler(m, r_hobby)

def r_hobby(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'hobby', m)
    bot.send_message(uid, "💼 အလုပ်? (/skip)-")
    bot.register_next_step_handler(m, r_job)

def r_job(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'job', m)
    bot.send_message(uid,
        "📝 *မိမိအကြောင်း အတိုချုံး* (/skip)-\n"
        "_(ဥပမာ: ဆေးကျောင်းသား, ဂီတကိုနှစ်သက်သူ)_",
        parse_mode="Markdown")
    bot.register_next_step_handler(m, r_bio)

def r_bio(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'bio', m)
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add('Male', 'Female', '/skip')
    bot.send_message(uid, "⚧ သင့်လိင်?", reply_markup=mk)
    bot.register_next_step_handler(m, r_gender)

def r_gender(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'gender', m)
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add('Male', 'Female', 'Both', '/skip')
    bot.send_message(uid, "💑 ရှာဖွေနေတဲ့ လိင်?", reply_markup=mk)
    bot.register_next_step_handler(m, r_lgender)

def r_lgender(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'looking_gender', m)
    mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('Any', '/skip')
    bot.send_message(uid, "🔮 ရှာဖွေနေတဲ့ ရာသီ?", reply_markup=mk)
    bot.register_next_step_handler(m, r_lzodiac)

def r_lzodiac(m):
    if _is_start(m): return
    uid = m.chat.id
    if not _sk(m): _sv(uid, 'looking_zodiac', m)
    bot.send_message(uid,
        "📸 ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက /skip)_",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m, r_photo)

def r_photo(m):
    if _is_start(m): return
    uid    = m.chat.id
    is_new = db_get(uid) is None

    if _sk(m):
        old = db_get(uid)
        if old and old.get('photo'):
            _reg.setdefault(uid, {})['photo'] = old['photo']
    elif m.content_type == 'photo':
        _reg.setdefault(uid, {})['photo'] = m.photo[-1].file_id
    else:
        bot.send_message(uid, "⚠️ ဓာတ်ပုံ ပေးပို့ပါ (သို့) /skip-")
        bot.register_next_step_handler(m, r_photo); return

    data = _reg.pop(uid, {})
    db_save(uid, data)

    bot.send_message(uid,
        f"✅ Profile {'တည်ဆောက်' if is_new else 'ပြင်ဆင်'} ပြီးပါပြီ! 🎉\n\n"
        "👇 ခလုတ်များနှိပ်ပြီး သုံးနိုင်ပါပြီ",
        parse_mode="Markdown", reply_markup=kb(uid))

    if is_new:
        admin_msg(f"🆕 *User သစ် မှတ်ပုံတင်ပြီး*\n"
                  f"🆔 `{uid}` — {sf(data,'name')}\n"
                  f"👥 {db_count()} ယောက်\n"
                  f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ══════════════════════════════════════════
# /start
# ══════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid = message.chat.id
    _reg.pop(uid, None)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass

    if db_get(uid):
        bot.send_message(uid,
            "✨ *ကြိုဆိုပါတယ်!* ✨\n\n👇 ခလုတ်များနှိပ်ပြီး သုံးနိုင်ပါပြီ",
            parse_mode="Markdown", reply_markup=kb(uid))
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

# ══════════════════════════════════════════
# FIND MATCH
# ══════════════════════════════════════════
def find_match(message):
    uid = message.chat.id
    me  = db_get(uid)
    if not me:
        bot.send_message(uid, "/start နှိပ်ပြီး Profile အရင်တည်ဆောက်ပါ。",
                         reply_markup=kb(uid)); return

    if not check_ch(uid):
        mk = InlineKeyboardMarkup()
        mk.add(InlineKeyboardButton("📢 Channel Join မည်", url=CHANNEL_LINK))
        bot.send_message(uid, "⚠️ Channel ကို အရင် Join ပေးပါ。", reply_markup=mk); return

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
            bot.send_message(uid, "🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ...")
            find_match(message); return
        bot.send_message(uid,
            "😔 သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ。\n"
            "ဖော်ဆွေများကို ဖိတ်ကြားပါ 😊", reply_markup=kb(uid)); return

    # zodiac preferred first
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

    send_safe(uid, tgt.get('photo'), text, mk)

# ══════════════════════════════════════════
# MY PROFILE
# ══════════════════════════════════════════
def show_profile(message):
    uid = message.chat.id
    tp  = db_get(uid)
    if not tp:
        bot.send_message(uid, "Profile မရှိသေးပါ။ /start နှိပ်ပါ。",
                         reply_markup=kb(uid)); return

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

# ══════════════════════════════════════════
# HELP
# ══════════════════════════════════════════
def show_help(message):
    bot.send_message(message.chat.id,
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ရှာမည်* — ကိုက်ညီမယ့်သူ ရှာပါ\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
        "🔄 *ပြန်လုပ်* — Profile ပြန်ဖြည့်ပါ\n\n"
        "ပြဿနာများ Admin ထံ ဆက်သွယ်ပါ。",
        parse_mode="Markdown", reply_markup=kb(message.chat.id))

# ══════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════
def show_stats(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်。"); return
    s = db_stats()
    bot.send_message(ADMIN_ID,
        f"📊 *Admin Stats*\n\n"
        f"👥 စုစုပေါင်း : *{s['total']}* ယောက်\n"
        f"♂️ ကျား      : {s['male']}\n"
        f"♀️ မ         : {s['female']}\n"
        f"📸 ဓာတ်ပုံပါ : {s['photo']}\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        parse_mode="Markdown", reply_markup=admin_kb())

def show_admin(message):
    if message.chat.id != ADMIN_ID: return
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📊 Stats",     callback_data="adm_stats"),
          InlineKeyboardButton("👥 Users",      callback_data="adm_users"))
    m.row(InlineKeyboardButton("📢 Broadcast",  callback_data="adm_bcast"),
          InlineKeyboardButton("🗑 User ဖျက်", callback_data="adm_del"))
    bot.send_message(ADMIN_ID, "🛠 *Admin Panel*", parse_mode="Markdown", reply_markup=m)

def _bcast(m):
    if m.text and m.text.startswith('/'): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    ok=fail=0
    for uid in db_ids():
        try: bot.send_message(uid,f"📢 *Yay Zat*\n\n{m.text}",parse_mode="Markdown"); ok+=1
        except: fail+=1
    bot.send_message(ADMIN_ID,f"✅ {ok} ရောက် / ❌ {fail} မရောက်")

def _del_u(m):
    if m.text and m.text.startswith('/'): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    try:
        uid=int(m.text.strip())
        if db_get(uid): db_delete(uid); bot.send_message(ADMIN_ID,f"✅ `{uid}` ဖျက်ပြီး",parse_mode="Markdown")
        else: bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ。")
    except: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ。")

# single field edit save
def save_edit(message, field):
    uid = message.chat.id
    if _is_start(message): return
    try:
        if field == 'photo':
            if message.content_type != 'photo':
                bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ。"); return
            db_update(uid,'photo',message.photo[-1].file_id)
        else:
            if not message.text or message.text.strip() == '/skip':
                bot.send_message(uid,"✅ မပြောင်းဘဲ ထိန်းသိမ်းပြီး。",reply_markup=kb(uid)); return
            db_update(uid,field,message.text.strip())
        bot.send_message(uid,"✅ ပြင်ဆင်မှု အောင်မြင်!",reply_markup=kb(uid))
    except Exception as e:
        err_log(f'edit/{field}',e,uid)
        bot.send_message(uid,"⚠️ မှားသွားပါသည်。")

# ══════════════════════════════════════════
# MENU ROUTER
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
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့",  callback_data="reset_go"),
          InlineKeyboardButton("❌ မလုပ်တော့", callback_data="reset_no"))
    bot.send_message(message.chat.id,
        "⚠️ Profile ကို ပြန်လုပ်မှာ သေချာပါသလား?", reply_markup=m)

@bot.message_handler(func=lambda m: m.text in MENU)
def menu_router(message):
    uid = message.chat.id
    _reg.pop(uid, None)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass
    try: MENU[message.text](message)
    except Exception as e:
        err_log(f'menu/{message.text}',e,uid)

@bot.message_handler(commands=['reset'])
def cmd_reset(m): ask_reset(m)
@bot.message_handler(commands=['myprofile'])
def cmd_profile(m): show_profile(m)

# ══════════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════════
EDIT_LABELS = {
    'name':'နာမည်','age':'အသက်','zodiac':'ရာသီ','city':'မြို့',
    'hobby':'ဝါသနာ','job':'အလုပ်','bio':'Bio','gender':'လိင်',
    'looking_gender':'ရှာဖွေမည့်လိင်','looking_zodiac':'ရှာဖွေမည့်ရာသီ'
}

@bot.callback_query_handler(func=lambda c: True)
def on_cb(call):
    uid = call.message.chat.id
    d   = call.data
    try:
        _cb(call, uid, d)
    except Exception as e:
        err_log(f'cb/{d}',e,uid)
        try: bot.answer_callback_query(call.id,"⚠️ မှားသွားပါသည်。",show_alert=True)
        except: pass

def _cb(call, uid, d):

    # ── Like ──────────────────────────────
    if d.startswith("like_"):
        tid = int(d[5:])
        try: bot.delete_message(uid, call.message.message_id)
        except: pass

        # 1. Send heart sticker first
        try: bot.send_sticker(uid, HEART_STICKER)
        except: bot.send_message(uid, "❤️")   # fallback if sticker fails

        # 2. Notify target
        me  = db_get(uid) or {}
        lnm = sf(me,'name','တစ်ယောက်')
        mk  = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{uid}"),
               InlineKeyboardButton("❌ ငြင်းမည်",  callback_data="decline"))
        cap = (f"💌 *'{lnm}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n"
               + fmt(me, title='👤 *သူ/သူမ ရဲ့ Profile*'))
        try:
            send_safe(tid, me.get('photo'), cap, mk)
            bot.send_message(uid,
                "❤️ Like လုပ်လိုက်ပါပြီ!\n"
                "တစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊",
                reply_markup=kb(uid))
        except Exception as e:
            err_log('like/send',e,uid)
            bot.send_message(uid,"⚠️ တစ်ဖက်လူမှာ Bot Block ထားသဖြင့် မပို့နိုင်ပါ。",
                             reply_markup=kb(uid))

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

        # send match link to both
        for me, partner in [(uid, liker),(liker, uid)]:
            pd = db_get(partner)
            try:
                bot.send_message(me,
                    f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
                    f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner}) "
                    f"{sf(pd,'name','ဖူးစာရှင်')} နဲ့ စကားပြောနိုင်ပါပြီ 🎉",
                    parse_mode="Markdown", reply_markup=kb(me))
            except: pass

        # share prompt to both
        try: share_prompt(uid)
        except: pass
        try: share_prompt(liker)
        except: pass

    # ── Decline ───────────────────────────
    elif d == "decline":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        bot.send_message(uid,"❌ ငြင်းဆန်လိုက်ပါပြီ。",reply_markup=kb(uid))

    # ── Continue find ─────────────────────
    elif d == "continue_find":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        find_match(call.message)

    # ── Reset ─────────────────────────────
    elif d == "reset_go":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        old = db_get(uid)
        begin_reg(uid, call.message, prefill=old)

    elif d == "reset_no":
        bot.answer_callback_query(call.id,"မလုပ်တော့ပါ 👍")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass

    # ── Delete ────────────────────────────
    elif d == "do_delete":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့",  callback_data="del_yes"),
               InlineKeyboardButton("❌ မဖျက်တော့", callback_data="del_no"))
        bot.send_message(uid,"⚠️ Profile ဖျက်မှာ သေချာပါသလား?",reply_markup=mk)

    elif d == "del_yes":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        _reg.pop(uid,None)
        db_delete(uid)
        bot.send_message(uid,
            "🗑 Profile ဖျက်ပြီးပါပြီ。\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်。",
            reply_markup=ReplyKeyboardRemove())

    elif d == "del_no":
        bot.answer_callback_query(call.id,"မဖျက်တော့ပါ 👍")
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
                                   reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_edit, 'photo')
        else:
            label = EDIT_LABELS.get(field, field)
            msg = bot.send_message(uid,
                f"📝 *{label}* အသစ် ရိုက်ထည့်ပါ-\n_(/skip — မပြောင်းဘဲ ကျော်)_",
                parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_edit, field)

    # ── Admin callbacks ───────────────────
    elif d == "adm_stats" and uid == ADMIN_ID:
        show_stats(call.message)

    elif d == "adm_users" and uid == ADMIN_ID:
        rows = db_all()[:30]
        lines = [f"{i}. {sf(u,'name')} `{u['user_id']}`"
                 for i,u in enumerate(rows,1)]
        bot.send_message(ADMIN_ID,
            "👥 *User List (ပထမ 30)*\n\n"+("\n".join(lines) or "မရှိသေး"),
            parse_mode="Markdown")

    elif d == "adm_bcast" and uid == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID,"📢 Message (/cancel)-")
        bot.register_next_step_handler(msg, _bcast)

    elif d == "adm_del" and uid == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID,"🗑 User ID (/cancel)-")
        bot.register_next_step_handler(msg, _del_u)

    try: bot.answer_callback_query(call.id)
    except: pass

# ══════════════════════════════════════════
# AUTO-RESTART POLLING — bot မရပ်ပါ
# ══════════════════════════════════════════
print(f"✅ Yay Zat Bot [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
admin_msg(f"🟢 *Bot Online*\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

while True:
    try:
        bot.polling(none_stop=True, interval=0,
                    timeout=40, long_polling_timeout=40)
    except Exception as e:
        msg = (f"🔴 *Polling Error*\n`{type(e).__name__}: {e}`\n"
               f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}\nRestarting...")
        print(msg)
        try: _req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                       json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"},
                       timeout=6)
        except: pass
        time.sleep(5)
