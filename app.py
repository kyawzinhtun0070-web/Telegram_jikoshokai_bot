"""
Yay Zat Zodiac Bot — Koyeb Optimized (Webhook + Flask Health)
"""
import os
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
from flask import Flask, request, jsonify

# ══════════════════════════════════════════
# ⚙️ CONFIG
# ══════════════════════════════════════════
TOKEN        = os.getenv('BOT_TOKEN', '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc')
ADMIN_ID     = int(os.getenv('ADMIN_ID', '6131831207'))
HEART_STICKER = os.getenv('HEART_STICKER', 'CAACAgIAAxkBAAEBmjFnQ_example')
ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

# Koyeb အတွက် Port & Domain
PORT = int(os.getenv('PORT', 8000))
WEBHOOK_URL = os.getenv('WEBHOOK_URL', f"https://your-app-name.koyeb.app/webhook")  # ← ကိုယ့် Koyeb app URL ထည့်ပါ

# ══════════════════════════════════════════
# 🌐 REQUESTS SESSION
# ══════════════════════════════════════════
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_retry_session():
    session = _req.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.mount('http://', HTTPAdapter(max_retries=retry))
    return session

_retry_session = create_retry_session()
import telebot.apihelper
telebot.apihelper.REQ_TIMEOUT = 60
telebot.apihelper.session = _retry_session

bot = telebot.TeleBot(TOKEN, threaded=True, skip_pending=True)
# ══════════════════════════════════════════
# 🗄️ DATABASE
# ══════════════════════════════════════════
DB = 'yayzat.db'
_lk = threading.Lock()
_db = None

