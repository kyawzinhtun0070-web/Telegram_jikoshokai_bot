"""
Yay Zat Zodiac Bot — Stable v3
Critical fix: /start always works regardless of step handler state
"""
import telebot, sqlite3, threading, traceback, time, requests as _req
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)

# ═══════════════════════════════════════
# CONFIG  ← ဒီနေရာတွင်သာ ပြောင်းရမည်
# ═══════════════════════════════════════
TOKEN        = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID   = -1003641016541
CHANNEL_LINK = "https://t.me/yayzatofficial"
ADMIN_ID     = 6131831207
BOT_USERNAME = "YayZatBot"   # @ မပါ
SHARE_NEEDED = 7

ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

bot = telebot.TeleBot(TOKEN, threaded=True)

# ═══════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════
DB_FILE = 'yayzat.db'
_lock   = threading.Lock()
_db     = None

def open_db():
    global _db
    c = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    _db = c

open_db()

def xq(sql, p=()):
    global _db
    with _lock:
        for _ in range(3):
            try:
                cur = _db.execute(sql, p); _db.commit(); return cur
            except sqlite3.OperationalError:
                open_db(); time.sleep(0.2)

def xr(sql, p=()):
    global _db
    with _lock:
        for _ in range(3):
            try: return _db.execute(sql, p)
            except sqlite3.OperationalError:
                open_db(); time.sleep(0.2)
        return None

