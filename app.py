import os
import telebot
from telebot import types

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# --- Data Mapping ---
LEVELS = {
    "N5 (အောင်မြင်ပြီး)": {"jp": "日本語能力試験N5に合格しています。", "mm": "JLPT N5 ကို အောင်မြင်ထားပါတယ်။"},
    "N4 (အောင်မြင်ပြီး)": {"jp": "日本語能力試験N4に合格しています。", "mm": "JLPT N4 ကို အောင်မြင်ထားပါတယ်။"},
    "N3 (အောင်မြင်ပြီး)": {"jp": "日本語能力試験N3に合格しています。", "mm": "JLPT N3 ကို အောင်မြင်ထားပါတယ်။"},
    "Studying (လေ့လာနေဆဲ)": {"jp": "現在は、日本語ကို勉強中です。", "mm": "လက်ရှိမှာ ဂျပန်စာကို လေ့လာနေဆဲ ဖြစ်ပါတယ်။"}
}

HOBBIES = {
    "သီချင်းနားထောင်ခြင်း": {"jp": "趣味は音楽を聴くことです。", "mm": "ဝါသနာကတော့ သီချင်းနားထောင်ခြင်း ဖြစ်ပါတယ်။"},
    "စာဖတ်ခြင်း": {"jp": "趣味は本を読むことです。", "mm": "ဝါသနာကတော့ စာဖတ်ခြင်း ဖြစ်ပါတယ်။"},
    "အားကစားလုပ်ခြင်း": {"jp": "趣味はスポーツをすることです。", "mm": "ဝါသနာကတော့ အားကစားလုပ်ခြင်း ဖြစ်ပါတယ်။"},
    "ဟင်းချက်ခြင်း": {"jp": "趣味は料理を作ることです。", "mm": "ဝါသနာကတော့ ဟင်းချက်ခြင်း ဖြစ်ပါတယ်။"},
    "ခရီးသွားခြင်း": {"jp": "趣味は旅行に行くことです。", "mm": "ဝါသနာကတော့ ခရီးသွားခြင်း ဖြစ်ပါတယ်။"},
    "ရုပ်ရှင်ကြည့်ခြင်း": {"jp": "趣味は映画を見ることです。", "mm": "ဝါသနာကတော့ ရုပ်ရှင်ကြည့်ခြင်း ဖြစ်ပါတယ်။"},
    "ဓာတ်ပုံရိုက်ခြင်း": {"jp": "趣味は写真を撮ることです。", "mm": "ဝါသနာကတော့ ဓာတ်ပုံရိုက်ခြင်း ဖြစ်ပါတယ်။"},
    "ဂျပန်စာလေ့လာခြင်း": {"jp": "趣味は日本語を勉強することです。", "mm": "ဝါသနာကတော့ ဂျပန်စာလေ့လာခြင်း ဖြစ်ပါတယ်။"},
    "ဘောလုံးကစားခြင်း": {"jp": "趣味はサッカーをすることです。", "mm": "ဝါသနာကတော့ ဘောလုံးကစားခြင်း ဖြစ်ပါတယ်။"},
    "အပင်စိုက်ခြင်း": {"jp": "趣味は植物を育てることです。", "mm": "ဝါသနာကတော့ အပင်စိုက်ခြင်း ဖြစ်ပါတယ်။"}
}

FIELDS = {
    "ဘိုးဘွားစောင့်ရှောက်": {"jp": "お年寄りと接することが好きで、役に立ちたいからです。", "mm": "လူကြီးသူမတွေနဲ့ ထိတွေ့ရတာကို နှစ်သက်ပြီး အကျိုးပြုချင်လို့ပါ။"},
    "စားသောက်ဆိုင်": {"jp": "接客が好きで、日本の美味しい料理を広めたいからです。", "mm": "ဧည့်ဝတ်ပြုရတာကို နှစ်သက်ပြီး ဂျပန်ရဲ့ အရသာရှိတဲ့ အစားအစာတွေကို ဖြန့်ဝေချင်လို့ပါ။"},
    "စားသောက်ကုန်ထုတ်": {"jp": "食べ物を作ることが好きで、品質管理を学びたいからです。", "mm": "အစားအစာထုတ်လုပ်ရတာကို နှစ်သက်ပြီး အရည်အသွေးထိန်းသိမ်းမှုအပိုင်းကို သင်ယူချင်လို့ပါ။"},
    "စိုက်ပျိုးရေး": {"jp": "農業に興味があり、日本の先進的な技術を学びたいからです。", "mm": "စိုက်ပျိုးရေးကို စိတ်ဝင်စားပြီး ဂျပန်ရဲ့ အဆင့်မြင့်နည်းပညာတွေကို သင်ယူချင်လို့ပါ။"},
    "ကုန်ထုတ် (စက်ရုံ)": {"jp": "ものづくりが好きで、日本の高い技術に触れたいからです。", "mm": "ပစ္စည်းထုတ်လုပ်ရတာကို နှစ်သက်ပြီး ဂျပန်ရဲ့ နည်းပညာမြင့်မားမှုကို ထိတွေ့ချင်လို့ပါ။"},
    "ဟိုတယ်": {"jp": "日本のおもてなしを学び、お客様を笑顔にしたいからです。", "mm": "ဂျပန်ရဲ့ ဧည့်ဝတ်ပြုမှုကို သင်ယူပြီး ဧည့်သည်တွေကို ပြုံးပျော်စေချင်လို့ပါ။"},
    "သန့်ရှင်းရေး": {"jp": "きれいな環境を作ることが好きで、真面目に働きたいからです。", "mm": "သန့်ရှင်းတဲ့ပတ်ဝန်းကျင် ဖန်တီးရတာကို နှစ်သက်ပြီး ကြိုးကြိုးစားစား လုပ်ကိုင်ချင်လို့ပါ။"},
    "အင်ဂျင်နီယာ": {"jp": "自分の専門知識を活かして、日本のプロジェクトに貢献したいからです。", "mm": "ကိုယ့်ရဲ့ ပညာရပ်ကို အသုံးချပြီး ဂျပန်ရဲ့ ပရောဂျက်တွေမှာ ပါဝင်ကူညီချင်လို့ပါ။"}
}