def open_db():
    global _db
    if _db:
        try: _db.close()
        except: pass
    c = sqlite3.connect(DB, check_same_thread=False, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=15000")
    _db = c
open_db()

def xq(sql, p=()):
    with _lk:
        for _ in range(3):
            try: r=_db.execute(sql,p); _db.commit(); return r
            except sqlite3.OperationalError: open_db(); time.sleep(0.3)

def xr(sql, p=()):
    with _lk:
        for _ in range(3):
            try: return _db.execute(sql,p)
            except sqlite3.OperationalError: open_db(); time.sleep(0.3)
        return None

def init_db():
    xq('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, name TEXT, age TEXT, zodiac TEXT,
        city TEXT, hobby TEXT, job TEXT, bio TEXT, gender TEXT,
        looking_gender TEXT, looking_zodiac TEXT, photo TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )''')
    xq('CREATE TABLE IF NOT EXISTS seen (user_id INTEGER, seen_id INTEGER, PRIMARY KEY(user_id, seen_id))')
    xq('CREATE TABLE IF NOT EXISTS reports (reporter_id INTEGER, reported_id INTEGER, PRIMARY KEY(reporter_id, reported_id))')
init_db()

UF = ['name','age','zodiac','city','hobby','job','bio','gender','looking_gender','looking_zodiac','photo']

def db_get(uid):
    try:
        r = xr('SELECT * FROM users WHERE user_id=?', (uid,))
        row = r.fetchone() if r else None
        return dict(row) if row else None    except: return None

def db_save(uid, data):
    try:
        old = db_get(uid)
        if old and not data.get('photo') and old.get('photo'): data['photo'] = old['photo']
        cols=','.join(UF); ph=','.join(['?']*len(UF)); vals=[data.get(f) for f in UF]
        upd=','.join([f"{f}=excluded.{f}" for f in UF])
        xq(f"INSERT INTO users (user_id,{cols}) VALUES(?,{ph}) ON CONFLICT(user_id) DO UPDATE SET {upd}", [uid]+vals)
        return True
    except: return False

def db_update(uid, field, val):
    if field in set(UF): xq(f"UPDATE users SET {field}=? WHERE user_id=?", (val, uid))

def db_delete(uid):
    xq('DELETE FROM users WHERE user_id=?', (uid,))
    xq('DELETE FROM seen WHERE user_id=? OR seen_id=?', (uid, uid))

def db_all(): return [dict(r) for r in (xr('SELECT * FROM users') or [])]
def db_ids(): return [r[0] for r in (xr('SELECT user_id FROM users') or [])]
def db_count(): r=xr('SELECT COUNT(*) FROM users'); return r.fetchone()[0] if r else 0
def db_seen_add(u,s): xq('INSERT OR IGNORE INTO seen VALUES(?,?)', (u,s))
def db_seen_get(uid): r=xr('SELECT seen_id FROM seen WHERE user_id=?', (uid,)); return {x[0] for x in r} if r else set()
def db_seen_clear(uid): xq('DELETE FROM seen WHERE user_id=?', (uid,))
def db_report(a,b): xq('INSERT OR IGNORE INTO reports VALUES(?,?)', (a,b))
def db_reported_by(uid): r=xr('SELECT reported_id FROM reports WHERE reporter_id=?', (uid,)); return {x[0] for x in r} if r else set()
def db_stats():
    def n(q): r=xr(q); return r.fetchone()[0] if r else 0
    return {'total':n('SELECT COUNT(*) FROM users'),'male':n("SELECT COUNT(*) FROM users WHERE gender='Male'"),
            'female':n("SELECT COUNT(*) FROM users WHERE gender='Female'"),'photo':n('SELECT COUNT(*) FROM users WHERE photo IS NOT NULL')}

# ══════════════════════════════════════════
# ⌨️ KEYBOARDS & UTILS
# ══════════════════════════════════════════
def main_kb():
    m=ReplyKeyboardMarkup(resize_keyboard=True,is_persistent=True)
    m.row(KeyboardButton("🔍 ရှာမည်"),KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    m.row(KeyboardButton("ℹ️ အကူအညီ"),KeyboardButton("🔄 ပြန်လုပ်"))
    return m
def admin_kb():
    m=main_kb(); m.row(KeyboardButton("📊 Admin Stats"),KeyboardButton("🛠 Admin Panel")); return m
def kb(uid): return admin_kb() if uid==ADMIN_ID else main_kb()

def sf(d,k,fb='—'): v=(d or {}).get(k); return v.strip() if isinstance(v,str) and v.strip() else fb
def admin_msg(txt):
    try: bot.send_message(ADMIN_ID, txt, parse_mode="Markdown", timeout=30)
    except: pass
def err_log(ctx,e,uid=None):
    tb=traceback.format_exc()[-300:]    msg=f"🔴 *Error* `{ctx}`\n👤 `{uid}`\n`{type(e).__name__}: {str(e)[:80]}`\n```\n{tb}```"
    try: _retry_session.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":ADMIN_ID,"text":msg,"parse_mode":"Markdown"}, timeout=15)
    except: pass
def fmt(tp, title='👤 *ပရိုဖိုင်*'):
    bio=f"\n📝 Bio      : {sf(tp,'bio')}" if (tp or {}).get('bio') else ''
    return (f"{title}\n\n📛 နာမည်   : {sf(tp,'name')}\n🎂 အသက်   : {sf(tp,'age')} နှစ်\n🔮 ရာသီ   : {sf(tp,'zodiac')}\n"
            f"📍 မြို့    : {sf(tp,'city')}\n🎨 ဝါသနာ  : {sf(tp,'hobby')}\n💼 အလုပ်   : {sf(tp,'job')}{bio}\n"
            f"⚧ လိင်    : {sf(tp,'gender')}\n🔍 ရှာဖွေ  : {sf(tp,'looking_gender')} / {sf(tp,'looking_zodiac','Any')}")
def send_safe(uid, photo, caption, markup):
    if photo:
        try: bot.send_photo(uid, photo, caption=caption, reply_markup=markup, parse_mode="Markdown", timeout=30); return
        except: pass
    bot.send_message(uid, caption, reply_markup=markup, parse_mode="Markdown", timeout=30)
def share_prompt(uid):
    link=f"https://t.me/{BOT_USERNAME}?start=s"
    m=InlineKeyboardMarkup(); m.row(InlineKeyboardButton("📤 Share လုပ်မည်", url=f"https://t.me/share/url?url={link}&text=✨+Yay+Zat+Bot"))
    m.row(InlineKeyboardButton("🔍 ဆက်ရှာမည်", callback_data="continue_find"))
    bot.send_message(uid, "💖 *Match ဖြစ်သွားပါပြီ!* 🙏 Bot ကို မိတ်ဆွေများထံ Share ပေးပါ!", parse_mode="Markdown", reply_markup=m, timeout=30)

# ══════════════════════════════════════════
# 🔄 REGISTRATION (Condensed for Koyeb)
# ══════════════════════════════════════════
_reg, _step = {}, {}
def _is_start(msg):
    if msg.text and msg.text.strip().lower().startswith('/start'):
        uid=msg.chat.id; _reg.pop(uid,None); _step.pop(uid,None)
        try: bot.clear_step_handler_by_chat_id(uid); except: pass
        cmd_start(msg); return True
    return False
def _sk(msg): return msg.text and msg.text.strip()=='/skip'
def _sv(uid,k,msg): _reg.setdefault(uid,{})[k]=msg.text.strip()
def safe_next(msg, func, *a):
    try: bot.register_next_step_handler(msg, func, *a)
    except Exception as e: err_log('safe_next',e,msg.chat.id if hasattr(msg,'chat') else None)

def begin_reg(uid, msg, prefill=None):
    _reg[uid]=dict(prefill) if prefill else {}
    try: bot.clear_step_handler_by_chat_id(uid); except: pass
    bot.send_message(uid, "📋 *မှတ်ပုံတင်မည်*\n_(/skip ကျော်လို့ရ)_\n📛 *နာမည်*", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(), timeout=30)
    safe_next(msg, r_name)

# [Registration steps r_name, r_age, r_zodiac, r_city, r_hobby, r_job, r_bio, r_gender, r_lgender, r_lzodiac, r_photo]
# → ထပ်တူရေးရမည်။ နေရာချွေတာဖို့ ကျန်တဲ့အဆင့်များကို မူလကုဒ်အတိုင်း `safe_next` နဲ့ replace လုပ်ပါ။
# (ဥပမာ) r_name(m):
def r_name(m):
    if _is_start(m): return
    uid=m.chat.id
    if not _sk(m): _sv(uid,'name',m)
    bot.send_message(uid, "🎂 အသက်? (/skip)-", timeout=30); safe_next(m, r_age)
# ... အလားတူ ကျန်အဆင့်များ ...def r_photo(m):
    if _is_start(m): return
    uid=m.chat.id; is_new=db_get(uid) is None
    if _sk(m):
        old=db_get(uid)
        if old and old.get('photo'): _reg.setdefault(uid,{})['photo']=old['photo']
    elif m.content_type=='photo': _reg.setdefault(uid,{})['photo']=m.photo[-1].file_id
    else: bot.send_message(uid, "⚠️ ဓာတ်ပုံ ပေးပို့ပါ (သို့) /skip-", timeout=30); safe_next(m, r_photo); return
    data=_reg.pop(uid,{}); db_save(uid,data)
    bot.send_message(uid, f"✅ Profile {'တည်ဆောက်' if is_new else 'ပြင်ဆင်'} ပြီး! 🎉", reply_markup=kb(uid), timeout=30)
    if is_new: admin_msg(f"🆕 User `{uid}` — {sf(data,'name')}")

# ══════════════════════════════════════════
# 📡 HANDLERS & CALLBACKS
# ══════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(m):
    uid=m.chat.id; _reg.pop(uid,None)
    try: bot.clear_step_handler_by_chat_id(uid); except: pass
    if db_get(uid):
        bot.send_message(uid, "✨ *ကြိုဆိုပါတယ်!*", parse_mode="Markdown", reply_markup=kb(uid), timeout=30); return
    begin_reg(uid, m)

def find_match(m):
    uid=m.chat.id; me=db_get(uid)
    if not me: bot.send_message(uid, "/start နှိပ်ပြီး Profile အရင်တည်ဆောက်ပါ။", reply_markup=kb(uid), timeout=30); return
    seen=db_seen_get(uid); rptd=db_reported_by(uid); excl=seen|rptd|{uid}
    lg=(me.get('looking_gender') or '').strip(); lz=(me.get('looking_zodiac') or '').strip()
    pool=[u for u in db_all() if u['user_id'] not in excl and (lg in ('Both','Any','') or (u.get('gender') or '').strip()==lg)]
    if not pool:
        if seen: db_seen_clear(uid); bot.send_message(uid, "🔄 ပြန်စပါပြီ...", timeout=30); find_match(m); return
        bot.send_message(uid, "😔 ကိုက်ညီသူ မရှိသေးပါ။", reply_markup=kb(uid), timeout=30); return
    if lz and lz not in ('Any',''): pool=sorted(pool, key=lambda x: 0 if (x.get('zodiac') or '')==lz else 1)
    tgt=pool[0]; tid=tgt['user_id']; db_seen_add(uid,tid)
    note=f"\n_({lz} မတွေ့၍ အနီးစပ်ဆုံးပြပေးနေပါသည်)_" if lz and lz not in ('Any','') and (tgt.get('zodiac') or '')!=lz else ''
    mk=InlineKeyboardMarkup(); mk.row(InlineKeyboardButton("❤️",callback_data=f"like_{tid}"),InlineKeyboardButton("👎",callback_data=f"nope_{tid}"))
    send_safe(uid, tgt.get('photo'), fmt(tgt, f"✨ *ရှာတွေ့ပြီ!*{note}"), mk)

def show_profile(m):
    uid=m.chat.id; tp=db_get(uid)
    if not tp: bot.send_message(uid, "Profile မရှိသေးပါ။", reply_markup=kb(uid), timeout=30); return
    mk=InlineKeyboardMarkup()
    for f in ['name','age','zodiac','city','hobby','job','bio','photo','gender','looking_gender']: mk.row(InlineKeyboardButton(f"📝 {f}", callback_data=f"e_{f}"))
    mk.row(InlineKeyboardButton("🔄 ပြန်လုပ်", callback_data="do_reset"), InlineKeyboardButton("🗑 ဖျက်", callback_data="do_delete"))
    send_safe(uid, tp.get('photo'), fmt(tp), mk)

@bot.message_handler(func=lambda m: m.text in {"🔍 ရှာမည်","👤 ကိုယ့်ပရိုဖိုင်","ℹ️ အကူအညီ","🔄 ပြန်လုပ်","📊 Admin Stats","🛠 Admin Panel"})
def menu_router(m):
    uid=m.chat.id; _reg.pop(uid,None)
    try: bot.clear_step_handler_by_chat_id(uid); except: pass    try:
        {"🔍 ရှာမည်":find_match,"👤 ကိုယ့်ပရိုဖိုင်":show_profile}[m.text](m)
    except Exception as e: err_log(f'menu/{m.text}',e,uid)

EDIT_LABELS={'name':'နာမည်','age':'အသက်','zodiac':'ရာသီ','city':'မြို့','hobby':'ဝါသနာ','job':'အလုပ်','bio':'Bio','photo':'ဓာတ်ပုံ','gender':'လိင်','looking_gender':'ရှာဖွေမည့်လိင်'}
def save_edit(m, field):
    uid=m.chat.id
    if field=='photo' and m.content_type!='photo': bot.send_message(uid,"⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။", timeout=30); return
    val=m.photo[-1].file_id if field=='photo' else (m.text.strip() if m.text and m.text.strip()!='/skip' else None)
    if val: db_update(uid,field,val); bot.send_message(uid,"✅ ပြင်ဆင်ပြီး!", reply_markup=kb(uid), timeout=30)
    else: bot.send_message(uid,"✅ မပြောင်းဘဲ ထိန်းသိမ်းပြီး။", reply_markup=kb(uid), timeout=30)

@bot.callback_query_handler(func=lambda c: True)
def on_cb(call):
    uid=call.message.chat.id; d=call.data
    try:
        if d.startswith("like_"):
            tid=int(d[5:]); bot.delete_message(uid, call.message.message_id)
            try: bot.send_sticker(uid, HEART_STICKER, timeout=30); except: bot.send_message(uid, "❤️", timeout=30)
            me=db_get(uid) or {}; mk=InlineKeyboardMarkup()
            mk.row(InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{uid}"), InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline"))
            send_safe(tid, me.get('photo'), f"💌 *'{sf(me,'name','တစ်ယောက်')}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n{fmt(me)}", mk)
            bot.send_message(uid, "❤️ Like ပို့ပြီးပါပြီ!", reply_markup=kb(uid), timeout=30)
        elif d.startswith("nope_"): bot.delete_message(uid, call.message.message_id); find_match(call.message)
        elif d.startswith("accept_"):
            liker=int(d[7:]); bot.delete_message(uid, call.message.message_id)
            admin_msg(f"💖 Match!\n{uid} + {liker}")
            for me, p in [(uid,liker),(liker,uid)]:
                pd=db_get(p); bot.send_message(me, f"💖 *Match!* [နှိပ်ပါ](tg://user?id={p}) {sf(pd,'name','ဖူးစာ')} နဲ့ စကားပြောနိုင်ပါပြီ 🎉", parse_mode="Markdown", reply_markup=kb(me), timeout=30)
            try: share_prompt(uid); share_prompt(liker)
            except: pass
        elif d=="decline": bot.delete_message(uid, call.message.message_id); bot.send_message(uid,"❌ ငြင်းလိုက်ပါပြီ။", reply_markup=kb(uid), timeout=30)
        elif d=="continue_find": bot.delete_message(uid, call.message.message_id); find_match(call.message)
        elif d=="do_reset": bot.delete_message(uid, call.message.message_id); begin_reg(uid, call.message, prefill=db_get(uid))
        elif d=="do_delete": bot.delete_message(uid, call.message.message_id); db_delete(uid); _reg.pop(uid,None); bot.send_message(uid,"🗑 ဖျက်ပြီးပါပြီ။", reply_markup=ReplyKeyboardRemove(), timeout=30)
        elif d.startswith("e_"):
            f=d[2:]; bot.delete_message(uid, call.message.message_id); _reg.pop(uid,None)
            try: bot.clear_step_handler_by_chat_id(uid); except: pass
            if f=='photo': safe_next(bot.send_message(uid,"📸 ဓာတ်ပုံ ပေးပို့ပါ-", reply_markup=ReplyKeyboardRemove(), timeout=30), save_edit, 'photo')
            else: safe_next(bot.send_message(uid, f"📝 *{EDIT_LABELS.get(f,f)}* ရိုက်ထည့်ပါ-", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(), timeout=30), save_edit, f)
        bot.answer_callback_query(call.id, timeout=30)
    except Exception as e: err_log(f'cb/{d}',e,uid)

# ══════════════════════════════════════════
# 🌐 FLASK + KOYEB INTEGRATION
# ══════════════════════════════════════════
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def telegram_webhook():    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    return '', 403

@app.route('/')
def health():
    return jsonify({"status":"ok","bot":"YayZat","uptime":time.time()}), 200

def setup_webhook():
    print("🔗 Setting Webhook...")
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL, allowed_updates=bot.allowed_updates)
    print(f"✅ Webhook set: {WEBHOOK_URL}")

if __name__ == '__main__':
    setup_webhook()
    print(f"🚀 Yay Zat Bot running on Koyeb | Port: {PORT}")
    app.run(host='0.0.0.0', port=PORT)
