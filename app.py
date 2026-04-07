"""
Yay Zat Zodiac Bot — Full Production Version
Complete Fixed Version with All Features
"""
import telebot
import sqlite3
import threading
import traceback
import time
import os
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
# 💾  DATABASE
# ═══════════════════════════════════════════════════════════════
DB_FILE = 'yayzat.db'
_db_lock = threading.Lock()
_db = None

def get_db():
    global _db
    try:
        if _db is None:
            _db = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=10)
            _db.row_factory = sqlite3.Row
            _db.execute("PRAGMA journal_mode=WAL")
            _db.execute("PRAGMA busy_timeout=5000")
    except Exception as e:
        print(f"DB Connection Error: {e}")
    return _db
def execute_query(sql, params=(), commit=False):
    db = get_db()
    with _db_lock:
        try:
            cursor = db.execute(sql, params)
            if commit: 
                db.commit()
            return cursor
        except sqlite3.OperationalError as e:
            global _db
            _db = None
            db = get_db()
            try:
                cursor = db.execute(sql, params)
                if commit: 
                    db.commit()
                return cursor
            except:
                return None

def init_db():
    # Create Tables
    execute_query('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT, 
        age TEXT, 
        zodiac TEXT, 
        city TEXT, 
        hobby TEXT, 
        job TEXT, 
        song TEXT, 
        bio TEXT, 
        gender TEXT, 
        looking_gender TEXT, 
        looking_zodiac TEXT, 
        looking_type TEXT, 
        photo TEXT, 
        stars INTEGER DEFAULT 0, 
        created_at TEXT, 
        updated_at TEXT)''', commit=True)
    
    execute_query('''CREATE TABLE IF NOT EXISTS seen (
        user_id INTEGER, 
        seen_id INTEGER, 
        PRIMARY KEY (user_id, seen_id))''', commit=True)
    
    execute_query('''CREATE TABLE IF NOT EXISTS reports (
        reporter_id INTEGER, 
        reported_id INTEGER, 
        PRIMARY KEY (reporter_id, reported_id))''', commit=True)    
    execute_query('''CREATE TABLE IF NOT EXISTS referrals (
        referrer_id INTEGER, 
        referred_id INTEGER, 
        PRIMARY KEY (referrer_id, referred_id))''', commit=True)
    
    execute_query('''CREATE TABLE IF NOT EXISTS pending_match (
        user_id INTEGER PRIMARY KEY, 
        partner_id INTEGER, 
        created_at TEXT)''', commit=True)
    
    # Add missing columns if needed
    try:
        db = get_db()
        cursor = db.execute("PRAGMA table_info(users)")
        cols = [info[1] for info in cursor.fetchall()]
        
        missing_cols = {
            'bio': 'TEXT', 
            'song': 'TEXT', 
            'looking_type': 'TEXT', 
            'stars': 'INTEGER DEFAULT 0'
        }
        
        for col, typ in missing_cols.items():
            if col not in cols:
                try:
                    execute_query(f"ALTER TABLE users ADD COLUMN {col} {typ}", commit=True)
                    print(f"✅ Added column: {col}")
                except:
                    pass
    except Exception as e:
        print(f"DB Init Error: {e}")

init_db()

# ═══════════════════════════════════════════════════════════════
# 🔧  HELPERS
# ═══════════════════════════════════════════════════════════════
def safe_get(d, key, default='—'):
    if not d: 
        return default
    val = d.get(key)
    if not val: 
        return default
    return str(val).strip()

user_reg = {}

def save_user(uid, data):    try:
        old = get_user(uid)
        if old and 'photo' not in 
            data['photo'] = old.get('photo')
        
        cols = list(data.keys())
        vals = list(data.values())
        placeholders = ','.join(['?'] * len(cols))
        updates = ','.join([f"{c}=excluded.{c}" for c in cols])
        
        sql = f"""INSERT INTO users (user_id, {','.join(cols)}, updated_at) 
                  VALUES (?, {placeholders}, datetime('now'))
                  ON CONFLICT(user_id) DO UPDATE SET {updates}, updated_at=datetime('now')"""
        execute_query(sql, [uid] + vals, commit=True)
        return True
    except Exception as e:
        print(f"Save Error: {e}")
        return False

def get_user(uid):
    try:
        r = execute_query("SELECT * FROM users WHERE user_id=?", (uid,))
        row = r.fetchone() if r else None
        return dict(row) if row else None
    except: 
        return None

def delete_user(uid):
    try:
        execute_query("DELETE FROM users WHERE user_id=?", (uid,), commit=True)
        execute_query("DELETE FROM seen WHERE user_id=? OR seen_id=?", (uid, uid), commit=True)
        return True
    except: 
        return False

def get_ref_count(uid):
    try:
        r = execute_query("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (uid,))
        row = r.fetchone() if r else (0,)
        return row[0]
    except:
        return 0

def is_unlocked(uid):
    if uid == ADMIN_ID:
        return True
    return get_ref_count(uid) >= SHARE_NEEDED

# ═══════════════════════════════════════════════════════════════
# ⌨️  KEYBOARDS# ═══════════════════════════════════════════════════════════════
def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(KeyboardButton("🔍 ူးစာရှာမည်"), KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်"))
    m.row(KeyboardButton("ℹ️ အကူအညီ"), KeyboardButton("🔄 Profile ပြန်လုပ်"))
    return m

def share_kb(uid):
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("📤 Share လုပ်မည်", 
          url=f"https://t.me/share/url?url={link}&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
    m.row(InlineKeyboardButton("✅ စစ်ဆေးမည်", callback_data="check_unlock"))
    return m

# ═══════════════════════════════════════════════════════════════
# 🚀  START & REGISTRATION
# ═══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def cmd_start(m):
    try:
        uid = m.chat.id
        parts = m.text.split()
        
        # Handle referral
        if len(parts) > 1 and parts[1].startswith('ref_'):
            try:
                ref_uid = int(parts[1][4:])
                if ref_uid != uid and get_user(ref_uid) and not get_user(uid):
                    execute_query("INSERT OR IGNORE INTO referrals VALUES(?,?)", (ref_uid, uid), commit=True)
                    # Check if referrer should be unlocked
                    if is_unlocked(ref_uid):
                        process_pending_match(ref_uid)
            except Exception as e:
                print(f"Referral error: {e}")

        if get_user(uid):
            bot.send_message(uid, "✨ ကြိုဆိုပါတယ်! ခလုတ်များနှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇", 
                           reply_markup=main_kb())
        else:
            user_reg[uid] = {}
            bot.send_message(uid, 
                "✨ Yay Zat Zodiac မှ ကြိုဆိုပါတယ်! ✨\n\n"
                "ဖူးစာရှင်ရှာဖို့ မေးခွန်းလေးတွေ ဖြေပေးပါ 🙏\n"
                "_( /skip — ကျော်ချင်ရင် )_\n\n"
                "📛 နာမည် -", 
                parse_mode="Markdown", 
                reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(m, reg_name)
    except Exception as e:        print(f"Start error: {e}")

# ── REGISTRATION FLOW ──
def next_step(m, func, prompt, kb=None):
    try:
        bot.send_message(m.chat.id, prompt, reply_markup=kb, parse_mode="Markdown")
        bot.register_next_step_handler(m, func)
    except Exception as e:
        print(f"Next step error: {e}")
        bot.send_message(m.chat.id, "⚠️ Error - /start ထပ်နှိပ်ပါ")

def reg_name(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['name'] = m.text.strip()
        next_step(m, reg_age, "🎂 အသက်? `(/skip)`-")
    except: pass

def reg_age(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            if m.text.strip().isdigit(): 
                user_reg.setdefault(uid, {})['age'] = m.text.strip()
            else:
                bot.send_message(uid, "⚠️ ဂဏန်းသာ ထည့်ပါ (သို့) `/skip`-")
                bot.register_next_step_handler(m, reg_age)
                return
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.add(*ZODIACS)
        mk.add('/skip')
        next_step(m, reg_zodiac, "🔮 ရာသီခွင်?", mk)
    except: pass

def reg_zodiac(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['zodiac'] = m.text.strip()
        next_step(m, reg_city, "📍 မြို့ (ဥပမာ Mandalay)? `(/skip)`-")
    except: pass

def reg_city(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['city'] = m.text.strip()
        next_step(m, reg_hobby, "🎨 ဝါသနာ (ဥပမာ ခရီးသွား,ဂီတ)? `(/skip)`-")
    except: pass
def reg_hobby(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['hobby'] = m.text.strip()
        next_step(m, reg_job, "💼 အလုပ်? `(/skip)`-")
    except: pass

def reg_job(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['job'] = m.text.strip()
        next_step(m, reg_song, "🎵 အကြိုက်ဆုံး သီချင်း? `(/skip)`-")
    except: pass

def reg_song(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['song'] = m.text.strip()
        next_step(m, reg_bio, "📝 *မိမိအကြောင်း အတိုချုံး* `(/skip)`-\n_(ဥပမာ: ဆေးကျောင်းသား, ဂီတကိုနှစ်သက်သူ)_")
    except: pass

def reg_bio(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['bio'] = m.text.strip()
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.row('💑 ဖူးစာရှာနေသူ','🤝 မိတ်ဆွေဖွဲ့ချင်သူ')
        mk.add('/skip')
        next_step(m, reg_ltype, "🎯 ာရှာနေပါသလဲ?", mk)
    except: pass

def reg_ltype(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['looking_type'] = m.text.strip()
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.add('Male','Female','/skip')
        next_step(m, reg_gender, "⚧ သင့်လိင်?", mk)
    except: pass

def reg_gender(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip':             user_reg.setdefault(uid, {})['gender'] = m.text.strip()
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.add('Male','Female','Both','/skip')
        next_step(m, reg_lgender, "💑 ရှာဖွေနေတဲ့ လိင်?", mk)
    except: pass

def reg_lgender(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['looking_gender'] = m.text.strip()
        mk = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        mk.add(*ZODIACS)
        mk.add('Any','/skip')
        next_step(m, reg_lzodiac, "🔮 ရှာဖွေနေတဲ့ ရာသီ?", mk)
    except: pass

def reg_lzodiac(m):
    try:
        uid = m.chat.id
        if m.text and m.text.strip() != '/skip': 
            user_reg.setdefault(uid, {})['looking_zodiac'] = m.text.strip()
        next_step(m, reg_photo, "📸 Profile ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက `/skip`)_")
    except: pass

def reg_photo(m):
    try:
        uid = m.chat.id
        if m.content_type == 'photo':
            user_reg.setdefault(uid, {})['photo'] = m.photo[-1].file_id
        
        success = save_user(uid, user_reg.pop(uid, {}))
        if success:
            bot.send_message(uid, 
                "✅ Profile တည်ဆောက် ပြီးပါပြီ! 🎉\n\n"
                "ခလုတ်များ နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇", 
                parse_mode="Markdown", 
                reply_markup=main_kb())
        else:
            bot.send_message(uid, "⚠️ Error ဖြစ်သွားပါသည်။ /start ထပ်နှိပ်ပါ")
    except Exception as e:
        print(f"Photo error: {e}")
        bot.send_message(uid, "⚠️ Error - /start ထပ်နှိပ်ပါ")

# ═══════════════════════════════════════════════════════════════
# 🔍  MATCH & PROFILE
# ═══════════════════════════════════════════════════════════════
def fmt_profile(u):
    if not u: 
        return "Profile မရှိပါ"    return (
        f"📛 *နာမည်*: {safe_get(u, 'name')}\n"
        f"🎂 *အသက်*: {safe_get(u, 'age')} | 🔮 *ရာသီ*: {safe_get(u, 'zodiac')}\n"
        f"📍 *မြို့*: {safe_get(u, 'city')} | 💼 *အလုပ်*: {safe_get(u, 'job')}\n"
        f"🎵 *သီချင်း*: {safe_get(u, 'song')}\n"
        f"📝 *Bio*: {safe_get(u, 'bio')}\n"
        f"⚧ *လိင်*: {safe_get(u, 'gender')} | 💑 *ရှာဖွေ*: {safe_get(u, 'looking_gender')}"
    )

def process_pending_match(uid):
    """Deliver match link if unlocked"""
    try:
        r = execute_query("SELECT partner_id FROM pending_match WHERE user_id=?", (uid,))
        row = r.fetchone() if r else None
        if row:
            partner_id = row[0]
            execute_query("DELETE FROM pending_match WHERE user_id=?", (uid,), commit=True)
            partner = get_user(partner_id)
            if partner:
                bot.send_message(uid, 
                    f"💖 *Match ြစ်သွားပါပြီ!*\n\n"
                    f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner_id}) "
                    f"{safe_get(partner, 'name')} နဲ့ စကားပြောနိုင်ပါပြီ 🎉",
                    parse_mode="Markdown", 
                    reply_markup=main_kb())
    except Exception as e:
        print(f"Pending match error: {e}")

@bot.message_handler(func=lambda m: m.text == "👤 ကိုယ့်ပရိုဖိုင်")
def show_profile(m):
    try:
        uid = m.chat.id
        user = get_user(uid)
        if not user:
            bot.send_message(uid, "Profile မရှိသေးပါ။ /start ကိုနှိပ်ပါ။", 
                           reply_markup=main_kb())
            return
        
        refs = get_ref_count(uid)
        stars = safe_get(user, 'stars', '0')
        
        text = (
            fmt_profile(user) + 
            f"\n\n⭐ ကြယ်ပွင့်: {stars} ခု\n"
            f"🔗 ဖိတ်ကြားမှု: {refs}/{SHARE_NEEDED}"
            f"{' ✅ Unlock ပြီး' if is_unlocked(uid else f' 🔒 ({SHARE_NEEDED-refs} ကျန်)'}"
        )
        
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("🔄 ပြန်လုပ်မည်", callback_data="reset_profile"),               InlineKeyboardButton(" Invite Link", callback_data="my_invite"))
        
        if user.get('photo'):
            try:
                bot.send_photo(uid, user['photo'], caption=text, 
                             parse_mode="Markdown", reply_markup=kb)
            except:
                bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
        else:
            bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        print(f"Profile error: {e}")
        bot.send_message(m.chat.id, "⚠️ Error ဖြစ်သွားပါသည်")

@bot.message_handler(func=lambda m: m.text == "🔍 ဖူးစာရှာမည်")
def find_match(m):
    try:
        uid = m.chat.id
        user = get_user(uid)
        
        if not user:
            bot.send_message(uid, "/start ကိုနှိပ်ပြီး Profile ဦးတည်ဆောက်ပါ။", 
                           reply_markup=main_kb())
            return

        # Check unlock
        if not is_unlocked(uid):
            refs = get_ref_count(uid)
            bot.send_message(uid,
                f"🔒 *ဖူးစာရှာရန် Unlock လိုအပ်ပါသည်*\n\n"
                f"မိတ်ဆွေ *{SHARE_NEEDED}* ယောက် Bot ကိုသုံးစေပြီးမှ\n"
                f"ဖူးစာရှင်ရဲ့ Telegram link ကို ပေးမည်ဖြစ်ပါသည် 🙏\n\n"
                f"📊 ဖိတ်ပြီး Join ဖြစ်သူ: *{refs}/{SHARE_NEEDED}*\n"
                f"🎯 ကျန်: *{SHARE_NEEDED - refs}* ယောက်",
                parse_mode="Markdown",
                reply_markup=share_kb(uid))
            return

        # Get seen users
        r = execute_query("SELECT seen_id FROM seen WHERE user_id=?", (uid,))
        seen_ids = [row[0] for row in r] if r else []
        seen_ids.append(uid)  # Don't show self
        
        # Get reported users
        r = execute_query("SELECT reported_id FROM reports WHERE reporter_id=?", (uid,))
        reported_ids = [row[0] for row in r] if r else []
        
        excluded = list(set(seen_ids + reported_ids))
        
        # Build query        user_gender = safe_get(user, 'gender', '')
        looking_gender = safe_get(user, 'looking_gender', '')
        looking_zodiac = safe_get(user, 'looking_zodiac', '')
        
        filters = ["user_id NOT IN ({})".format(','.join(['?']*len(excluded))) if excluded else "1=1"]
        params = excluded[:]
        
        if looking_gender and looking_gender not in ('Both', 'Any'):
            filters.append("(gender=? OR gender IS NULL)")
            params.append(looking_gender)
        
        # Sort by zodiac match first, then stars
        if looking_zodiac and looking_zodiac not in ('Any', ''):
            order = f"CASE WHEN zodiac='{looking_zodiac}' THEN 0 ELSE 1 END, stars DESC, RANDOM()"
        else:
            order = "stars DESC, RANDOM()"
        
        query = f"SELECT * FROM users WHERE {' AND '.join(filters)} ORDER BY {order} LIMIT 1"
        r = execute_query(query, params)
        partner_row = r.fetchone() if r else None
        
        if not partner_row:
            # Clear seen and try again
            if seen_ids and len(seen_ids) > 1:
                execute_query("DELETE FROM seen WHERE user_id=?", (uid,), commit=True)
                bot.send_message(uid, "🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ...")
                find_match(m)  # Retry
                return
            else:
                bot.send_message(uid, 
                    "😔 သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ။\n"
                    "ဖော်ဆွေများကို ဖိတ်ကြားပါ 😊",
                    reply_markup=main_kb())
                return
        
        p_dict = dict(partner_row)
        execute_query("INSERT OR IGNORE INTO seen VALUES(?,?)", (uid, p_dict['user_id']), commit=True)
        
        # Check zodiac match note
        note = ""
        if looking_zodiac and looking_zodiac not in ('Any', ''):
            if safe_get(p_dict, 'zodiac', '') != looking_zodiac:
                note = f"\n_({looking_zodiac} မတွေ့သောကြောင့် အနီးစပ်ဆုံးပြပေးနေပါသည်)_"
        
        text = fmt_profile(p_dict) + note
        
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("❤️ Like", callback_data=f"like_{p_dict['user_id']}"),
               InlineKeyboardButton("⏭ Skip", callback_data="skip_match"),
               InlineKeyboardButton("🚩 Report", callback_data=f"report_{p_dict['user_id']}"))        
        if p_dict.get('photo'):
            try:
                bot.send_photo(uid, p_dict['photo'], caption=text, 
                             parse_mode="Markdown", reply_markup=kb)
            except Exception as e:
                print(f"Send photo error: {e}")
                bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
        else:
            bot.send_message(uid, text, parse_mode="Markdown", reply_markup=kb)
            
    except Exception as e:
        print(f"Find match error: {e}")
        bot.send_message(m.chat.id, "⚠️ Error ဖြစ်သွားပါသည်")

@bot.message_handler(func=lambda m: m.text == "🔄 Profile ပြန်လုပ်")
def cmd_reset(m):
    try:
        uid = m.chat.id
        kb = InlineKeyboardMarkup()
        kb.row(InlineKeyboardButton("✅ ဟုတ်ကဲ့", callback_data="reset_confirm"),
               InlineKeyboardButton("❌ မဟုတ်ပါ", callback_data="cancel"))
        bot.send_message(uid, 
            "⚠️ Profile ကို ပြန်လုပ်မှာ သေချာပါသလား?\n"
            "_(ဟောင်းသွားပါမည်)_",
            parse_mode="Markdown",
            reply_markup=kb)
    except: pass

@bot.message_handler(func=lambda m: m.text == "ℹ️ အကူအညီ")
def show_help(m):
    try:
        bot.send_message(m.chat.id,
            "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
            "🔍 *ဖူးစာရှာမည်* — ကိုက်ညီနိုင်မယ့်သူ ရှာပါ\n"
            "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
            "🔄 *Profile ပြန်လုပ်* — Profile ပြန်ဖြည့်ပါ\n\n"
            "*Unlock လုပ်နည်း*\n"
            f"မိတ်ဆွေ {SHARE_NEEDED} ဦးကို Bot ဆီဖိတ်ပါ\n"
            "သူတို့ Profile ဖြည့်ရင် Unlock ဖြစ်ပါပြီ\n\n"
            "⚠️ ပြဿနာများ Admin ထံ ဆက်သွယ်ပါ",
            parse_mode="Markdown", 
            reply_markup=main_kb())
    except: pass

# ═══════════════════════════════════════════════════════════════
# 🔘  CALLBACKS
# ═══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def on_cb(c):    try:
        uid = c.message.chat.id
        data = c.data
        
        if data == "check_unlock":
            refs = get_ref_count(uid)
            if refs >= SHARE_NEEDED:
                bot.answer_callback_query(c.id, "🎉 Unlock ြစ်ပါပြီ!", show_alert=True)
                process_pending_match(uid)
            else:
                bot.answer_callback_query(c.id, 
                    f"ကျန်သေးသည် {SHARE_NEEDED - refs} ဦး", 
                    show_alert=True)
        
        elif data == "my_invite":
            link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
            refs = get_ref_count(uid)
            kb = InlineKeyboardMarkup()
            kb.row(InlineKeyboardButton("📤 Share လုပ်မည်", 
                  url=f"https://t.me/share/url?url={link}&text=✨+Yay+Zat+Bot+မှာ+ဖူးစာရှာနိုင်ပါတယ်+💖"))
            bot.send_message(uid,
                f"🔗 *Invite Link*\n\n`{link}`\n\n"
                f"👥 Join ြစ်သူ: *{refs}/{SHARE_NEEDED}*\n"
                f"{'✅ Unlock ပြီး' if is_unlocked(uid else f'🔒 {SHARE_NEEDED-refs} ကျန်')}",
                parse_mode="Markdown",
                reply_markup=kb)
        
        elif data == "reset_profile":
            try:
                bot.delete_message(uid, c.message.message_id)
            except: pass
            user_reg[uid] = {}
            bot.send_message(uid, "🔄 Profile ပြန်လုပ်မည်\n\n📛 နာမည် -", 
                           reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(c.message, reg_name)
        
        elif data == "reset_confirm":
            try:
                bot.delete_message(uid, c.message.message_id)
            except: pass
            user_reg[uid] = {}
            bot.send_message(uid, "🔄 Profile ပြန်လုပ်မည်\n\n📛 နာမည် -", 
                           reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(c.message, reg_name)
        
        elif data == "cancel":
            try:
                bot.delete_message(uid, c.message.message_id)
            except: pass
            bot.answer_callback_query(c.id, "ပယ်ဖျက်ပြီး")        
        elif data == "skip_match":
            try:
                bot.delete_message(uid, c.message.message_id)
            except: pass
            # Find next match
            find_match(c.message)
        
        elif data.startswith("like_"):
            target_id = int(data.split("_")[1])
            try:
                bot.delete_message(uid, c.message.message_id)
            except: pass
            
            me = get_user(uid)
            my_name = safe_get(me, 'name', 'တစ်ယောက်')
            
            # Send notification to target
            accept_kb = InlineKeyboardMarkup()
            accept_kb.row(
                InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{uid}"),
                InlineKeyboardButton("❌ ြင်းမည်", callback_data="decline")
            )
            
            cap = (f"💌 *'{my_name}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n"
                   + fmt_profile(me))
            
            try:
                if me and me.get('photo'):
                    bot.send_photo(target_id, me['photo'], caption=cap,
                                 parse_mode="Markdown", reply_markup=accept_kb)
                else:
                    bot.send_message(target_id, cap, 
                                   parse_mode="Markdown", reply_markup=accept_kb)
                
                bot.send_message(uid,
                    "❤️ Like လုပ်လိုက်ပါပြီ!\n"
                    "တစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊",
                    reply_markup=main_kb())
                bot.answer_callback_query(c.id, "Like ပို့လိုက်ပါပြီ ❤️")
            except Exception as e:
                print(f"Like send error: {e}")
                bot.send_message(uid, 
                    "⚠️ တစ်ဖက်လူမှာ Bot Block ထားသဖြင့် ပေးပို့မရပါ။",
                    reply_markup=main_kb())
        
        elif data.startswith("accept_"):
            liker_id = int(data.split("_")[1])
            try:
                bot.delete_message(uid, c.message.message_id)            except: pass
            
            # Both users get match notification
            liker = get_user(liker_id)
            me = get_user(uid)
            
            def send_match(to_uid, partner_uid, partner_name):
                try:
                    if is_unlocked(to_uid):
                        bot.send_message(to_uid,
                            f"💖 *Match ြစ်သွားပါပြီ!*\n\n"
                            f"[ဒီမှာနှိပ်ပြီး](tg://user?id={partner_uid}) "
                            f"{partner_name} နဲ့ စကားပြောနိုင်ပါပြီ 🎉",
                            parse_mode="Markdown", 
                            reply_markup=main_kb())
                    else:
                        # Store pending match
                        execute_query(
                            "INSERT OR REPLACE INTO pending_match VALUES(?,?,datetime('now'))",
                            (to_uid, partner_uid), 
                            commit=True
                        )
                        refs = get_ref_count(to_uid)
                        bot.send_message(to_uid,
                            f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
                            f"🔒 Unlock မရသေးပါ။ မိတ်ဆွေ {SHARE_NEEDED-refs} ဦး ထပ်ဖိတ်ပါ\n"
                            f"Unlock ရရင် Link အလိုအလျောက် ရပါမယ်",
                            parse_mode="Markdown",
                            reply_markup=share_kb(to_uid))
                except Exception as e:
                    print(f"Send match error: {e}")
            
            send_match(uid, liker_id, safe_get(liker, 'name', 'ဖူးစာရှင်'))
            send_match(liker_id, uid, safe_get(me, 'name', 'ဖူးစာရှင်'))
            
            bot.answer_callback_query(c.id, "🎉 လက်ခံလိုက်ပါပြီ!")
        
        elif data == "decline":
            try:
                bot.delete_message(uid, c.message.message_id)
            except: pass
            bot.send_message(uid, "❌ ငြင်းဆန်လိုက်ပါပြီ။", 
                           reply_markup=main_kb())
            bot.answer_callback_query(c.id, "ငြင်းဆန်လိုက်ပါပြီ")
        
        elif data.startswith("report_"):
            target_id = int(data.split("_")[1])
            execute_query("INSERT OR IGNORE INTO reports VALUES(?,?)", (uid, target_id), commit=True)
            bot.answer_callback_query(c.id, "🚩 Report လုပ်ပြီး", show_alert=True)
            try:                bot.delete_message(uid, c.message.message_id)
            except: pass
            bot.send_message(uid, "✅ Report လုပ်ပြီးပါပြီ", 
                           reply_markup=main_kb())
        
    except Exception as e:
        print(f"Callback error: {e}")
        try:
            bot.answer_callback_query(c.id, "⚠️ Error")
        except: pass

# ═══════════════════════════════════════════════════════════════
# 🔁  POLLING
# ═══════════════════════════════════════════════════════════════
print("=" * 50)
print(f"✅ Yay Zat Bot Started")
print(f"🤖 Bot: @{BOT_USERNAME}")
print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

while True:
    try:
        bot.polling(none_stop=True, interval=1, timeout=30)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        break
    except Exception as e:
        print(f"❌ Polling Error: {e}")
        traceback.print_exc()
        time.sleep(5)
