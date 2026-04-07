import telebot
import sqlite3
import os
from datetime import datetime
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ”‘  CONFIG
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
TOKEN        = '8651910143:AAFd0mv_MWn_wjnvx6H0brIXXHEtZJ_zvEc'
CHANNEL_ID   = -1003641016541
CHANNEL_LINK = "https://t.me/yayzatofficial"
ADMIN_ID     = 6131831207

bot     = telebot.TeleBot(TOKEN)
DB_FILE = 'yayzat.db'

ZODIACS = [
    'Aries','Taurus','Gemini','Cancer','Leo','Virgo',
    'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'
]

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ’¾  SQLite â€” Schema + Helpers
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
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
            photo          TEXT,
            created_at     TEXT DEFAULT (datetime('now')),
            updated_at     TEXT DEFAULT (datetime('now'))
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS seen (
            user_id INTEGER, seen_id INTEGER,
            PRIMARY KEY (user_id, seen_id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS reports (
            reporter_id INTEGER, reported_id INTEGER,
            reported_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (reporter_id, reported_id)
        )''')
        existing = {row[1] for row in c.execute("PRAGMA table_info(users)")}
        for col, typ in [('bio','TEXT'),('song','TEXT')]:
            if col not in existing:
                try:
                    c.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
                except Exception as e:
                    print(f"[WARN] ALTER TABLE {col}: {e}")
        c.commit()

init_db()

# â”€â”€ CRUD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
FIELDS = ['name','age','zodiac','city','hobby','job','song','bio',
          'gender','looking_gender','looking_zodiac','photo']

def db_get(uid):
    with get_conn() as c:
        row = c.execute('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone()
        return dict(row) if row else None

def db_save(uid, data):
    cols = ','.join(FIELDS)
    ph   = ','.join(['?']*len(FIELDS))
    vals = [data.get(f) for f in FIELDS]
    upd  = ','.join([f"{f}=excluded.{f}" for f in FIELDS])
    with get_conn() as c:
        c.execute(
            f"INSERT INTO users (user_id,{cols},updated_at) VALUES (?,{ph},datetime('now')) "
            f"ON CONFLICT(user_id) DO UPDATE SET {upd},updated_at=datetime('now')",
            [uid]+vals)
        c.commit()

def db_update(uid, field, value):
    if field not in set(FIELDS): return
    with get_conn() as c:
        c.execute(f'UPDATE users SET {field}=?,updated_at=datetime("now") WHERE user_id=?',
                  (value, uid))
        c.commit()

def db_delete(uid):
    with get_conn() as c:
        c.execute('DELETE FROM users WHERE user_id=?',(uid,))
        c.execute('DELETE FROM seen WHERE user_id=? OR seen_id=?',(uid,uid))
        c.commit()

def db_all():
    with get_conn() as c:
        return [dict(r) for r in c.execute('SELECT * FROM users').fetchall()]

def db_all_ids():
    with get_conn() as c:
        return [r[0] for r in c.execute('SELECT user_id FROM users').fetchall()]

def db_count():
    with get_conn() as c:
        return c.execute('SELECT COUNT(*) FROM users').fetchone()[0]

def db_seen_add(uid, sid):
    with get_conn() as c:
        c.execute('INSERT OR IGNORE INTO seen VALUES (?,?)',(uid,sid))
        c.commit()

def db_seen_get(uid):
    with get_conn() as c:
        return {r[0] for r in c.execute('SELECT seen_id FROM seen WHERE user_id=?',(uid,))}

def db_seen_clear(uid):
    with get_conn() as c:
        c.execute('DELETE FROM seen WHERE user_id=?',(uid,))
        c.commit()

def db_report_add(reporter, reported):
    with get_conn() as c:
        c.execute('INSERT OR IGNORE INTO reports VALUES (?,?,datetime("now"))',(reporter,reported))
        c.commit()

def db_reported_ids_by(uid):
    """uid á€€ report á€œá€¯á€•á€ºá€‘á€¬á€¸á€á€²á€· user_id set á€€á€­á€¯ á€•á€¼á€”á€ºá€•á€±á€¸á€žá€Šá€º"""
    with get_conn() as c:
        return {r[0] for r in c.execute(
            'SELECT reported_id FROM reports WHERE reporter_id=?',(uid,))}

def db_stats():
    with get_conn() as c:
        total  = c.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        male   = c.execute("SELECT COUNT(*) FROM users WHERE gender='Male'").fetchone()[0]
        female = c.execute("SELECT COUNT(*) FROM users WHERE gender='Female'").fetchone()[0]
        photo  = c.execute("SELECT COUNT(*) FROM users WHERE photo IS NOT NULL").fetchone()[0]
        return {'total':total,'male':male,'female':female,'photo':photo}

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# âŒ¨ï¸  KEYBOARDS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def main_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(KeyboardButton("ðŸ” á€–á€°á€¸á€…á€¬á€›á€¾á€¬á€™á€Šá€º"), KeyboardButton("ðŸ‘¤ á€€á€­á€¯á€šá€·á€ºá€•á€›á€­á€¯á€–á€­á€¯á€„á€º"))
    m.row(KeyboardButton("â„¹ï¸ á€¡á€€á€°á€¡á€Šá€®"),      KeyboardButton("ðŸ”„ Profile á€•á€¼á€”á€ºá€œá€¯á€•á€º"))
    return m

def admin_kb():
    m = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    m.row(KeyboardButton("ðŸ” á€–á€°á€¸á€…á€¬á€›á€¾á€¬á€™á€Šá€º"), KeyboardButton("ðŸ‘¤ á€€á€­á€¯á€šá€·á€ºá€•á€›á€­á€¯á€–á€­á€¯á€„á€º"))
    m.row(KeyboardButton("â„¹ï¸ á€¡á€€á€°á€¡á€Šá€®"),      KeyboardButton("ðŸ”„ Profile á€•á€¼á€”á€ºá€œá€¯á€•á€º"))
    m.row(KeyboardButton("ðŸ“Š á€…á€¬á€›á€„á€ºá€¸á€¡á€„á€ºá€¸"),   KeyboardButton("ðŸ›  Admin Panel"))
    return m

def kb(uid): return admin_kb() if uid == ADMIN_ID else main_kb()

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ”§  UTILITIES
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def safe(d, key, fallback='â€”'):
    v = (d or {}).get(key)
    if isinstance(v, str): v = v.strip()
    return v if v else fallback

def check_channel(uid):
    try:
        return bot.get_chat_member(CHANNEL_ID, uid).status in ('member','creator','administrator')
    except:
        return False

def notify_admin(text):
    try:
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except:
        pass

def fmt_profile(tp, title='ðŸ‘¤ *á€•á€›á€­á€¯á€–á€­á€¯á€„á€º*'):
    bio_line = f"\nðŸ“ á€¡á€€á€¼á€±á€¬á€„á€ºá€¸ : {safe(tp,'bio')}" if (tp or {}).get('bio') else ''
    return (
        f"{title}\n\n"
        f"ðŸ“› á€”á€¬á€™á€Šá€º   : {safe(tp,'name')}\n"
        f"ðŸŽ‚ á€¡á€žá€€á€º   : {safe(tp,'age')} á€”á€¾á€…á€º\n"
        f"ðŸ”® á€›á€¬á€žá€®   : {safe(tp,'zodiac')}\n"
        f"ðŸ“ á€™á€¼á€­á€¯á€·    : {safe(tp,'city')}\n"
        f"ðŸŽ¨ á€á€«á€žá€”á€¬  : {safe(tp,'hobby')}\n"
        f"ðŸ’¼ á€¡á€œá€¯á€•á€º   : {safe(tp,'job')}\n"
        f"ðŸŽµ á€žá€®á€á€»á€„á€ºá€¸  : {safe(tp,'song')}"
        f"{bio_line}\n"
        f"âš§ á€œá€­á€„á€º    : {safe(tp,'gender')}\n"
        f"ðŸ’‘ á€›á€¾á€¬á€–á€½á€±  : {safe(tp,'looking_gender')} / {safe(tp,'looking_zodiac','Any')}"
    )

def stats_text():
    s = db_stats()
    return (
        f"ðŸ“Š *Yay Zat Bot â€” á€…á€¬á€›á€„á€ºá€¸á€¡á€„á€ºá€¸*\n\n"
        f"ðŸ‘¥ á€…á€¯á€…á€¯á€•á€±á€«á€„á€ºá€¸       : *{s['total']}* á€šá€±á€¬á€€á€º\n"
        f"â™‚ï¸ á€€á€»á€¬á€¸            : {s['male']} á€šá€±á€¬á€€á€º\n"
        f"â™€ï¸ á€™               : {s['female']} á€šá€±á€¬á€€á€º\n"
        f"ðŸ“¸ á€“á€¬á€á€ºá€•á€¯á€¶á€•á€«       : {s['photo']} á€šá€±á€¬á€€á€º\n"
        f"â° Update          : {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )

user_reg = {}   # temp registration state

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ›¡  MENU TEXT SET â€” Registration á€‘á€² menu button á€™á€•á€„á€ºá€†á€„á€ºá€–á€­á€¯á€·
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
MENU_TEXTS = {
    "ðŸ” á€–á€°á€¸á€…á€¬á€›á€¾á€¬á€™á€Šá€º",
    "ðŸ‘¤ á€€á€­á€¯á€šá€·á€ºá€•á€›á€­á€¯á€–á€­á€¯á€„á€º",
    "â„¹ï¸ á€¡á€€á€°á€¡á€Šá€®",
    "ðŸ”„ Profile á€•á€¼á€”á€ºá€œá€¯á€•á€º",
    "ðŸ“Š á€…á€¬á€›á€„á€ºá€¸á€¡á€„á€ºá€¸",
    "ðŸ›  Admin Panel",
}

def _skip(msg):
    """Registration step á€€á€»á€±á€¬á€ºá€›á€™á€Šá€·á€º á€¡á€á€¼á€±á€¡á€”á€±:
       /skip command (á€žá€­á€¯á€·) Menu button text (á€žá€­á€¯á€·) á€™á€Šá€ºá€žá€Šá€·á€º command á€™á€†á€­á€¯"""
    if not msg.text:
        return False
    txt = msg.text.strip()
    return txt == '/skip' or txt in MENU_TEXTS or txt.startswith('/')

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸš€  /start
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@bot.message_handler(commands=['start'])
def start_bot(message):
    uid   = message.chat.id
    total = db_count()
    if db_get(uid):
        bot.send_message(uid,
            f"âœ¨ *á€€á€¼á€­á€¯á€†á€­á€¯á€•á€«á€á€šá€º!* âœ¨\n\n"
            f"ðŸ‘¥ á€œá€€á€ºá€›á€¾á€­ á€¡á€žá€¯á€¶á€¸á€•á€¼á€¯á€žá€° : *{total}* á€šá€±á€¬á€€á€º\n\n"
            f"á€á€œá€¯á€á€ºá€™á€»á€¬á€¸á€”á€¾á€­á€•á€ºá€•á€¼á€®á€¸ á€¡á€žá€¯á€¶á€¸á€•á€¼á€¯á€”á€­á€¯á€„á€ºá€•á€«á€•á€¼á€® ðŸ‘‡",
            parse_mode="Markdown", reply_markup=kb(uid))
        return

    try:
        tg = message.from_user.username or message.from_user.first_name or str(uid)
        fn = message.from_user.first_name or ''
        ln = message.from_user.last_name  or ''
    except:
        tg = fn = ln = str(uid)

    notify_admin(
        f"ðŸ†• *á€¡á€žá€¯á€¶á€¸á€•á€¼á€¯á€žá€°á€žá€…á€º á€…á€á€„á€ºá€žá€¯á€¶á€¸á€”á€±á€•á€«á€•á€¼á€®!*\n\n"
        f"ðŸ‘¤ {fn} {ln}\nðŸ”— @{tg}\nðŸ†” `{uid}`\n"
        f"ðŸ‘¥ á€™á€¾á€á€ºá€•á€¯á€¶á€á€„á€ºá€•á€¼á€®á€¸á€žá€¬á€¸ : {total} á€šá€±á€¬á€€á€º\n"
        f"â° {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    )
    user_reg[uid] = {}
    msg = bot.send_message(uid,
        f"âœ¨ *Yay Zat Zodiac á€™á€¾ á€€á€¼á€­á€¯á€†á€­á€¯á€•á€«á€á€šá€º!* âœ¨\n\n"
        f"ðŸ‘¥ á€¡á€žá€¯á€¶á€¸á€•á€¼á€¯á€žá€° : *{total}* á€šá€±á€¬á€€á€º\n\n"
        f"á€–á€°á€¸á€…á€¬á€›á€¾á€„á€ºá€€á€­á€¯á€›á€¾á€¬á€–á€½á€±á€–á€­á€¯á€· á€™á€±á€¸á€á€½á€”á€ºá€¸á€œá€±á€¸á€á€½á€± á€–á€¼á€±á€•á€±á€¸á€•á€« ðŸ™\n"
        f"_( /skip â€” á€€á€»á€±á€¬á€ºá€á€»á€„á€ºá€á€²á€·á€™á€±á€¸á€á€½á€”á€ºá€¸á€¡á€á€½á€€á€º )_\n\n"
        f"ðŸ“› *á€”á€¬á€™á€Šá€º (á€žá€­á€¯á€·) á€¡á€™á€Šá€ºá€á€¾á€€á€º* á€€á€­á€¯ á€›á€­á€¯á€€á€ºá€‘á€Šá€·á€ºá€•á€«-",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, reg_name)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ“  REGISTRATION STEPS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def reg_name(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['name'] = message.text.strip()
    msg = bot.send_message(uid, "ðŸŽ‚ á€¡á€žá€€á€º á€˜á€šá€ºá€œá€±á€¬á€€á€ºá€œá€²? (/skip)-")
    bot.register_next_step_handler(msg, reg_age)

def reg_age(message):
    uid = message.chat.id
    if not _skip(message):
        if message.text.strip().isdigit():
            user_reg.setdefault(uid, {})['age'] = message.text.strip()
        else:
            msg = bot.send_message(uid, "âš ï¸ á€‚á€á€”á€ºá€¸á€žá€¬ á€›á€­á€¯á€€á€ºá€•á€« (á€¥á€•á€™á€¬ 25)- (/skip)")
            bot.register_next_step_handler(msg, reg_age)
            return
    m = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for z in ZODIACS: m.add(z)
    m.add('/skip')
    msg = bot.send_message(uid, "ðŸ”® á€›á€¬á€žá€®á€á€½á€„á€ºá€€á€­á€¯ á€›á€½á€±á€¸á€•á€«-", reply_markup=m)
    bot.register_next_step_handler(msg, reg_zodiac)

def reg_zodiac(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['zodiac'] = message.text.strip()
    msg = bot.send_message(uid, "ðŸ“ á€”á€±á€‘á€­á€¯á€„á€ºá€á€²á€· á€™á€¼á€­á€¯á€· (á€¥á€•á€™á€¬ Mandalay)- (/skip)",
                           reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, reg_city)

def reg_city(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['city'] = message.text.strip()
    msg = bot.send_message(uid, "ðŸŽ¨ á€á€«á€žá€”á€¬ á€˜á€¬á€•á€«á€œá€²? (á€¥á€•á€™á€¬ á€á€›á€®á€¸á€žá€½á€¬á€¸, á€‚á€®á€)- (/skip)")
    bot.register_next_step_handler(msg, reg_hobby)

def reg_hobby(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['hobby'] = message.text.strip()
    msg = bot.send_message(uid, "ðŸ’¼ á€¡á€œá€¯á€•á€ºá€¡á€€á€­á€¯á€„á€º?- (/skip)")
    bot.register_next_step_handler(msg, reg_job)

def reg_job(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['job'] = message.text.strip()
    msg = bot.send_message(uid, "ðŸŽµ á€¡á€€á€¼á€­á€¯á€€á€ºá€†á€¯á€¶á€¸ á€žá€®á€á€»á€„á€ºá€¸ á€á€…á€ºá€•á€¯á€’á€º?- (/skip)")
    bot.register_next_step_handler(msg, reg_song)

def reg_song(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['song'] = message.text.strip()
    msg = bot.send_message(uid,
        "ðŸ“ *á€™á€­á€™á€­á€¡á€€á€¼á€±á€¬á€„á€ºá€¸ á€¡á€á€­á€¯á€á€»á€¯á€¶á€¸* á€›á€±á€¸á€•á€¼á€•á€«\n"
        "_(á€¥á€•á€™á€¬: á€†á€±á€¸á€€á€»á€±á€¬á€„á€ºá€¸á€žá€¬á€¸, á€‚á€®á€á€á€½á€„á€ºá€™á€¾á€®á€á€²á€žá€°, á€•á€¼á€±á€¬á€†á€­á€¯á€›á€„á€ºá€¸á€”á€¾á€®á€¸á€á€»á€„á€ºá€žá€°)_- (/skip)",
        parse_mode="Markdown")
    bot.register_next_step_handler(msg, reg_bio)

def reg_bio(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['bio'] = message.text.strip()
    m = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    m.add('Male', 'Female', '/skip')
    msg = bot.send_message(uid, "âš§ á€žá€„á€·á€ºá€œá€­á€„á€ºá€€á€­á€¯ á€›á€½á€±á€¸á€•á€«-", reply_markup=m)
    bot.register_next_step_handler(msg, reg_gender)

def reg_gender(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['gender'] = message.text.strip()
    m = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    m.add('Male', 'Female', 'Both', '/skip')
    msg = bot.send_message(uid, "ðŸ’‘ á€›á€¾á€¬á€–á€½á€±á€”á€±á€á€²á€· á€œá€­á€„á€ºá€€á€­á€¯ á€›á€½á€±á€¸á€•á€«-", reply_markup=m)
    bot.register_next_step_handler(msg, reg_looking_gender)

def reg_looking_gender(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['looking_gender'] = message.text.strip()
    m = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for z in ZODIACS: m.add(z)
    m.add('Any', '/skip')
    msg = bot.send_message(uid, "ðŸ”® á€›á€¾á€¬á€–á€½á€±á€”á€±á€á€²á€· á€›á€¬á€žá€®á€á€½á€„á€ºá€€á€­á€¯ á€›á€½á€±á€¸á€•á€«-", reply_markup=m)
    bot.register_next_step_handler(msg, reg_looking_zodiac)

def reg_looking_zodiac(message):
    uid = message.chat.id
    if not _skip(message):
        user_reg.setdefault(uid, {})['looking_zodiac'] = message.text.strip()
    msg = bot.send_message(uid,
        "ðŸ“¸ Profile á€“á€¬á€á€ºá€•á€¯á€¶ á€•á€±á€¸á€•á€­á€¯á€·á€•á€« _(á€™á€œá€­á€¯á€•á€«á€€ /skip)_",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, reg_photo)

def reg_photo(message):
    uid    = message.chat.id
    is_new = uid not in [u['user_id'] for u in db_all()] or db_get(uid) is None

    if message.content_type == 'photo':
        user_reg.setdefault(uid, {})['photo'] = message.photo[-1].file_id
    elif not _skip(message):
        # á€“á€¬á€á€ºá€•á€¯á€¶ á€™á€Ÿá€¯á€á€ºá€˜á€² text á€›á€­á€¯á€€á€ºá€›á€„á€º á€•á€¼á€”á€ºá€á€±á€¬á€„á€ºá€¸á€žá€Šá€º
        msg = bot.send_message(uid, "âš ï¸ á€“á€¬á€á€ºá€•á€¯á€¶á€žá€¬ á€•á€±á€¸á€•á€­á€¯á€·á€•á€« (á€žá€­á€¯á€·) /skip á€Ÿá€¯á€›á€­á€¯á€€á€ºá€•á€«-")
        bot.register_next_step_handler(msg, reg_photo)
        return

    data = user_reg.pop(uid, {})
    # is_new á€€á€­á€¯ db á€…á€…á€ºá€•á€¼á€®á€¸á€™á€¾ á€™á€¾á€á€ºá€šá€°á€•á€«
    is_new = db_get(uid) is None
    db_save(uid, data)
    total = db_count()
    bot.send_message(uid,
        f"âœ… Profile {'á€á€Šá€ºá€†á€±á€¬á€€á€º' if is_new else 'á€•á€¼á€„á€ºá€†á€„á€º'} á€•á€¼á€®á€¸á€•á€«á€•á€¼á€®! ðŸŽ‰\n\n"
        f"ðŸ‘¥ á€œá€€á€ºá€›á€¾á€­ á€¡á€žá€¯á€¶á€¸á€•á€¼á€¯á€žá€° : *{total}* á€šá€±á€¬á€€á€º\n\n"
        f"á€á€œá€¯á€á€ºá€™á€»á€¬á€¸ á€”á€¾á€­á€•á€ºá€•á€¼á€®á€¸ á€¡á€žá€¯á€¶á€¸á€•á€¼á€¯á€”á€­á€¯á€„á€ºá€•á€«á€•á€¼á€® ðŸ‘‡",
        parse_mode="Markdown", reply_markup=kb(uid))
    if is_new:
        notify_admin(
            f"ðŸŽ‰ *á€™á€¾á€á€ºá€•á€¯á€¶á€á€„á€ºá€á€¼á€„á€ºá€¸ á€•á€¼á€®á€¸á€™á€¼á€±á€¬á€€á€ºá€•á€«á€•á€¼á€®!*\n\n"
            f"ðŸ†” `{uid}` â€” ðŸ“› {safe(data,'name')}\n"
            f"ðŸ‘¥ á€…á€¯á€…á€¯á€•á€±á€«á€„á€ºá€¸ : *{total}* á€šá€±á€¬á€€á€º\n"
            f"â° {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ‘¤  MY PROFILE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def show_my_profile(message):
    uid = message.chat.id
    tp  = db_get(uid)
    if not tp:
        bot.send_message(uid, "Profile á€™á€›á€¾á€­á€žá€±á€¸á€•á€«á‹ /start á€€á€­á€¯á€”á€¾á€­á€•á€ºá€•á€«á‹", reply_markup=kb(uid))
        return
    text = f"ðŸ“Š á€¡á€žá€¯á€¶á€¸á€•á€¼á€¯á€žá€° : *{db_count()}* á€šá€±á€¬á€€á€º\n\n" + fmt_profile(tp)
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("ðŸ“› á€”á€¬á€™á€Šá€º",  callback_data="edit_name"),
          InlineKeyboardButton("ðŸŽ‚ á€¡á€žá€€á€º",   callback_data="edit_age"))
    m.row(InlineKeyboardButton("ðŸ”® á€›á€¬á€žá€®",   callback_data="edit_zodiac"),
          InlineKeyboardButton("ðŸ“ á€™á€¼á€­á€¯á€·",   callback_data="edit_city"))
    m.row(InlineKeyboardButton("ðŸŽ¨ á€á€«á€žá€”á€¬", callback_data="edit_hobby"),
          InlineKeyboardButton("ðŸ’¼ á€¡á€œá€¯á€•á€º",  callback_data="edit_job"))
    m.row(InlineKeyboardButton("ðŸŽµ á€žá€®á€á€»á€„á€ºá€¸", callback_data="edit_song"),
          InlineKeyboardButton("ðŸ“ Bio",    callback_data="edit_bio"))
    m.row(InlineKeyboardButton("ðŸ“¸ á€“á€¬á€á€ºá€•á€¯á€¶", callback_data="edit_photo"))
    m.row(InlineKeyboardButton("ðŸ”„ á€¡á€€á€¯á€”á€ºá€•á€¼á€”á€ºá€œá€¯á€•á€º", callback_data="edit_all"))
    m.row(InlineKeyboardButton("ðŸ—‘ Profile á€–á€»á€€á€º",   callback_data="delete_profile"))
    if tp.get('photo'):
        bot.send_photo(uid, tp['photo'], caption=text, reply_markup=m, parse_mode="Markdown")
    else:
        bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ”  FIND MATCH
#     â€¢ Gender  â†’ strict always
#     â€¢ Zodiac  â†’ preferred first, fallback to others
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def run_find_match(message):
    uid = message.chat.id
    me  = db_get(uid)
    if not me:
        bot.send_message(uid, "/start á€€á€­á€¯á€”á€¾á€­á€•á€ºá€•á€¼á€®á€¸ Profile á€¡á€›á€„á€ºá€á€Šá€ºá€†á€±á€¬á€€á€ºá€•á€«á‹", reply_markup=kb(uid))
        return
    if not check_channel(uid):
        m = InlineKeyboardMarkup()
        m.add(InlineKeyboardButton("ðŸ“¢ Channel Join á€™á€Šá€º", url=CHANNEL_LINK))
        bot.send_message(uid, "âš ï¸ Channel á€€á€­á€¯ á€¡á€›á€„á€º Join á€•á€±á€¸á€•á€«á‹", reply_markup=m)
        return

    seen     = db_seen_get(uid)
    reported = db_reported_ids_by(uid)
    exclude  = seen | reported | {uid}

    looking_g = (me.get('looking_gender') or '').strip()
    looking_z = (me.get('looking_zodiac')  or '').strip()

    all_users = db_all()

    def get_eligible(exclude_ids):
        result = []
        for u in all_users:
            if u['user_id'] in exclude_ids: continue
            if looking_g and looking_g not in ('Both', 'Any'):
                if (u.get('gender') or '').strip() != looking_g: continue
            result.append(u)
        return result

    eligible = get_eligible(exclude)

    if not eligible:
        if seen:
            # seen clear á€•á€¼á€®á€¸á€”á€±á€¬á€€á€º eligible á€›á€¾á€­á€™á€›á€¾á€­ á€¡á€›á€„á€ºá€…á€…á€º
            db_seen_clear(uid)
            exclude_after_clear = reported | {uid}
            eligible_after = get_eligible(exclude_after_clear)
            if not eligible_after:
                bot.send_message(uid,
                    "ðŸ˜” á€œá€±á€¬á€œá€±á€¬á€†á€šá€º á€žá€„á€·á€ºá€¡á€á€½á€€á€º á€€á€­á€¯á€€á€ºá€Šá€®á€žá€° á€™á€›á€¾á€­á€žá€±á€¸á€•á€«á‹\n"
                    "á€”á€±á€¬á€€á€ºá€™á€¾ á€•á€¼á€”á€ºá€€á€¼á€­á€¯á€¸á€…á€¬á€¸á€€á€¼á€Šá€·á€ºá€•á€«á‹", reply_markup=kb(uid))
                return
            bot.send_message(uid, "ðŸ”„ á€€á€¼á€Šá€·á€ºá€•á€¼á€®á€¸á€žá€¬á€¸á€™á€»á€¬á€¸ á€€á€¯á€”á€ºá€žá€–á€¼á€„á€·á€º á€•á€¼á€”á€ºá€…á€•á€«á€•á€¼á€®...")
            eligible = eligible_after
        else:
            bot.send_message(uid,
                "ðŸ˜” á€œá€±á€¬á€œá€±á€¬á€†á€šá€º á€žá€„á€·á€ºá€¡á€á€½á€€á€º á€€á€­á€¯á€€á€ºá€Šá€®á€žá€° á€™á€›á€¾á€­á€žá€±á€¸á€•á€«á‹\n"
                "á€”á€±á€¬á€€á€ºá€™á€¾ á€•á€¼á€”á€ºá€€á€¼á€­á€¯á€¸á€…á€¬á€¸á€€á€¼á€Šá€·á€ºá€•á€«á‹", reply_markup=kb(uid))
            return

    # zodiac preferred first, then fallback
    if looking_z and looking_z not in ('Any', ''):
        pref    = [u for u in eligible if (u.get('zodiac') or '') == looking_z]
        fallback = [u for u in eligible if (u.get('zodiac') or '') != looking_z]
        ordered = pref + fallback
    else:
        ordered = eligible

    target = ordered[0]
    tid    = target['user_id']
    db_seen_add(uid, tid)

    note = ''
    if looking_z and looking_z not in ('Any', '') and (target.get('zodiac') or '') != looking_z:
        note = f"\n_( {looking_z} á€€á€­á€¯ á€™á€á€½á€±á€·á€žá€±á€¬á€€á€¼á€±á€¬á€„á€·á€º á€¡á€”á€®á€¸á€…á€•á€ºá€†á€¯á€¶á€¸á€•á€¼á€•á€±á€¸á€”á€±á€•á€«á€žá€Šá€º )_"

    text = fmt_profile(target, title=f"ðŸŽ¯ *á€™á€­á€á€ºá€†á€½á€±á€”á€²á€· á€€á€­á€¯á€€á€ºá€Šá€®á€”á€­á€¯á€„á€ºá€™á€šá€·á€ºá€žá€°*{note}")
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("â¤ï¸ Like",   callback_data=f"like_{tid}"),
          InlineKeyboardButton("â­ Skip",   callback_data="skip"),
          InlineKeyboardButton("ðŸš© Report", callback_data=f"report_{tid}"))

    if target.get('photo'):
        bot.send_photo(uid, target['photo'], caption=text, reply_markup=m, parse_mode="Markdown")
    else:
        bot.send_message(uid, text, reply_markup=m, parse_mode="Markdown")

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ”„  RESET  â„¹ï¸ HELP  ðŸ“Š STATS  ðŸ›  ADMIN
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def run_reset(message):
    uid      = message.chat.id
    existing = db_get(uid)
    user_reg[uid] = dict(existing) if existing else {}
    msg = bot.send_message(uid,
        "ðŸ”„ *Profile á€•á€¼á€”á€ºá€œá€¯á€•á€ºá€™á€Šá€º*\n\nðŸ“› á€”á€¬á€™á€Šá€º á€›á€­á€¯á€€á€ºá€‘á€Šá€·á€ºá€•á€«- (/skip á€”á€²á€· á€€á€»á€±á€¬á€ºá€”á€­á€¯á€„á€º)",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, reg_name)

def show_help(message):
    bot.send_message(message.chat.id,
        "â„¹ï¸ *Yay Zat Bot â€” á€¡á€€á€°á€¡á€Šá€®*\n\n"
        "ðŸ” *á€–á€°á€¸á€…á€¬á€›á€¾á€¬á€™á€Šá€º* â€” á€€á€­á€¯á€€á€ºá€Šá€®á€”á€­á€¯á€„á€ºá€™á€šá€·á€ºá€žá€° á€›á€¾á€¬á€•á€«\n"
        "ðŸ‘¤ *á€€á€­á€¯á€šá€·á€ºá€•á€›á€­á€¯á€–á€­á€¯á€„á€º* â€” Profile á€€á€¼á€Šá€·á€º/á€•á€¼á€„á€ºá€•á€«\n"
        "ðŸ”„ *Profile á€•á€¼á€”á€ºá€œá€¯á€•á€º* â€” Profile á€¡á€žá€…á€ºá€•á€¼á€”á€ºá€–á€¼á€Šá€·á€ºá€•á€«\n\n"
        "*Commands*\n"
        "/start â€” á€…á€á€„á€ºá€™á€¾á€á€ºá€•á€¯á€¶á€á€„á€ºá€•á€«\n"
        "/reset â€” Profile á€•á€¼á€”á€ºá€œá€¯á€•á€ºá€•á€«\n"
        "/deleteprofile â€” Profile á€–á€»á€€á€ºá€•á€«\n\n"
        "á€•á€¼á€¿á€”á€¬á€™á€»á€¬á€¸ Admin á€€á€­á€¯ á€†á€€á€ºá€žá€½á€šá€ºá€•á€«á‹",
        parse_mode="Markdown", reply_markup=kb(message.chat.id))

def show_stats(message):
    uid = message.chat.id
    if uid != ADMIN_ID:
        bot.send_message(uid, "â›” Admin á€žá€¬ á€€á€¼á€Šá€·á€ºá€›á€¾á€¯á€”á€­á€¯á€„á€ºá€•á€«á€žá€Šá€ºà¥¤")
        return
    bot.send_message(ADMIN_ID, stats_text(), parse_mode="Markdown", reply_markup=admin_kb())

def show_admin_panel(message):
    if message.chat.id != ADMIN_ID: return
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("ðŸ“Š Full Stats", callback_data="adm_stats"),
          InlineKeyboardButton("ðŸ‘¥ User List",  callback_data="adm_userlist"))
    m.row(InlineKeyboardButton("ðŸ“¢ Broadcast",  callback_data="adm_broadcast"),
          InlineKeyboardButton("ðŸ—‘ User á€–á€»á€€á€º",  callback_data="adm_deluser"))
    bot.send_message(ADMIN_ID, "ðŸ›  *Admin Panel*", parse_mode="Markdown", reply_markup=m)

def _broadcast_step(message):
    if message.text == '/cancel':
        bot.send_message(ADMIN_ID, "á€•á€šá€ºá€–á€»á€€á€ºá€•á€¼á€®á€¸á€•á€«á€•á€¼á€®á‹")
        return
    ok = fail = 0
    for uid in db_all_ids():
        try:
            bot.send_message(uid,
                f"ðŸ“¢ *Admin á€™á€¾ á€žá€á€„á€ºá€¸á€…á€€á€¬á€¸*\n\n{message.text}",
                parse_mode="Markdown")
            ok += 1
        except:
            fail += 1
    bot.send_message(ADMIN_ID,
        f"âœ… Broadcast á€•á€¼á€®á€¸á€•á€«á€•á€¼á€®!\nâœ”ï¸ {ok} á€šá€±á€¬á€€á€º á€›á€±á€¬á€€á€ºá€•á€«á€žá€Šá€º\nâŒ {fail} á€šá€±á€¬á€€á€º á€™á€›á€±á€¬á€€á€ºá€•á€«")

def _deluser_step(message):
    if message.text == '/cancel':
        bot.send_message(ADMIN_ID, "á€•á€šá€ºá€–á€»á€€á€ºá€•á€¼á€®á€¸á€•á€«á€•á€¼á€®á‹")
        return
    try:
        uid = int(message.text.strip())
        if db_get(uid):
            db_delete(uid)
            bot.send_message(ADMIN_ID, f"âœ… User `{uid}` á€–á€»á€€á€ºá€•á€¼á€®á€¸á€•á€«á€•á€¼á€®á‹", parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_ID, "âš ï¸ á€‘á€­á€¯ ID á€™á€á€½á€±á€·á€•á€«á‹")
    except ValueError:
        bot.send_message(ADMIN_ID, "âš ï¸ ID á€‚á€á€”á€ºá€¸á€žá€¬ á€›á€­á€¯á€€á€ºá€•á€«á‹")

def save_field(message, field):
    uid = message.chat.id
    if field == 'photo':
        if message.content_type != 'photo':
            msg = bot.send_message(uid, "âš ï¸ á€“á€¬á€á€ºá€•á€¯á€¶á€žá€¬ á€•á€±á€¸á€•á€­á€¯á€·á€•á€«á‹")
            bot.register_next_step_handler(msg, save_field, field)
            return
        db_update(uid, 'photo', message.photo[-1].file_id)
    else:
        if not message.text or not message.text.strip():
            msg = bot.send_message(uid, "âš ï¸ á€—á€œá€¬á€™á€‘á€¬á€¸á€•á€«á€”á€²á€·-")
            bot.register_next_step_handler(msg, save_field, field)
            return
        db_update(uid, field, message.text.strip())
    bot.send_message(uid, "âœ… á€•á€¼á€„á€ºá€†á€„á€ºá€™á€¾á€¯ á€¡á€±á€¬á€„á€ºá€™á€¼á€„á€ºá€•á€«á€žá€Šá€º!", reply_markup=kb(uid))

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ”˜  MENU ROUTER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
MENU = {
    "ðŸ” á€–á€°á€¸á€…á€¬á€›á€¾á€¬á€™á€Šá€º"   : run_find_match,
    "ðŸ‘¤ á€€á€­á€¯á€šá€·á€ºá€•á€›á€­á€¯á€–á€­á€¯á€„á€º" : show_my_profile,
    "â„¹ï¸ á€¡á€€á€°á€¡á€Šá€®"        : show_help,
    "ðŸ”„ Profile á€•á€¼á€”á€ºá€œá€¯á€•á€º": run_reset,
    "ðŸ“Š á€…á€¬á€›á€„á€ºá€¸á€¡á€„á€ºá€¸"     : show_stats,
    "ðŸ›  Admin Panel"     : show_admin_panel,
}

@bot.message_handler(func=lambda m: m.text in MENU)
def menu_router(message):
    MENU[message.text](message)

@bot.message_handler(commands=['reset'])
def cmd_reset(m): run_reset(m)

@bot.message_handler(commands=['stats'])
def cmd_stats(m): show_stats(m)

@bot.message_handler(commands=['myprofile'])
def cmd_myprofile(m): show_my_profile(m)

@bot.message_handler(commands=['deleteprofile'])
def cmd_deleteprofile(message):
    uid = message.chat.id
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("âœ… á€Ÿá€¯á€á€ºá€á€šá€º á€–á€»á€€á€ºá€™á€Šá€º", callback_data="confirm_delete"),
          InlineKeyboardButton("âŒ á€™á€–á€»á€€á€ºá€á€±á€¬á€·á€•á€«",      callback_data="cancel_delete"))
    bot.send_message(uid, "âš ï¸ Profile á€€á€­á€¯ á€–á€»á€€á€ºá€™á€¾á€¬ á€žá€±á€á€»á€¬á€•á€«á€žá€œá€¬á€¸?", reply_markup=m)

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸ“ž  CALLBACK QUERY
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
@bot.callback_query_handler(func=lambda call: True)
def on_callback(call):
    uid = call.message.chat.id
    d   = call.data

    # â”€â”€ Edit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if d.startswith("edit_"):
        field = d[5:]
        try: bot.delete_message(uid, call.message.message_id)
        except: pass

        if field == "all":
            existing = db_get(uid)
            user_reg[uid] = dict(existing) if existing else {}
            # âœ… FIX: send_message return value á€€á€­á€¯ register_next_step_handler á€™á€¾á€¬ á€žá€¯á€¶á€¸á€•á€«
            msg = bot.send_message(uid,
                "ðŸ”„ Profile á€•á€¼á€”á€ºá€á€Šá€ºá€†á€±á€¬á€€á€ºá€™á€Šá€º\nðŸ“› á€”á€¬á€™á€Šá€º á€›á€­á€¯á€€á€ºá€‘á€Šá€·á€ºá€•á€«- (/skip)",
                reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, reg_name)

        elif field == "photo":
            msg = bot.send_message(uid, "ðŸ“¸ á€“á€¬á€á€ºá€•á€¯á€¶á€¡á€žá€…á€º á€•á€±á€¸á€•á€­á€¯á€·á€•á€«-",
                                   reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_field, 'photo')

        else:
            labels = {
                'name'          : 'á€”á€¬á€™á€Šá€º',
                'age'           : 'á€¡á€žá€€á€º',
                'zodiac'        : 'á€›á€¬á€žá€®',
                'city'          : 'á€™á€¼á€­á€¯á€·',
                'hobby'         : 'á€á€«á€žá€”á€¬',
                'job'           : 'á€¡á€œá€¯á€•á€º',
                'song'          : 'á€žá€®á€á€»á€„á€ºá€¸',
                'bio'           : 'Bio',
                'gender'        : 'á€œá€­á€„á€º',
                'looking_gender': 'á€›á€¾á€¬á€–á€½á€±á€™á€Šá€·á€ºá€œá€­á€„á€º',
                'looking_zodiac': 'á€›á€¾á€¬á€–á€½á€±á€™á€Šá€·á€ºá€›á€¬á€žá€®',
            }
            msg = bot.send_message(uid,
                f"ðŸ“ {labels.get(field, field)} á€¡á€žá€…á€º á€›á€­á€¯á€€á€ºá€‘á€Šá€·á€ºá€•á€«-",
                reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, save_field, field)

    # â”€â”€ Delete â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif d == "delete_profile":
        m = InlineKeyboardMarkup()
        m.row(InlineKeyboardButton("âœ… á€Ÿá€¯á€á€ºá€á€šá€º á€–á€»á€€á€ºá€™á€Šá€º", callback_data="confirm_delete"),
              InlineKeyboardButton("âŒ á€™á€–á€»á€€á€ºá€á€±á€¬á€·á€•á€«",      callback_data="cancel_delete"))
        try: bot.edit_message_reply_markup(uid, call.message.message_id, reply_markup=m)
        except: pass

    elif d == "confirm_delete":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        db_delete(uid)
        bot.send_message(uid,
            "ðŸ—‘ Profile á€–á€»á€€á€ºá€•á€¼á€®á€¸á€•á€«á€•á€¼á€®á‹\n/start á€”á€¾á€­á€•á€ºá€•á€¼á€®á€¸ á€•á€¼á€”á€ºá€™á€¾á€á€ºá€•á€¯á€¶á€á€„á€ºá€”á€­á€¯á€„á€ºá€•á€«á€žá€Šá€ºá‹",
            reply_markup=ReplyKeyboardRemove())

    elif d == "cancel_delete":
        bot.answer_callback_query(call.id, "á€™á€–á€»á€€á€ºá€á€±á€¬á€·á€•á€«á‹")
        try: bot.delete_message(uid, call.message.message_id)
        except: pass

    # â”€â”€ Skip â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif d == "skip":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        run_find_match(call.message)

    # â”€â”€ Like â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif d.startswith("like_"):
        tid = int(d[5:])
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        if not check_channel(uid):
            bot.answer_callback_query(call.id, "âš ï¸ Channel á€€á€­á€¯ Join á€•á€«!", show_alert=True)
            return
        me_data    = db_get(uid) or {}
        liker_name = safe(me_data, 'name', 'á€á€…á€ºá€šá€±á€¬á€€á€º')
        like_m = InlineKeyboardMarkup()
        like_m.row(InlineKeyboardButton("âœ… á€œá€€á€ºá€á€¶á€™á€Šá€º", callback_data=f"accept_{uid}"),
                   InlineKeyboardButton("âŒ á€„á€¼á€„á€ºá€¸á€™á€Šá€º",  callback_data="decline"))
        like_caption = (
            f"ðŸ’Œ *'{liker_name}'* á€€ á€žá€„á€·á€ºá€€á€­á€¯ Like á€œá€¯á€•á€ºá€‘á€¬á€¸á€•á€«á€á€šá€º!\n\n"
            + fmt_profile(me_data, title='ðŸ‘¤ *á€žá€°/á€žá€°á€™ á€›á€²á€· Profile*')
        )
        try:
            if me_data.get('photo'):
                bot.send_photo(tid, me_data['photo'], caption=like_caption,
                               reply_markup=like_m, parse_mode="Markdown")
            else:
                bot.send_message(tid, like_caption, reply_markup=like_m, parse_mode="Markdown")
            bot.send_message(uid,
                "â¤ï¸ Like á€œá€¯á€•á€ºá€œá€­á€¯á€€á€ºá€•á€«á€•á€¼á€®!\ná€á€…á€ºá€–á€€á€ºá€€ á€œá€€á€ºá€á€¶á€›á€„á€º á€¡á€€á€¼á€±á€¬á€„á€ºá€¸á€€á€¼á€¬á€¸á€•á€±á€¸á€•á€«á€™á€šá€º ðŸ˜Š",
                reply_markup=kb(uid))
        except:
            bot.send_message(uid,
                "âš ï¸ á€á€…á€ºá€–á€€á€ºá€œá€°á€™á€¾á€¬ Bot á€€á€­á€¯ Block á€‘á€¬á€¸á€žá€–á€¼á€„á€·á€º á€•á€±á€¸á€•á€­á€¯á€·á€™á€›á€•á€«á‹",
                reply_markup=kb(uid))

    # â”€â”€ Accept â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif d.startswith("accept_"):
        liker_id = int(d[7:])
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        notify_admin(
            f"ðŸ’– *New Match!*\n\n"
            f"[User A](tg://user?id={uid}) + [User B](tg://user?id={liker_id})\n"
            f"â° {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        for a, b in [(uid, liker_id), (liker_id, uid)]:
            try:
                bot.send_message(a,
                    f"ðŸ’– *Match á€–á€¼á€…á€ºá€žá€½á€¬á€¸á€•á€«á€•á€¼á€®!*\n\n"
                    f"[á€’á€®á€™á€¾á€¬á€”á€¾á€­á€•á€ºá€•á€¼á€®á€¸](tg://user?id={b}) á€…á€€á€¬á€¸á€•á€¼á€±á€¬á€”á€­á€¯á€„á€ºá€•á€«á€•á€¼á€® ðŸŽ‰",
                    parse_mode="Markdown", reply_markup=kb(a))
            except:
                pass

    # â”€â”€ Decline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif d == "decline":
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        bot.send_message(uid, "âŒ á€„á€¼á€„á€ºá€¸á€†á€”á€ºá€œá€­á€¯á€€á€ºá€•á€«á€•á€¼á€®á‹", reply_markup=kb(uid))

    # â”€â”€ Report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif d.startswith("report_"):
        tid = int(d[7:])
        db_report_add(uid, tid)
        bot.answer_callback_query(call.id, "ðŸš© Report á€œá€¯á€•á€ºá€•á€¼á€®á€¸á€•á€«á€•á€¼á€®á‹", show_alert=True)
        try: bot.delete_message(uid, call.message.message_id)
        except: pass
        notify_admin(
            f"ðŸš© *User Report*\n\n"
            f"Reporter : `{uid}` {safe(db_get(uid),'name')}\n"
            f"Reported : `{tid}` {safe(db_get(tid),'name')}\n"
            f"â° {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        run_find_match(call.message)

    # â”€â”€ Admin Callbacks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    elif d == "adm_stats" and uid == ADMIN_ID:
        bot.send_message(ADMIN_ID, stats_text(), parse_mode="Markdown")

    elif d == "adm_broadcast" and uid == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID, "ðŸ“¢ Message á€€á€­á€¯ á€›á€­á€¯á€€á€ºá€‘á€Šá€·á€ºá€•á€« (/cancel-á€•á€šá€ºá€–á€»á€€á€º)-")
        bot.register_next_step_handler(msg, _broadcast_step)

    elif d == "adm_userlist" and uid == ADMIN_ID:
        rows  = db_all()[:30]
        lines = [f"{i}. {safe(u,'name')} â€” `{u['user_id']}`" for i, u in enumerate(rows, 1)]
        bot.send_message(ADMIN_ID,
            "ðŸ‘¥ *User List (á€•á€‘á€™ 30)*\n\n" + ("\n".join(lines) if lines else "á€™á€›á€¾á€­á€žá€±á€¸"),
            parse_mode="Markdown")

    elif d == "adm_deluser" and uid == ADMIN_ID:
        msg = bot.send_message(ADMIN_ID, "ðŸ—‘ á€–á€»á€€á€ºá€™á€Šá€·á€º User ID á€›á€­á€¯á€€á€ºá€•á€« (/cancel-á€•á€šá€ºá€–á€»á€€á€º)-")
        bot.register_next_step_handler(msg, _deluser_step)

    try: bot.answer_callback_query(call.id)
    except: pass

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ðŸš€  POLLING
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
print(f"âœ… Yay Zat Bot á€…á€á€„á€ºá€”á€±á€•á€«á€•á€¼á€®... [{datetime.now().strftime('%d/%m/%Y %H:%M')}]")
bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