def init_db():
    xq('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, name TEXT, age TEXT, zodiac TEXT,
        city TEXT, hobby TEXT, job TEXT, song TEXT, bio TEXT,
        gender TEXT, looking_gender TEXT, looking_zodiac TEXT,
        looking_type TEXT, photo TEXT, stars INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    xq('CREATE TABLE IF NOT EXISTS seen (user_id INTEGER, seen_id INTEGER, PRIMARY KEY(user_id,seen_id))')
    xq('CREATE TABLE IF NOT EXISTS reports (reporter_id INTEGER, reported_id INTEGER, PRIMARY KEY(reporter_id,reported_id))')
    xq('CREATE TABLE IF NOT EXISTS referrals (referrer_id INTEGER, referred_id INTEGER, PRIMARY KEY(referrer_id,referred_id))')
    xq('CREATE TABLE IF NOT EXISTS pending_match (user_id INTEGER PRIMARY KEY, partner_id INTEGER)')
    ex = {r[1] for r in (xr("PRAGMA table_info(users)") or [])}
    for col,typ in [('bio','TEXT'),('song','TEXT'),('looking_type','TEXT'),('stars','INTEGER DEFAULT 0')]:
        if col not in ex:
            try: xq(f"ALTER TABLE users ADD COLUMN {col} {typ}")
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
        if not data.get('photo') and old.get('photo'): data['photo'] = old['photo']
        data['stars'] = old.get('stars', 0)
    else:
        data.setdefault('stars', 0)
    cols = ','.join(UFIELDS); ph = ','.join(['?']*len(UFIELDS))
    vals = [data.get(f) for f in UFIELDS]
    upd  = ','.join([f"{f}=excluded.{f}" for f in UFIELDS])
    xq(f"INSERT INTO users (user_id,{cols},updated_at) VALUES(?,{ph},datetime('now','localtime')) "
       f"ON CONFLICT(user_id) DO UPDATE SET {upd},updated_at=datetime('now','localtime')", [uid]+vals)

def db_update(uid, field, val):
    if field not in set(UFIELDS): return
    xq(f"UPDATE users SET {field}=?,updated_at=datetime('now','localtime') WHERE user_id=?",(val,uid))

def db_delete(uid):
    for sql in ['DELETE FROM users WHERE user_id=?',
                'DELETE FROM seen WHERE user_id=? OR seen_id=?',
                'DELETE FROM pending_match WHERE user_id=? OR partner_id=?']:
        try:
            if sql.count('?') == 2: xq(sql,(uid,uid))
            else: xq(sql,(uid,))
        except: pass

def db_all():   return [dict(r) for r in (xr('SELECT * FROM users') or [])]
def db_ids():   return [r[0] for r in (xr('SELECT user_id FROM users') or [])]
def db_count():
    r = xr('SELECT COUNT(*) FROM users'); return r.fetchone()[0] if r else 0

def db_seen_add(u,s): xq('INSERT OR IGNORE INTO seen VALUES(?,?)',(u,s))
def db_seen_get(uid):
    r = xr('SELECT seen_id FROM seen WHERE user_id=?',(uid,))
    return {x[0] for x in r} if r else set()
def db_seen_clear(uid): xq('DELETE FROM seen WHERE user_id=?',(uid,))

def db_report(a,b): xq('INSERT OR IGNORE INTO reports VALUES(?,?)',(a,b))
def db_reported_by(uid):
    r = xr('SELECT reported_id FROM reports WHERE reporter_id=?',(uid,))
    return {x[0] for x in r} if r else set()

def db_ref_add(referrer, referred):
    xq('INSERT OR IGNORE INTO referrals VALUES(?,?)',(referrer,referred))
    xq('UPDATE users SET stars=stars+1 WHERE user_id=?',(referrer,))

def db_ref_count(uid):
    r = xr('SELECT COUNT(*) FROM referrals WHERE referrer_id=?',(uid,))
    return r.fetchone()[0] if r else 0

def db_is_unlocked(uid):
    if uid == ADMIN_ID: return True
    return db_ref_count(uid) >= SHARE_NEEDED

def pm_set(u,p): xq('INSERT OR REPLACE INTO pending_match VALUES(?,?)',(u,p))
def pm_get(uid):
    r = xr('SELECT partner_id FROM pending_match WHERE user_id=?',(uid,))
    row = r.fetchone() if r else None; return row[0] if row else None
def pm_clear(uid): xq('DELETE FROM pending_match WHERE user_id=?',(uid,))

def db_stats():
    def n(q): r=xr(q); return r.fetchone()[0] if r else 0
    return {
        'total'   : n('SELECT COUNT(*) FROM users'),
        'male'    : n("SELECT COUNT(*) FROM users WHERE gender='Male'"),
        'female'  : n("SELECT COUNT(*) FROM users WHERE gender='Female'"),
        'photo'   : n('SELECT COUNT(*) FROM users WHERE photo IS NOT NULL'),
        'refs'    : n('SELECT COUNT(*) FROM referrals'),
        'unlocked': sum(1 for u in db_ids() if db_ref_count(u) >= SHARE_NEEDED),
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
def kb(uid): return admin_kb() if uid==ADMIN_ID else main_kb()

# ═══════════════════════════════════════
# UTILS
# ═══════════════════════════════════════
def sf(d,k,fb='—'):
    v=(d or {}).get(k)
    if isinstance(v,str): v=v.strip()
    return v if v else fb

def check_ch(uid):
    try: return bot.get_chat_member(CHANNEL_ID,uid).status in ('member','creator','administrator')
    except: return False

def notify_admin(txt):
    try: bot.send_message(ADMIN_ID,txt,parse_mode="Markdown")
    except: pass

def err_notify(ctx,e,uid=None):
    tb=traceback.format_exc()[-500:]
    msg=(f"🔴 *Bot Error*\n📍 `{ctx}`\n👤 `{uid}`\n"
         f"❌ `{type(e).__name__}: {e}`\n"
         f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n```\n{tb}```")
    try:
        _req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"},timeout=8)
    except: pass

def fmt(tp, title='👤 *ပရိုဖိုင်*'):
    bio  = f"\n📝 အကြောင်း  : {sf(tp,'bio')}"          if (tp or {}).get('bio')          else ''
    lt   = f"\n🎯 ရှာဖွေရန်  : {sf(tp,'looking_type')}" if (tp or {}).get('looking_type') else ''
    return (f"{title}\n\n"
            f"📛 နာမည်   : {sf(tp,'name')}\n"
            f"🎂 အသက်   : {sf(tp,'age')} နှစ်\n"
            f"🔮 ရာသီ   : {sf(tp,'zodiac')}\n"
            f"📍 မြို့    : {sf(tp,'city')}\n"
            f"🎨 ဝါသနာ  : {sf(tp,'hobby')}\n"
            f"💼 အလုပ်   : {sf(tp,'job')}\n"
            f"🎵 သီချင်း  : {sf(tp,'song')}"
            f"{bio}{lt}\n"
            f"⚧ လိင်    : {sf(tp,'gender')}\n"
            f"💑 ရှာဖွေ  : {sf(tp,'looking_gender')} / {sf(tp,'looking_zodiac','Any')}")

def stars_str(n):
    n=max(0,min(int(n or 0),10))
    return ('⭐'*n) if n>0 else 'မရှိသေး'

def inv_link(uid): return f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"

def send_photo_safe(uid, photo_id, caption, markup):
    try:
        bot.send_photo(uid, photo_id, caption=caption,
                       reply_markup=markup, parse_mode="Markdown")
        return True
    except Exception as e:
        err_notify('send_photo', e, uid)
        try:
            bot.send_message(uid, caption, reply_markup=markup, parse_mode="Markdown")
        except: pass
        return False

# ═══════════════════════════════════════
# SHARE GATE
# ═══════════════════════════════════════
def share_gate(uid):
    cnt  = db_ref_count(uid)
    need = max(0, SHARE_NEEDED-cnt)
    link = inv_link(uid)
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📤 မိတ်ဆွေများကို Share လုပ်မည်",
          url=f"https://t.me/share/url?url={link}&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
    m.row(InlineKeyboardButton("✅ Share ပြီးပြီ — Join စစ်မည်", callback_data="chk_share"))
    bot.send_message(uid,
        f"🔒 *ဖူးစာရှာရန် Unlock လိုအပ်ပါသည်*\n\n"
        f"မိတ်ဆွေ *{SHARE_NEEDED}* ယောက် Bot ကိုသုံးစေပြီးမှ\n"
        f"ဖူးစာရှင်ရဲ့ Telegram link ကို ပေးမည်ဖြစ်ပါသည် 🙏\n\n"
        f"📊 Join ဖြစ်သူ : *{cnt} / {SHARE_NEEDED}*\n"
        f"🎯 ကျန်        : *{need}* ယောက်\n\n"
        f"🔗 `{link}`\n\nShare ပြီးရင် ✅ ကိုနှိပ်ပြီး စစ်ဆေးပေးပါ 👇",
        parse_mode="Markdown", reply_markup=m)

def deliver_match(me, partner):
    """Unlock ဖြစ်ရင် link ချ၊ မဖြစ်ရင် pending သိမ်း + share gate"""
    if db_is_unlocked(me):
        pd = db_get(partner)
        try:
            bot.send_message(me,
                f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
                f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner}) "
                f"{sf(pd,'name','ဖူးစာရှင်')} နဲ့ စကားပြောနိုင်ပါပြီ 🎉",
                parse_mode="Markdown", reply_markup=kb(me))
        except Exception as e:
            err_notify('deliver_match',e,me)
    else:
        pm_set(me, partner)
        share_gate(me)

# ═══════════════════════════════════════
# REGISTRATION STATE
# ═══════════════════════════════════════
_reg   = {}     # uid -> data dict
_in_reg= set()  # uids currently in registration

def start_reg(uid, message, existing_data=None):
    """Start fresh registration, cancel any previous step"""
    _reg[uid] = dict(existing_data) if existing_data else {}
    _in_reg.add(uid)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass
    bot.send_message(uid,
        "✨ *Yay Zat Zodiac မှ ကြိုဆိုပါတယ်!* ✨\n\n"
        "ဖူးစာရှင်/မိတ်ဆွေကို ရှာဖွေဖို့ မေးခွန်းလေးတွေ ဖြေပေးပါ 🙏\n"
        "_(/skip ရိုက်ပြီး ကျော်နိုင်ပါသည်)_\n\n"
        "📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, step_name)

# ── THE KEY FIX: every step checks for /start first ──────────
def _is_restart(msg):
    """Returns True if user typed /start — redirect immediately"""
    if msg.text and msg.text.strip().lower().startswith('/start'):
        uid = msg.chat.id
        _in_reg.discard(uid)
        _reg.pop(uid, None)
        # Manually trigger start flow
        cmd_start(msg)
        return True
    return False

def _skip(msg): return msg.text and msg.text.strip() == '/skip'
def _set(uid,k,msg): _reg.setdefault(uid,{})[k]=msg.text.strip()

# ── Registration steps ────────────────────────────────────────
def step_name(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'name',m)
    bot.send_message(uid,"🎂 အသက် ဘယ်လောက်လဲ? (/skip)-")
    bot.register_next_step_handler(m,step_age)

def step_age(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text:
        if m.text.strip().isdigit(): _set(uid,'age',m)
        else:
            bot.send_message(uid,"⚠️ ဂဏန်းသာ ရိုက်ပါ (ဥပမာ 25)  (/skip)-")
            bot.register_next_step_handler(m,step_age); return
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('/skip')
    bot.send_message(uid,"🔮 ရာသီခွင်?",reply_markup=mk)
    bot.register_next_step_handler(m,step_zodiac)

def step_zodiac(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'zodiac',m)
    bot.send_message(uid,"📍 မြို့ (ဥပမာ Mandalay)? (/skip)-",reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m,step_city)

def step_city(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'city',m)
    bot.send_message(uid,"🎨 ဝါသနာ (ဥပမာ ခရီးသွား, ဂီတ)? (/skip)-")
    bot.register_next_step_handler(m,step_hobby)

def step_hobby(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'hobby',m)
    bot.send_message(uid,"💼 အလုပ်? (/skip)-")
    bot.register_next_step_handler(m,step_job)

def step_job(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'job',m)
    bot.send_message(uid,"🎵 အကြိုက်ဆုံး သီချင်း? (/skip)-")
    bot.register_next_step_handler(m,step_song)

def step_song(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'song',m)
    bot.send_message(uid,
        "📝 *မိမိအကြောင်း အတိုချုံး* (/skip)-\n"
        "_(ဥပမာ: ဆေးကျောင်းသား, ဂီတကိုနှစ်သက်သူ)_",parse_mode="Markdown")
    bot.register_next_step_handler(m,step_bio)

def step_bio(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'bio',m)
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    mk.row('💑 ဖူးစာရှာနေသူ','🤝 မိတ်ဆွေဖွဲ့ချင်သူ'); mk.add('/skip')
    bot.send_message(uid,"🎯 ဘာရှာနေပါသလဲ?",reply_markup=mk)
    bot.register_next_step_handler(m,step_ltype)

def step_ltype(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'looking_type',m)
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    mk.add('Male','Female','/skip')
    bot.send_message(uid,"⚧ သင့်လိင်?",reply_markup=mk)
    bot.register_next_step_handler(m,step_gender)

def step_gender(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'gender',m)
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    mk.add('Male','Female','Both','/skip')
    bot.send_message(uid,"💑 ရှာဖွေနေတဲ့ လိင်?",reply_markup=mk)
    bot.register_next_step_handler(m,step_lgender)

def step_lgender(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'looking_gender',m)
    mk=ReplyKeyboardMarkup(one_time_keyboard=True,resize_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('Any','/skip')
    bot.send_message(uid,"🔮 ရှာဖွေနေတဲ့ ရာသီ?",reply_markup=mk)
    bot.register_next_step_handler(m,step_lzodiac)

def step_lzodiac(m):
    if _is_restart(m): return
    uid=m.chat.id
    if not _skip(m) and m.text: _set(uid,'looking_zodiac',m)
    bot.send_message(uid,
        "📸 Profile ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက /skip)_",
        parse_mode="Markdown",reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(m,step_photo)

def step_photo(m):
    if _is_restart(m): return
    uid    = m.chat.id
    is_new = db_get(uid) is None

    if _skip(m):
        old = db_get(uid)
        if old and old.get('photo'): _reg.setdefault(uid,{})['photo']=old['photo']
    elif m.content_type == 'photo':
        _reg.setdefault(uid,{})['photo'] = m.photo[-1].file_id
    else:
        bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ  (သို့)  /skip ဟုရိုက်ပါ-")
        bot.register_next_step_handler(m,step_photo); return

    data = _reg.pop(uid, {})
    _in_reg.discard(uid)
    db_save(uid, data)

    bot.send_message(uid,
        f"✅ Profile {'တည်ဆောက်' if is_new else 'ပြင်ဆင်'} ပြီးပါပြီ! 🎉\n\n"
        f"ခလုတ်များ နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇",
        parse_mode="Markdown",reply_markup=kb(uid))

    if is_new:
        notify_admin(
            f"🎉 *မှတ်ပုံတင် ပြီးမြောက်!*\n🆔 `{uid}` — {sf(data,'name')}\n"
            f"👥 {db_count()} ယောက်\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ═══════════════════════════════════════
# /start
# ═══════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(message):
    uid  = message.chat.id

    # Handle referral
    try:
        args = message.text.split()
        if len(args)>1 and args[1].startswith('ref_'):
            referrer = int(args[1][4:])
            if referrer!=uid and db_get(referrer) and not db_get(uid):
                db_ref_add(referrer, uid)
                if db_is_unlocked(referrer):
                    pid=pm_get(referrer)
                    if pid: pm_clear(referrer); deliver_match(referrer,pid)
    except Exception as e: err_notify('start/ref',e,uid)

    # Existing user
    if db_get(uid):
        # Cancel any ongoing registration
        _in_reg.discard(uid); _reg.pop(uid,None)
        try: bot.clear_step_handler_by_chat_id(uid)
        except: pass
        bot.send_message(uid,
            "✨ *ကြိုဆိုပါတယ်!* ✨\n\nခလုတ်များနှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇",
            parse_mode="Markdown",reply_markup=kb(uid))
        return

    # New user notification
    try:
        tg=message.from_user.username or str(uid)
        fn=message.from_user.first_name or ''
        ln=message.from_user.last_name  or ''
    except: tg=fn=ln=str(uid)

    notify_admin(
        f"🆕 *User သစ်*\n👤 {fn} {ln} @{tg}\n🆔 `{uid}`\n"
        f"👥 {db_count()} ယောက်\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    start_reg(uid, message)

# ═══════════════════════════════════════
# MY PROFILE
# ═══════════════════════════════════════
def show_profile(message):
    uid=message.chat.id
    tp=db_get(uid)
    if not tp:
        bot.send_message(uid,"Profile မရှိသေးပါ။ /start ကိုနှိပ်ပါ。",reply_markup=kb(uid)); return

    stars=tp.get('stars') or 0
    refs=db_ref_count(uid)
    lock=("✅ Unlock ပြီး" if db_is_unlocked(uid)
          else f"🔒 {refs}/{SHARE_NEEDED} ({max(0,SHARE_NEEDED-refs)} ကျန်)")
    text=(fmt(tp)+
          f"\n\n⭐ ကြယ်ပွင့်   : {stars_str(stars)} ({stars} ခု)\n"
          f"🔗 ဖိတ်ကြားမှု : {lock}")

    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📛 နာမည်",  callback_data="e_name"),
          InlineKeyboardButton("🎂 အသက်",   callback_data="e_age"))
    m.row(InlineKeyboardButton("🔮 ရာသီ",   callback_data="e_zodiac"),
          InlineKeyboardButton("📍 မြို့",   callback_data="e_city"))
    m.row(InlineKeyboardButton("🎨 ဝါသနာ", callback_data="e_hobby"),
          InlineKeyboardButton("💼 အလုပ်",  callback_data="e_job"))
    m.row(InlineKeyboardButton("🎵 သီချင်း",callback_data="e_song"),
          InlineKeyboardButton("📝 Bio",    callback_data="e_bio"))
    m.row(InlineKeyboardButton("📸 ဓာတ်ပုံ",callback_data="e_photo"))
    m.row(InlineKeyboardButton("🔗 Invite Link",     callback_data="my_invite"))
    m.row(InlineKeyboardButton("🔄 Profile ပြန်လုပ်",callback_data="do_reset"),
          InlineKeyboardButton("🗑 Profile ဖျက်",    callback_data="do_delete"))

    if tp.get('photo'):
        send_photo_safe(uid, tp['photo'], text, m)
    else:
        bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")

# ═══════════════════════════════════════
# FIND MATCH
# ═══════════════════════════════════════
def find_match(message):
    uid=message.chat.id
    me=db_get(uid)
    if not me:
        bot.send_message(uid,"/start ကိုနှိပ်ပြီး Profile ဦးတည်ဆောက်ပါ。",reply_markup=kb(uid)); return
    if not db_is_unlocked(uid):
        share_gate(uid); return
    if not check_ch(uid):
        mk=InlineKeyboardMarkup()
        mk.add(InlineKeyboardButton("📢 Channel Join မည်",url=CHANNEL_LINK))
        bot.send_message(uid,"⚠️ Channel ကို အရင် Join ပေးပါ。",reply_markup=mk); return

    seen=db_seen_get(uid); rptd=db_reported_by(uid); excl=seen|rptd|{uid}
    lg=(me.get('looking_gender') or '').strip()
    lz=(me.get('looking_zodiac')  or '').strip()

    pool=[u for u in db_all()
          if u['user_id'] not in excl
          and (not lg or lg in ('Both','Any') or (u.get('gender') or '').strip()==lg)]

    if not pool:
        if seen:
            db_seen_clear(uid)
            bot.send_message(uid,"🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ...")
            find_match(message)
        else:
            bot.send_message(uid,"😔 သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ。\nဖော်ဆွေများကို ဖိတ်ကြားပါ 😊",reply_markup=kb(uid))
        return

    def sk(u):
        zm=0 if (lz and lz not in ('Any','') and (u.get('zodiac') or '')==lz) else 1
        return (zm, -(u.get('stars') or 0))

    pool.sort(key=sk)
    tgt=pool[0]; tid=tgt['user_id']
    db_seen_add(uid,tid)

    note=''
    if lz and lz not in ('Any','') and (tgt.get('zodiac') or '')!=lz:
        note=f"\n_({lz} မတွေ့သောကြောင့် အနီးစပ်ဆုံးပြပေးနေပါသည်)_"

    text=fmt(tgt,title=f"🎯 *မိတ်ဆွေနဲ့ ကိုက်ညီနိုင်မယ့်သူ*{note}")
    mk=InlineKeyboardMarkup()
    mk.row(InlineKeyboardButton("❤️ Like",   callback_data=f"like_{tid}"),
           InlineKeyboardButton("⏭ Skip",   callback_data="skip"),
           InlineKeyboardButton("🚩 Report", callback_data=f"rpt_{tid}"))

    if tgt.get('photo'):
        send_photo_safe(uid, tgt['photo'], text, mk)
    else:
        bot.send_message(uid,text,reply_markup=mk,parse_mode="Markdown")

# ═══════════════════════════════════════
# OTHER HANDLERS
# ═══════════════════════════════════════
def ask_reset(message):
    uid=message.chat.id
    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့ ပြန်လုပ်မည်",callback_data="reset_go"),
          InlineKeyboardButton("❌ မလုပ်တော့ပါ",        callback_data="reset_no"))
    bot.send_message(uid,
        "⚠️ Profile ကို ပြန်လုပ်မှာ သေချာပါသလား?\n"
        "_(/skip ကျော်ပြီး ဟောင်းတန်ဖိုးများ ထိန်းသိမ်းနိုင်ပါသည်)_",
        parse_mode="Markdown",reply_markup=m)

def show_help(message):
    bot.send_message(message.chat.id,
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ဖူးစာရှာမည်* — ကိုက်ညီနိုင်မယ့်သူ ရှာပါ\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
        "🔄 *Profile ပြန်လုပ်* — Profile ပြန်ဖြည့်ပါ\n\n"
        "⚠️ ပြဿနာများ Admin ထံ ဆက်သွယ်ပါ。",
        parse_mode="Markdown",reply_markup=kb(message.chat.id))

def show_stats(message):
    uid=message.chat.id
    if uid!=ADMIN_ID: bot.send_message(uid,"⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်。"); return
    s=db_stats()
    bot.send_message(ADMIN_ID,
        f"📊 *Admin Stats*\n\n"
        f"👥 စုစုပေါင်း   : *{s['total']}* ယောက်\n"
        f"♂️ ကျား        : {s['male']}\n♀️ မ           : {s['female']}\n"
        f"📸 ဓာတ်ပုံပါ   : {s['photo']}\n"
        f"🔓 Unlock ပြီး : {s['unlocked']}\n"
        f"🔗 Referral    : {s['refs']}\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        parse_mode="Markdown",reply_markup=admin_kb())

def show_admin(message):
    if message.chat.id!=ADMIN_ID: return
    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📊 Stats",       callback_data="adm_stats"),
          InlineKeyboardButton("👥 Users",        callback_data="adm_users"))
    m.row(InlineKeyboardButton("📢 Broadcast",    callback_data="adm_bcast"),
          InlineKeyboardButton("🗑 User ဖျက်",   callback_data="adm_del"))
    m.row(InlineKeyboardButton("🔓 Manual Unlock",callback_data="adm_unlock"))
    bot.send_message(ADMIN_ID,"🛠 *Admin Panel*",parse_mode="Markdown",reply_markup=m)

def _bcast(m):
    if m.text and m.text.startswith('/'): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    ok=fail=0
    for uid in db_ids():
        try: bot.send_message(uid,f"📢 *Admin မှ*\n\n{m.text}",parse_mode="Markdown"); ok+=1
        except: fail+=1
    bot.send_message(ADMIN_ID,f"✅ {ok} ရောက် / ❌ {fail} မရောက်")

def _del_u(m):
    if m.text and m.text.startswith('/'): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    try:
        uid=int(m.text.strip())
        if db_get(uid): db_delete(uid); bot.send_message(ADMIN_ID,f"✅ `{uid}` ဖျက်ပြီး",parse_mode="Markdown")
        else: bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ。")
    except: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ。")

def _unlock_u(m):
    if m.text and m.text.startswith('/'): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး。"); return
    try:
        uid=int(m.text.strip())
        if db_get(uid):
            for i in range(SHARE_NEEDED):
                xq('INSERT OR IGNORE INTO referrals VALUES(?,?)',(uid,-(i+1)))
            xq('UPDATE users SET stars=stars+? WHERE user_id=?',(SHARE_NEEDED,uid))
            bot.send_message(ADMIN_ID,f"✅ `{uid}` unlock ပြီး",parse_mode="Markdown")
            try: bot.send_message(uid,"✅ Admin က unlock လုပ်ပေးပြီးပါပြီ!\n🔍 ဖူးစာရှာနိုင်ပါပြီ 💖",reply_markup=kb(uid))
            except: pass
            pid=pm_get(uid)
            if pid: pm_clear(uid); deliver_match(uid,pid)
        else: bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ。")
    except: bot.send_message(ADMIN_ID,"⚠️ ID ဂဏန်းသာ。")

def save_edit(message, field):
    uid=message.chat.id
    if _is_restart(message): return
    try:
        if field=='photo':
            if message.content_type!='photo':
                bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ。"); return
            db_update(uid,'photo',message.photo[-1].file_id)
        else:
            if not message.text or not message.text.strip() or message.text=='/skip':
                bot.send_message(uid,"✅ မပြောင်းဘဲ ထိန်းသိမ်းပြီး。",reply_markup=kb(uid)); return
            db_update(uid,field,message.text.strip())
        bot.send_message(uid,"✅ ပြင်ဆင်မှု အောင်မြင်!",reply_markup=kb(uid))
    except Exception as e:
        err_notify(f'save_edit/{field}',e,uid)
        bot.send_message(uid,"⚠️ မှားသွားပါသည်。ထပ်ကြိုးစားပါ。")

# ═══════════════════════════════════════
# MENU ROUTER
# ═══════════════════════════════════════
MENU={
    "🔍 ဖူးစာရှာမည်"    :find_match,
    "👤 ကိုယ့်ပရိုဖိုင်" :show_profile,
    "ℹ️ အကူအညီ"         :show_help,
    "🔄 Profile ပြန်လုပ်" :ask_reset,
    "📊 စာရင်းအင်း"      :show_stats,
    "🛠 Admin Panel"      :show_admin,
}

@bot.message_handler(func=lambda m: m.text in MENU)
def menu_router(message):
    uid=message.chat.id
    # cancel any ongoing registration step
    _in_reg.discard(uid); _reg.pop(uid,None)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass
    try: MENU[message.text](message)
    except Exception as e:
        err_notify(f'menu/{message.text}',e,uid)
        bot.send_message(uid,"⚠️ မှားသွားပါသည်。နောက်မှ ထပ်ကြိုးစားပါ。")

@bot.message_handler(commands=['reset'])
def cmd_reset(m): ask_reset(m)
@bot.message_handler(commands=['myprofile'])
def cmd_profile(m): show_profile(m)
@bot.message_handler(commands=['stats'])
def cmd_stats(m): show_stats(m)
@bot.message_handler(commands=['deleteprofile'])
def cmd_del(message):
    uid=message.chat.id
    m=InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့ ဖျက်မည်",callback_data="del_yes"),
          InlineKeyboardButton("❌ မဖျက်တော့ပါ",     callback_data="del_no"))
    bot.send_message(uid,"⚠️ Profile ဖျက်မှာ သေချာပါသလား?",reply_markup=m)

# ═══════════════════════════════════════
# CALLBACK HANDLER
# ═══════════════════════════════════════
EDIT_LABELS={'name':'နာမည်','age':'အသက်','zodiac':'ရာသီ','city':'မြို့',
             'hobby':'ဝါသနာ','job':'အလုပ်','song':'သီချင်း','bio':'Bio',
             'looking_type':'ရှာဖွေမည့်အမျိုးအစား','gender':'လိင်',
             'looking_gender':'ရှာဖွေမည့်လိင်','looking_zodiac':'ရှာဖွေမည့်ရာသီ'}

@bot.callback_query_handler(func=lambda c: True)
def on_cb(call):
    uid=call.message.chat.id; d=call.data
    try: _cb(call,uid,d)
    except Exception as e:
        err_notify(f'cb/{d}',e,uid)
        try: bot.answer_callback_query(call.id,"⚠️ မှားသွားပါသည်。",show_alert=True)
        except: pass

def _cb(call,uid,d):

    if d=="chk_share":
        cnt=db_ref_count(uid)
        if cnt>=SHARE_NEEDED:
            bot.answer_callback_query(call.id,"🎉 Unlock ဖြစ်ပါပြီ!",show_alert=True)
            try: bot.delete_message(uid,call.message.message_id)
            except: pass
            bot.send_message(uid,
                f"✅ *{SHARE_NEEDED} ယောက် ပြည့်ပါပြီ! Unlock ဖြစ်ပါပြီ!* 🎉\n\n"
                f"🔍 ဖူးစာရှာမည် ကိုနှိပ်ပြီး ရှာနိုင်ပါပြီ 💖",
                parse_mode="Markdown",reply_markup=kb(uid))
            pid=pm_get(uid)
            if pid: pm_clear(uid); deliver_match(uid,pid)
        else:
            bot.answer_callback_query(call.id,
                f"ကျန်သေးသည် {SHARE_NEEDED-cnt} ယောက်。ဆက်ဖိတ်ကြားပါ!",show_alert=True)

    elif d=="do_reset":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        ask_reset(call.message)

    elif d=="reset_go":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        old=db_get(uid)
        start_reg(uid, call.message, existing_data=old)

    elif d=="reset_no":
        bot.answer_callback_query(call.id,"မလုပ်တော့ပါ 👍")
        try: bot.delete_message(uid,call.message.message_id)
        except: pass

    elif d=="do_delete":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        m=InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့ ဖျက်မည်",callback_data="del_yes"),
              InlineKeyboardButton("❌ မဖျက်တော့ပါ",     callback_data="del_no"))
        bot.send_message(uid,"⚠️ Profile ဖျက်မှာ သေချာပါသလား?",reply_markup=m)

    elif d=="del_yes":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        _in_reg.discard(uid); _reg.pop(uid,None)
        db_delete(uid)
        bot.send_message(uid,
            "🗑 Profile ဖျက်ပြီးပါပြီ。\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်。",
            reply_markup=ReplyKeyboardRemove())

    elif d=="del_no":
        bot.answer_callback_query(call.id,"မဖျက်တော့ပါ 👍")
        try: bot.delete_message(uid,call.message.message_id)
        except: pass

    elif d.startswith("e_"):
        field=d[2:]
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        _in_reg.discard(uid); _reg.pop(uid,None)
        if field=='photo':
            msg=bot.send_message(uid,"📸 ဓာတ်ပုံအသစ် ပေးပို့ပါ-",reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg,save_edit,'photo')
        else:
            label=EDIT_LABELS.get(field,field)
            msg=bot.send_message(uid,
                f"📝 *{label}* အသစ် ရိုက်ထည့်ပါ-\n_(/skip — မပြောင်းဘဲ ကျော်ရန်)_",
                parse_mode="Markdown",reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg,save_edit,field)

    elif d=="my_invite":
        cnt=db_ref_count(uid); link=inv_link(uid)
        m=InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("📤 Share လုပ်မည်",
              url=f"https://t.me/share/url?url={link}&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
        bot.send_message(uid,
            f"🔗 *Invite Link*\n\n`{link}`\n\n"
            f"👥 Join ဖြစ်သူ : *{cnt}/{SHARE_NEEDED}*\n"
            +("✅ Unlock ပြီး" if db_is_unlocked(uid) else f"🔒 {SHARE_NEEDED-cnt} ကျန်"),
            parse_mode="Markdown",reply_markup=m)

    elif d=="skip":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        find_match(call.message)

    elif d.startswith("like_"):
        tid=int(d[5:])
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        if not check_ch(uid):
            bot.answer_callback_query(call.id,"⚠️ Channel ကို Join ပါ!",show_alert=True); return
        me=db_get(uid) or {}
        am=InlineKeyboardMarkup()
        am.row(InlineKeyboardButton("✅ လက်ခံမည်",callback_data=f"accept_{uid}"),
               InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline"))
        cap=(f"💌 *'{sf(me,'name','တစ်ယောက်')}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n"
             +fmt(me,title='👤 *သူ/သူမ ရဲ့ Profile*'))
        try:
            if me.get('photo'): send_photo_safe(tid,me['photo'],cap,am)
            else: bot.send_message(tid,cap,reply_markup=am,parse_mode="Markdown")
            bot.send_message(uid,
                "❤️ Like လုပ်လိုက်ပါပြီ!\nတစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊",
                reply_markup=kb(uid))
        except Exception as e:
            err_notify('like/send',e,uid)
            bot.send_message(uid,"⚠️ တစ်ဖက်လူမှာ Bot Block ထားသဖြင့် ပေးပို့မရပါ。",reply_markup=kb(uid))

    elif d.startswith("accept_"):
        liker=int(d[7:])
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        notify_admin(f"💖 *Match!* [A](tg://user?id={uid}) + [B](tg://user?id={liker})\n"
                     f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        deliver_match(uid,liker)
        deliver_match(liker,uid)

    elif d=="decline":
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        bot.send_message(uid,"❌ ငြင်းဆန်လိုက်ပါပြီ。",reply_markup=kb(uid))

    elif d.startswith("rpt_"):
        tid=int(d[4:])
        db_report(uid,tid)
        bot.answer_callback_query(call.id,"🚩 Report လုပ်ပြီး。",show_alert=True)
        try: bot.delete_message(uid,call.message.message_id)
        except: pass
        notify_admin(f"🚩 *Report*\n`{uid}` {sf(db_get(uid),'name')} → `{tid}` {sf(db_get(tid),'name')}")

    elif d=="adm_stats" and uid==ADMIN_ID: show_stats(call.message)
    elif d=="adm_users" and uid==ADMIN_ID:
        rows=db_all()[:30]
        lines=[f"{i}. {sf(u,'name')} `{u['user_id']}` ⭐{u.get('stars',0)} "
               f"{'🔓' if db_is_unlocked(u['user_id']) else '🔒'}"
               for i,u in enumerate(rows,1)]
        bot.send_message(ADMIN_ID,"👥 *User List*\n\n"+("\n".join(lines) or "မရှိသေး"),parse_mode="Markdown")
    elif d=="adm_bcast" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"📢 Message (/cancel)-")
        bot.register_next_step_handler(msg,_bcast)
    elif d=="adm_del" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"🗑 User ID (/cancel)-")
        bot.register_next_step_handler(msg,_del_u)
    elif d=="adm_unlock" and uid==ADMIN_ID:
        msg=bot.send_message(ADMIN_ID,"🔓 Unlock မည့် User ID (/cancel)-")
        bot.register_next_step_handler(msg,_unlock_u)

    try: bot.answer_callback_query(call.id)
    except: pass

# ═══════════════════════════════════════
# AUTO-RESTART POLLING
# ═══════════════════════════════════════
print(f"✅ Yay Zat Bot [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
notify_admin(f"🟢 *Bot Online*\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=40, long_polling_timeout=40)
    except Exception as e:
        msg=(f"🔴 *Polling Error — Restarting...*\n`{type(e).__name__}: {e}`\n"
             f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print(msg)
        try: _req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                       json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"},timeout=8)
        except: pass
        time.sleep(5)
