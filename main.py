"""
Yay Zat Bot — Simple Polling Version (for Koyeb Worker)
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
ADMIN_ID     = 6131831207
HEART_STICKER = "CAACAgIAAxkBAAEBmjFnQ_example"  # ← သင့် sticker ID ထည့်ပါ
ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

bot = telebot.TeleBot(TOKEN, threaded=True, skip_pending=True)

# ══════════════════════════════════════════
# 🗄️ DATABASE
# ══════════════════════════════════════════
DB = 'yayzat.db'
_lk = threading.Lock()
_db = None

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
        _db = c
    except Exception as e:
        print(f"❌ DB error: {e}")

open_db()

def xq(sql, p=()):    with _lk:
        for _ in range(3):
            try:
                r = _db.execute(sql, p)
                _db.commit()
                return r
            except:
                open_db()
                time.sleep(0.3)

def xr(sql, p=()):
    with _lk:
        for _ in range(3):
            try:
                return _db.execute(sql, p)
            except:
                open_db()
                time.sleep(0.3)
        return None

def init_db():
    xq('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, name TEXT, age TEXT, zodiac TEXT,
        city TEXT, hobby TEXT, job TEXT, bio TEXT, gender TEXT,
        looking_gender TEXT, looking_zodiac TEXT, photo TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    xq('CREATE TABLE IF NOT EXISTS seen (user_id INTEGER, seen_id INTEGER, PRIMARY KEY(user_id, seen_id))')
init_db()

UF = ['name','age','zodiac','city','hobby','job','bio','gender','looking_gender','looking_zodiac','photo']

def db_get(uid):
    try:
        r = xr('SELECT * FROM users WHERE user_id=?', (uid,))
        row = r.fetchone() if r else None
        return dict(row) if row else None
    except: return None

def db_save(uid, data):
    try:
        old = db_get(uid)
        if old and not data.get('photo') and old.get('photo'): data['photo'] = old['photo']
        cols=','.join(UF); ph=','.join(['?']*len(UF)); vals=[data.get(f) for f in UF]
        upd=','.join([f"{f}=excluded.{f}" for f in UF])
        xq(f"INSERT INTO users (user_id,{cols}) VALUES(?,{ph}) ON CONFLICT(user_id) DO UPDATE SET {upd}", [uid]+vals)
    except: pass

def db_update(uid, f, v):
    if f in UF:        try: xq(f"UPDATE users SET {f}=? WHERE user_id=?", (v, uid))
        except: pass

def db_delete(uid):
    try:
        xq('DELETE FROM users WHERE user_id=?', (uid,))
        xq('DELETE FROM seen WHERE user_id=? OR seen_id=?', (uid, uid))
    except: pass

def db_all():
    try: return [dict(r) for r in (xr('SELECT * FROM users') or [])]
    except: return []
def db_ids():
    try: return [r[0] for r in (xr('SELECT user_id FROM users') or [])]
    except: return []
def db_count():
    try: r=xr('SELECT COUNT(*) FROM users'); return r.fetchone()[0] if r else 0
    except: return 0
def db_seen_add(u,s):
    try: xq('INSERT OR IGNORE INTO seen VALUES(?,?)', (u,s))
    except: pass
def db_seen_get(uid):
    try: r=xr('SELECT seen_id FROM seen WHERE user_id=?',(uid,)); return {x[0] for x in r} if r else set()
    except: return set()
def db_seen_clear(uid):
    try: xq('DELETE FROM seen WHERE user_id=?',(uid,))
    except: pass

# ══════════════════════════════════════════
# ⌨️ UTILS & KEYBOARDS
# ══════════════════════════════════════════
def sf(d,k,fb='—'): v=(d or {}).get(k); return v.strip() if isinstance(v,str) and v.strip() else fb

def kb(uid):
    m=ReplyKeyboardMarkup(resize_keyboard=True,is_persistent=True)
    m.row(KeyboardButton("🔍 ရှာမည်"),KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    m.row(KeyboardButton("ℹ️ အကူအညီ"),KeyboardButton("🔄 ပြန်လုပ်"))
    return m

def fmt(tp, title='👤 *ပရိုဖိုင်*'):
    bio=f"\n📝 Bio:{sf(tp,'bio')}" if (tp or {}).get('bio') else ''
    return (f"{title}\n\n📛:{sf(tp,'name')}\n🎂:{sf(tp,'age')}\n🔮:{sf(tp,'zodiac')}\n📍:{sf(tp,'city')}\n"
            f"🎨:{sf(tp,'hobby')}\n💼:{sf(tp,'job')}{bio}\n⚧:{sf(tp,'gender')}\n🔍:{sf(tp,'looking_gender')}/{sf(tp,'looking_zodiac','Any')}")

def send_safe(uid, photo, caption, markup):
    if photo:
        try: bot.send_photo(uid, photo, caption=caption, reply_markup=markup, parse_mode="Markdown", timeout=30); return
        except: pass
    bot.send_message(uid, caption, reply_markup=markup, parse_mode="Markdown", timeout=30)
def admin_msg(txt):
    try: bot.send_message(ADMIN_ID, txt, parse_mode="Markdown", timeout=30)
    except: pass

def err_log(ctx,e,uid=None):
    tb=traceback.format_exc()[-300:]
    msg=f"🔴 *Error* `{ctx}`\n👤 `{uid}`\n`{type(e).__name__}: {str(e)[:80]}`\n```\n{tb}```"
    try: _req.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"}, timeout=15)
    except: pass

# ══════════════════════════════════════════
# 🔄 REGISTRATION
# ══════════════════════════════════════════
_reg, _step = {}, {}

def _is_start(msg):
    if msg.text and msg.text.strip().lower().startswith('/start'):
        uid=msg.chat.id; _reg.pop(uid,None); _step.pop(uid,None)
        try: bot.clear_step_handler_by_chat_id(uid)
        except: pass
        cmd_start(msg); return True
    return False

def _sk(msg): return msg.text and msg.text.strip()=='/skip'
def _sv(uid,k,msg): _reg.setdefault(uid,{})[k]=msg.text.strip()

def safe_next(msg, func, *a):
    try: bot.register_next_step_handler(msg, func, *a)
    except: pass

def begin_reg(uid, msg, prefill=None):
    _reg[uid]=dict(prefill) if prefill else {}
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass
    bot.send_message(uid, "📋 *မှတ်ပုံတင်မည်*\n_(/skip ကျော်)_\n📛 *နာမည်*", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(), timeout=30)
    safe_next(msg, r_name)

def r_name(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'name',m)
    bot.send_message(uid, "🎂 အသက်? (/skip)-", timeout=30); safe_next(m, r_age)

def r_age(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m) and m.text and m.text.strip().isdigit(): _sv(uid,'age',m)
    mk=ReplyKeyboardMarkup(one_time_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('/skip')    bot.send_message(uid, "🔮 ရာသီ?", reply_markup=mk, timeout=30); safe_next(m, r_zodiac)

def r_zodiac(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'zodiac',m)
    bot.send_message(uid, "📍 မြို့? (/skip)-", reply_markup=ReplyKeyboardRemove(), timeout=30); safe_next(m, r_city)

def r_city(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'city',m)
    bot.send_message(uid, "🎨 ဝါသနာ? (/skip)-", timeout=30); safe_next(m, r_hobby)

def r_hobby(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'hobby',m)
    bot.send_message(uid, "💼 အလုပ်? (/skip)-", timeout=30); safe_next(m, r_job)

def r_job(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'job',m)
    bot.send_message(uid, "📝 Bio? (/skip)-", parse_mode="Markdown", timeout=30); safe_next(m, r_bio)

def r_bio(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'bio',m)
    mk=ReplyKeyboardMarkup(one_time_keyboard=True); mk.add('Male','Female','/skip')
    bot.send_message(uid, "⚧ လိင်?", reply_markup=mk, timeout=30); safe_next(m, r_gender)

def r_gender(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'gender',m)
    mk=ReplyKeyboardMarkup(one_time_keyboard=True); mk.add('Male','Female','Both','/skip')
    bot.send_message(uid, "💑 ရှာမည့်လိင်?", reply_markup=mk, timeout=30); safe_next(m, r_lgender)

def r_lgender(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'looking_gender',m)
    mk=ReplyKeyboardMarkup(one_time_keyboard=True)
    for z in ZODIACS: mk.add(z)
    mk.add('Any','/skip')
    bot.send_message(uid, "🔮 ရှာမည့်ရာသီ?", reply_markup=mk, timeout=30); safe_next(m, r_lzodiac)

def r_lzodiac(m):    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'looking_zodiac',m)
    bot.send_message(uid, "📸 ဓာတ်ပုံ? (/skip)-", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(), timeout=30); safe_next(m, r_photo)

def r_photo(m):
    if _is_start(m): return
    uid=m.chat.id; is_new=db_get(uid) is None
    if _sk(m):
        old=db_get(uid)
        if old and old.get('photo'): _reg.setdefault(uid,{})['photo']=old['photo']
    elif m.content_type=='photo': _reg.setdefault(uid,{})['photo']=m.photo[-1].file_id
    else: bot.send_message(uid, "⚠️ ဓာတ်ပုံ (သို့) /skip-", timeout=30); safe_next(m, r_photo); return
    data=_reg.pop(uid,{}); db_save(uid,data)
    bot.send_message(uid, f"✅ Profile {'အသစ်' if is_new else 'ပြင်'}ပြီး!", reply_markup=kb(uid), timeout=30)
    if is_new: admin_msg(f"🆕 User `{uid}` — {sf(data,'name')}")

# ══════════════════════════════════════════
# 📡 HANDLERS
# ══════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(m):
    uid=m.chat.id; _reg.pop(uid,None)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass
    if db_get(uid):
        bot.send_message(uid, "✨ *ကြိုဆိုပါတယ်!*", parse_mode="Markdown", reply_markup=kb(uid), timeout=30); return
    begin_reg(uid, m)

def find_match(m):
    uid=m.chat.id; me=db_get(uid)
    if not me: bot.send_message(uid, "/start နှိပ်ပါ", reply_markup=kb(uid), timeout=30); return
    seen=db_seen_get(uid); excl=seen|{uid}
    lg=(me.get('looking_gender')or'').strip(); lz=(me.get('looking_zodiac')or'').strip()
    pool=[u for u in db_all() if u['user_id'] not in excl and (lg in('Both','Any','') or (u.get('gender')or'').strip()==lg)]
    if not pool:
        if seen: db_seen_clear(uid); bot.send_message(uid, "🔄 ပြန်စ...", timeout=30); find_match(m); return
        bot.send_message(uid, "😔 မတွေ့", reply_markup=kb(uid), timeout=30); return
    if lz and lz not in('Any',''): pool=sorted(pool, key=lambda x:0 if(x.get('zodiac')or'')==lz else 1)
    tgt=pool[0]; tid=tgt['user_id']; db_seen_add(uid,tid)
    mk=InlineKeyboardMarkup(); mk.row(InlineKeyboardButton("❤️",callback_data=f"like_{tid}"),InlineKeyboardButton("👎",callback_data=f"nope_{tid}"))
    send_safe(uid, tgt.get('photo'), fmt(tgt, f"✨ ရှာတွေ့!"), mk)

def show_profile(m):
    uid=m.chat.id; tp=db_get(uid)
    if not tp: bot.send_message(uid, "Profile မရှိ", reply_markup=kb(uid), timeout=30); return
    mk=InlineKeyboardMarkup()
    for f in ['name','age','zodiac','city','hobby','job','bio','photo','gender','looking_gender']:
        mk.row(InlineKeyboardButton(f"📝 {f}", callback_data=f"e_{f}"))
    mk.row(InlineKeyboardButton("🔄 ပြန်လုပ်", callback_data="do_reset"), InlineKeyboardButton("🗑 ဖျက်", callback_data="do_delete"))    send_safe(uid, tp.get('photo'), fmt(tp), mk)

@bot.message_handler(func=lambda m: m.text in {"🔍 ရှာမည်","👤 ကိုယ့်ပရိုဖိုင်","ℹ️ အကူအညီ","🔄 ပြန်လုပ်"})
def menu_router(m):
    uid=m.chat.id; _reg.pop(uid,None)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass
    {"🔍 ရှာမည်":find_match, "👤 ကိုယ့်ပရိုဖိုင်":show_profile}.get(m.text, lambda x:bot.send_message(x.chat.id,"🚧",reply_markup=kb(x.chat.id),timeout=30))(m)

EDIT_MAP={'name':'နာမည်','age':'အသက်','zodiac':'ရာသီ','city':'မြို့','hobby':'ဝါသနာ','job':'အလုပ်','bio':'Bio','photo':'ဓာတ်ပုံ','gender':'လိင်','looking_gender':'ရှာဖွေမည့်လိင်'}
def save_edit(m, field):
    uid=m.chat.id
    if field=='photo' and m.content_type!='photo': bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ", timeout=30); return
    val=m.photo[-1].file_id if field=='photo' else (m.text.strip() if m.text and m.text.strip()!='/skip' else None)
    if val: db_update(uid,field,val); bot.send_message(uid,"✅ ပြင်ပြီး", reply_markup=kb(uid), timeout=30)
    else: bot.send_message(uid,"✅ မပြောင်းဘဲ ထိန်း", reply_markup=kb(uid), timeout=30)

@bot.callback_query_handler(func=lambda c: True)
def on_cb(call):
    uid=call.message.chat.id; d=call.data
    try:
        if d.startswith("like_"):
            tid=int(d[5:]); bot.delete_message(uid, call.message.message_id)
            try: bot.send_sticker(uid, HEART_STICKER, timeout=30)
            except: bot.send_message(uid, "❤️", timeout=30)
            me=db_get(uid) or {}; mk=InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("✅",callback_data=f"accept_{uid}"),InlineKeyboardButton("❌",callback_data="decline"))
            send_safe(tid, me.get('photo'), f"💌 '{sf(me,'name','တစ်ယောက်')}' က Like လုပ်ထား!\n{fmt(me)}", mk)
            bot.send_message(uid, "❤️ ပို့ပြီး", reply_markup=kb(uid), timeout=30)
        elif d.startswith("nope_"): bot.delete_message(uid, call.message.message_id); find_match(call.message)
        elif d.startswith("accept_"):
            liker=int(d[7:]); bot.delete_message(uid, call.message.message_id)
            for me,p in [(uid,liker),(liker,uid)]:
                pd=db_get(p); bot.send_message(me, f"💖 Match! [နှိပ်](tg://user?id={p})", parse_mode="Markdown", reply_markup=kb(me), timeout=30)
        elif d=="decline": bot.delete_message(uid, call.message.message_id); bot.send_message(uid, "❌", reply_markup=kb(uid), timeout=30)
        elif d=="do_reset": bot.delete_message(uid, call.message.message_id); begin_reg(uid, call.message, prefill=db_get(uid))
        elif d=="do_delete": bot.delete_message(uid, call.message.message_id); db_delete(uid); _reg.pop(uid,None); bot.send_message(uid, "🗑 ဖျက်ပြီး", reply_markup=ReplyKeyboardRemove(), timeout=30)
        elif d.startswith("e_"):
            f=d[2:]; bot.delete_message(uid, call.message.message_id); _reg.pop(uid,None)
            try: bot.clear_step_handler_by_chat_id(uid)
            except: pass
            if f=='photo': safe_next(bot.send_message(uid,"📸 ဓာတ်ပုံ ပေးပို့ပါ", reply_markup=ReplyKeyboardRemove(), timeout=30), save_edit, 'photo')
            else: safe_next(bot.send_message(uid, f"📝 *{EDIT_MAP.get(f,f)}* ရိုက်ပါ", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(), timeout=30), save_edit, f)
        bot.answer_callback_query(call.id, timeout=30)
    except: pass

# ══════════════════════════════════════════
# 🔄 POLLING LOOP — Worker အတွက်
# ══════════════════════════════════════════
print(f"✅ Yay Zat Bot Started [{datetime.now()}]")admin_msg(f"🟢 *Bot Online*\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

while True:
    try:
        bot.polling(none_stop=True, interval=2, timeout=60, long_polling_timeout=50)
    except KeyboardInterrupt:
        print("🛑 Stopped")
        break
    except Exception as e:
        print(f"🔴 Error: {e}")
        admin_msg(f"🔴 Error: {e}")
        time.sleep(5)