user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "J.F.Y Jikoshokai Builder မှ ကြိုဆိုပါတယ်။\nသင့်နာမည်ကို အင်္ဂလိပ်လို ရိုက်ထည့်ပေးပါ။ (ဥပမာ - Aung Aung)")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    user_data[message.chat.id] = {'name': message.text}
    bot.send_message(message.chat.id, "သင့်အသက်ကို ဂဏန်းဖြင့် ရိုက်ထည့်ပေးပါ။ (ဥပမာ - 24)")
    bot.register_next_step_handler(message, get_age)

def get_age(message):
    user_data[message.chat.id]['age'] = message.text
    bot.send_message(message.chat.id, "သင်နေထိုင်ရာမြို့ကို အင်္ဂလိပ်လို ရိုက်ထည့်ပေးပါ။ (ဥပမာ - Yangon)")
    bot.register_next_step_handler(message, get_city)

def get_city(message):
    user_data[message.chat.id]['city'] = message.text
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
    markup.add(*LEVELS.keys())
    bot.send_message(message.chat.id, "သင့်ရဲ့ ဂျပန်စာ Level ကို ရွေးချယ်ပါ။", reply_markup=markup)
    bot.register_next_step_handler(message, get_level)

def get_level(message):
    user_data[message.chat.id]['level'] = message.text
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
    markup.add(*HOBBIES.keys())
    bot.send_message(message.chat.id, "ဝါသနာကို ရွေးချယ်ပါ။", reply_markup=markup)
    bot.register_next_step_handler(message, get_hobby)

def get_hobby(message):
    user_data[message.chat.id]['hobby'] = message.text
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
    markup.add(*FIELDS.keys())
    bot.send_message(message.chat.id, "လျှောက်ထားမည့် နယ်ပယ်ကို ရွေးချယ်ပါ။", reply_markup=markup)
    bot.register_next_step_handler(message, get_field)

def get_field(message):
    user_data[message.chat.id]['field'] = message.text
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("Short Version", "Long Version")
    bot.send_message(message.chat.id, "ဘယ်လိုဗားရှင်းမျိုး ထုတ်ပေးရမလဲ?", reply_markup=markup)
    bot.register_next_step_handler(message, generate_result)

def generate_result(message):
    chat_id = message.chat.id
    if chat_id not in user_data: return
    data = user_data[chat_id]
    version = message.text
    
    name, age, city = data['name'], data['age'], data['city']
    l = LEVELS[data['level']]
    h = HOBBIES[data['hobby']]
    f = FIELDS[data['field']]
    
    if version == "Short Version":
        jp_text = f"はじめまして。私は {name} と申します。今年 {age} 歳です。{city} から参りました。{h['jp']} 精一杯頑張りますので、よろしくお願いいたします。"
        mm_text = f"မင်္ဂလာပါ။ ကျွန်တော့်နာမည်ကတော့ {name} လို့ ခေါ်ပါတယ်။ အသက်ကတော့ {age} နှစ်ပါ။ {city} ကနေ လာပါတယ်။ {h['mm']} အစွမ်းကုန် ကြိုးစားသွားပါ့မယ်။ ကူညီစောင့်ရှောက်ပေးဖို့ တောင်းဆိုအပ်ပါတယ်။"
    else:
        jp_text = f"はじめまして။ 私は {name} と申します။ 今年 {age} 歳です။ ミャンマーの {city} から参りました။ {l['jp']} {h['jp']} {f['jp']} 本日は面接の機会をいただき、誠にありがとうございます။ 日本へ行ったら、一生懸命頑張ります။ よろしくお願いいたします။"
        mm_text = f"မင်္ဂလာပါ။ ကျွန်တော့်နာမည်ကတော့ {name} လို့ ခေါ်ပါတယ်။ အသက်ကတော့ {age} နှစ်ပါ။ မြန်မာနိုင်ငံ၊ {city} မြို့ကနေ လာပါတယ်။ {l['mm']} {h['mm']} {f['mm']} ဒီနေ့ အင်တာဗျူး ဖြေဆိုခွင့်ရတဲ့အတွက် ကျေးဇူးအများကြီးတင်ပါတယ်။ ဂျပန်ရောက်ရင် အစွမ်းကုန် ကြိုးစားသွားပါ့မယ်။ ကူညီစောင့်ရှောက်ပေးဖို့ တောင်းဆိုအပ်ပါတယ်။"

    bot.send_message(chat_id, f"🇯🇵 **Japanese:**\n`{jp_text}`\n\n🇲🇲 **Myanmar:**\n{mm_text}", parse_mode="Markdown")

bot.infinity_polling()
