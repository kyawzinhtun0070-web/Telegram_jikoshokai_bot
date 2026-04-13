"""
Yay Zat Zodiac Bot — Never-Stop Edition
"""
import telebot, threading, traceback, time, requests as _req, sys, os
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)

# ══════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════
TOKEN        = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID   = -1003923468164
CHANNEL_LINK = "https://t.me/yayzatofficial"
ADMIN_ID     = 6131831207
BOT_USERNAME = "yay_zat_zodiac_bot"  # @ မပါ
HEART_STICKER = ""               # heart sticker file_id (ဗလာဆိုရင် emoji သုံးမည်)

ZODIACS = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
           'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

bot = telebot.TeleBot(TOKEN, threaded=True)

# ══════════════════════════════════════════
# ERROR HANDLING — ဘယ် error မဆို Admin ထံပို့
# ══════════════════════════════════════════
def send_admin_raw(txt):
    """requests သုံးပြီး တိုက်ရိုက်ပို့ — bot object မလိုဘူး"""
    try:
        _req.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": ADMIN_ID, "text": txt,
                  "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=8)
    except: pass

def err_log(ctx, e, uid=None):
    tb = traceback.format_exc()
    # ပထမ/နောက်ဆုံး 300 char ပဲယူ
    tb_short = tb[:300] + "\n..." + tb[-200:] if len(tb) > 500 else tb
    msg = (f"🔴 *Error* `{ctx}`\n"
           f"👤 UID: `{uid}`\n"
           f"`{type(e).__name__}: {str(e)[:200]}`\n"
           f"```\n{tb_short}```\n"
           f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    send_admin_raw(msg)
    print(f"ERROR [{ctx}] uid={uid}: {e}\n{tb}")

# ══════════════════════════════════════════
# SAFE WRAPPER — handler တိုင်းကို ခြုံ
# ══════════════════════════════════════════
def safe_handler(fn):
    """Decorator: မည်သည့် exception မဆို ဖမ်းပြီး bot မရပ်ပါ"""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            # message/call ရဲ့ uid ကိုရအောင်
            uid = None
            try:
                if args:
                    obj = args[0]
                    if hasattr(obj, 'chat'): uid = obj.chat.id
                    elif hasattr(obj, 'message'): uid = obj.message.chat.id
            except: pass
            err_log(fn.__name__, e, uid)
            # user ကို gentle error message
            if uid:
                try:
                    bot.send_message(uid,
                        "⚠️ တစ်ခုခုမှားသွားပါသည်။\n"
                        "နောက်မှ ထပ်ကြိုးစားကြည့်ပါ။")
                except: pass
    return wrapper

# ══════════════════════════════════════════
# DATABASE — PostgreSQL (Neon)
# ══════════════════════════════════════════
import psycopg2
import psycopg2.pool
import psycopg2.extras

DATABASE_URL = "postgresql://neondb_owner:npg_UoRaO9AHuLS7@ep-young-sky-a1ayekiz-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

_pool = None
_lk   = threading.Lock()

def open_db():
    global _pool
    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1, maxconn=10,
        dsn=DATABASE_URL,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

open_db()

def _get_conn():
    global _pool
    for attempt in range(3):
        try:
            return _pool.getconn()
        except Exception:
            try: open_db()
            except: pass
            time.sleep(0.5)
    raise Exception("DB connection failed")

def _put_conn(conn):
    try: _pool.putconn(conn)
    except: pass

def xq(sql, p=()):
    """Write query — auto-commit"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, p)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except: pass
        raise
    finally:
        _put_conn(conn)

def xr(sql, p=()):
    """Read query — returns list of RealDictRow"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, p)
            return cur.fetchall()
    finally:
        _put_conn(conn)

def xr1(sql, p=()):
    """Read single row"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, p)
            return cur.fetchone()
    finally:
        _put_conn(conn)

def init_db():
    xq('''CREATE TABLE IF NOT EXISTS users (
        user_id        BIGINT PRIMARY KEY,
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
        created_at     TIMESTAMPTZ DEFAULT NOW()
    )''')
    xq('''CREATE TABLE IF NOT EXISTS seen (
        user_id BIGINT, seen_id BIGINT,
        PRIMARY KEY(user_id, seen_id)
    )''')
    xq('''CREATE TABLE IF NOT EXISTS reports (
        reporter_id BIGINT, reported_id BIGINT,
        PRIMARY KEY(reporter_id, reported_id)
    )''')

init_db()

UF = ['name','age','zodiac','city','hobby','job','bio',
      'gender','looking_gender','looking_zodiac','photo']

_DB_ERROR = object()   # sentinel — distinct from None

def db_get(uid):
    """Return user dict or None. Returns _DB_ERROR on DB failure."""
    try:
        row = xr1('SELECT * FROM users WHERE user_id=%s', (uid,))
        return dict(row) if row else None
    except Exception as e:
        err_log('db_get', e, uid)
        return _DB_ERROR

def db_save(uid, data):
    try:
        old = db_get(uid)
        if old and old is not _DB_ERROR:
            if not data.get('photo') and old.get('photo'):
                data['photo'] = old['photo']
        cols = ','.join(UF)
        ph   = ','.join(['%s']*len(UF))
        vals = [data.get(f) for f in UF]
        upd  = ','.join([f"{f}=EXCLUDED.{f}" for f in UF])
        xq(f"INSERT INTO users (user_id,{cols}) VALUES(%s,{ph}) "
           f"ON CONFLICT (user_id) DO UPDATE SET {upd}",
           [uid]+vals)
    except Exception as e:
        err_log('db_save', e, uid)

def db_update(uid, field, val):
    try:
        if field in set(UF):
            xq(f"UPDATE users SET {field}=%s WHERE user_id=%s", (val, uid))
    except Exception as e:
        err_log('db_update', e, uid)

def db_delete(uid):
    try:
        xq('DELETE FROM users WHERE user_id=%s', (uid,))
        xq('DELETE FROM seen WHERE user_id=%s OR seen_id=%s', (uid, uid))
    except Exception as e:
        err_log('db_delete', e, uid)

def db_all():
    try: return [dict(r) for r in (xr('SELECT * FROM users') or [])]
    except: return []

def db_ids():
    try: return [r['user_id'] for r in (xr('SELECT user_id FROM users') or [])]
    except: return []

def db_count():
    try:
        row = xr1('SELECT COUNT(*) AS c FROM users')
        return row['c'] if row else 0
    except: return 0

def db_seen_add(u, s):
    try: xq('INSERT INTO seen VALUES(%s,%s) ON CONFLICT DO NOTHING', (u, s))
    except: pass

def db_seen_get(uid):
    try: return {r['seen_id'] for r in (xr('SELECT seen_id FROM seen WHERE user_id=%s',(uid,)) or [])}
    except: return set()

def db_seen_clear(uid):
    try: xq('DELETE FROM seen WHERE user_id=%s', (uid,))
    except: pass

def db_report(a, b):
    try: xq('INSERT INTO reports VALUES(%s,%s) ON CONFLICT DO NOTHING', (a, b))
    except: pass

def db_reported_by(uid):
    try: return {r['reported_id'] for r in (xr('SELECT reported_id FROM reports WHERE reporter_id=%s',(uid,)) or [])}
    except: return set()

def db_stats():
    try:
        def n(q):
            row = xr1(q)
            return list(row.values())[0] if row else 0
        return {
            'total' : n('SELECT COUNT(*) FROM users'),
            'male'  : n("SELECT COUNT(*) FROM users WHERE gender='Male'"),
            'female': n("SELECT COUNT(*) FROM users WHERE gender='Female'"),
            'photo' : n('SELECT COUNT(*) FROM users WHERE photo IS NOT NULL'),
        }
    except: return {'total':0,'male':0,'female':0,'photo':0}

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
    m.row(KeyboardButton("📊 Stats"), KeyboardButton("🛠 Admin"))
    return m

def kb(uid): return admin_kb() if uid == ADMIN_ID else main_kb()

# ══════════════════════════════════════════
# UTILS
# ══════════════════════════════════════════
def sf(d, k, fb='—'):
    try:
        v = (d or {}).get(k)
        if isinstance(v, str): v = v.strip()
        return v if v else fb
    except: return fb

def check_ch(uid):
    try:
        status = bot.get_chat_member(CHANNEL_ID, uid).status
        return status in ('member', 'creator', 'administrator')
    except telebot.apihelper.ApiTelegramException as e:
        # "user not found" = not a member
        if "user not found" in str(e).lower():
            return False
        # other API errors (bot not admin, etc) = don't block user
        return True
    except Exception:
        # Network error etc = don't block user
        return True

def admin_msg(txt):
    try: bot.send_message(ADMIN_ID, txt, parse_mode="Markdown")
    except: pass

def fmt(tp, title='👤 *ပရိုဖိုင်*'):
    try:
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
    except: return f"{title}\n\n(Profile ဖတ်မရပါ)"

def send_safe(uid, photo, caption, markup):
    """Photo ပေးပို့မရရင် text fallback"""
    try:
        if photo:
            try:
                bot.send_photo(uid, photo, caption=caption,
                               reply_markup=markup, parse_mode="Markdown")
                return
            except telebot.apihelper.ApiTelegramException as e:
                if "wrong file identifier" in str(e).lower() or \
                   "file_id" in str(e).lower():
                    pass  # photo expired/invalid → fallback to text
                else:
                    raise
        bot.send_message(uid, caption, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        err_log('send_safe', e, uid)
        try: bot.send_message(uid, caption, reply_markup=markup, parse_mode="Markdown")
        except: pass

def share_prompt(uid):
    try:
        link = f"https://t.me/{BOT_USERNAME}"
        m = InlineKeyboardMarkup()
        m.row(InlineKeyboardButton(
            "📤 မိတ်ဆွေများကို Share လုပ်မည်",
            url=f"https://t.me/share/url?url={link}"
                f"&text=✨+Yay+Zat+Zodiac+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
        bot.send_message(uid,
            "🙏 Bot ကို မိတ်ဆွေများကို Share ပေးပါ!\n"
            "_(မဖြစ်မနေ မဟုတ်ပါ — ကျေးဇူးတင်ပါသည် 😊)_",
            parse_mode="Markdown", reply_markup=m)
    except Exception as e:
        err_log('share_prompt', e, uid)

# ══════════════════════════════════════════
# REGISTRATION STATE
# ══════════════════════════════════════════
_reg = {}

def _is_start(msg):
    """Step handler တွင် /start ရိုက်ရင် redirect"""
    try:
        if msg.text and msg.text.strip().lower().startswith('/start'):
            uid = msg.chat.id
            _reg.pop(uid, None)
            try: bot.clear_step_handler_by_chat_id(uid)
            except: pass
            cmd_start(msg)
            return True
    except: pass
    return False

def _sk(msg):
    try: return bool(msg.text and msg.text.strip() == '/skip')
    except: return False

def _sv(uid, k, msg):
    """Save value to registration dict — always ensure uid key exists"""
    try:
        _reg.setdefault(uid, {})
        if msg.text and msg.text.strip() and msg.text.strip() != '/skip':
            _reg[uid][k] = msg.text.strip()
    except: pass

def _check_reg(uid, msg):
    """Ensure _reg[uid] exists — if not, restart registration"""
    if uid not in _reg:
        bot.send_message(uid,
            "⚠️ Registration မှတ်ဉာဏ် ပျောက်သွားပါသည်။\n"
            "/start နှိပ်ပြီး ပြန်စပါ။")
        return False
    return True

def begin_reg(uid, msg, prefill=None):
    try:
        _reg[uid] = dict(prefill) if prefill else {}
        try: bot.clear_step_handler_by_chat_id(uid)
        except: pass
        bot.send_message(uid,
            "📋 *မှတ်ပုံတင်မည်*\n\n"
            "_(/skip — ကျော်ချင်ရင်)_\n\n"
            "📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-",
            parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, r_name)
    except Exception as e:
        err_log('begin_reg', e, uid)

# ── Registration steps (all wrapped) ─────
def r_name(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'name', m)
        bot.send_message(uid, "🎂 အသက်? (/skip)-")
        bot.register_next_step_handler(m, r_age)
    except Exception as e:
        err_log('r_name', e, getattr(m,'chat',None) and m.chat.id)

def r_age(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
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
    except Exception as e:
        err_log('r_age', e, getattr(m,'chat',None) and m.chat.id)

def r_zodiac(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'zodiac', m)
        bot.send_message(uid, "📍 မြို့? (/skip)-", reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(m, r_city)
    except Exception as e:
        err_log('r_zodiac', e, getattr(m,'chat',None) and m.chat.id)

def r_city(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'city', m)
        bot.send_message(uid, "🎨 ဝါသနာ? (/skip)-")
        bot.register_next_step_handler(m, r_hobby)
    except Exception as e:
        err_log('r_city', e, getattr(m,'chat',None) and m.chat.id)

def r_hobby(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'hobby', m)
        bot.send_message(uid, "💼 အလုပ်? (/skip)-")
        bot.register_next_step_handler(m, r_job)
    except Exception as e:
        err_log('r_hobby', e, getattr(m,'chat',None) and m.chat.id)

def r_job(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'job', m)
        bot.send_message(uid,
            "📝 *မိမိအကြောင်း အတိုချုံး* (/skip)-\n"
            "_(ဥပမာ - ဆေးကျောင်းသား၊ ဂီတကိုနှစ်သက်သူ)_",
            parse_mode="Markdown")
        bot.register_next_step_handler(m, r_bio)
    except Exception as e:
        err_log('r_job', e, getattr(m,'chat',None) and m.chat.id)

def r_bio(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'bio', m)
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.add('Male','Female','/skip')
        bot.send_message(uid, "⚧ သင့်လိင်?", reply_markup=mk)
        bot.register_next_step_handler(m, r_gender)
    except Exception as e:
        err_log('r_bio', e, getattr(m,'chat',None) and m.chat.id)

def r_gender(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'gender', m)
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.add('Male','Female','Both','/skip')
        bot.send_message(uid, "💑 ရှာဖွေနေတဲ့ လိင်?", reply_markup=mk)
        bot.register_next_step_handler(m, r_lgender)
    except Exception as e:
        err_log('r_gender', e, getattr(m,'chat',None) and m.chat.id)

def r_lgender(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'looking_gender', m)
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        for z in ZODIACS: mk.add(z)
        mk.add('Any','/skip')
        bot.send_message(uid, "🔮 ရှာဖွေနေတဲ့ ရာသီ?", reply_markup=mk)
        bot.register_next_step_handler(m, r_lzodiac)
    except Exception as e:
        err_log('r_lgender', e, getattr(m,'chat',None) and m.chat.id)

def r_lzodiac(m):
    try:
        if _is_start(m): return
        uid = m.chat.id
        _reg.setdefault(uid, {})
        if not _sk(m): _sv(uid, 'looking_zodiac', m)
        bot.send_message(uid,
            "📸 ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက /skip)_",
            parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(m, r_photo)
    except Exception as e:
        err_log('r_lzodiac', e, getattr(m,'chat',None) and m.chat.id)

def r_photo(m):
    try:
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
    except Exception as e:
        err_log('r_photo', e, getattr(m,'chat',None) and m.chat.id)

# ══════════════════════════════════════════
# /start
# ══════════════════════════════════════════
@bot.message_handler(commands=['start'])
@safe_handler
def cmd_start(message):
    uid = message.chat.id
    _reg.pop(uid, None)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass

    user = db_get(uid)

    # DB error — don't treat as new user, show retry message
    if user is _DB_ERROR:
        bot.send_message(uid,
            "⚠️ ခဏစောင့်ပြီး ထပ်ကြိုးစားကြည့်ပါ။",
            reply_markup=kb(uid))
        return

    if user:
        mk = InlineKeyboardMarkup()
        mk.row(InlineKeyboardButton("📢 Channel Join မည်", url=CHANNEL_LINK))
        bot.send_message(uid,
            "✨ *ကြိုဆိုပါတယ်!* ✨\n\n"
            "👇 ခလုတ်များနှိပ်ပြီး သုံးနိုင်ပါပြီ",
            parse_mode="Markdown", reply_markup=kb(uid))
        bot.send_message(uid,
            "📢 ကျွန်ုပ်တို့ Channel ကိုလည်း Join ပေးပါ 🙏",
            reply_markup=mk)
        return

    # Genuinely new user
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
@safe_handler
def find_match(message):
    uid = message.chat.id
    me  = db_get(uid)
    if me is _DB_ERROR:
        bot.send_message(uid,"⚠️ ခဏစောင့်ပြီး ထပ်ကြိုးစားကြည့်ပါ။",reply_markup=kb(uid)); return
    if not me:
        bot.send_message(uid, "/start နှိပ်ပြီး Profile ဦးတည်ဆောက်ပါ။",
                         reply_markup=kb(uid)); return

    if not check_ch(uid):
        mk = InlineKeyboardMarkup()
        mk.add(InlineKeyboardButton("📢 Channel Join မည်", url=CHANNEL_LINK))
        bot.send_message(uid,
            "⚠️ ဖူးစာရှာရန် ကျွန်ုပ်တို့ Channel ကို အရင် Join ပေးပါ 🙏",
            reply_markup=mk)
        return

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
            "😔 သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ။\n"
            "ဖော်ဆွေများကို ဖိတ်ကြားပါ 😊",
            reply_markup=kb(uid)); return

    # zodiac preferred first
    if lz and lz not in ('Any',''):
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
@safe_handler
def show_profile(message):
    uid = message.chat.id
    tp  = db_get(uid)
    if tp is _DB_ERROR:
        bot.send_message(uid,"⚠️ ခဏစောင့်ပြီး ထပ်ကြိုးစားကြည့်ပါ။",reply_markup=kb(uid)); return
    if not tp:
        bot.send_message(uid, "Profile မရှိသေးပါ။ /start နှိပ်ပါ။",
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
# HELP / STATS / ADMIN
# ══════════════════════════════════════════
@safe_handler
def show_help(message):
    bot.send_message(message.chat.id,
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ရှာမည်* — ကိုက်ညီမယ့်သူ ရှာပါ\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
        "🔄 *ပြန်လုပ်* — Profile ပြန်ဖြည့်ပါ\n\n"
        "ပြဿနာများ Admin ထံ ဆက်သွယ်ပါ။",
        parse_mode="Markdown", reply_markup=kb(message.chat.id))

@safe_handler
def show_stats(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်။"); return
    s = db_stats()
    bot.send_message(ADMIN_ID,
        f"📊 *Admin Stats*\n\n"
        f"👥 စုစုပေါင်း : *{s['total']}* ယောက်\n"
        f"♂️ ကျား      : {s['male']}\n"
        f"♀️ မ         : {s['female']}\n"
        f"📸 ဓာတ်ပုံပါ : {s['photo']}\n"
        f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        parse_mode="Markdown", reply_markup=admin_kb())

@safe_handler
def show_admin(message):
    if message.chat.id != ADMIN_ID: return
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📊 Stats",    callback_data="adm_stats"),
          InlineKeyboardButton("👥 Users",     callback_data="adm_users"))
    m.row(InlineKeyboardButton("📢 Broadcast", callback_data="adm_bcast"),
          InlineKeyboardButton("🗑 User ဖျက်",callback_data="adm_del"))
    bot.send_message(ADMIN_ID, "🛠 *Admin Panel*", parse_mode="Markdown", reply_markup=m)

def _bcast(m):
    try:
        if m.text and m.text.startswith('/'): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး။"); return
        ok=fail=0
        for uid in db_ids():
            try: bot.send_message(uid,f"📢 *Yay Zat*\n\n{m.text}",parse_mode="Markdown"); ok+=1
            except: fail+=1
        bot.send_message(ADMIN_ID,f"✅ {ok} ရောက် / ❌ {fail} မရောက်")
    except Exception as e: err_log('_bcast',e)

def _del_u(m):
    try:
        if m.text and m.text.startswith('/'): bot.send_message(ADMIN_ID,"ပယ်ဖျက်ပြီး။"); return
        uid=int(m.text.strip())
        if db_get(uid): db_delete(uid); bot.send_message(ADMIN_ID,f"✅ `{uid}` ဖျက်ပြီး",parse_mode="Markdown")
        else: bot.send_message(ADMIN_ID,"⚠️ မတွေ့ပါ။")
    except Exception as e: bot.send_message(ADMIN_ID,f"⚠️ {e}")

def save_edit(message, field):
    try:
        if _is_start(message): return
        uid = message.chat.id
        if field == 'photo':
            if message.content_type != 'photo':
                bot.send_message(uid,"⚠️ ဓာတ်ပုံ ပေးပို့ပါ။"); return
            db_update(uid,'photo',message.photo[-1].file_id)
        else:
            if not message.text or message.text.strip() == '/skip':
                bot.send_message(uid,"✅ မပြောင်းဘဲ ထိန်းသိမ်းပြီး။",reply_markup=kb(uid)); return
            db_update(uid,field,message.text.strip())
        bot.send_message(uid,"✅ ပြင်ဆင်မှု အောင်မြင်!",reply_markup=kb(uid))
    except Exception as e:
        err_log(f'save_edit/{field}',e,message.chat.id)
        try: bot.send_message(message.chat.id,"⚠️ မှားသွားပါသည်။")
        except: pass

# ══════════════════════════════════════════
# MENU ROUTER
# ══════════════════════════════════════════
MENU = {
    "🔍 ရှာမည်"           : find_match,
    "👤 ကိုယ့်ပရိုဖိုင်"  : show_profile,
    "ℹ️ အကူအညီ"           : show_help,
    "🔄 ပြန်လုပ်"          : lambda m: ask_reset(m),
    "📊 Stats"             : show_stats,
    "🛠 Admin"             : show_admin,
}

def ask_reset(message):
    try:
        m = InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့",  callback_data="reset_go"),
              InlineKeyboardButton("❌ မလုပ်တော့", callback_data="reset_no"))
        bot.send_message(message.chat.id,
            "⚠️ Profile ကို ပြန်လုပ်မှာ သေချာပါသလား?", reply_markup=m)
    except Exception as e:
        err_log('ask_reset',e,message.chat.id)

@bot.message_handler(func=lambda m: m.text in MENU)
@safe_handler
def menu_router(message):
    uid = message.chat.id
    _reg.pop(uid, None)
    try: bot.clear_step_handler_by_chat_id(uid)
    except: pass
    MENU[message.text](message)

@bot.message_handler(commands=['reset'])
@safe_handler
def cmd_reset(m): ask_reset(m)

@bot.message_handler(commands=['myprofile'])
@safe_handler
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
@safe_handler
def on_cb(call):
    uid = call.message.chat.id
    d   = call.data

    # ── Like ──────────────────────────────────────────────────
    if d.startswith("like_"):
        tid = int(d[5:])
        try: bot.delete_message(uid, call.message.message_id)
        except: pass

        # Heart sticker/emoji
        if HEART_STICKER:
            try: bot.send_sticker(uid, HEART_STICKER)
            except: bot.send_message(uid, "❤️")
        else:
            bot.send_message(uid, "❤️")

        me  = db_get(uid)
        if me is _DB_ERROR or not me: me = {}
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
            bot.send_message(uid,
                "⚠️ တစ်ဖက်လူမှာ Bot Block ထားသဖြင့် မပို့နိုင်ပါ။",
                reply_markup=kb(uid))

    # ── Nope ──────────────────────────────────────────────────
    elif d.startswith("nope_"):
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        find_match(call.message)

    # ── Accept ────────────────────────────────────────────────
    elif d.startswith("accept_"):
        liker = int(d[7:])
        # profile message ကို မဖျက်ဘဲ ထားပါ — user မြင်နေနိုင်အောင်

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
                    parse_mode="Markdown", reply_markup=kb(me))
            except Exception as e:
                err_log(f'accept/send/{me}',e,me)
        # share prompt
        try: share_prompt(uid)
        except: pass
        try: share_prompt(liker)
        except: pass

    # ── Decline ───────────────────────────────────────────────
    elif d == "decline":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        bot.send_message(uid,"❌ ငြင်းဆန်လိုက်ပါပြီ။",reply_markup=kb(uid))

    # ── Continue find ─────────────────────────────────────────
    elif d == "continue_find":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        find_match(call.message)

    # ── Reset ─────────────────────────────────────────────────
    elif d == "reset_go":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        old = db_get(uid)
        begin_reg(uid, call.message, prefill=old)

    elif d == "reset_no":
        bot.answer_callback_query(call.id,"မလုပ်တော့ပါ 👍")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass

    # ── do_reset button in profile ────────────────────────────
    elif d == "do_reset":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        ask_reset(call.message)

    # ── Delete ────────────────────────────────────────────────
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
            "🗑 Profile ဖျက်ပြီးပါပြီ။\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်။",
            reply_markup=ReplyKeyboardRemove())

    elif d == "del_no":
        bot.answer_callback_query(call.id,"မဖျက်တော့ပါ 👍")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass

    # ── Edit fields ───────────────────────────────────────────
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

    # ── Admin callbacks ───────────────────────────────────────
    elif d == "adm_stats" and uid == ADMIN_ID:
        show_stats(call.message)

    elif d == "adm_users" and uid == ADMIN_ID:
        rows = db_all()[:30]
        lines = [f"{i}. {sf(u,'name')} `{u['user_id']}`"
                 for i,u in enumerate(rows,1)]
        bot.send_message(ADMIN_ID,
            "👥 *User List*\n\n"+("\n".join(lines) or "မရှိသေး"),
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
# ══════════════════════════════════════════
# NEVER-STOP POLLING
# ══════════════════════════════════════════
print(f"✅ Yay Zat Bot [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
admin_msg(f"🟢 *Bot Online*\n⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ── Neon keep-alive — sleep မချအောင် 4 min တစ်ကြိမ် ping ──
def _db_keepalive():
    while True:
        time.sleep(240)   # 4 minutes
        try: xr1('SELECT 1')
        except: pass

threading.Thread(target=_db_keepalive, daemon=True).start()

import requests.exceptions

while True:
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling...")
        bot.polling(
            none_stop            = True,
            interval             = 0,
            timeout              = 30,        # HTTP timeout
            long_polling_timeout = 20,        # Telegram long poll wait
        )
    except KeyboardInterrupt:
        print("Stopped.")
        sys.exit(0)

    except (requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout) as e:
        # ── ဒါပုံမှန် network hiccup — Admin မပို့ဘဲ 5s နောက် ဆက်သည် ──
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Network error (normal): {e}")
        try: bot.stop_polling()
        except: pass
        time.sleep(5)
        try: open_db()   # reconnect pool
        except: pass

    except Exception as e:
        # ── တကယ့် unexpected error သာ Admin ထံပို့သည် ──
        err_str = str(e)
        # 409 conflict = instance တစ်ခုထက်မို run နေတာ
        if "409" in err_str:
            send_admin_raw(
                "⚠️ *Error 409 — Bot instance တစ်ခုထက်မို run နေသည်*\n"
                "Koyeb မှာ instance တစ်ခုပဲ run နေအောင် စစ်ဆေးပါ\n"
                f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            time.sleep(30)  # 409 ဆိုရင် ကြာကြာစောင့်
        else:
            msg = (f"🔴 *Polling Error*\n"
                   f"`{type(e).__name__}: {err_str[:200]}`\n"
                   f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print(msg)
            send_admin_raw(msg)
            time.sleep(5)

        try: bot.stop_polling()
        except: pass
        try: open_db()
        except: pass
