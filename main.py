import os
import json
import logging
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import telebot
from telebot import types

# ============================================
# 1. KONFİGÜRASYON
# ============================================

load_dotenv()

TOKEN = "8501106486:AAGFKuy6v0aAbZyvc_6QnBWgR4uIHU_a3ZI"  # ✅ YENİ TOKEN (DOĞRU)
ADMIN_ID = 8992278433  # ⚠️ BURAYA KENDİ TELEGRAM ID'NI YAZ (Örnek: 123456789)

BOT_NAME = "EmreSxrguPanel77bot"
VERSION = "2.0.0"

# Premium fiyatları
PREMIUM_FIYATLAR = {
    "haftalık": {"fiyat": 350, "gun": 7, "emoji": "📅"},
    "aylık": {"fiyat": 500, "gun": 30, "emoji": "📅"},
    "yıllık": {"fiyat": 800, "gun": 365, "emoji": "📅"},
    "sınırsız": {"fiyat": 1200, "gun": None, "emoji": "♾️"}
}

PREMIUM_CONTACT = "@paneldesteksorgu"

# API URL'leri
API_URLS = {
    "tc": "https://arastir-01.site/api/tc.php?tc=",
    "tcpro": "https://arastir-01.site/api/tcpro.php?tc=",
    "adsoyad": "https://arastir-01.site/api/adsoyad.php?ad=",
    "tcgsm": "https://arastir-01.site/api/tcgsm.php?tc=",
    "adres": "https://arastir-01.site/api/adres.php?tc=",
    "gsmtc": "https://arastir-01.site/api/gsmtc.php?gsm=",
    "aile": "https://arastir-01.site/api/aile.php?tc=",
    "sulale": "https://arastir-01.site/api/sülale.php?tc=",
    "cocuk": "https://arastir-01.site/api/cocuk.php?tc=",
    "isyeri": "https://arastir-01.site/api/isyeri.php?tc="
}

# ============================================
# 2. LOG SİSTEMİ
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(BOT_NAME)

# ============================================
# 3. VERİTABANI
# ============================================

DB_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Kullanıcı tablosu (ban eklendi)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            join_date TEXT,
            is_premium INTEGER DEFAULT 0,
            premium_type TEXT,
            premium_start TEXT,
            premium_end TEXT,
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT,
            message_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query_type TEXT,
            query_data TEXT,
            response TEXT,
            timestamp TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS premium_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            user_id INTEGER,
            action TEXT,
            premium_type TEXT,
            duration TEXT,
            timestamp TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ban_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            user_id INTEGER,
            action TEXT,
            reason TEXT,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Veritabanı hazır")

