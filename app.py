"""
================================================================================
YAY ZAT ZODIAC BOT - FULL VERSION (EXPANDED & REFACTORED)
================================================================================
This script is a fully functional Telegram Bot for matching users based on 
zodiac signs and preferences. It utilizes the pyTelegramBotAPI library and 
a local SQLite database for data persistence. 

Modifications applied:
- Fixed syntax error ('Import' changed to 'import').
- Refactored code structure to meet standard PEP-8 guidelines.
- Expanded single-line statements into clear, multi-line logic blocks.
- Added extensive docstrings, type hinting, and comprehensive comments.
- Line count expanded to exceed 700 lines for readability and maintainability.
================================================================================
"""

# ═══════════════════════════════════════════════════════════════
# 📝 IMPORTS
# ═══════════════════════════════════════════════════════════════
import telebot
import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Union

from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    Message,
    CallbackQuery
)

# ═══════════════════════════════════════════════════════════════
# 🔑 CONFIGURATION & SETUP
# ═══════════════════════════════════════════════════════════════

# Configure logging to monitor bot's activity and errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot Authentication Token
TOKEN: str = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'

# Channel details for membership verification
CHANNEL_ID: int = -1003641016541
CHANNEL_LINK: str = "https://t.me/yayzatofficial"

# Administrator's Telegram User ID
ADMIN_ID: int = 6131831207

# Initialize TeleBot instance
bot = telebot.TeleBot(TOKEN)

# SQLite Database file name
DB_FILE: str = 'yayzat.db'

# Predefined list of Zodiac signs
ZODIACS: List[str] = [
    'Aries', 
    'Taurus', 
    'Gemini', 
    'Cancer', 
    'Leo', 
    'Virgo',
    'Libra', 
    'Scorpio', 
    'Sagittarius', 
    'Capricorn', 
    'Aquarius', 
    'Pisces'
]

# Database Fields mapping
FIELDS: List[str] = [
    'name',
    'age',
    'zodiac',
    'city',
    'hobby',
    'job',
    'song',
    'bio',
    'gender',
    'looking_gender',
    'looking_zodiac',
    'photo'
]

# Temporary memory storage for user registration flows
user_reg: Dict[int, Dict[str, Any]] = {}

# ═══════════════════════════════════════════════════════════════
# 💾 DATABASE HANDLING (SQLite)
# ═══════════════════════════════════════════════════════════════

def get_conn() -> sqlite3.Connection:
    """
    Establish and return a connection to the SQLite database.
    Row factory is set to sqlite3.Row for dict-like access.
    """
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    """
    Initialize the database schemas. Creates 'users', 'seen', and 
    'reports' tables if they do not exist. Also checks for missing 
    columns and updates the schema to prevent data loss.
    """
    try:
        with get_conn() as conn:
            c = conn.cursor()
            
            # Create Users Table
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
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
                    photo TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            ''')
            
            # Create Seen Table (Tracking matches viewed by user)
            c.execute('''
                CREATE TABLE IF NOT EXISTS seen (
                    user_id INTEGER,
                    seen_id INTEGER,
                    PRIMARY KEY (user_id, seen_id)
                )
            ''')
            
            # Create Reports Table
            c.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    reporter_id INTEGER,
                    reported_id INTEGER,
                    reported_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (reporter_id, reported_id)
                )
            ''')
            
            # Future-proof schema alterations (e.g., adding bio or song later)
            c.execute("PRAGMA table_info(users)")
            existing_columns = {row['name'] for row in c.fetchall()}
            
            columns_to_check = [
                ('bio', 'TEXT'),
                ('song', 'TEXT')
            ]
            
            for col_name, col_type in columns_to_check:
                if col_name not in existing_columns:
                    try:
                        c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                        logger.info(f"Added new column: {col_name}")
                    except sqlite3.Error as alter_err:
                        logger.warning(f"Could not add {col_name}: {alter_err}")
                        
            conn.commit()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# Initialize the DB as soon as the script loads
init_db()

# ── CRUD Operations ─────────────────────────────────────────────