def add_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, join_date, message_count)
        VALUES (?, ?, ?, ?, ?, COALESCE((SELECT message_count FROM users WHERE user_id=?), 0))
    ''', (user_id, username, first_name, last_name, datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_user_by_username(username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    result = cursor.fetchone()
    conn.close()
    return result

def is_banned(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def ban_user(user_id, reason, admin_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET is_banned = 1, ban_reason = ?
        WHERE user_id = ?
    ''', (reason, user_id))
    conn.commit()
    
    cursor.execute('''
        INSERT INTO ban_logs (admin_id, user_id, action, reason, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (admin_id, user_id, "ban", reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def unban_user(user_id, admin_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET is_banned = 0, ban_reason = NULL
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    
    cursor.execute('''
        INSERT INTO ban_logs (admin_id, user_id, action, reason, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (admin_id, user_id, "unban", "Ban kaldırıldı", datetime.now().isoformat()))
    conn.commit()
    conn.close()

def log_query(user_id, query_type, query_data, response):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (user_id, query_type, query_data, response, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, query_type, query_data, response, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def log_premium(admin_id, user_id, action, premium_type, duration):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO premium_logs (admin_id, user_id, action, premium_type, duration, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (admin_id, user_id, action, premium_type, duration, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def is_premium(user_id):
    if is_banned(user_id):
        return False
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT is_premium, premium_end FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0] == 1:
        if result[1]:
            end_date = datetime.fromisoformat(result[1])
            if datetime.now() > end_date:
                remove_premium_from_db(user_id)
                return False
        return True
    return False

def remove_premium_from_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET is_premium = 0, premium_type = NULL, premium_start = NULL, premium_end = NULL
        WHERE user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

def set_premium(user_id, premium_type, duration_days):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    start_date = datetime.now()
    
    if premium_type == "sınırsız":
        end_date = None
    else:
        end_date = start_date + timedelta(days=duration_days)
    
    cursor.execute('''
        UPDATE users 
        SET is_premium = 1, 
            premium_type = ?, 
            premium_start = ?, 
            premium_end = ?
        WHERE user_id = ?
    ''', (premium_type, start_date.isoformat(), end_date.isoformat() if end_date else None, user_id))
    
    conn.commit()
    conn.close()

# ============================================
# 4. BOT VE KLAVYE
# ============================================

bot = telebot.TeleBot(TOKEN)

def is_admin(user_id):
    return user_id == ADMIN_ID

def admin_or_ban_check(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(message, "🚫 Bu botu kullanma izniniz yok! Yönetici ile iletişime geçin.")
        return False
    
    return True

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "🔍 Ücretsiz Sorgu",
        "⭐ Premium Sorgu",
        "🛒 Premium Satın Al",
        "ℹ️ Hakkımda",
        "📊 Profilim"
    ]
    
    if is_admin(ADMIN_ID):
        buttons.append("👑 Admin Panel")
    
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "📝 Premium Ver",
        "❌ Premium Kaldır",
        "🚫 Kullanıcı Banla",
        "✅ Ban Kaldır",
        "📊 İstatistikler",
        "📢 Duyuru Gönder",
        "👥 Kullanıcı Ara",
        "📋 Premium Logları",
        "📋 Ban Logları",
        "🔙 Ana Menü"
    ]
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))
    return markup

def premium_type_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "📅 Haftalık (350₺)",
        "📅 Aylık (500₺)",
        "📅 Yıllık (800₺)",
        "♾️ Sınırsız (1200₺)",
        "🔙 Geri"
    ]
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))
    return markup

def free_query_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "📝 TC Sorgu (Ücretsiz)",
        "👤 Ad Soyad Sorgu (Ücretsiz)",
        "🔙 Ana Menü"
    ]
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))
    return markup

def premium_query_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        "📝 TC Pro Sorgu",
        "📱 TC-GSM Sorgu",
        "📱 GSM-TC Sorgu",
        "🏠 Adres Sorgu",
        "👨‍👩‍👧‍👦 Aile Sorgu",
        "👨‍👩‍👧‍👦 Sülale Sorgu",
        "👶 Çocuk Sorgu",
        "🏢 İşyeri Sorgu",
        "🔙 Ana Menü"
    ]
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))
    return markup

# ============================================
# 5. API İSTEK FONKSİYONU
# ============================================