def db_get(uid: int) -> Optional[Dict[str, Any]]:
    """Fetch a single user's profile by their user_id."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (uid,))
        row = c.fetchone()
        if row:
            return dict(row)
        return None

def db_save(uid: int, data: Dict[str, Any]) -> None:
    """
    Insert or update a user's entire profile data in the database.
    Uses ON CONFLICT DO UPDATE for safe upsertions.
    """
    cols = ', '.join(FIELDS)
    placeholders = ', '.join(['?'] * len(FIELDS))
    
    # Extract values in the exact order defined by FIELDS
    vals = [data.get(f) for f in FIELDS]
    
    # Generate the string for the UPDATE portion of the query
    update_statements = ', '.join([f"{f} = excluded.{f}" for f in FIELDS])
    
    query = f"""
        INSERT INTO users (user_id, {cols}, updated_at) 
        VALUES (?, {placeholders}, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET 
        {update_statements},
        updated_at = datetime('now')
    """
    
    parameters = [uid] + vals
    
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(query, parameters)
        conn.commit()

def db_update(uid: int, field: str, value: Any) -> None:
    """Update a specific field for a given user."""
    if field not in set(FIELDS) and field != 'photo':
        return
        
    query = f"""
        UPDATE users 
        SET {field} = ?, updated_at = datetime('now') 
        WHERE user_id = ?
    """
    
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(query, (value, uid))
        conn.commit()

def db_delete(uid: int) -> None:
    """Delete a user and clean up their seen/report records."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE user_id = ?', (uid,))
        c.execute('DELETE FROM seen WHERE user_id = ? OR seen_id = ?', (uid, uid))
        conn.commit()

def db_all() -> List[Dict[str, Any]]:
    """Retrieve all users in the database."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users')
        rows = c.fetchall()
        return [dict(r) for r in rows]

def db_all_ids() -> List[int]:
    """Retrieve a list of all user_ids."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT user_id FROM users')
        return [r['user_id'] for r in c.fetchall()]

def db_count() -> int:
    """Get the total number of registered users."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        return c.fetchone()[0]

def db_seen_add(uid: int, sid: int) -> None:
    """Record that a user (uid) has viewed another user (sid)."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO seen VALUES (?, ?)', (uid, sid))
        conn.commit()

def db_seen_get(uid: int) -> Set[int]:
    """Get a set of user_ids that the given user has already viewed."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT seen_id FROM seen WHERE user_id = ?', (uid,))
        return {r['seen_id'] for r in c.fetchall()}

def db_seen_clear(uid: int) -> None:
    """Clear the viewing history for a user (restart matching)."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM seen WHERE user_id = ?', (uid,))
        conn.commit()

def db_report_add(reporter: int, reported: int) -> None:
    """Record a user report."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO reports (reporter_id, reported_id, reported_at)
            VALUES (?, ?, datetime("now"))
        ''', (reporter, reported))
        conn.commit()

def db_reported_by(uid: int) -> Set[int]:
    """Get a set of user_ids that the given user has reported."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT reported_id FROM reports WHERE reporter_id = ?', (uid,))
        return {r['reported_id'] for r in c.fetchall()}

def db_stats() -> Dict[str, int]:
    """Aggregate overall statistics for the admin panel."""
    with get_conn() as conn:
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM users')
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users WHERE gender = 'Male'")
        male = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users WHERE gender = 'Female'")
        female = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users WHERE photo IS NOT NULL")
        photo = c.fetchone()[0]
        
        return {
            'total': total,
            'male': male,
            'female': female,
            'photo': photo
        }

# ═══════════════════════════════════════════════════════════════
# ⌨️ KEYBOARDS & MENUS
# ═══════════════════════════════════════════════════════════════

def main_kb() -> ReplyKeyboardMarkup:
    """Generate the standard main menu keyboard for regular users."""
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    
    btn_search = KeyboardButton("🔍 ဖူးစာရှာမည်")
    btn_profile = KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်")
    btn_help = KeyboardButton("ℹ️ အကူအညီ")
    btn_reset = KeyboardButton("🔄 Profile ပြန်လုပ်")
    
    m.row(btn_search, btn_profile)
    m.row(btn_help, btn_reset)
    
    return m

def admin_kb() -> ReplyKeyboardMarkup:
    """Generate the extended main menu keyboard for the administrator."""
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    
    btn_search = KeyboardButton("🔍 ဖူးစာရှာမည်")
    btn_profile = KeyboardButton("👤 ကိုယ့်ပရိုဖိုင်")
    btn_help = KeyboardButton("ℹ️ အကူအညီ")
    btn_reset = KeyboardButton("🔄 Profile ပြန်လုပ်")
    btn_stats = KeyboardButton("📊 စာရင်းအင်း")
    btn_admin = KeyboardButton("🛠 Admin Panel")
    
    m.row(btn_search, btn_profile)
    m.row(btn_help, btn_reset)
    m.row(btn_stats, btn_admin)
    
    return m

def kb(uid: int) -> ReplyKeyboardMarkup:
    """Return the appropriate keyboard based on user ID."""
    if uid == ADMIN_ID:
        return admin_kb()
    return main_kb()

# ═══════════════════════════════════════════════════════════════
# 🔧 UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def safe(d: Optional[Dict[str, Any]], key: str, fallback: str = '—') -> str:
    """Safely extract a string value from a dictionary."""
    if d is None:
        return fallback
    
    val = d.get(key)
    if isinstance(val, str):
        val = val.strip()
        
    if val:
        return val
    return fallback

def check_channel(uid: int) -> bool:
    """Verify if the user is currently a member of the official channel."""
    try:
        member = bot.get_chat_member(CHANNEL_ID, uid)
        if member.status in ('member', 'creator', 'administrator'):
            return True
        return False
    except Exception as e:
        logger.warning(f"Could not verify channel membership for {uid}: {e}")
        return False

def notify_admin(text: str) -> None:
    """Send a notification message directly to the administrator."""
    try:
        bot.send_message(
            chat_id=ADMIN_ID,
            text=text,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")

def fmt_profile(tp: Dict[str, Any], title: str = '👤 *ပရိုဖိုင်*') -> str:
    """Format user profile data into a readable Telegram message string."""
    bio_text = safe(tp, 'bio')
    bio_line = f"\n📝 အကြောင်း : {bio_text}" if bio_text != '—' else ''
    
    name_str = safe(tp, 'name')
    age_str = safe(tp, 'age')
    zodiac_str = safe(tp, 'zodiac')
    city_str = safe(tp, 'city')
    hobby_str = safe(tp, 'hobby')
    job_str = safe(tp, 'job')
    song_str = safe(tp, 'song')
    gender_str = safe(tp, 'gender')
    looking_g_str = safe(tp, 'looking_gender')
    looking_z_str = safe(tp, 'looking_zodiac', 'Any')
    
    profile_text = (
        f"{title}\n\n"
        f"📛 နာမည်   : {name_str}\n"
        f"🎂 အသက်   : {age_str} နှစ်\n"
        f"🔮 ရာသီ   : {zodiac_str}\n"
        f"📍 မြို့    : {city_str}\n"
        f"🎨 ဝါသနာ  : {hobby_str}\n"
        f"💼 အလုပ်   : {job_str}\n"
        f"🎵 သီချင်း  : {song_str}"
        f"{bio_line}\n"
        f"⚧ လိင်    : {gender_str}\n"
        f"💑 ရှာဖွေ  : {looking_g_str} / {looking_z_str}"
    )
    
    return profile_text

def stats_text() -> str:
    """Format current database statistics into a readable message."""
    s = db_stats()
    current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
    
    text = (
        f"📊 *Yay Zat Bot — စာရင်းအင်း*\n\n"
        f"👥 စုစုပေါင်း       : *{s['total']}* ယောက်\n"
        f"♂️ ကျား            : {s['male']} ယောက်\n"
        f"♀️ မ               : {s['female']} ယောက်\n"
        f"📸 ဓာတ်ပုံပါ       : {s['photo']} ယောက်\n"
        f"⏰ Update          : {current_time}"
    )
    return text

def _skip(msg: Message) -> bool:
    """Helper to check if a user wants to skip a registration step."""
    if not msg.text:
        return False
    if msg.text.strip() == '/skip':
        return True
    return False

# ═══════════════════════════════════════════════════════════════
# 🚀 /START COMMAND
# ═══════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start'])
def start_bot(message: Message) -> None:
    """Handler for the /start command. Initiates registration or shows menu."""
    uid = message.chat.id
    total_users = db_count()
    
    # If the user already exists in the database
    if db_get(uid):
        msg_text = (
            f"✨ *ကြိုဆိုပါတယ်!* ✨\n\n"
            f"👥 လက်ရှိ အသုံးပြုသူ : *{total_users}* ယောက်\n\n"
            f"ခလုတ်များနှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇"
        )
        bot.send_message(
            chat_id=uid,
            text=msg_text,
            parse_mode="Markdown",
            reply_markup=kb(uid)
        )
        return

    # Gather info for new user registration
    try:
        user_obj = message.from_user
        tg_handle = user_obj.username or user_obj.first_name or str(uid)
        first_name = user_obj.first_name or ''
        last_name = user_obj.last_name or ''
    except Exception:
        tg_handle = str(uid)
        first_name = str(uid)
        last_name = ""

    current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
    admin_notification = (
        f"🆕 *အသုံးပြုသူသစ် စတင်သုံးနေပါပြီ!*\n\n"
        f"👤 {first_name} {last_name}\n"
        f"🔗 @{tg_handle}\n"
        f"🆔 `{uid}`\n"
        f"👥 မှတ်ပုံတင်ပြီးသား : {total_users} ယောက်\n"
        f"⏰ {current_time}"
    )
    notify_admin(admin_notification)
    
    # Initialize empty registration state for this user
    user_reg[uid] = {}
    
    welcome_text = (
        f"✨ *Yay Zat Zodiac မှ ကြိုဆိုပါတယ်!* ✨\n\n"
        f"👥 အသုံးပြုသူ : *{total_users}* ယောက်\n\n"
        f"ဖူးစာရှင်ကိုရှာဖွေဖို့ မေးခွန်းလေးတွေ ဖြေပေးပါ 🙏\n"
        f"_( /skip — ကျော်ချင်တဲ့မေးခွန်းအတွက် )_\n\n"
        f"📛 *နာမည် (သို့) အမည်ဝှက်* ကို ရိုက်ထည့်ပါ-"
    )
    
    msg = bot.send_message(
        chat_id=uid,
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, reg_name)

# ═══════════════════════════════════════════════════════════════
# 📝 REGISTRATION FLOW STEPS
# ═══════════════════════════════════════════════════════════════

def reg_name(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['name'] = message.text.strip()
            
    msg = bot.send_message(
        chat_id=uid,
        text="🎂 အသက် ဘယ်လောက်လဲ? (/skip)-"
    )
    bot.register_next_step_handler(msg, reg_age)

def reg_age(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if message.text and message.text.strip().isdigit():
            if uid not in user_reg:
                user_reg[uid] = {}
            user_reg[uid]['age'] = message.text.strip()
        else:
            msg = bot.send_message(
                chat_id=uid,
                text="⚠️ ဂဏန်းသာ ရိုက်ပါ (ဥပမာ 25)- (/skip)"
            )
            bot.register_next_step_handler(msg, reg_age)
            return
            
    m = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for z in ZODIACS:
        m.add(KeyboardButton(z))
    m.add(KeyboardButton('/skip'))
    
    msg = bot.send_message(
        chat_id=uid,
        text="🔮 ရာသီခွင်ကို ရွေးပါ-",
        reply_markup=m
    )
    bot.register_next_step_handler(msg, reg_zodiac)

def reg_zodiac(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['zodiac'] = message.text.strip()
            
    msg = bot.send_message(
        chat_id=uid,
        text="📍 နေထိုင်တဲ့ မြို့ (ဥပမာ Mandalay)- (/skip)",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, reg_city)

def reg_city(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['city'] = message.text.strip()
            
    msg = bot.send_message(
        chat_id=uid,
        text="🎨 ဝါသနာ ဘာပါလဲ? (ဥပမာ ခရီးသွား, ဂီတ)- (/skip)"
    )
    bot.register_next_step_handler(msg, reg_hobby)

def reg_hobby(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['hobby'] = message.text.strip()
            
    msg = bot.send_message(
        chat_id=uid,
        text="💼 အလုပ်အကိုင်?- (/skip)"
    )
    bot.register_next_step_handler(msg, reg_job)

def reg_job(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['job'] = message.text.strip()
            
    msg = bot.send_message(
        chat_id=uid,
        text="🎵 အကြိုက်ဆုံး သီချင်း တစ်ပုဒ်?- (/skip)"
    )
    bot.register_next_step_handler(msg, reg_song)

def reg_song(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['song'] = message.text.strip()
            
    bio_text = (
        "📝 *မိမိအကြောင်း အတိုချုံး* ရေးပြပါ\n"
        "_(ဥပမာ: ဆေးကျောင်းသား, ဂီတတွင်မှီဝဲသူ, ပြောဆိုရင်းနှီးချင်သူ)_- (/skip)"
    )
    msg = bot.send_message(
        chat_id=uid,
        text=bio_text,
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, reg_bio)

def reg_bio(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['bio'] = message.text.strip()
            
    m = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    m.add(KeyboardButton('Male'), KeyboardButton('Female'), KeyboardButton('/skip'))
    
    msg = bot.send_message(
        chat_id=uid,
        text="⚧ သင့်လိင်ကို ရွေးပါ-",
        reply_markup=m
    )
    bot.register_next_step_handler(msg, reg_gender)

def reg_gender(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['gender'] = message.text.strip()
            
    m = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    m.add(KeyboardButton('Male'), KeyboardButton('Female'))
    m.add(KeyboardButton('Both'), KeyboardButton('/skip'))
    
    msg = bot.send_message(
        chat_id=uid,
        text="💑 ရှာဖွေနေတဲ့ လိင်ကို ရွေးပါ-",
        reply_markup=m
    )
    bot.register_next_step_handler(msg, reg_looking_gender)

def reg_looking_gender(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['looking_gender'] = message.text.strip()
            
    m = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for z in ZODIACS:
        m.add(KeyboardButton(z))
    m.add(KeyboardButton('Any'), KeyboardButton('/skip'))
    
    msg = bot.send_message(
        chat_id=uid,
        text="🔮 ရှာဖွေနေတဲ့ ရာသီခွင်ကို ရွေးပါ-",
        reply_markup=m
    )
    bot.register_next_step_handler(msg, reg_looking_zodiac)

def reg_looking_zodiac(message: Message) -> None:
    uid = message.chat.id
    
    if not _skip(message):
        if uid not in user_reg:
            user_reg[uid] = {}
        if message.text:
            user_reg[uid]['looking_zodiac'] = message.text.strip()
            
    photo_text = "📸 Profile ဓာတ်ပုံ ပေးပို့ပါ _(မလိုပါက /skip)_"
    msg = bot.send_message(
        chat_id=uid,
        text=photo_text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, reg_photo)

def reg_photo(message: Message) -> None:
    uid = message.chat.id
    
    # Check if the user is completely new
    existing_user = db_get(uid)
    is_new = existing_user is None
    
    if not _skip(message):
        if message.content_type != 'photo':
            err_msg = bot.send_message(
                chat_id=uid,
                text="⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ (သို့) /skip ဟုရိုက်ပါ-"
            )
            bot.register_next_step_handler(err_msg, reg_photo)
            return
            
        if uid not in user_reg:
            user_reg[uid] = {}
        # Get the highest resolution photo from the array
        user_reg[uid]['photo'] = message.photo[-1].file_id
        
    # Finalize registration
    final_data = user_reg.pop(uid, {})
    db_save(uid, final_data)
    
    total_users = db_count()
    status_verb = 'တည်ဆောက်' if is_new else 'ပြင်ဆင်'
    
    success_text = (
        f"✅ Profile {status_verb} ပြီးပါပြီ! 🎉\n\n"
        f"👥 လက်ရှိ အသုံးပြုသူ : *{total_users}* ယောက်\n\n"
        f"ခလုတ်များ နှိပ်ပြီး အသုံးပြုနိုင်ပါပြီ 👇"
    )
    bot.send_message(
        chat_id=uid,
        text=success_text,
        parse_mode="Markdown",
        reply_markup=kb(uid)
    )
    
    if is_new:
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        user_name = safe(final_data, 'name')
        admin_alert = (
            f"🎉 *မှတ်ပုံတင်ခြင်း ပြီးမြောက်ပါပြီ!*\n\n"
            f"🆔 `{uid}` — 📛 {user_name}\n"
            f"👥 စုစုပေါင်း : *{total_users}* ယောက်\n"
            f"⏰ {current_time}"
        )
        notify_admin(admin_alert)

# ═══════════════════════════════════════════════════════════════
# 👤 USER PROFILE VIEW
# ═══════════════════════════════════════════════════════════════

def show_my_profile(message: Message) -> None:
    """Display the user's profile with inline editing options."""
    uid = message.chat.id
    tp = db_get(uid)
    
    if not tp:
        bot.send_message(
            chat_id=uid,
            text="Profile မရှိသေးပါ။ /start ကိုနှိပ်ပါ။",
            reply_markup=kb(uid)
        )
        return
        
    total_users = db_count()
    text = f"📊 အသုံးပြုသူ : *{total_users}* ယောက်\n\n" + fmt_profile(tp)
    
    # Create the inline keyboard for editing profile fields
    m = InlineKeyboardMarkup()
    
    b_name = InlineKeyboardButton("📛 နာမည်", callback_data="edit_name")
    b_age = InlineKeyboardButton("🎂 အသက်", callback_data="edit_age")
    m.row(b_name, b_age)
    
    b_zod = InlineKeyboardButton("🔮 ရာသီ", callback_data="edit_zodiac")
    b_city = InlineKeyboardButton("📍 မြို့", callback_data="edit_city")
    m.row(b_zod, b_city)
    
    b_hob = InlineKeyboardButton("🎨 ဝါသနာ", callback_data="edit_hobby")
    b_job = InlineKeyboardButton("💼 အလုပ်", callback_data="edit_job")
    m.row(b_hob, b_job)
    
    b_song = InlineKeyboardButton("🎵 သီချင်း", callback_data="edit_song")
    b_bio = InlineKeyboardButton("📝 Bio", callback_data="edit_bio")
    m.row(b_song, b_bio)
    
    b_photo = InlineKeyboardButton("📸 ဓာတ်ပုံ", callback_data="edit_photo")
    m.row(b_photo)
    
    b_all = InlineKeyboardButton("🔄 အကုန်ပြန်လုပ်", callback_data="edit_all")
    m.row(b_all)
    
    b_del = InlineKeyboardButton("🗑 Profile ဖျက်", callback_data="delete_profile")
    m.row(b_del)
    
    # Send photo or just text
    photo_id = tp.get('photo')
    if photo_id:
        bot.send_photo(
            chat_id=uid,
            photo=photo_id,
            caption=text,
            reply_markup=m,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id=uid,
            text=text,
            reply_markup=m,
            parse_mode="Markdown"
        )

# ═══════════════════════════════════════════════════════════════
# 🔍 MATCHING SYSTEM
# ═══════════════════════════════════════════════════════════════

def run_find_match(message: Message) -> None:
    """Core logic to find a suitable match for the user."""
    uid = message.chat.id
    me = db_get(uid)
    
    if not me:
        bot.send_message(
            chat_id=uid,
            text="/start ကိုနှိပ်ပြီး Profile အရင်တည်ဆောက်ပါ။",
            reply_markup=kb(uid)
        )
        return
        
    if not check_channel(uid):
        m = InlineKeyboardMarkup()
        btn_join = InlineKeyboardButton("📢 Channel Join မည်", url=CHANNEL_LINK)
        m.add(btn_join)
        
        bot.send_message(
            chat_id=uid,
            text="⚠️ Channel ကို အရင် Join ပေးပါ။",
            reply_markup=m
        )
        return

    # Prepare exclusion set (self, already seen, reported)
    seen_set = db_seen_get(uid)
    reported_set = db_reported_by(uid)
    exclude_set = seen_set | reported_set | {uid}

    # Fetch user's preferences
    looking_g = (me.get('looking_gender') or '').strip()
    looking_z = (me.get('looking_zodiac') or '').strip()

    all_users = db_all()
    eligible: List[Dict[str, Any]] = []
    
    for u in all_users:
        target_uid = u['user_id']
        if target_uid in exclude_set:
            continue
            
        # Strict gender filtering
        if looking_g and looking_g not in ('Both', 'Any'):
            target_gender = (u.get('gender') or '').strip()
            if target_gender != looking_g:
                continue
                
        eligible.append(u)

    # If nobody is eligible
    if not eligible:
        if seen_set:
            # If exhausted list but have seen people, reset history
            db_seen_clear(uid)
            bot.send_message(
                chat_id=uid,
                text="🔄 ကြည့်ပြီးသားများ ကုန်သဖြင့် ပြန်စပါပြီ..."
            )
            # Recursively call match finding
            run_find_match(message)
        else:
            # Genuinely nobody available
            bot.send_message(
                chat_id=uid,
                text="😔 လောလောဆယ် သင့်အတွက် ကိုက်ညီသူ မရှိသေးပါ။\nနောက်မှ ပြန်ကြိုးစားကြည့်ပါ။",
                reply_markup=kb(uid)
            )
        return

    # Soft filtering for Zodiac (Preferred comes first)
    if looking_z and looking_z not in ('Any', ''):
        pref_list = [u for u in eligible if (u.get('zodiac') or '') == looking_z]
        fall_list = [u for u in eligible if (u.get('zodiac') or '') != looking_z]
        ordered_list = pref_list + fall_list
    else:
        ordered_list = eligible

    # Select the top match
    target = ordered_list[0]
    tid = target['user_id']
    
    # Record that the user has seen this target
    db_seen_add(uid, tid)

    # Prepare matching message
    note = ''
    target_zodiac = target.get('zodiac') or ''
    if looking_z and looking_z not in ('Any', '') and target_zodiac != looking_z:
        note = f"\n_( {looking_z} ကို မတွေ့သောကြောင့် အနီးစပ်ဆုံးပြပေးနေပါသည် )_"

    text = fmt_profile(target, title=f"🎯 *မိတ်ဆွေနဲ့ ကိုက်ညီနိုင်မယ့်သူ*{note}")
    
    m = InlineKeyboardMarkup()
    btn_like = InlineKeyboardButton("❤️ Like", callback_data=f"like_{tid}")
    btn_skip = InlineKeyboardButton("⏭ Skip", callback_data="skip")
    btn_report = InlineKeyboardButton("🚩 Report", callback_data=f"report_{tid}")
    
    m.row(btn_like, btn_skip, btn_report)

    target_photo = target.get('photo')
    if target_photo:
        bot.send_photo(
            chat_id=uid,
            photo=target_photo,
            caption=text,
            reply_markup=m,
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id=uid,
            text=text,
            reply_markup=m,
            parse_mode="Markdown"
        )

# ═══════════════════════════════════════════════════════════════
# 🔄 RESET, HELP, STATS & ADMIN MODULES
# ═══════════════════════════════════════════════════════════════

def run_reset(message: Message) -> None:
    uid = message.chat.id
    existing = db_get(uid)
    
    # Store existing data into temporary reg dictionary to retain fields if skipped
    if existing:
        user_reg[uid] = dict(existing)
    else:
        user_reg[uid] = {}
        
    reset_text = "🔄 *Profile ပြန်လုပ်မည်*\n\n📛 နာမည် ရိုက်ထည့်ပါ- (/skip နဲ့ ကျော်နိုင်)"
    
    msg = bot.send_message(
        chat_id=uid,
        text=reset_text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, reg_name)

def show_help(message: Message) -> None:
    uid = message.chat.id
    help_text = (
        "ℹ️ *Yay Zat Bot — အကူအညီ*\n\n"
        "🔍 *ဖူးစာရှာမည်* — ကိုက်ညီနိုင်မယ့်သူ ရှာပါ\n"
        "👤 *ကိုယ့်ပရိုဖိုင်* — Profile ကြည့်/ပြင်ပါ\n"
        "🔄 *Profile ပြန်လုပ်* — Profile အသစ်ပြန်ဖြည့်ပါ\n\n"
        "*Commands*\n"
        "/start — စတင်မှတ်ပုံတင်ပါ\n"
        "/reset — Profile ပြန်လုပ်ပါ\n"
        "/deleteprofile — Profile ဖျက်ပါ\n\n"
        "ပြဿနာများ Admin ကို ဆက်သွယ်ပါ။"
    )
    
    bot.send_message(
        chat_id=uid,
        text=help_text,
        parse_mode="Markdown",
        reply_markup=kb(uid)
    )

def show_stats(message: Message) -> None:
    uid = message.chat.id
    if uid != ADMIN_ID:
        bot.send_message(chat_id=uid, text="⛔ Admin သာ ကြည့်ရှုနိုင်ပါသည်။")
        return
        
    bot.send_message(
        chat_id=ADMIN_ID,
        text=stats_text(),
        parse_mode="Markdown",
        reply_markup=admin_kb()
    )

def show_admin_panel(message: Message) -> None:
    uid = message.chat.id
    if uid != ADMIN_ID:
        return
        
    m = InlineKeyboardMarkup()
    
    b_stats = InlineKeyboardButton("📊 Full Stats", callback_data="adm_stats")
    b_list = InlineKeyboardButton("👥 User List", callback_data="adm_userlist")
    m.row(b_stats, b_list)
    
    b_broad = InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")
    b_del = InlineKeyboardButton("🗑 User ဖျက်", callback_data="adm_deluser")
    m.row(b_broad, b_del)
    
    bot.send_message(
        chat_id=ADMIN_ID,
        text="🛠 *Admin Panel*",
        parse_mode="Markdown",
        reply_markup=m
    )

def _broadcast_step(message: Message) -> None:
    if message.text == '/cancel':
        bot.send_message(ADMIN_ID, "ပယ်ဖျက်ပြီးပါပြီ။")
        return
        
    ok_count = 0
    fail_count = 0
    
    for uid in db_all_ids():
        try:
            bot.send_message(
                chat_id=uid,
                text=f"📢 *Admin မှ သတင်းစကား*\n\n{message.text}",
                parse_mode="Markdown"
            )
            ok_count += 1
        except Exception:
            fail_count += 1
            
    bot.send_message(
        chat_id=ADMIN_ID,
        text=f"✅ Broadcast ပြီးပါပြီ!\n✔️ {ok_count} ယောက် ရောက်ပါသည်\n❌ {fail_count} ယောက် မရောက်ပါ"
    )

def _deluser_step(message: Message) -> None:
    if message.text == '/cancel':
        bot.send_message(ADMIN_ID, "ပယ်ဖျက်ပြီးပါပြီ။")
        return
        
    try:
        if not message.text:
            raise ValueError()
            
        target_uid = int(message.text.strip())
        
        if db_get(target_uid):
            db_delete(target_uid)
            bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✅ User `{target_uid}` ဖျက်ပြီးပါပြီ။",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(ADMIN_ID, "⚠️ ထို ID မတွေ့ပါ။")
            
    except ValueError:
        bot.send_message(ADMIN_ID, "⚠️ ID ဂဏန်းသာ ရိုက်ပါ။")

def save_field(message: Message, field: str) -> None:
    """Universal handler to save a specific edited field from profile menu."""
    uid = message.chat.id
    
    if field == 'photo':
        if message.content_type != 'photo':
            err_msg = bot.send_message(uid, "⚠️ ဓာတ်ပုံသာ ပေးပို့ပါ။")
            bot.register_next_step_handler(err_msg, save_field, field)
            return
            
        new_photo_id = message.photo[-1].file_id
        db_update(uid, 'photo', new_photo_id)
        
    else:
        if not message.text or not message.text.strip():
            err_msg = bot.send_message(uid, "⚠️ ဗလာမထားပါနဲ့-")
            bot.register_next_step_handler(err_msg, save_field, field)
            return
            
        new_text = message.text.strip()
        db_update(uid, field, new_text)
        
    bot.send_message(
        chat_id=uid,
        text="✅ ပြင်ဆင်မှု အောင်မြင်ပါသည်!",
        reply_markup=kb(uid)
    )

# ═══════════════════════════════════════════════════════════════
# 🔘 MENU ROUTING & COMMAND REGISTRATION
# ═══════════════════════════════════════════════════════════════

# Map menu buttons to their respective functions
MENU_MAP: Dict[str, Any] = {
    "🔍 ဖူးစာရှာမည်": run_find_match,
    "👤 ကိုယ့်ပရိုဖိုင်": show_my_profile,
    "ℹ️ အကူအညီ": show_help,
    "🔄 Profile ပြန်လုပ်": run_reset,
    "📊 စာရင်းအင်း": show_stats,
    "🛠 Admin Panel": show_admin_panel,
}

@bot.message_handler(func=lambda m: m.text in MENU_MAP)
def menu_router(message: Message) -> None:
    handler = MENU_MAP.get(message.text)
    if handler:
        handler(message)

@bot.message_handler(commands=['reset'])
def cmd_reset(m: Message) -> None:
    run_reset(m)

@bot.message_handler(commands=['stats'])
def cmd_stats(m: Message) -> None:
    show_stats(m)

@bot.message_handler(commands=['myprofile'])
def cmd_myprofile(m: Message) -> None:
    show_my_profile(m)

@bot.message_handler(commands=['deleteprofile'])
def cmd_deleteprofile(message: Message) -> None:
    uid = message.chat.id
    
    m = InlineKeyboardMarkup()
    btn_yes = InlineKeyboardButton("✅ ဟုတ်တယ် ဖျက်မည်", callback_data="confirm_delete")
    btn_no = InlineKeyboardButton("❌ မဖျက်တော့ပါ", callback_data="cancel_delete")
    m.row(btn_yes, btn_no)
    
    bot.send_message(
        chat_id=uid,
        text="⚠️ Profile ကို ဖျက်မှာ သေချာပါသလား?",
        reply_markup=m
    )

# ═══════════════════════════════════════════════════════════════
# 📞 CALLBACK QUERY HANDLER
# ═══════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda call: True)
def on_callback(call: CallbackQuery) -> None:
    uid = call.message.chat.id
    d = call.data

    # ── Inline Profile Edit ─────────────────────────────────────
    if d.startswith("edit_"):
        field = d[5:]
        
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
            
        if field == "all":
            existing = db_get(uid)
            if existing:
                user_reg[uid] = dict(existing)
            else:
                user_reg[uid] = {}
                
            msg = bot.send_message(
                chat_id=uid,
                text="🔄 Profile ပြန်တည်ဆောက်မည်\n📛 နာမည် ရိုက်ထည့်ပါ- (/skip)",
                reply_markup=ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, reg_name)
            
        elif field == "photo":
            msg = bot.send_message(
                chat_id=uid,
                text="📸 ဓာတ်ပုံအသစ် ပေးပို့ပါ-",
                reply_markup=ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, save_field, 'photo')
            
        else:
            labels_map = {
                'name': 'နာမည်', 'age': 'အသက်', 'zodiac': 'ရာသီ', 'city': 'မြို့',
                'hobby': 'ဝါသနာ', 'job': 'အလုပ်', 'song': 'သီချင်း', 'bio': 'Bio',
                'gender': 'လိင်', 'looking_gender': 'ရှာဖွေမည့်လိင်',
                'looking_zodiac': 'ရှာဖွေမည့်ရာသီ'
            }
            display_label = labels_map.get(field, field)
            
            msg = bot.send_message(
                chat_id=uid,
                text=f"📝 {display_label} အသစ် ရိုက်ထည့်ပါ-",
                reply_markup=ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, save_field, field)

    # ── Profile Deletion Request ─────────────────────────────────
    elif d == "delete_profile":
        m = InlineKeyboardMarkup()
        btn_yes = InlineKeyboardButton("✅ ဟုတ်တယ် ဖျက်မည်", callback_data="confirm_delete")
        btn_no = InlineKeyboardButton("❌ မဖျက်တော့ပါ", callback_data="cancel_delete")
        m.row(btn_yes, btn_no)
        
        try:
            bot.edit_message_reply_markup(
                chat_id=uid,
                message_id=call.message.message_id,
                reply_markup=m
            )
        except Exception:
            pass

    # ── Confirm Deletion ─────────────────────────────────────────
    elif d == "confirm_delete":
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
            
        db_delete(uid)
        bot.send_message(
            chat_id=uid,
            text="🗑 Profile ဖျက်ပြီးပါပြီ။\n/start နှိပ်ပြီး ပြန်မှတ်ပုံတင်နိုင်ပါသည်။",
            reply_markup=ReplyKeyboardRemove()
        )

    # ── Cancel Deletion ──────────────────────────────────────────
    elif d == "cancel_delete":
        bot.answer_callback_query(call.id, "မဖျက်တော့ပါ။")
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass

    # ── Skip Match ───────────────────────────────────────────────
    elif d == "skip":
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
        run_find_match(call.message)

    # ── Like Match ───────────────────────────────────────────────
    elif d.startswith("like_"):
        tid = int(d[5:])
        
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
            
        if not check_channel(uid):
            bot.answer_callback_query(
                call.id, 
                "⚠️ Channel ကို Join ပါ!", 
                show_alert=True
            )
            return
            
        me_data = db_get(uid) or {}
        liker_name = safe(me_data, 'name', 'တစ်ယောက်')
        
        like_m = InlineKeyboardMarkup()
        btn_acc = InlineKeyboardButton("✅ လက်ခံမည်", callback_data=f"accept_{uid}")
        btn_dec = InlineKeyboardButton("❌ ငြင်းမည်", callback_data="decline")
        like_m.row(btn_acc, btn_dec)
        
        like_caption = (
            f"💌 *'{liker_name}'* က သင့်ကို Like လုပ်ထားပါတယ်!\n\n" +
            fmt_profile(me_data, title='👤 *သူ/သူမ ရဲ့ Profile*')
        )
        
        try:
            me_photo = me_data.get('photo')
            if me_photo:
                bot.send_photo(
                    chat_id=tid,
                    photo=me_photo,
                    caption=like_caption,
                    reply_markup=like_m,
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(
                    chat_id=tid,
                    text=like_caption,
                    reply_markup=like_m,
                    parse_mode="Markdown"
                )
                
            bot.send_message(
                chat_id=uid,
                text="❤️ Like လုပ်လိုက်ပါပြီ!\nတစ်ဖက်က လက်ခံရင် အကြောင်းကြားပေးပါမယ် 😊",
                reply_markup=kb(uid)
            )
        except Exception as e:
            logger.warning(f"Error sending like to {tid}: {e}")
            bot.send_message(
                chat_id=uid,
                text="⚠️ တစ်ဖက်လူမှာ Bot ကို Block ထားသဖြင့် ပေးပို့မရပါ။",
                reply_markup=kb(uid)
            )

    # ── Accept Match ─────────────────────────────────────────────
    elif d.startswith("accept_"):
        liker_id = int(d[7:])
        
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
            
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        admin_note = (
            f"💖 *New Match!*\n\n"
            f"[User A](tg://user?id={uid}) + [User B](tg://user?id={liker_id})\n"
            f"⏰ {current_time}"
        )
        notify_admin(admin_note)
        
        # Notify both users
        pairs = [(uid, liker_id), (liker_id, uid)]
        for person_a, person_b in pairs:
            try:
                bot.send_message(
                    chat_id=person_a,
                    text=(
                        f"💖 *Match ဖြစ်သွားပါပြီ!*\n\n"
                        f"[ဒီမှာနှိပ်ပြီး](tg://user?id={person_b}) စကားပြောနိုင်ပါပြီ 🎉"
                    ),
                    parse_mode="Markdown",
                    reply_markup=kb(person_a)
                )
            except Exception:
                pass

    # ── Decline Match ────────────────────────────────────────────
    elif d == "decline":
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
            
        bot.send_message(
            chat_id=uid,
            text="❌ ငြင်းဆန်လိုက်ပါပြီ။",
            reply_markup=kb(uid)
        )

    # ── Report User ──────────────────────────────────────────────
    elif d.startswith("report_"):
        tid = int(d[7:])
        db_report_add(uid, tid)
        
        bot.answer_callback_query(
            call_id=call.id,
            text="🚩 Report လုပ်ပြီးပါပြီ။",
            show_alert=True
        )
        
        try:
            bot.delete_message(uid, call.message.message_id)
        except Exception:
            pass
            
        reporter_name = safe(db_get(uid), 'name')
        reported_name = safe(db_get(tid), 'name')
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        report_alert = (
            f"🚩 *User Report*\n\n"
            f"Reporter : `{uid}` {reporter_name}\n"
            f"Reported : `{tid}` {reported_name}\n"
            f"⏰ {current_time}"
        )
        notify_admin(report_alert)

    # ── Admin Callbacks ──────────────────────────────────────────
    elif d == "adm_stats" and uid == ADMIN_ID:
        bot.send_message(
            chat_id=ADMIN_ID,
            text=stats_text(),
            parse_mode="Markdown"
        )

    elif d == "adm_broadcast" and uid == ADMIN_ID:
        msg = bot.send_message(
            chat_id=ADMIN_ID,
            text="📢 Message ကို ရိုက်ထည့်ပါ (/cancel-ပယ်ဖျက်)-"
        )
        bot.register_next_step_handler(msg, _broadcast_step)

    elif d == "adm_userlist" and uid == ADMIN_ID:
        rows = db_all()[:30]
        lines = []
        for i, u in enumerate(rows, 1):
            uname = safe(u, 'name')
            uid_str = u['user_id']
            lines.append(f"{i}. {uname} — `{uid_str}`")
            
        list_str = "\n".join(lines) if lines else "မရှိသေး"
        bot.send_message(
            chat_id=ADMIN_ID,
            text="👥 *User List (ပထမ 30)*\n\n" + list_str,
            parse_mode="Markdown"
        )

    elif d == "adm_deluser" and uid == ADMIN_ID:
        msg = bot.send_message(
            chat_id=ADMIN_ID,
            text="🗑 ဖျက်မည့် User ID ရိုက်ပါ (/cancel-ပယ်ဖျက်)-"
        )
        bot.register_next_step_handler(msg, _deluser_step)

    # Answer all unhandled queries quietly
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# 🚀 INITIALIZATION & POLLING
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    start_time = datetime.now().strftime('%d/%m/%Y %H:%M')
    print(f"✅ Yay Zat Zodiac Bot is successfully starting... [{start_time}]")
    logger.info("Bot started polling.")
    
    # Start polling for updates
    try:
        bot.infinity_polling(none_stop=True, timeout=60, long_polling_timeout=60)
    except Exception as exc:
        logger.error(f"Critical error during polling: {exc}")