def api_istek(url):
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "data": data}
        else:
            return {"success": False, "message": f"HTTP {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "⏰ Zaman aşımı!"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "🔌 Bağlantı hatası!"}
    except json.JSONDecodeError:
        return {"success": False, "message": "📄 Geçersiz yanıt!"}
    except Exception as e:
        return {"success": False, "message": f"❌ Hata: {str(e)}"}

# ============================================
# 6. KOMUT İŞLEYİCİLER
# ============================================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.reply_to(message, "🚫 Bu botu kullanma izniniz yok! Yönetici ile iletişime geçin.")
        return
    
    user = message.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    
    premium_status = "✅ Aktif" if is_premium(user.id) else "❌ Pasif"
    
    welcome = f"""
🤖 *{BOT_NAME}'a Hoş Geldin!*

Merhaba {user.first_name}! 👋
⭐ Premium Durum: {premium_status}

🔍 *Ücretsiz Sorgular:*
• TC Kimlik sorgulama
• Ad - Soyad sorgulama

⭐ *Premium Sorgular:*
• TC Pro sorgulama
• TC - GSM sorgulama
• GSM - TC sorgulama
• Adres sorgulama
• Aile bilgileri
• Sülale bilgileri
• Çocuk bilgileri
• İşyeri bilgileri

🛒 Premium satın almak için butonu kullan.

📌 *Komutlar:*
/start - Başlat
/help - Yardım
"""
    bot.reply_to(message, welcome, parse_mode='Markdown', reply_markup=main_menu())

@bot.message_handler(commands=['help'])
def help_command(message):
    if not admin_or_ban_check(message):
        return
    
    help_text = """
❓ *Yardım*

🔍 *Ücretsiz Sorgular:*
• TC Sorgu → TC No
• Ad Soyad Sorgu → Ad Soyad

⭐ *Premium Sorgular:*
• TC Pro → TC No
• TC-GSM → TC No
• GSM-TC → GSM
• Adres → TC No
• Aile → TC No
• Sülale → TC No
• Çocuk → TC No
• İşyeri → TC No

🛒 Premium satın almak için Premium Satın Al butonuna tıkla.
"""
    bot.reply_to(message, help_text, parse_mode='Markdown')

# ============================================
# 7. ANA MENÜ BUTONLARI
# ============================================

@bot.message_handler(func=lambda m: m.text == "🔍 Ücretsiz Sorgu")
def free_query_panel(message):
    if not admin_or_ban_check(message):
        return
    
    bot.reply_to(message, "🔍 *Ücretsiz Sorgular*", parse_mode='Markdown', reply_markup=free_query_menu())

@bot.message_handler(func=lambda m: m.text == "⭐ Premium Sorgu")
def premium_query_panel(message):
    if not admin_or_ban_check(message):
        return
    
    if is_premium(message.from_user.id):
        user = get_user(message.from_user.id)
        premium_type = user[4] if user else "Bilinmiyor"
        end_date = user[6] if user else "Bilinmiyor"
        
        bot.reply_to(message, f"""
⭐ *Premium Sorgular*

📌 Premium Tip: {premium_type}
📅 Bitiş: {end_date if end_date else '♾️ Sınırsız'}

Aşağıdan seçim yap:
""", parse_mode='Markdown', reply_markup=premium_query_menu())
    else:
        bot.reply_to(message, f"""
❌ *Premium Üye Değilsin!*

Bu özelliği kullanmak için premium üye olmalısın.

🛒 Premium satın almak için butonu kullan.
""", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🛒 Premium Satın Al")
def buy_premium(message):
    if not admin_or_ban_check(message):
        return
    
    text = f"""
🛒 *Premium Üyelik Paketleri*

⭐ *Premium Özellikler:*
• TC Pro Sorgu
• TC-GSM Sorgu
• GSM-TC Sorgu
• Adres Sorgu
• Aile Bilgileri
• Sülale Bilgileri
• Çocuk Bilgileri
• İşyeri Bilgileri
• Sınırsız Sorgu Hakkı

💳 *Paket Fiyatları:*
📅 Haftalık: 350₺ (7 Gün)
📅 Aylık: 500₺ (30 Gün)
📅 Yıllık: 800₺ (365 Gün)
♾️ Sınırsız: 1200₺ (Ömür Boyu)

📲 *Satın Almak İçin:*
👉 {PREMIUM_CONTACT}

Hemen yaz, üyelik başlasın! 🚀
"""
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "ℹ️ Hakkımda")
def about(message):
    if not admin_or_ban_check(message):
        return
    
    text = f"""
🤖 *{BOT_NAME}*
📌 Versiyon: {VERSION}

🔍 *Özellikler:*
• Ücretsiz TC Sorgu
• Ücretsiz Ad Soyad Sorgu
• ⭐ Premium Sorgular
• Hızlı ve Güvenilir

📡 API ile entegre çalışır.
"""
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📊 Profilim")
def profile(message):
    if not admin_or_ban_check(message):
        return
    
    user = message.from_user
    user_data = get_user(user.id)
    
    if user_data:
        premium_status = "✅ Aktif" if user_data[3] == 1 else "❌ Pasif"
        premium_type = user_data[4] if user_data[4] else "-"
        end_date = user_data[6] if user_data[6] else "♾️ Sınırsız"
        ban_status = "🚫 Banlı" if user_data[8] == 1 else "✅ Aktif"
    else:
        premium_status = "❌ Pasif"
        premium_type = "-"
        end_date = "-"
        ban_status = "✅ Aktif"
    
    text = f"""
📊 *Profilim*

👤 Ad: {user.first_name}
🆔 ID: {user.id}
⭐ Premium: {premium_status}
📌 Premium Tip: {premium_type}
📅 Bitiş: {end_date}
🚫 Durum: {ban_status}
💬 Mesaj: {user_data[10] if user_data else 0}
"""
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔙 Ana Menü")
def back_menu(message):
    if not admin_or_ban_check(message):
        return
    
    bot.reply_to(message, "📋 Ana menü:", reply_markup=main_menu())

# ============================================
# 8. 👑 ADMIN PANEL
# ============================================

@bot.message_handler(func=lambda m: m.text == "👑 Admin Panel")
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Bu alan sadece admin içindir!")
        return
    
    bot.reply_to(message, "👑 *Admin Paneli*\n\nNe yapmak istersin?", parse_mode='Markdown', reply_markup=admin_menu())

# ============================================
# 8.1 📝 PREMIUM VER
# ============================================

@bot.message_handler(func=lambda m: m.text == "📝 Premium Ver")
def admin_give_premium(message):
    if not is_admin(message.from_user.id):
        return
    
    bot.reply_to(message, "📝 *Premium Ver*\n\nKullanıcı ID veya @kullaniciadı girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, admin_get_user_for_premium)

def admin_get_user_for_premium(message):
    user_input = message.text.strip()
    
    if user_input.startswith('@'):
        username = user_input[1:]
        user_data = get_user_by_username(username)
    else:
        try:
            user_id = int(user_input)
            user_data = get_user(user_id)
        except:
            user_data = None
    
    if not user_data:
        bot.reply_to(message, "❌ Kullanıcı bulunamadı! Tekrar dene.")
        return
    
    if user_data[8] == 1:
        bot.reply_to(message, "⚠️ Bu kullanıcı banlı! Önce ban'ı kaldır.")
        return
    
    bot.reply_to(message, f"""
✅ Kullanıcı bulundu:
👤 {user_data[2]} (@{user_data[1]})
🆔 {user_data[0]}

Premium tipini seç:
""", parse_mode='Markdown', reply_markup=premium_type_menu())
    
    bot.user_data = {"target_user_id": user_data[0]}

@bot.message_handler(func=lambda m: m.text in ["📅 Haftalık (350₺)", "📅 Aylık (500₺)", "📅 Yıllık (800₺)", "♾️ Sınırsız (1200₺)"])
def admin_select_premium_type(message):
    if not is_admin(message.from_user.id):
        return
    
    if not hasattr(bot, 'user_data') or 'target_user_id' not in bot.user_data:
        bot.reply_to(message, "❌ Önce kullanıcı seç!")
        return
    
    target_user_id = bot.user_data['target_user_id']
    
    premium_map = {
        "📅 Haftalık (350₺)": ("haftalık", 7),
        "📅 Aylık (500₺)": ("aylık", 30),
        "📅 Yıllık (800₺)": ("yıllık", 365),
        "♾️ Sınırsız (1200₺)": ("sınırsız", None)
    }
    
    premium_type, duration = premium_map.get(message.text, (None, None))
    
    if not premium_type:
        bot.reply_to(message, "❌ Geçersiz premium tipi!")
        return
    
    if duration:
        set_premium(target_user_id, premium_type, duration)
    else:
        set_premium(target_user_id, premium_type, None)
    
    log_premium(message.from_user.id, target_user_id, "verildi", premium_type, str(duration) if duration else "sınırsız")
    
    fiyat = PREMIUM_FIYATLAR[premium_type]["fiyat"]
    
    bot.reply_to(message, f"""
✅ Premium verildi!

👤 Kullanıcı: {target_user_id}
📌 Tip: {premium_type}
💰 Fiyat: {fiyat}₺
📅 Süre: {duration if duration else '♾️ Sınırsız'}
""", parse_mode='Markdown')
    
    try:
        bot.send_message(target_user_id, f"""
🎉 *Premium Üye Oldun!*

📌 Premium Tip: {premium_type}
💰 Ödenen: {fiyat}₺
📅 Süre: {duration if duration else '♾️ Sınırsız'}

Tüm sorgulara erişimin açıldı! 🚀
""", parse_mode='Markdown')
    except:
        pass
    
    del bot.user_data

# ============================================
# 8.2 ❌ PREMIUM KALDIR
# ============================================

@bot.message_handler(func=lambda m: m.text == "❌ Premium Kaldır")
def admin_remove_premium(message):
    if not is_admin(message.from_user.id):
        return
    
    bot.reply_to(message, "❌ *Premium Kaldır*\n\nKullanıcı ID veya @kullaniciadı girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, admin_remove_premium_confirm)

def admin_remove_premium_confirm(message):
    user_input = message.text.strip()
    
    if user_input.startswith('@'):
        username = user_input[1:]
        user_data = get_user_by_username(username)
    else:
        try:
            user_id = int(user_input)
            user_data = get_user(user_id)
        except:
            user_data = None
    
    if not user_data:
        bot.reply_to(message, "❌ Kullanıcı bulunamadı!")
        return
    
    remove_premium_from_db(user_data[0])
    log_premium(message.from_user.id, user_data[0], "kaldırıldı", "-", "-")
    
    bot.reply_to(message, f"✅ Kullanıcı {user_data[0]} premium'dan çıkarıldı!")
    
    try:
        bot.send_message(user_data[0], "❌ Premium üyeliğiniz sonlandırıldı. Detay için: @paneldesteksorgu")
    except:
        pass

# ============================================
# 8.3 🚫 KULLANICI BANLA
# ============================================

@bot.message_handler(func=lambda m: m.text == "🚫 Kullanıcı Banla")
def admin_ban_user(message):
    if not is_admin(message.from_user.id):
        return
    
    bot.reply_to(message, "🚫 *Kullanıcı Banla*\n\nKullanıcı ID veya @kullaniciadı girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, admin_ban_user_confirm)

def admin_ban_user_confirm(message):
    user_input = message.text.strip()
    
    if user_input.startswith('@'):
        username = user_input[1:]
        user_data = get_user_by_username(username)
    else:
        try:
            user_id = int(user_input)
            user_data = get_user(user_id)
        except:
            user_data = None
    
    if not user_data:
        bot.reply_to(message, "❌ Kullanıcı bulunamadı!")
        return
    
    if user_data[0] == ADMIN_ID:
        bot.reply_to(message, "❌ Admin kendini banlayamaz!")
        return
    
    if user_data[8] == 1:
        bot.reply_to(message, "⚠️ Bu kullanıcı zaten banlı!")
        return
    
    bot.reply_to(message, f"""
⚠️ *BAN ONAYI*

👤 Kullanıcı: {user_data[2]} (@{user_data[1]})
🆔 ID: {user_data[0]}

Ban sebebini yaz (veya 'iptal' yaz):
""", parse_mode='Markdown')
    
    bot.user_data = {"target_user_id": user_data[0]}

@bot.message_handler(func=lambda m: m.chat.id in [ADMIN_ID] and hasattr(bot, 'user_data') and 'target_user_id' in bot.user_data)
def admin_ban_reason(message):
    if not is_admin(message.from_user.id):
        return
    
    if message.text.lower() == "iptal":
        del bot.user_data
        bot.reply_to(message, "❌ Ban işlemi iptal edildi.")
        return
    
    target_user_id = bot.user_data['target_user_id']
    reason = message.text.strip()
    
    ban_user(target_user_id, reason, message.from_user.id)
    
    bot.reply_to(message, f"""
✅ Kullanıcı banlandı!

👤 Kullanıcı: {target_user_id}
📌 Sebep: {reason}
""", parse_mode='Markdown')
    
    try:
        bot.send_message(target_user_id, f"""
🚫 *Hesabınız Banlandı!*

📌 Sebep: {reason}

Detay için: @paneldesteksorgu
""", parse_mode='Markdown')
    except:
        pass
    
    del bot.user_data

# ============================================
# 8.4 ✅ BAN KALDIR
# ============================================

@bot.message_handler(func=lambda m: m.text == "✅ Ban Kaldır")
def admin_unban_user(message):
    if not is_admin(message.from_user.id):
        return
    
    bot.reply_to(message, "✅ *Ban Kaldır*\n\nKullanıcı ID veya @kullaniciadı girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, admin_unban_confirm)

def admin_unban_confirm(message):
    user_input = message.text.strip()
    
    if user_input.startswith('@'):
        username = user_input[1:]
        user_data = get_user_by_username(username)
    else:
        try:
            user_id = int(user_input)
            user_data = get_user(user_id)
        except:
            user_data = None
    
    if not user_data:
        bot.reply_to(message, "❌ Kullanıcı bulunamadı!")
        return
    
    if user_data[8] == 0:
        bot.reply_to(message, "⚠️ Bu kullanıcı zaten banlı değil!")
        return
    
    unban_user(user_data[0], message.from_user.id)
    
    bot.reply_to(message, f"✅ Kullanıcı {user_data[0]} ban'ı kaldırıldı!")
    
    try:
        bot.send_message(user_data[0], "✅ Ban'ınız kaldırıldı. Botu tekrar kullanabilirsiniz!")
    except:
        pass

# ============================================
# 8.5 📊 İSTATİSTİKLER
# ============================================

@bot.message_handler(func=lambda m: m.text == "📊 İstatistikler")
def admin_stats(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_premium = 1')
    premium_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
    banned_users = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM logs')
    total_queries = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM premium_logs')
    total_premium_logs = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM ban_logs')
    total_ban_logs = cursor.fetchone()[0]
    
    conn.close()
    
    text = f"""
📊 *Bot İstatistikleri*

👥 Toplam Kullanıcı: {total_users}
⭐ Premium Üye: {premium_users}
🚫 Banlı Kullanıcı: {banned_users}
🔍 Toplam Sorgu: {total_queries}
📋 Premium Log: {total_premium_logs}
📋 Ban Log: {total_ban_logs}
🤖 Bot: {BOT_NAME}
🟢 Durum: Aktif ✅
"""
    bot.reply_to(message, text, parse_mode='Markdown')

# ============================================
# 8.6 📢 DUYURU GÖNDER
# ============================================

@bot.message_handler(func=lambda m: m.text == "📢 Duyuru Gönder")
def admin_broadcast(message):
    if not is_admin(message.from_user.id):
        return
    
    bot.reply_to(message, "📢 *Duyuru Mesajını Yaz:*", parse_mode='Markdown')
    bot.register_next_step_handler(message, admin_send_broadcast)

def admin_send_broadcast(message):
    msg = message.text.strip()
    
    if not msg:
        bot.reply_to(message, "❌ Boş mesaj gönderemezsin!")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE is_banned = 0')
    users = cursor.fetchall()
    conn.close()
    
    sent = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 *Duyuru*\n\n{msg}", parse_mode='Markdown')
            sent += 1
        except:
            pass
    
    bot.reply_to(message, f"✅ {sent} aktif kullanıcıya duyuru gönderildi!")

# ============================================
# 8.7 👥 KULLANICI ARA
# ============================================

@bot.message_handler(func=lambda m: m.text == "👥 Kullanıcı Ara")
def admin_search_user(message):
    if not is_admin(message.from_user.id):
        return
    
    bot.reply_to(message, "🔍 *Kullanıcı Ara*\n\nID veya @kullaniciadı girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, admin_show_user)

def admin_show_user(message):
    user_input = message.text.strip()
    
    if user_input.startswith('@'):
        username = user_input[1:]
        user_data = get_user_by_username(username)
    else:
        try:
            user_id = int(user_input)
            user_data = get_user(user_id)
        except:
            user_data = None
    
    if not user_data:
        bot.reply_to(message, "❌ Kullanıcı bulunamadı!")
        return
    
    premium_status = "✅ Aktif" if user_data[3] == 1 else "❌ Pasif"
    ban_status = "🚫 Banlı" if user_data[8] == 1 else "✅ Aktif"
    
    text = f"""
👤 *Kullanıcı Bilgileri*

🆔 ID: {user_data[0]}
👤 Ad: {user_data[2]}
📌 Kullanıcı: @{user_data[1] if user_data[1] else 'yok'}
⭐ Premium: {premium_status}
📅 Premium Tip: {user_data[4] if user_data[4] else '-'}
📅 Başlangıç: {user_data[5] if user_data[5] else '-'}
📅 Bitiş: {user_data[6] if user_data[6] else '♾️ Sınırsız'}
🚫 Durum: {ban_status}
📌 Ban Sebep: {user_data[9] if user_data[9] else '-'}
💬 Mesaj: {user_data[10] if user_data[10] else 0}
"""
    bot.reply_to(message, text, parse_mode='Markdown')

# ============================================
# 8.8 📋 PREMIUM LOGLARI
# ============================================

@bot.message_handler(func=lambda m: m.text == "📋 Premium Logları")
def admin_premium_logs(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM premium_logs ORDER BY id DESC LIMIT 10')
    logs = cursor.fetchall()
    conn.close()
    
    if not logs:
        bot.reply_to(message, "📋 Henüz premium log'u yok.")
        return
    
    text = "📋 *Son 10 Premium Log:*\n\n"
    for log in logs:
        text += f"🆔 {log[2]} → {log[3]} {log[4]} ({log[5]})\n📅 {log[6][:16]}\n\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ============================================
# 8.9 📋 BAN LOGLARI
# ============================================

@bot.message_handler(func=lambda m: m.text == "📋 Ban Logları")
def admin_ban_logs(message):
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ban_logs ORDER BY id DESC LIMIT 10')
    logs = cursor.fetchall()
    conn.close()
    
    if not logs:
        bot.reply_to(message, "📋 Henüz ban log'u yok.")
        return
    
    text = "📋 *Son 10 Ban Log:*\n\n"
    for log in logs:
        action = "🚫 BAN" if log[3] == "ban" else "✅ UNBAN"
        text += f"{action} | 🆔 {log[2]}\n📌 {log[4]}\n📅 {log[5][:16]}\n\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ============================================
# 9. SORGU İŞLEYİCİLER
# ============================================

user_waiting = {}

@bot.message_handler(func=lambda m: m.text in [
    "📝 TC Sorgu (Ücretsiz)",
    "👤 Ad Soyad Sorgu (Ücretsiz)"
])
def start_free_query(message):
    if not admin_or_ban_check(message):
        return
    
    query_type = message.text
    user_waiting[message.chat.id] = query_type
    
    prompts = {
        "📝 TC Sorgu (Ücretsiz)": "TC Kimlik Numarası (11 hane):",
        "👤 Ad Soyad Sorgu (Ücretsiz)": "Ad Soyad (örn: Ahmet Yılmaz):"
    }
    
    bot.reply_to(message, f"📝 *{query_type}*\n{prompts.get(query_type)}", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text in [
    "📝 TC Pro Sorgu",
    "📱 TC-GSM Sorgu",
    "📱 GSM-TC Sorgu",
    "🏠 Adres Sorgu",
    "👨‍👩‍👧‍👦 Aile Sorgu",
    "👨‍👩‍👧‍👦 Sülale Sorgu",
    "👶 Çocuk Sorgu",
    "🏢 İşyeri Sorgu"
])
def start_premium_query(message):
    if not admin_or_ban_check(message):
        return
    
    if not is_premium(message.from_user.id):
        bot.reply_to(message, f"""
❌ *Premium Üye Değilsin!*

Bu sorguyu kullanmak için premium üye olmalısın.

🛒 Satın al: @paneldesteksorgu
""", parse_mode='Markdown')
        return
    
    query_type = message.text
    user_waiting[message.chat.id] = query_type
    
    prompts = {
        "📝 TC Pro Sorgu": "TC Kimlik Numarası:",
        "📱 TC-GSM Sorgu": "TC Kimlik Numarası:",
        "📱 GSM-TC Sorgu": "GSM Numarası:",
        "🏠 Adres Sorgu": "TC Kimlik Numarası:",
        "👨‍👩‍👧‍👦 Aile Sorgu": "TC Kimlik Numarası:",
        "👨‍👩‍👧‍👦 Sülale Sorgu": "TC Kimlik Numarası:",
        "👶 Çocuk Sorgu": "TC Kimlik Numarası:",
        "🏢 İşyeri Sorgu": "TC Kimlik Numarası:"
    }
    
    bot.reply_to(message, f"⭐ *{query_type}*\n{prompts.get(query_type)}", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.chat.id in user_waiting)
def handle_query(message):
    if not admin_or_ban_check(message):
        return
    
    chat_id = message.chat.id
    query_type = user_waiting.pop(chat_id)
    user_input = message.text.strip()
    
    if not user_input:
        bot.reply_to(message, "❌ Boş veri girdin! Tekrar dene.")
        return
    
    query_map = {
        "📝 TC Sorgu (Ücretsiz)": "tc",
        "👤 Ad Soyad Sorgu (Ücretsiz)": "adsoyad",
        "📝 TC Pro Sorgu": "tcpro",
        "📱 TC-GSM Sorgu": "tcgsm",
        "📱 GSM-TC Sorgu": "gsmtc",
        "🏠 Adres Sorgu": "adres",
        "👨‍👩‍👧‍👦 Aile Sorgu": "aile",
        "👨‍👩‍👧‍👦 Sülale Sorgu": "sulale",
        "👶 Çocuk Sorgu": "cocuk",
        "🏢 İşyeri Sorgu": "isyeri"
    }
    
    key = query_map.get(query_type)
    
    if not key:
        bot.reply_to(message, "❌ Geçersiz sorgu tipi!")
        return
    
    api_url = API_URLS.get(key, "")
    
    if not api_url:
        bot.reply_to(message, "❌ API URL'si tanımlı değil!")
        return
    
    if key == "adsoyad":
        user_input = user_input.replace(" ", "+")
    
    full_url = api_url + user_input
    
    bot.reply_to(message, "⏳ Sorgu yapılıyor, lütfen bekleyin...")
    result = api_istek(full_url)
    
    log_query(message.from_user.id, query_type, user_input, json.dumps(result))
    
    if result["success"]:
        data = result["data"]
        if isinstance(data, dict):
            response_text = "\n".join([f"📌 {k}: {v}" for k, v in data.items()])
        else:
            response_text = str(data)
        
        bot.reply_to(message, f"✅ *Sorgu Tamamlandı!*\n\n{response_text}", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ *Sorgu Başarısız!*\n{result.get('message', 'Bilinmeyen hata')}", parse_mode='Markdown')
    
    if "Ücretsiz" in query_type:
        bot.reply_to(message, "🔍 Ücretsiz sorgu için:", reply_markup=free_query_menu())
    else:
        bot.reply_to(message, "⭐ Premium sorgu için:", reply_markup=premium_query_menu())

# ============================================
# 10. ANA ÇALIŞTIRICI
# ============================================

@bot.message_handler(content_types=['photo', 'video', 'document', 'audio'])
def handle_media(message):
    if not admin_or_ban_check(message):
        return
    
    bot.reply_to(message, "📎 Sadece metin sorgusu yapabilirsin.")

def main():
    init_db()
    
    print("="*50)
    print(f"🤖 {BOT_NAME}")
    print(f"📌 Versiyon: {VERSION}")
    print(f"🔑 Token: {TOKEN[:15]}...")
    print("="*50)
    print("✅ Bot çalışıyor!")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("="*50)
    print("🔍 Ücretsiz: TC, Ad Soyad")
    print("⭐ Premium: TC Pro, TC-GSM, GSM-TC, Adres, Aile, Sülale, Çocuk, İşyeri")
    print("="*50)
    print("💰 Premium Fiyatlar:")
    print("   📅 Haftalık: 350₺")
    print("   📅 Aylık: 500₺")
    print("   📅 Yıllık: 800₺")
    print("   ♾️ Sınırsız: 1200₺")
    print("="*50)
    print("🚫 Admin Yetkileri:")
    print("   • Premium Ver/Kaldır")
    print("   • Kullanıcı Banla/Ban Kaldır")
    print("   • Duyuru Gönder")
    print("   • İstatistikler")
    print("   • Log Görüntüleme")
    print("="*50)
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n👋 Bot kapatıldı.")
    except Exception as e:
        logger.error(f"❌ Bot hatası: {e}")
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()
