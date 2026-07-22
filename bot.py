import sqlite3

import requests

from flask import Flask, request

from datetime import datetime

from contextlib import contextmanager

import json

import io

import re

import os

# ===== КОНФИГУРАЦИЯ =====

TOKEN = "8078793115:AAFyXHvNgUQbrQbGeMxqySo0hGrGsN9N5Cw"

ADMIN_ID = 8423031459

whitelist_users = set()

whitelist_notified = set()

DB_PATH = os.getenv('DATABASE_PATH', 'spy.db')

WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://telegram-bot-lggs.onrender.com/webhook')

BOT_USERNAME = "@v373ments_bot"

API_URL = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)

# ===== ДЕФОЛТНЫЕ НАСТРОЙКИ ДИЗАЙНА =====

DEFAULT_SETTINGS = {

    # Изображения

    'start_image': "https://i.ibb.co/vWf7KTL/photo-2026-05-05-20-00-18.jpg",

    'welcome_image': "https://i.ibb.co/m5kx1c7C/photo-2026-05-05-19-08-58.jpg", 

    'settings_image': "https://i.ibb.co/7tKL334J/4e297130-9e22-41e4-af43-57c6e58882a1.png",

    'whitelist_on_image': "AgACAgIAAxkBAAIThmn_tUEFbWvMa2FBUhtYJGF7PldkAAL_GWsbEZr4S4dg8OXCgx73AQADAgADeAADOwQ",

    'whitelist_off_image': "AgACAgIAAxkBAAITh2n_tUSm-MLAEBDPccto9c8lOU8dAAMaaxsRmvhL5KQx_Mh9MI0BAAMCAAN5AAM7BA",

    

    # Основные тексты

    'start_text': "🔍 <b>Подключите бота, чтобы он смог Вам помочь в нужный момент в чатах.</b>\n\nС уважением, {bot_name}",

    'welcome_text': "✅ <b>Бот успешно подключен к вам!</b>\n\nТеперь вы будете получать:\n🗑 Удалённые сообщения\n✏️ Редактированные сообщения\n\n⚙️ Настройте уведомления через /settings",

    'help_text': "ℹ️ <b>Помощь</b>\n━━━━━━━━━━━━━━━\n/start — Главное меню\n/settings — Настройки уведомлений\n/stats — Ваша статистика\n/chat @username или ID — Экспорт истории чата\n\n<b>Как подключить:</b>\n1. Откройте <b>Ваш профиль</b> в Telegram\n2. Перейдите в <b>Автоматизация чатов</b>\n3. В поисковую строку напишите: <code>v373ments_bot</code>\n4. Выберите <b>@v373ments_bot</b>\n5. Разрешите доступ ко всем чатам и сообщениям.",

    'whitelist_on_text': "🔒 <b>Включен белый список/технические работы.</b>\n\nСкоро вернёмся!",

    'whitelist_off_text': "✅ <b>Белый список/технические работы отключены.</b>\n\nБот снова работает, извиняемся за ожидание!",

    

    # Шаблоны уведомлений

    'deleted_template': "🗑 <b>{sender}</b> — удалил сообщение:\n🕐 {time}",

    'edited_template': "✏️ <b>{sender}</b> — изменил сообщение:\n🕐 {time}\n\n<blockquote>{old_content}</blockquote>\n\nна:\n\n<blockquote>{new_content}</blockquote>",

    'edited_fast_template': "✏️ <b>Редактирование</b>\n━━━━━━━━━━━━━━━\n💬 <b>Чат:</b> {chat}\n👤 <b>От:</b> {sender}\n🕐 {time}\n━━━━━━━━━━━━━━━\n❌ <b>Было:</b>\n<blockquote><i>(сообщение отредактировано слишком быстро)</i></blockquote>\n\n✅ <b>Стало:</b>\n<blockquote>{content}</blockquote>",

    

    # Настройки форматирования

    'time_format': "%d.%m.%Y %H:%M",

    'bot_name': "@v373ments_bot",

    'instruction_link': "https://t.me/SU1C1D3X/12",

    

    # Иконки медиа

    'photo_icon': "📷",

    'video_icon': "🎥", 

    'voice_icon': "🎤",

    'audio_icon': "🎵",

    'document_icon': "📎",

    'animation_icon': "🎞",

    'video_note_icon': "⭕",

    'sticker_icon': "🎭",

    'contact_icon': "📞",

    'location_icon': "📍",

    'poll_icon': "📊",

    'unknown_icon': "❓"

}

# ===== БАЗА ДАННЫХ =====

@contextmanager

def get_db():

    conn = sqlite3.connect(DB_PATH, timeout=15)

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL")

    try:

        yield conn

    finally:

        conn.close()

def get_whitelist_mode():

    with get_db() as conn:

        row = conn.execute("SELECT value FROM bot_settings WHERE key='whitelist_mode'").fetchone()

        return row["value"] == "1" if row else False

def set_whitelist_mode(val):

    with get_db() as conn:

        conn.execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES ('whitelist_mode', ?)",

            ("1" if val else "0",))

        conn.commit()

def load_whitelist():

    global whitelist_users

    try:

        with get_db() as conn:

            rows = conn.execute("SELECT user_id FROM whitelist").fetchall()

            whitelist_users = set(r["user_id"] for r in rows)

    except:

        whitelist_users = set()

whitelist_notified = set()

load_whitelist()

def init_db():

    with get_db() as conn:

        # Пользователи бота

        conn.execute('''CREATE TABLE IF NOT EXISTS users (

            user_id    INTEGER PRIMARY KEY,

            username   TEXT,

            first_name TEXT,

            joined_at  TEXT,

            is_muted   INTEGER DEFAULT 0,

            is_banned  INTEGER DEFAULT 0

        )''')

        

        # Подключения бизнес-аккаунтов

        conn.execute('''CREATE TABLE IF NOT EXISTS connections (

            connection_id TEXT PRIMARY KEY,

            user_id       INTEGER

        )''')

        

        # Все входящие сообщения

        conn.execute('''CREATE TABLE IF NOT EXISTS messages (

            id          INTEGER PRIMARY KEY AUTOINCREMENT,

            message_id  INTEGER,

            owner_id    INTEGER,

            sender_id   INTEGER,

            sender_name TEXT,

            chat_id     INTEGER,

            chat_name   TEXT,

            content     TEXT,

            media_type  TEXT,

            file_id     TEXT,

            timestamp   TEXT,

            deleted     INTEGER DEFAULT 0,

            edited      INTEGER DEFAULT 0,

            edit_count  INTEGER DEFAULT 0,

            UNIQUE(message_id, owner_id, chat_id)

        )''')

        

        # История редактирований

        conn.execute('''CREATE TABLE IF NOT EXISTS edits (

            id          INTEGER PRIMARY KEY AUTOINCREMENT,

            message_id  INTEGER,

            owner_id    INTEGER,

            chat_id     INTEGER,

            sender_name TEXT,

            chat_name   TEXT,

            old_content TEXT,

            new_content TEXT,

            media_type  TEXT,

            file_id     TEXT,

            edited_at   TEXT

        )''')

        

        # Настройки каждого пользователя

        conn.execute('''CREATE TABLE IF NOT EXISTS settings (

            user_id       INTEGER PRIMARY KEY,

            notify_edits  INTEGER DEFAULT 1,

            notify_deletes INTEGER DEFAULT 1,

            blur_media    INTEGER DEFAULT 0

        )''')

        

        # Белый список

        conn.execute('''CREATE TABLE IF NOT EXISTS whitelist (

            user_id INTEGER PRIMARY KEY

        )''')

        

        # Настройки бота

        conn.execute('''CREATE TABLE IF NOT EXISTS bot_settings (

            key   TEXT PRIMARY KEY,

            value TEXT

        )''')

        

        # Состояния админа

        conn.execute('''CREATE TABLE IF NOT EXISTS admin_states_db (

            user_id INTEGER PRIMARY KEY,

            action  TEXT,

            data    TEXT

        )''')

        

        # НОВАЯ ТАБЛИЦА: Кастомизация бота

        conn.execute('''CREATE TABLE IF NOT EXISTS bot_customization (

            setting_key   TEXT PRIMARY KEY,

            setting_value TEXT,

            setting_type  TEXT,

            description   TEXT,

            created_at    TEXT,

            updated_at    TEXT

        )''')

        

        conn.commit()

        

        # Инициализируем дефолтные настройки дизайна

        init_default_design()

def init_default_design():

    """Инициализация дефолтных настроек дизайна"""

    with get_db() as conn:

        for key, value in DEFAULT_SETTINGS.items():

            existing = conn.execute("SELECT setting_key FROM bot_customization WHERE setting_key=?", (key,)).fetchone()

            if not existing:

                setting_type = get_setting_type(key)

                description = get_setting_description(key)

                conn.execute("""INSERT INTO bot_customization 

                    (setting_key, setting_value, setting_type, description, created_at, updated_at) 

                    VALUES (?,?,?,?,?,?)""",

                    (key, value, setting_type, description, datetime.now().isoformat(), datetime.now().isoformat()))

        conn.commit()

def get_setting_type(key):

    """Определяет тип настройки по ключу"""

    if 'image' in key:

        return 'image'

    elif key in ['time_format', 'bot_name', 'instruction_link']:

        return 'config'

    elif 'template' in key:

        return 'template'

    elif 'icon' in key:

        return 'icon'

    else:

        return 'text'

def get_setting_description(key):

    """Возвращает описание настройки"""

    descriptions = {

        'start_image': 'Изображение для команды /start',

        'welcome_image': 'Изображение при подключении бота',

        'settings_image': 'Изображение в настройках',

        'whitelist_on_image': 'Изображение при включении белого списка',

        'whitelist_off_image': 'Изображение при выключении белого списка',

        'start_text': 'Текст приветствия /start',

        'welcome_text': 'Текст при подключении',

        'help_text': 'Текст помощи /help',

        'whitelist_on_text': 'Текст при включении белого списка',

        'whitelist_off_text': 'Текст при выключении белого списка',

        'deleted_template': 'Шаблон удалённого сообщения',

        'edited_template': 'Шаблон редактированного сообщения',

        'edited_fast_template': 'Шаблон быстрого редактирования',

        'time_format': 'Формат времени (%d.%m.%Y %H:%M)',

        'bot_name': 'Имя бота в сообщениях',

        'instruction_link': 'Ссылка на инструкцию'

    }

    return descriptions.get(key, f'Настройка {key}')

# ===== ФУНКЦИИ РАБОТЫ С КАСТОМИЗАЦИЕЙ =====

def get_custom_setting(key, default=None):

    """Получает кастомную настройку из БД"""

    with get_db() as conn:

        row = conn.execute("SELECT setting_value FROM bot_customization WHERE setting_key=?", (key,)).fetchone()

        if row:

            return row["setting_value"]

        return default or DEFAULT_SETTINGS.get(key, "")

def set_custom_setting(key, value, setting_type=None):

    """Сохраняет кастомную настройку в БД"""

    with get_db() as conn:

        if not setting_type:

            setting_type = get_setting_type(key)

        description = get_setting_description(key)

        

        conn.execute("""INSERT OR REPLACE INTO bot_customization 

            (setting_key, setting_value, setting_type, description, updated_at) 

            VALUES (?,?,?,?,?)""",

            (key, value, setting_type, description, datetime.now().isoformat()))

        conn.commit()

def format_template(template, **kwargs):

    """Форматирует шаблон с подстановкой переменных"""

    try:

        # Безопасная замена плейсхолдеров

        for key, value in kwargs.items():

            if value is None:

                value = ""

            template = template.replace(f"{{{key}}}", str(value))

        return template

    except Exception as e:

        print(f"[format_template] Error: {e}")

        return template

init_db()

# ===== НАСТРОЙКИ =====

def get_settings(user_id):

    with get_db() as conn:

        row = conn.execute("SELECT * FROM settings WHERE user_id=?", (user_id,)).fetchone()

        if row:

            return dict(row)

        conn.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))

        conn.commit()

        return {"user_id": user_id, "notify_edits": 1, "notify_deletes": 1, "blur_media": 0}

def set_setting(user_id, key, value):

    if key not in {"notify_edits", "notify_deletes", "blur_media"}:

        return

    with get_db() as conn:

        conn.execute(f"UPDATE settings SET {key}=? WHERE user_id=?", (value, user_id))

        conn.commit()

# ===== ВСПОМОГАТЕЛЬНЫЕ =====

def get_owner(connection_id):

    with get_db() as conn:

        row = conn.execute("SELECT user_id FROM connections WHERE connection_id=?", (connection_id,)).fetchone()

        return row["user_id"] if row else None

def is_muted(user_id):

    with get_db() as conn:

        row = conn.execute("SELECT is_muted FROM users WHERE user_id=?", (user_id,)).fetchone()

        return bool(row["is_muted"]) if row else False

def is_banned(user_id):

    with get_db() as conn:

        row = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()

        return bool(row["is_banned"]) if row else False

def register_user(user_id, username, first_name):

    with get_db() as conn:

        conn.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_at) VALUES (?,?,?,?)",

            (user_id, username, first_name, datetime.now().isoformat()))

        conn.commit()

def parse_media(msg):

    """Возвращает (media_type, file_id, content) с кастомными иконками"""

    if "text" in msg:

        return None, None, msg["text"]

    

    cap = msg.get("caption") or ""

    

    if "photo" in msg:

        photos = msg["photo"]

        if isinstance(photos, list) and photos:

            icon = get_custom_setting('photo_icon', '📷')

            return "photo", photos[-1]["file_id"], cap or f"{icon} Фото"

    

    if "video" in msg:

        icon = get_custom_setting('video_icon', '🎥')

        return "video", msg["video"]["file_id"], cap or f"{icon} Видео"

    

    if "voice" in msg:

        icon = get_custom_setting('voice_icon', '🎤')

        return "voice", msg["voice"]["file_id"], f"{icon} Голосовое"

    

    if "video_note" in msg:

        icon = get_custom_setting('video_note_icon', '⭕')

        return "video_note", msg["video_note"]["file_id"], f"{icon} Кружок"

    

    if "animation" in msg:

        icon = get_custom_setting('animation_icon', '🎞')

        return "animation", msg["animation"]["file_id"], cap or f"{icon} GIF"

    

    if "audio" in msg:

        icon = get_custom_setting('audio_icon', '🎵')

        return "audio", msg["audio"]["file_id"], cap or f"{icon} Аудио"

    

    if "document" in msg:

        icon = get_custom_setting('document_icon', '📎')

        return "document", msg["document"]["file_id"], cap or f"{icon} Документ"

    

    if "sticker" in msg:

        s = msg["sticker"]

        icon = get_custom_setting('sticker_icon', '🎭')

        return "sticker", s["file_id"], f"{icon} Стикер {s.get('emoji','')}"

    

    if "contact" in msg:

        c = msg["contact"]

        icon = get_custom_setting('contact_icon', '📞')

        return None, None, f"{icon} Контакт: {c.get('first_name','')} {c.get('phone_number','')}"

    

    if "location" in msg:

        loc = msg["location"]

        icon = get_custom_setting('location_icon', '📍')

        return None, None, f"{icon} Локация: {loc['latitude']}, {loc['longitude']}"

    

    if "poll" in msg:

        icon = get_custom_setting('poll_icon', '📊')

        return None, None, f"{icon} Опрос: {msg['poll'].get('question','')}"

    

    icon = get_custom_setting('unknown_icon', '❓')

    return None, None, f"{icon} Неизвестный тип"

def get_sender(msg):

    u = msg.get("from") or {}

    name = ((u.get("first_name") or "") + " " + (u.get("last_name") or "")).strip()

    if u.get("username"):

        name += f" (@{u['username']})"

    return name or "Неизвестный", u.get("id", 0)

def get_chat_name(msg):

    chat = msg.get("chat") or {}

    name = ((chat.get("first_name") or "") + " " + (chat.get("last_name") or "")).strip()

    return name or chat.get("title") or chat.get("username") or "Неизвестный чат"

def format_time():

    """Форматирует время согласно настройкам"""

    time_format = get_custom_setting('time_format', '%d.%m.%Y %H:%M')

    return datetime.now().strftime(time_format)

# ===== TELEGRAM API =====

def api(method, **kwargs):

    try:

        r = requests.post(f"{API_URL}{method}", json=kwargs, timeout=10).json()

        if not r.get("ok"):

            print(f"[API] {method} → {r.get('description')}")

        return r

    except Exception as e:

        print(f"[API] {method} exception: {e}")

        return {}

def send_msg(chat_id, text, markup=None):

    p = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

    if markup: p["reply_markup"] = markup

    return api("sendMessage", **p)

def send_photo_msg(chat_id, photo, caption=None, markup=None, spoiler=False):

    p = {"chat_id": chat_id, "photo": photo, "parse_mode": "HTML"}

    if caption: p["caption"] = caption

    if markup: p["reply_markup"] = markup

    if spoiler: p["has_spoiler"] = True

    return api("sendPhoto", **p)

def send_video_msg(chat_id, video, caption=None, spoiler=False):

    p = {"chat_id": chat_id, "video": video, "parse_mode": "HTML"}

    if caption: p["caption"] = caption

    if spoiler: p["has_spoiler"] = True

    return api("sendVideo", **p)

def send_voice_msg(chat_id, voice, caption=None):

    p = {"chat_id": chat_id, "voice": voice, "parse_mode": "HTML"}

    if caption: p["caption"] = caption

    return api("sendVoice", **p)

def send_audio_msg(chat_id, audio, caption=None):

    p = {"chat_id": chat_id, "audio": audio, "parse_mode": "HTML"}

    if caption: p["caption"] = caption

    return api("sendAudio", **p)

def send_doc_msg(chat_id, doc, caption=None):

    p = {"chat_id": chat_id, "document": doc, "parse_mode": "HTML"}

    if caption: p["caption"] = caption

    return api("sendDocument", **p)

def send_anim_msg(chat_id, anim, caption=None, spoiler=False):

    p = {"chat_id": chat_id, "animation": anim, "parse_mode": "HTML"}

    if caption: p["caption"] = caption

    if spoiler: p["has_spoiler"] = True

    return api("sendAnimation", **p)

def send_vnote_msg(chat_id, vnote):

    return api("sendVideoNote", chat_id=chat_id, video_note=vnote)

def send_sticker_msg(chat_id, sticker):

    return api("sendSticker", chat_id=chat_id, sticker=sticker)

def edit_cap(chat_id, msg_id, caption, markup=None):

    p = {"chat_id": chat_id, "message_id": msg_id, "caption": caption, "parse_mode": "HTML"}

    if markup: p["reply_markup"] = markup

    return api("editMessageCaption", **p)

def edit_txt(chat_id, msg_id, text, markup=None):

    p = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}

    if markup: p["reply_markup"] = markup

    return api("editMessageText", **p)

def answer_cb(cb_id, text=None, alert=False):

    p = {"callback_query_id": cb_id}

    if text: p["text"] = text

    if alert: p["show_alert"] = True

    return api("answerCallbackQuery", **p)

# ===== ОТПРАВКА УДАЛЁННОГО МЕДИА =====

def notify_deleted(owner_id, row):

    s = get_settings(owner_id)

    spoiler = s["blur_media"] == 1

    ts = format_time()

    sender = row["sender_name"] or "?"

    

    # Используем кастомный шаблон

    template = get_custom_setting('deleted_template')

    header = format_template(template, sender=sender, time=ts)

    

    content = row["content"] or ""

    media_type = row["media_type"]

    file_id = row["file_id"]

    # Определяем иконки из настроек

    plain_labels = {

        f"{get_custom_setting('photo_icon', '📷')} Фото",

        f"{get_custom_setting('video_icon', '🎥')} Видео", 

        f"{get_custom_setting('audio_icon', '🎵')} Аудио",

        f"{get_custom_setting('document_icon', '📎')} Документ",

        f"{get_custom_setting('voice_icon', '🎤')} Голосовое",

        f"{get_custom_setting('video_note_icon', '⭕')} Кружок",

        f"{get_custom_setting('animation_icon', '🎞')} GIF",

        f"{get_custom_setting('unknown_icon', '❓')} Неизвестный тип"

    }

    

    sticker_prefix = f"{get_custom_setting('sticker_icon', '🎭')} Стикер"

    has_text = content and content not in plain_labels and not content.startswith(sticker_prefix)

    if media_type and file_id:

        caption = header

        if has_text:

            caption += f"\n<blockquote>{content}</blockquote>"

            

        if media_type == "photo":

            send_photo_msg(owner_id, file_id, caption=caption, spoiler=spoiler)

        elif media_type == "video":

            send_video_msg(owner_id, file_id, caption=caption, spoiler=spoiler)

        elif media_type == "voice":

            send_voice_msg(owner_id, file_id, caption=caption)

        elif media_type == "audio":

            send_audio_msg(owner_id, file_id, caption=caption)

        elif media_type == "document":

            send_doc_msg(owner_id, file_id, caption=caption)

        elif media_type == "animation":

            send_anim_msg(owner_id, file_id, caption=caption, spoiler=spoiler)

        elif media_type == "video_note":

            send_msg(owner_id, header)

            send_vnote_msg(owner_id, file_id)

        elif media_type == "sticker":

            send_msg(owner_id, header)

            send_sticker_msg(owner_id, file_id)

    else:

        text = header

        if content:

            text += f"\n<blockquote>{content}</blockquote>"

        send_msg(owner_id, text)

def notify_edited(owner_id, row, old_content, new_content, edit_num):

    ts = format_time()

    sender = row["sender_name"] or "?"

    

    # Используем кастомный шаблон

    template = get_custom_setting('edited_template')

    text = format_template(template, 

        sender=sender, 

        time=ts, 

        old_content=old_content if old_content else "📎 Медиафайл",

        new_content=new_content if new_content else "📎 Медиафайл"

    )

    

    s = get_settings(owner_id)

    spoiler = s["blur_media"] == 1

    if row["media_type"] and row["file_id"]:

        mt = row["media_type"]

        fid = row["file_id"]

        if mt == "photo":

            send_photo_msg(owner_id, fid, caption=text, spoiler=spoiler)

        elif mt == "video":

            send_video_msg(owner_id, fid, caption=text, spoiler=spoiler)

        elif mt == "voice":

            send_voice_msg(owner_id, fid, caption=text)

        elif mt == "audio":

            send_audio_msg(owner_id, fid, caption=text)

        elif mt == "document":

            send_doc_msg(owner_id, fid, caption=text)

        elif mt == "animation":

            send_anim_msg(owner_id, fid, caption=text, spoiler=spoiler)

        elif mt == "video_note":

            send_msg(owner_id, text)

            send_vnote_msg(owner_id, fid)

        elif mt == "sticker":

            send_msg(owner_id, text)

            send_sticker_msg(owner_id, fid)

    else:

        send_msg(owner_id, text)

# ===== КЛАВИАТУРЫ =====

def kb_start():

    bot_name = get_custom_setting('bot_name')

    instruction_link = get_custom_setting('instruction_link')

    return {"inline_keyboard": [

        [{"text": f"📋 Скопировать {bot_name}", "callback_data": "copy_username"}],

        [{"text": "📖 Подробная инструкция", "url": instruction_link}]

    ]}

def kb_settings(user_id):

    s = get_settings(user_id)

    e = "✅" if s["notify_edits"] else "❌"

    d = "✅" if s["notify_deletes"] else "❌"

    b = "✅" if s["blur_media"] else "❌"

    return {"inline_keyboard": [

        [{"text": f"{e} Уведомления об изменении", "callback_data": "s_edits"}],

        [{"text": f"{d} Уведомления об удалении", "callback_data": "s_deletes"}],

        [{"text": f"{b} Блюр удаленных медиа", "callback_data": "s_blur"}],

        [{"text": "‹ Назад", "callback_data": "back_start"}]

    ]}

def kb_detail(stype, val):

    btn = ("❌ Выключить", f"off_{stype}") if val else ("✅ Включить", f"on_{stype}")

    return {"inline_keyboard": [

        [{"text": btn[0], "callback_data": btn[1]}],

        [{"text": "‹ Назад", "callback_data": "back_settings"}]

    ]}

# ===== ДИЗАЙН ПАНЕЛЬ =====

def kb_design_main():

    """Главное меню дизайн-панели"""

    return {"inline_keyboard": [

        [{"text": "📷 Изображения", "callback_data": "design_images"}],

        [{"text": "📝 Тексты", "callback_data": "design_texts"}],

        [{"text": "🎨 Шаблоны", "callback_data": "design_templates"}],

        [{"text": "⚙️ Настройки", "callback_data": "design_config"}],

        [{"text": "🔧 Иконки", "callback_data": "design_icons"}],

        [{"text": "💾 Экспорт/Импорт", "callback_data": "design_export"}],

        [{"text": "🔄 Сброс", "callback_data": "design_reset"}]

    ]}

def kb_design_images():

    """Меню настройки изображений"""

    return {"inline_keyboard": [

        [{"text": "🖼 Стартовое фото", "callback_data": "edit_start_image"}],

        [{"text": "👋 Приветствие", "callback_data": "edit_welcome_image"}],

        [{"text": "⚙️ Настройки", "callback_data": "edit_settings_image"}],

        [{"text": "🔒 Белый список ВКЛ", "callback_data": "edit_whitelist_on_image"}],

        [{"text": "🔓 Белый список ВЫКЛ", "callback_data": "edit_whitelist_off_image"}],

        [{"text": "‹ Назад", "callback_data": "design_main"}]

    ]}

def kb_design_texts():

    """Меню настройки текстов"""

    return {"inline_keyboard": [

        [{"text": "🏠 Приветствие /start", "callback_data": "edit_start_text"}],

        [{"text": "👋 При подключении", "callback_data": "edit_welcome_text"}],

        [{"text": "❓ Помощь /help", "callback_data": "edit_help_text"}],

        [{"text": "🔒 Белый список ВКЛ", "callback_data": "edit_whitelist_on_text"}],

        [{"text": "🔓 Белый список ВЫКЛ", "callback_data": "edit_whitelist_off_text"}],

        [{"text": "‹ Назад", "callback_data": "design_main"}]

    ]}

def kb_design_templates():

    """Меню настройки шаблонов"""

    return {"inline_keyboard": [

        [{"text": "🗑 Шаблон удаления", "callback_data": "edit_deleted_template"}],

        [{"text": "✏️ Шаблон редактирования", "callback_data": "edit_edited_template"}],

        [{"text": "⚡ Быстрое редактирование", "callback_data": "edit_edited_fast_template"}],

        [{"text": "‹ Назад", "callback_data": "design_main"}]

    ]}

def kb_design_config():

    """Меню настройки конфигурации"""

    return {"inline_keyboard": [

        [{"text": "🕐 Формат времени", "callback_data": "edit_time_format"}],

        [{"text": "🤖 Имя бота", "callback_data": "edit_bot_name"}],

        [{"text": "🔗 Ссылка инструкции", "callback_data": "edit_instruction_link"}],

        [{"text": "‹ Назад", "callback_data": "design_main"}]

    ]}

def kb_design_icons():

    """Меню настройки иконок"""

    return {"inline_keyboard": [

        [{"text": "📷 Фото", "callback_data": "edit_photo_icon"}, {"text": "🎥 Видео", "callback_data": "edit_video_icon"}],

        [{"text": "🎤 Голос", "callback_data": "edit_voice_icon"}, {"text": "🎵 Аудио", "callback_data": "edit_audio_icon"}],

        [{"text": "📎 Документ", "callback_data": "edit_document_icon"}, {"text": "🎞 GIF", "callback_data": "edit_animation_icon"}],

        [{"text": "⭕ Кружок", "callback_data": "edit_video_note_icon"}, {"text": "🎭 Стикер", "callback_data": "edit_sticker_icon"}],

        [{"text": "📞 Контакт", "callback_data": "edit_contact_icon"}, {"text": "📍 Локация", "callback_data": "edit_location_icon"}],

        [{"text": "📊 Опрос", "callback_data": "edit_poll_icon"}, {"text": "❓ Неизвестно", "callback_data": "edit_unknown_icon"}],

        [{"text": "‹ Назад", "callback_data": "design_main"}]

    ]}

def kb_design_preview(setting_key):

    """Кнопки для предпросмотра настройки"""

    return {"inline_keyboard": [

        [{"text": "👀 Предпросмотр", "callback_data": f"preview_{setting_key}"}],

        [{"text": "💾 Сохранить", "callback_data": f"save_{setting_key}"}, {"text": "❌ Отмена", "callback_data": "design_main"}]

    ]}

SETTING_TEXTS = {

    "edits": "<b>✏️ Уведомления об изменении</b>\n\nКак это работает?\n<blockquote>Если ваш собеседник изменит любое сообщение, бот мгновенно сохранит вам его старую и новую версию.</blockquote>",

    "deletes": "<b>🗑️ Уведомления об удалении</b>\n\nКак это работает?\n<blockquote>Если ваш собеседник удалит любое сообщение, бот мгновенно сохранит его вам.</blockquote>",

    "blur": "<b>🎭 Блюр удаленных медиа</b>\n\nКак это работает?\n<blockquote>Все удаленные медиа/фото будут приходить с эффектом блюра. Это особенно полезно, если вы находитесь в общественном месте.</blockquote>",

}

SETTING_KEYS = {"edits": "notify_edits", "deletes": "notify_deletes", "blur": "blur_media"}

# ===== ОБРАБОТЧИКИ ДИЗАЙН-ПАНЕЛИ =====

def handle_design_command(chat_id, user_id):

    """Обработчик команды /design"""

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    

    send_msg(chat_id, 

        "🎨 <b>Дизайн-панель бота</b>\n\n"

        "Здесь вы можете настроить:\n"

        "📷 <b>Изображения</b> — фото в сообщениях\n"

        "📝 <b>Тексты</b> — приветствие, помощь\n"

        "🎨 <b>Шаблоны</b> — удаление, редактирование\n"

        "⚙️ <b>Настройки</b> — формат времени, ссылки\n"

        "🔧 <b>Иконки</b> — символы типов медиа\n\n"

        "💡 <i>Используйте плейсхолдеры в шаблонах:</i>\n"

        "<code>{sender}</code> — имя отправителя\n"

        "<code>{time}</code> — время\n"

        "<code>{content}</code> — текст сообщения\n"

        "<code>{chat}</code> — название чата\n"

        "<code>{bot_name}</code> — имя бота",

        markup=kb_design_main())

def handle_design_callback(cb):

    """Обработчик callback'ов дизайн-панели"""

    cb_id = cb["id"]

    data = cb["data"]

    user_id = cb["from"]["id"]

    chat_id = cb["message"]["chat"]["id"]

    msg_id = cb["message"]["message_id"]

    

    if not is_admin(user_id):

        answer_cb(cb_id, "⛔ Нет доступа", alert=True)

        return

    

    # Навигация по разделам

    if data == "design_main":

        edit_txt(chat_id, msg_id, 

            "🎨 <b>Дизайн-панель бота</b>\n\nВыберите раздел для настройки:",

            markup=kb_design_main())

        answer_cb(cb_id)

    

    elif data == "design_images":

        edit_txt(chat_id, msg_id,

            "📷 <b>Настройка изображений</b>\n\nВыберите изображение для изменения:\n\n"

            "💡 <i>Отправьте фото или ссылку на изображение</i>",

            markup=kb_design_images())

        answer_cb(cb_id)

    

    elif data == "design_texts":

        edit_txt(chat_id, msg_id,

            "📝 <b>Настройка текстов</b>\n\nВыберите текст для изменения:\n\n"

            "💡 <i>Можно использовать HTML разметку и плейсхолдеры</i>",

            markup=kb_design_texts())

        answer_cb(cb_id)

    

    elif data == "design_templates":

        edit_txt(chat_id, msg_id,

            "🎨 <b>Настройка шаблонов</b>\n\nВыберите шаблон для изменения:\n\n"

            "💡 <i>Доступные плейсхолдеры:</i>\n"

            "<code>{sender}</code> — отправитель\n"

            "<code>{time}</code> — время\n"

            "<code>{content}</code>, <code>{old_content}</code>, <code>{new_content}</code> — содержимое\n"

            "<code>{chat}</code> — чат",

            markup=kb_design_templates())

        answer_cb(cb_id)

    

    elif data == "design_config":

        edit_txt(chat_id, msg_id,

            "⚙️ <b>Настройка конфигурации</b>\n\nВыберите параметр для изменения:",

            markup=kb_design_config())

        answer_cb(cb_id)

    

    elif data == "design_icons":

        edit_txt(chat_id, msg_id,

            "🔧 <b>Настройка иконок</b>\n\nВыберите иконку для изменения:\n\n"

            "💡 <i>Используйте эмодзи или текст</i>",

            markup=kb_design_icons())

        answer_cb(cb_id)

    

    # Редактирование настроек

    elif data.startswith("edit_"):

        setting_key = data[5:]  # убираем "edit_"

        handle_edit_setting(chat_id, user_id, msg_id, setting_key)

        answer_cb(cb_id)

    

    # Предпросмотр

    elif data.startswith("preview_"):

        setting_key = data[8:]  # убираем "preview_"

        handle_preview_setting(chat_id, user_id, setting_key)

        answer_cb(cb_id)

    

    # Сохранение

    elif data.startswith("save_"):

        setting_key = data[5:]  # убираем "save_"

        handle_save_setting(chat_id, user_id, setting_key)

        answer_cb(cb_id, "✅ Сохранено!", alert=True)

    

    # Сброс настроек

    elif data == "design_reset":

        edit_txt(chat_id, msg_id,

            "🔄 <b>Сброс настроек</b>\n\n"

            "⚠️ Все настройки дизайна будут сброшены к стандартным.\n\n"

            "Вы уверены?",

            markup={"inline_keyboard": [

                [{"text": "✅ Да, сбросить", "callback_data": "confirm_reset"}],

                [{"text": "❌ Отмена", "callback_data": "design_main"}]

            ]})

        answer_cb(cb_id)

    

    elif data == "confirm_reset":

        reset_design_settings()

        edit_txt(chat_id, msg_id,

            "✅ <b>Настройки сброшены</b>\n\nВсе параметры дизайна возвращены к стандартным значениям.",

            markup=kb_design_main())

        answer_cb(cb_id)

def handle_edit_setting(chat_id, user_id, msg_id, setting_key):

    """Начало редактирования настройки"""

    current_value = get_custom_setting(setting_key)

    description = get_setting_description(setting_key)

    setting_type = get_setting_type(setting_key)

    

    # Сохраняем состояние редактирования

    set_admin_state(user_id, {

        "action": "design_edit",

        "setting_key": setting_key,

        "original_msg_id": msg_id

    })

    

    text = f"✏️ <b>Редактирование:</b> {description}\n\n"

    

    if setting_type == "image":

        text += "📷 <b>Текущее изображение:</b>\n"

        text += f"<code>{current_value}</code>\n\n"

        text += "📤 Отправьте новое изображение (фото или ссылку):"

    

    elif setting_type == "template":

        text += "🎨 <b>Текущий шаблон:</b>\n"

        text += f"<blockquote>{current_value}</blockquote>\n\n"

        text += "📝 Отправьте новый шаблон:"

        

        if "deleted" in setting_key:

            text += "\n\n💡 <b>Доступные плейсхолдеры:</b>\n"

            text += "<code>{sender}</code> — отправитель\n<code>{time}</code> — время"

        elif "edited" in setting_key:

            text += "\n\n💡 <b>Доступные плейсхолдеры:</b>\n"

            text += "<code>{sender}</code> — отправитель\n<code>{time}</code> — время\n"

            text += "<code>{old_content}</code> — старый текст\n<code>{new_content}</code> — новый текст\n"

            text += "<code>{chat}</code> — название чата"

    

    else:

        text += "📝 <b>Текущее значение:</b>\n"

        text += f"<blockquote>{current_value}</blockquote>\n\n"

        text += "📤 Отправьте новое значение:"

    

    edit_txt(chat_id, msg_id, text, markup={"inline_keyboard": [

        [{"text": "❌ Отмена", "callback_data": "design_main"}]

    ]})

def handle_preview_setting(chat_id, user_id, setting_key):

    """Предпросмотр настройки с тестовыми данными"""

    state = get_admin_state(user_id)

    if not state or state.get("action") != "design_edit":

        return

    

    temp_value = state.get("temp_value", "")

    setting_type = get_setting_type(setting_key)

    

    if setting_type == "template":

        # Тестовые данные для предпросмотра

        test_data = {

            "sender": "Иван Иванов (@ivan)",

            "time": format_time(),

            "content": "Тестовое сообщение для примера",

            "old_content": "Старый текст сообщения",

            "new_content": "Новый текст сообщения",

            "chat": "Тестовый чат",

            "bot_name": get_custom_setting('bot_name')

        }

        

        preview_text = format_template(temp_value, **test_data)

        

        send_msg(chat_id, 

            f"👀 <b>Предпросмотр шаблона:</b>\n\n{preview_text}\n\n"

            f"<i>Это пример того, как будет выглядеть сообщение</i>")

    

    elif setting_type == "image":

        if temp_value.startswith("http"):

            send_photo_msg(chat_id, temp_value, caption="👀 <b>Предпросмотр изображения</b>")

        else:

            send_msg(chat_id, f"👀 <b>Предпросмотр:</b>\nFile ID: <code>{temp_value}</code>")

    

    else:

        send_msg(chat_id, f"👀 <b>Предпросмотр:</b>\n<blockquote>{temp_value}</blockquote>")

def handle_save_setting(chat_id, user_id, setting_key):

    """Сохранение настройки"""

    state = get_admin_state(user_id)

    if not state or state.get("action") != "design_edit":

        return

    

    temp_value = state.get("temp_value", "")

    if temp_value:

        set_custom_setting(setting_key, temp_value)

    

    # Возвращаемся к главному меню дизайна

    msg_id = state.get("original_msg_id")

    if msg_id:

        edit_txt(chat_id, msg_id,

            "🎨 <b>Дизайн-панель бота</b>\n\nВыберите раздел для настройки:",

            markup=kb_design_main())

    

    clear_admin_state(user_id)

def reset_design_settings():

    """Сброс всех настроек дизайна к дефолтным"""

    with get_db() as conn:

        conn.execute("DELETE FROM bot_customization")

        conn.commit()

    init_default_design()

def handle_design_message(chat_id, user_id, msg):

    """Обработка сообщений в режиме редактирования дизайна"""

    state = get_admin_state(user_id)

    if not state or state.get("action") != "design_edit":

        return False

    

    setting_key = state.get("setting_key")

    if not setting_key:

        return False

    

    # Получаем новое значение из сообщения

    new_value = None

    

    if "photo" in msg:

        # Если отправили фото

        photos = msg["photo"]

        if photos:

            new_value = photos[-1]["file_id"]

    elif "text" in msg:

        # Если отправили текст

        new_value = msg["text"]

    

    if new_value:

        # Сохраняем временное значение для предпросмотра

        state["temp_value"] = new_value

        set_admin_state(user_id, state)

        

        # Показываем меню с предпросмотром

        send_msg(chat_id,

            f"✅ <b>Новое значение получено</b>\n\n"

            f"🔧 <b>Настройка:</b> {get_setting_description(setting_key)}\n"

            f"📝 <b>Значение:</b> <code>{new_value[:100]}{'...' if len(str(new_value)) > 100 else ''}</code>",

            markup=kb_design_preview(setting_key))

        

        return True

    

    return False

# ===== ЭКСПОРТ ЧАТА =====

def handle_chat_export(chat_id, user_id, query):

    """Экспорт истории чата с пользователем в файл"""

    query = query.strip().lstrip("@")

    with get_db() as conn:

        # Сначала находим chat_id по запросу

        first_row = conn.execute("""

            SELECT chat_id FROM messages 

            WHERE owner_id=? AND (chat_name LIKE ? OR sender_name LIKE ? OR CAST(chat_id AS TEXT) = ?)

            LIMIT 1

        """, (user_id, f"%{query}%", f"%{query}%", query)).fetchone()

        if not first_row:

            send_msg(chat_id, f"❌ История чата с <b>{query}</b> не найдена.")

            return

        target_chat_id = first_row["chat_id"]

        # Теперь берём ВСЕ сообщения в этом чате

        rows = conn.execute("""

            SELECT message_id, sender_id, sender_name, chat_id, chat_name, content, media_type, file_id, timestamp, deleted

            FROM messages WHERE owner_id=? AND chat_id=?

            ORDER BY timestamp ASC

        """, (user_id, target_chat_id)).fetchall()

        if not rows:

            send_msg(chat_id, f"❌ История чата с <b>{query}</b> не найдена.")

            return

        # Получаем инфу о чате

        chat_name_export = rows[0]["chat_name"] or query

        # Формируем текст для файла

        lines = []

        lines.append(f"═══════════════════════════════════════")

        lines.append(f"История чата: {chat_name_export}")

        lines.append(f"ID чата: {target_chat_id or 'неизвестно'}")

        lines.append(f"Экспортировано: {format_time()}")

        lines.append(f"Всего сообщений: {len(rows)}")

        lines.append(f"═══════════════════════════════════════\n")

        for r in rows:

            ts = (r["timestamp"] or "")[:16].replace("T", " ")

            sender = r["sender_name"] or "Неизвестный"

            content = r["content"] or ""

            media_type = r["media_type"]

            deleted_mark = "🗑 [УДАЛЕНО]" if r["deleted"] else ""

            if media_type and not content:

                content = f"[{media_type}]"

            lines.append(f"[{ts}] {sender}:")

            lines.append(f"  {content} {deleted_mark}")

            if media_type and r["file_id"]:

                lines.append(f"  📎 Медиа: {media_type} (file_id: {r['file_id'][:30]}...)")

            lines.append("")

        # Создаём файл

        file_content = "\n".join(lines)

        filename = f"chat_{query}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        # Отправляем уведомление

        send_msg(chat_id, f"📤 <b>Экспорт чата</b>\n"

                          f"━━━━━━━━━━━━━━━\n"

                          f"💬 Чат: <b>{chat_name_export}</b>\n"

                          f"🆔 ID: <code>{target_chat_id or 'неизвестно'}</code>\n"

                          f"📊 Сообщений: <b>{len(rows)}</b>\n"

                          f"━━━━━━━━━━━━━━━\n"

                          f"📤 Отправляю файл...")

        # Загружаем файл на Telegram сервер

        files = {"document": (filename, io.BytesIO(file_content.encode('utf-8')))}

        data = {

            "chat_id": chat_id,

            "caption": f"📄 <b>История чата с {chat_name_export}</b>\n🆔 ID: <code>{target_chat_id or 'неизвестно'}</code>\n📊 Сообщений: {len(rows)}",

            "parse_mode": "HTML"

        }

        requests.post(f"{API_URL}sendDocument", files=files, data=data)

# ===== ОБРАБОТЧИКИ =====

def on_start(chat_id, user_id, username, first_name):

    register_user(user_id, username, first_name)

    get_settings(user_id)

    

    start_image = get_custom_setting('start_image')

    start_text = get_custom_setting('start_text')

    bot_name = get_custom_setting('bot_name')

    

    formatted_text = format_template(start_text, bot_name=bot_name)

    

    send_photo_msg(chat_id, start_image,

        caption=formatted_text,

        markup=kb_start())

def on_settings(chat_id, user_id):

    settings_image = get_custom_setting('settings_image')

    send_photo_msg(chat_id, settings_image,

        caption="<b>⚙️ Настройки</b>\n\nВыберите параметр для изменения:",

        markup=kb_settings(user_id))

def on_callback(cb):

    cb_id = cb["id"]

    data = cb["data"]

    user_id = cb["from"]["id"]

    chat_id = cb["message"]["chat"]["id"]

    msg_id = cb["message"]["message_id"]

    has_photo = "photo" in cb["message"]

    def edit(text, markup):

        if has_photo:

            edit_cap(chat_id, msg_id, text, markup=markup)

        else:

            edit_txt(chat_id, msg_id, text, markup=markup)

    # Обработка дизайн-панели

    if data.startswith("design_") or data.startswith("edit_") or data.startswith("preview_") or data.startswith("save_") or data == "confirm_reset":

        handle_design_callback(cb)

        return

    if data == "copy_username":

        bot_name = get_custom_setting('bot_name')

        answer_cb(cb_id, f"Скопируйте: {bot_name}", alert=True)

    elif data == "back_start":

        answer_cb(cb_id)

        start_text = get_custom_setting('start_text')

        bot_name = get_custom_setting('bot_name')

        formatted_text = format_template(start_text, bot_name=bot_name)

        edit(formatted_text, kb_start())

    elif data == "back_settings":

        edit("<b>⚙️ Настройки</b>\n\nВыберите параметр для изменения:", kb_settings(user_id))

        answer_cb(cb_id)

    elif data.startswith("s_"):

        stype = data[2:]

        s = get_settings(user_id)

        key = SETTING_KEYS.get(stype)

        if key:

            edit(SETTING_TEXTS[stype], kb_detail(stype, s[key]))

            answer_cb(cb_id)

    elif data.startswith("on_"):

        stype = data[3:]

        key = SETTING_KEYS.get(stype)

        if key:

            set_setting(user_id, key, 1)

            edit(SETTING_TEXTS[stype], kb_detail(stype, 1))

            answer_cb(cb_id, "✅ Включено", alert=True)

    elif data.startswith("off_"):

        stype = data[4:]

        key = SETTING_KEYS.get(stype)

        if key:

            set_setting(user_id, key, 0)

            edit(SETTING_TEXTS[stype], kb_detail(stype, 0))

            answer_cb(cb_id, "❌ Выключено", alert=True)

def on_business_connection(bc):

    user = bc["user"]

    user_id = user["id"]

    enabled = bc.get("is_enabled", True)

    register_user(user_id, user.get("username"), user.get("first_name"))

    get_settings(user_id)

    with get_db() as conn:

        if enabled:

            conn.execute("INSERT OR REPLACE INTO connections VALUES (?,?)", (bc["id"], user_id))

            conn.commit()

            

            welcome_image = get_custom_setting('welcome_image')

            welcome_text = get_custom_setting('welcome_text')

            

            send_photo_msg(user_id, welcome_image, caption=welcome_text)

        else:

            conn.execute("DELETE FROM connections WHERE connection_id=?", (bc["id"],))

            conn.commit()

            send_msg(user_id, "⚠️ <b>Бот был отключён.</b>\n\nЕсли это произошло случайно — подключите снова.")

def on_business_message(msg, owner_id):

    """Сохраняем входящее сообщение в БД"""

    try:

        # Проверка белого списка

        if not check_whitelist(owner_id):

            if owner_id not in whitelist_notified:

                whitelist_notified.add(owner_id)

                send_msg(owner_id, "🔒 Включен белый список/технические работы. Вернитесь позже.")

            return

        # Если владелец пишет сам себе — обрабатываем как команду

        sender_id = (msg.get("from") or {}).get("id", 0)

        if sender_id == owner_id:

            text = msg.get("text", "")

            chat_id = msg.get("chat", {}).get("id", owner_id)

            if text.startswith("/"):

                on_message(msg)

                return

            if get_admin_state(owner_id) is not None:

                handle_admin_confirm(chat_id, owner_id, text)

                return

            # Обработка сообщений дизайн-панели

            if handle_design_message(chat_id, owner_id, msg):

                return

        media_type, file_id, content = parse_media(msg)

        sender_name, sender_id = get_sender(msg)

        chat_name = get_chat_name(msg)

        msg_id = msg["message_id"]

        chat_id = msg.get("chat", {}).get("id", 0)

        with get_db() as conn:

            conn.execute("""INSERT OR REPLACE INTO messages(

                message_id, owner_id, sender_id, sender_name, chat_id, chat_name,

                content, media_type, file_id, timestamp, deleted, edited, edit_count

            ) VALUES (?,?,?,?,?,?,?,?,?,?,0,0,0)""",

                (msg_id, owner_id, sender_id, sender_name, chat_id, chat_name,

                 content or "", media_type, file_id, datetime.now().isoformat()))

            conn.commit()

    except Exception as e:

        print(f"[on_business_message] {e}")

def on_edited_business_message(msg, owner_id):

    """Сохраняем редактирование и уведомляем владельца"""

    try:

        media_type, file_id, new_content = parse_media(msg)

        sender_name, sender_id = get_sender(msg)

        chat_name = get_chat_name(msg)

        msg_id = msg["message_id"]

        chat_id = msg.get("chat", {}).get("id", 0)

        with get_db() as conn:

            row = conn.execute("SELECT * FROM messages WHERE message_id=? AND owner_id=? AND chat_id=?",

                (msg_id, owner_id, chat_id)).fetchone()

            if row:

                old_content = row["content"]

                new_count = row["edit_count"] + 1

                conn.execute("""INSERT INTO edits(

                    message_id, owner_id, chat_id, sender_name, chat_name,

                    old_content, new_content, media_type, file_id, edited_at

                ) VALUES (?,?,?,?,?,?,?,?,?,?)""",

                    (msg_id, owner_id, chat_id, sender_name, chat_name,

                     old_content, new_content, media_type, file_id, datetime.now().isoformat()))

                conn.execute("""UPDATE messages SET content=?, media_type=?, file_id=?,

                    edited=1, edit_count=? WHERE message_id=? AND owner_id=? AND chat_id=?""",

                    (new_content, media_type, file_id, new_count, msg_id, owner_id, chat_id))

                conn.commit()

                s = get_settings(owner_id)

                if s["notify_edits"] and not is_muted(owner_id):

                    notify_edited(owner_id, dict(row), old_content, new_content, new_count)

            else:

                conn.execute("""INSERT OR REPLACE INTO messages(

                    message_id, owner_id, sender_id, sender_name, chat_id, chat_name,

                    content, media_type, file_id, timestamp, deleted, edited, edit_count

                ) VALUES (?,?,?,?,?,?,?,?,?,?,0,1,1)""",

                    (msg_id, owner_id, sender_id, sender_name, chat_id, chat_name,

                     new_content or "", media_type, file_id, datetime.now().isoformat()))

                conn.commit()

                s = get_settings(owner_id)

                if s["notify_edits"] and not is_muted(owner_id):

                    template = get_custom_setting('edited_fast_template')

                    formatted_text = format_template(template,

                        chat=chat_name,

                        sender=sender_name,

                        time=format_time(),

                        content=new_content or ''

                    )

                    send_msg(owner_id, formatted_text)

    except Exception as e:

        print(f"[on_edited_business_message] {e}")

def on_deleted_business_messages(dbd):

    """Получаем удалённые сообщения и уведомляем владельца"""

    bc_id = dbd.get("business_connection_id")

    owner_id = get_owner(bc_id)

    if not owner_id:

        return

    for msg_id in dbd.get("message_ids", []):

        try:

            with get_db() as conn:

                rows = conn.execute("SELECT * FROM messages WHERE message_id=? AND owner_id=? AND deleted=0",

                    (msg_id, owner_id)).fetchall()

                for row in rows:

                    conn.execute("UPDATE messages SET deleted=1 WHERE message_id=? AND owner_id=? AND chat_id=?",

                        (msg_id, owner_id, row["chat_id"]))

                    conn.commit()

                    s = get_settings(owner_id)

                    if s["notify_deletes"] and not is_muted(owner_id):

                        notify_deleted(owner_id, dict(row))

        except Exception as e:

            print(f"[on_deleted] msg_id={msg_id} error: {e}")

# ===== АДМИН ПАНЕЛЬ =====

admin_states = {}

def get_admin_state(user_id):

    if user_id in admin_states:

        return admin_states[user_id]

    with get_db() as conn:

        row = conn.execute("SELECT action, data FROM admin_states_db WHERE user_id=?", (user_id,)).fetchone()

        if row:

            import json

            state = {"action": row["action"]}

            if row["data"]:

                state.update(json.loads(row["data"]))

            admin_states[user_id] = state

            return state

    return None

def set_admin_state(user_id, state):

    import json

    admin_states[user_id] = state

    data = json.dumps({k: v for k, v in state.items() if k != "action"})

    with get_db() as conn:

        conn.execute("INSERT OR REPLACE INTO admin_states_db (user_id, action, data) VALUES (?,?,?)",

            (user_id, state.get("action"), data))

        conn.commit()

def clear_admin_state(user_id):

    admin_states.pop(user_id, None)

    with get_db() as conn:

        conn.execute("DELETE FROM admin_states_db WHERE user_id=?", (user_id,))

        conn.commit()

def is_admin(user_id):

    return user_id == ADMIN_ID

def handle_admin_command(chat_id, user_id):

    print(f"[ADMIN] called by {user_id}, is_admin={is_admin(user_id)}", flush=True)

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    with get_db() as conn:

        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

        connected = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]

        total_del = conn.execute("SELECT COUNT(*) FROM messages WHERE deleted=1").fetchone()[0]

        total_edit = conn.execute("SELECT COUNT(*) FROM edits").fetchone()[0]

        total_msg = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]

        banned = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]

        muted = conn.execute("SELECT COUNT(*) FROM users WHERE is_muted=1").fetchone()[0]

    send_msg(chat_id,

        f"👑 <b>Админ-панель</b>\n"

        f"━━━━━━━━━━━━━━━\n"

        f"👥 Пользователей: <b>{total_users}</b>\n"

        f"🔗 Подключено: <b>{connected}</b>\n"

        f"💾 Сообщений в БД: <b>{total_msg}</b>\n"

        f"🗑 Удалений поймано: <b>{total_del}</b>\n"

        f"✏️ Редактирований: <b>{total_edit}</b>\n"

        f"🚫 Забанено: <b>{banned}</b>\n"

        f"🔇 Замьючено: <b>{muted}</b>\n"

        f"━━━━━━━━━━━━━━━\n"

        f"<b>Команды:</b>\n"

        f"/users — список пользователей\n"

        f"/design — дизайн-панель бота\n"

        f"━━━━━━━━━━━━━━━\n"

        f"👥 <b>Пользователи:</b>\n"

        f"/users — список пользователей\n"

        f"/find ID или @username — найти юзера\n"

        f"/info ID — инфо о юзере\n"

        f"/msg ID текст — написать юзеру\n"

        f"━━━━━━━━━━━━━━━\n"

        f"👁 <b>Слежка:</b>\n"

        f"/spy ID — удалённые юзера\n"

        f"/media ID — медиафайлы юзера\n"

        f"/getfile file_id — получить файл по ID\n"

        f"/spyedits ID — редактирования юзера\n"

        f"/spystats ID — статистика юзера\n"

        f"━━━━━━━━━━━━━━━\n"

        f"🚫 <b>Управление:</b>\n"

        f"/ban ID — забанить\n"

        f"/unban ID — разбанить\n"

        f"/mute ID — замьютить\n"

        f"/unmute ID — размьютить\n"

        f"━━━━━━━━━━━━━━━\n"

        f"📢 <b>Рассылка:</b>\n"

        f"/broadcast — рассылка всем\n"

        f"━━━━━━━━━━━━━━━\n"

        f"📋 <b>Белый список:</b>\n"

        f"/whitelist — вкл/выкл белый список\n"

        f"/wladd ID — добавить в список\n"

        f"/wlremove ID — убрать из списка\n"

        f"/wllist — показать список")

def handle_users_command(chat_id, user_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    with get_db() as conn:

        rows = conn.execute("""

            SELECT u.user_id, u.username, u.first_name, u.is_banned, u.is_muted,

                   COUNT(c.connection_id) as connected

            FROM users u

            LEFT JOIN connections c ON u.user_id = c.user_id

            GROUP BY u.user_id

            ORDER BY u.joined_at DESC

            LIMIT 20

        """).fetchall()

        if not rows:

            send_msg(chat_id, "👥 Пользователей нет.")

            return

        text = f"👥 <b>Пользователи (последние {len(rows)}):</b>\n\n"

        for r in rows:

            name = r["first_name"] or "?"

            uname = f"@{r['username']}" if r["username"] else "нет"

            icons = ""

            if r["connected"]: icons += "🔗"

            if r["is_banned"]: icons += "🚫"

            if r["is_muted"]: icons += "🔇"

            text += f"{icons} <b>{name}</b> ({uname})\n   ID: <code>{r['user_id']}</code>\n\n"

        send_msg(chat_id, text)

def handle_find_command(chat_id, user_id, query):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    query = query.strip().lstrip("@")

    with get_db() as conn:

        row = conn.execute("""

            SELECT u.*, COUNT(c.connection_id) as connected,

                   COUNT(m.id) as msg_count,

                   SUM(CASE WHEN m.deleted=1 THEN 1 ELSE 0 END) as del_count

            FROM users u

            LEFT JOIN connections c ON u.user_id = c.user_id

            LEFT JOIN messages m ON u.user_id = m.owner_id

            WHERE CAST(u.user_id AS TEXT) = ? OR u.username = ?

            GROUP BY u.user_id

        """, (query, query)).fetchone()

        if not row:

            send_msg(chat_id, f"❌ Пользователь <code>{query}</code> не найден.")

            return

        name = row["first_name"] or "?"

        uname = f"@{row['username']}" if row["username"] else "нет"

        joined = (row["joined_at"] or "")[:10]

        send_msg(chat_id,

            f"🔍 <b>Пользователь найден</b>\n"

            f"━━━━━━━━━━━━━━━\n"

            f"👤 Имя: <b>{name}</b>\n"

            f"📛 Username: {uname}\n"

            f"🆔 ID: <code>{row['user_id']}</code>\n"

            f"📅 Регистрация: {joined}\n"

            f"━━━━━━━━━━━━━━━\n"

            f"🔗 Подключён: {'✅' if row['connected'] else '❌'}\n"

            f"🚫 Бан: {'✅' if row['is_banned'] else '❌'}\n"

            f"🔇 Мьют: {'✅' if row['is_muted'] else '❌'}\n"

            f"━━━━━━━━━━━━━━━\n"

            f"💾 Сообщений: <b>{row['msg_count']}</b>\n"

            f"🗑 Удалений: <b>{row['del_count']}</b>")

def handle_ban_command(chat_id, user_id, target_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    set_admin_state(user_id, {"action": "ban", "target": target_id})

    with get_db() as conn:

        row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

        name = row["first_name"] if row else "?"

        uname = f"@{row['username']}" if row and row["username"] else "нет"

    send_msg(chat_id,

        f"⚠️ <b>Подтверди бан</b>\n\n"

        f"👤 {name} ({uname})\n"

        f"🆔 <code>{target_id}</code>\n\n"

        f"Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

def handle_unban_command(chat_id, user_id, target_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    set_admin_state(user_id, {"action": "unban", "target": target_id})

    with get_db() as conn:

        row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

        name = row["first_name"] if row else "?"

        uname = f"@{row['username']}" if row and row["username"] else "нет"

    send_msg(chat_id,

        f"⚠️ <b>Подтверди разбан</b>\n\n"

        f"👤 {name} ({uname})\n"

        f"🆔 <code>{target_id}</code>\n\n"

        f"Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

def handle_mute_command(chat_id, user_id, target_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    set_admin_state(user_id, {"action": "mute", "target": target_id})

    with get_db() as conn:

        row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

        name = row["first_name"] if row else "?"

        uname = f"@{row['username']}" if row and row["username"] else "нет"

    send_msg(chat_id,

        f"⚠️ <b>Подтверди мьют</b>\n\n"

        f"👤 {name} ({uname})\n"

        f"🆔 <code>{target_id}</code>\n\n"

        f"Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

def handle_unmute_command(chat_id, user_id, target_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    set_admin_state(user_id, {"action": "unmute", "target": target_id})

    with get_db() as conn:

        row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

        name = row["first_name"] if row else "?"

        uname = f"@{row['username']}" if row and row["username"] else "нет"

    send_msg(chat_id,

        f"⚠️ <b>Подтверди размьют</b>\n\n"

        f"👤 {name} ({uname})\n"

        f"🆔 <code>{target_id}</code>\n\n"

        f"Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

def handle_broadcast_command(chat_id, user_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    set_admin_state(user_id, {"action": "broadcast_text"})

    send_msg(chat_id, "📢 <b>Рассылка</b>\n\nВведи текст сообщения:")

def handle_admin_confirm(chat_id, user_id, text):

    state = get_admin_state(user_id) or {}

    if not state:

        return False

    action = state.get("action")

    if text.lower() == "нет" and action not in ("whitelist_on_broadcast", "whitelist_off_broadcast"):

        clear_admin_state(user_id)

        send_msg(chat_id, "❌ Отменено.")

        return True

    if action == "broadcast_text":

        if text.lower() in ("да", "нет"):

            send_msg(chat_id, "❌ Введи текст рассылки:")

            return True

        set_admin_state(user_id, {"action": "broadcast_confirm", "text": text})

        with get_db() as conn:

            count = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=0").fetchone()[0]

        send_msg(chat_id,

            f"📢 <b>Подтверди рассылку</b>\n\n"

            f"Текст:\n<blockquote>{text[:300]}</blockquote>\n\n"

            f"Получателей: <b>{count}</b>\n\n"

            f"Напиши <b>да</b> для отправки или <b>нет</b> для отмены.")

        return True

    if action == "broadcast_confirm":

        if text.lower() not in ("да", "нет", "да.", "нет."):

            send_msg(chat_id, "⚠️ Напиши <b>да</b> для отправки или <b>нет</b> для отмены.")

            return True

        if text.lower() == "да":

            broadcast_text = state.get("text", "")

            clear_admin_state(user_id)

            with get_db() as conn:

                users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()

            sent, failed = 0, 0

            for u in users:

                r = send_msg(u["user_id"], f"📢 <b>Сообщение от администратора:</b>\n\n{broadcast_text}")

                if r and r.get("ok"):

                    sent += 1

                else:

                    failed += 1

            send_msg(chat_id, f"📢 Рассылка завершена\n✅ Отправлено: {sent}\n❌ Ошибок: {failed}")

        else:

            clear_admin_state(user_id)

            send_msg(chat_id, "❌ Рассылка отменена.")

        return True

    if action == "whitelist_on":

        if text.lower() == "да":

            set_admin_state(user_id, {"action": "whitelist_on_broadcast"})

            send_msg(chat_id,

                "📢 <b>Отправить рассылку всем пользователям или тихий режим?</b>\n\n"

                "Напиши <b>да</b> — отправить рассылку\n"

                "Напиши <b>нет</b> — тихий режим (без уведомлений)")

            return True

    if action == "whitelist_on_broadcast":

        set_whitelist_mode(True)

        whitelist_notified.clear()

        clear_admin_state(user_id)

        send_msg(chat_id, "✅ Белый список включён.")

        if text.lower() == "да":

            with get_db() as conn:

                users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()

            sent = 0

            whitelist_on_image = get_custom_setting('whitelist_on_image')

            whitelist_on_text = get_custom_setting('whitelist_on_text')

            for u in users:

                if u["user_id"] != ADMIN_ID:

                    r = send_photo_msg(u["user_id"], whitelist_on_image, caption=whitelist_on_text)

                    if r and r.get("ok"):

                        sent += 1

            send_msg(chat_id, f"📢 Рассылка отправлена: {sent} пользователей")

        else:

            send_msg(chat_id, "🔇 Тихий режим — пользователи не уведомлены.")

        return True

    if action == "whitelist_off":

        if text.lower() == "да":

            set_admin_state(user_id, {"action": "whitelist_off_broadcast"})

            send_msg(chat_id,

                "📢 <b>Отправить рассылку всем пользователям или тихий режим?</b>\n\n"

                "Напиши <b>да</b> — отправить рассылку\n"

                "Напиши <b>нет</b> — тихий режим (без уведомлений)")

            return True

    if action == "whitelist_off_broadcast":

        set_whitelist_mode(False)

        whitelist_notified.clear()

        clear_admin_state(user_id)

        send_msg(chat_id, "✅ Белый список выключен.")

        if text.lower() == "да":

            with get_db() as conn:

                users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()

            sent = 0

            whitelist_off_image = get_custom_setting('whitelist_off_image')

            whitelist_off_text = get_custom_setting('whitelist_off_text')

            for u in users:

                if u["user_id"] != ADMIN_ID:

                    r = send_photo_msg(u["user_id"], whitelist_off_image, caption=whitelist_off_text)

                    if r and r.get("ok"):

                        sent += 1

            send_msg(chat_id, f"📢 Рассылка отправлена: {sent} пользователей")

        else:

            send_msg(chat_id, "🔇 Тихий режим — пользователи не уведомлены.")

        return True

    if action == "wladd":

        if text.lower() == "да":

            target = state.get("target")

            clear_admin_state(user_id)

            whitelist_users.add(target)

            with get_db() as conn:

                conn.execute("INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)", (target,))

                conn.commit()

            send_msg(chat_id, f"✅ <code>{target}</code> добавлен в белый список.")

            send_msg(target,

                "✅ <b>Вы добавлены в белый список.</b>\n\n"

                "При включении белого списка вы сможете пользоваться ботом как раньше.")

            return True

    if action == "wlremove":

        if text.lower() == "да":

            target = state.get("target")

            clear_admin_state(user_id)

            whitelist_users.discard(target)

            with get_db() as conn:

                conn.execute("DELETE FROM whitelist WHERE user_id=?", (target,))

                conn.commit()

            send_msg(chat_id, f"✅ <code>{target}</code> убран из белого списка.")

            send_msg(target,

                "⚠️ <b>Вы были отключены от белого списка.</b>\n\n"

                "Работа и функционал бота будет прекращена при включённом списке.")

            return True

    if action in ("ban", "unban", "mute", "unmute"):

        if text.lower() == "да":

            target = state.get("target")

            clear_admin_state(user_id)

            with get_db() as conn:

                if action == "ban":

                    conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (target,))

                    conn.commit()

                    send_msg(chat_id, f"🚫 <code>{target}</code> забанен.")

                    send_msg(target, "🚫 Вы заблокированы администратором.")

                elif action == "unban":

                    conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (target,))

                    conn.commit()

                    send_msg(chat_id, f"✅ <code>{target}</code> разбанен.")

                    send_msg(target, "✅ Вы разблокированы.")

                elif action == "mute":

                    conn.execute("UPDATE users SET is_muted=1 WHERE user_id=?", (target,))

                    conn.commit()

                    send_msg(chat_id, f"🔇 <code>{target}</code> замьючен.")

                elif action == "unmute":

                    conn.execute("UPDATE users SET is_muted=0 WHERE user_id=?", (target,))

                    conn.commit()

                    send_msg(chat_id, f"🔔 <code>{target}</code> размьючен.")

            return True

    return False

def handle_msg_command(chat_id, user_id, args):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    parts = args.strip().split(" ", 1)

    if len(parts) < 2:

        send_msg(chat_id, "❌ Использование: /msg ID текст")

        return

    try:

        target_id = int(parts[0])

        msg_text = parts[1]

        r = send_msg(target_id, f"📩 <b>Сообщение от администратора:</b>\n\n{msg_text}")

        if r and r.get("ok"):

            send_msg(chat_id, f"✅ Сообщение отправлено пользователю <code>{target_id}</code>")

        else:

            send_msg(chat_id, f"❌ Не удалось отправить. Пользователь заблокировал бота?")

    except ValueError:

        send_msg(chat_id, "❌ Неверный ID пользователя")

def handle_info_command(chat_id, user_id, target_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    with get_db() as conn:

        row = conn.execute("SELECT * FROM users WHERE user_id=?", (target_id,)).fetchone()

        connected = conn.execute("SELECT COUNT(*) FROM connections WHERE user_id=?", (target_id,)).fetchone()[0]

        msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=?", (target_id,)).fetchone()[0]

        del_count = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=? AND deleted=1", (target_id,)).fetchone()[0]

        edit_count = conn.execute("SELECT COUNT(*) FROM edits WHERE owner_id=?", (target_id,)).fetchone()[0]

        last_del = conn.execute("SELECT MAX(timestamp) FROM messages WHERE owner_id=? AND deleted=1", (target_id,)).fetchone()[0]

        if not row:

            send_msg(chat_id, f"❌ Пользователь <code>{target_id}</code> не найден.")

            return

        name = row["first_name"] or "?"

        uname = f"@{row['username']}" if row["username"] else "нет"

        joined = (row["joined_at"] or "")[:10]

        last = (last_del or "")[:16].replace("T", " ")

        send_msg(chat_id,

            f"👁 <b>Инфо о пользователе</b>\n"

            f"━━━━━━━━━━━━━━━\n"

            f"👤 Имя: <b>{name}</b>\n"

            f"📛 Username: {uname}\n"

            f"🆔 ID: <code>{target_id}</code>\n"

            f"📅 Регистрация: {joined}\n"

            f"━━━━━━━━━━━━━━━\n"

            f"🔗 Подключён: {'✅' if connected else '❌'}\n"

            f"🚫 Бан: {'✅' if row['is_banned'] else '❌'}\n"

            f"🔇 Мьют: {'✅' if row['is_muted'] else '❌'}\n"

            f"━━━━━━━━━━━━━━━\n"

            f"💾 Сообщений: <b>{msg_count}</b>\n"

            f"🗑 Удалений: <b>{del_count}</b>\n"

            f"✏️ Редактирований: <b>{edit_count}</b>\n"

            f"🕐 Последнее удаление: {last or 'нет'}")

def check_whitelist(user_id):

    if not get_whitelist_mode():

        return True

    if user_id == ADMIN_ID:

        return True

    with get_db() as conn:

        row = conn.execute("SELECT user_id FROM whitelist WHERE user_id=?", (user_id,)).fetchone()

        return row is not None

def handle_spy_command(chat_id, user_id, target_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    with get_db() as conn:

        rows = conn.execute("""

            SELECT sender_name, content, media_type, chat_name, timestamp

            FROM messages WHERE owner_id=? AND deleted=1

            ORDER BY timestamp DESC LIMIT 10

        """, (target_id,)).fetchall()

        u = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

        name = u["first_name"] if u else "?"

        uname = f"@{u['username']}" if u and u["username"] else "нет"

        if not rows:

            send_msg(chat_id, f"👁 У {name} ({uname}) нет удалённых сообщений.")

            return

        text = f"👁 <b>Удалённые юзера {name} ({uname}):</b>\n\n"

        for r in rows:

            ts = (r["timestamp"] or "")[:16].replace("T", " ")

            content = (r["content"] or "")[:60]

            icon = "📷" if r["media_type"] else "💬"

            text += f"{icon} <b>{r['sender_name']}</b> → {r['chat_name'] or '?'}\n   {content}\n   🕐 {ts}\n\n"

        send_msg(chat_id, text)

def handle_spyedits_command(chat_id, user_id, target_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    with get_db() as conn:

        rows = conn.execute("""

            SELECT e.old_content, e.new_content, e.edited_at, m.sender_name, m.chat_name

            FROM edits e JOIN messages m ON e.message_id=m.message_id AND e.owner_id=m.owner_id

            WHERE e.owner_id=? ORDER BY e.edited_at DESC LIMIT 10

        """, (target_id,)).fetchall()

        u = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

        name = u["first_name"] if u else "?"

        uname = f"@{u['username']}" if u and u["username"] else "нет"

        if not rows:

            send_msg(chat_id, f"✏️ У {name} ({uname}) нет редактирований.")

            return

        text = f"✏️ <b>Редактирования юзера {name} ({uname}):</b>\n\n"

        for r in rows:

            ts = (r["edited_at"] or "")[:16].replace("T", " ")

            old = (r["old_content"] or "")[:40]

            new = (r["new_content"] or "")[:40]

            text += f"👤 <b>{r['sender_name']}</b> → {r['chat_name'] or '?'}\n   ❌ {old}\n   ✅ {new}\n   🕐 {ts}\n\n"

        send_msg(chat_id, text)

def handle_spystats_command(chat_id, user_id, target_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    with get_db() as conn:

        u = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

        total = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=?", (target_id,)).fetchone()[0]

        deleted = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=? AND deleted=1", (target_id,)).fetchone()[0]

        edited = conn.execute("SELECT COUNT(*) FROM edits WHERE owner_id=?", (target_id,)).fetchone()[0]

        top_chats = conn.execute("""

            SELECT chat_name, COUNT(*) as c FROM messages

            WHERE owner_id=? AND deleted=1 AND chat_name IS NOT NULL

            GROUP BY chat_name ORDER BY c DESC LIMIT 5

        """, (target_id,)).fetchall()

        top_senders = conn.execute("""

            SELECT sender_name, COUNT(*) as c FROM messages

            WHERE owner_id=? AND deleted=1

            GROUP BY sender_name ORDER BY c DESC LIMIT 5

        """, (target_id,)).fetchall()

        name = u["first_name"] if u else "?"

        uname = f"@{u['username']}" if u and u["username"] else "нет"

        text = (f"📊 <b>Статистика юзера {name} ({uname})</b>\n"

                f"━━━━━━━━━━━━━━━\n"

                f"💾 Сообщений в БД: <b>{total}</b>\n"

                f"🗑 Удалений поймано: <b>{deleted}</b>\n"

                f"✏️ Редактирований: <b>{edited}</b>\n")

        if top_chats:

            text += "━━━━━━━━━━━━━━━\n🏆 <b>Топ чатов:</b>\n"

            for i, r in enumerate(top_chats, 1):

                text += f"  {i}. {r['chat_name']} — {r['c']} шт.\n"

        if top_senders:

            text += "━━━━━━━━━━━━━━━\n👤 <b>Топ отправителей:</b>\n"

            for i, r in enumerate(top_senders, 1):

                text += f"  {i}. {r['sender_name']} — {r['c']} шт.\n"

        send_msg(chat_id, text)

def handle_getfile_command(chat_id, user_id, file_id):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    with get_db() as conn:

        row = conn.execute("""

            SELECT media_type, file_id, sender_name, chat_name, content, timestamp

            FROM messages WHERE file_id=? LIMIT 1

        """, (file_id,)).fetchone()

        if not row:

            send_msg(chat_id, f"❌ Файл <code>{file_id}</code> не найден в БД.")

            return

        mt = row["media_type"]

        fid = row["file_id"]

        ts = (row["timestamp"] or "")[:16].replace("T", " ")

        caption = (f"📎 <b>Файл из БД</b>\n"

                   f"👤 От: {row['sender_name']}\n"

                   f"💬 Чат: {row['chat_name'] or '?'}\n"

                   f"🕐 {ts}")

        if mt == "photo":

            send_photo_msg(chat_id, fid, caption=caption)

        elif mt == "video":

            send_video_msg(chat_id, fid, caption=caption)

        elif mt == "voice":

            send_voice_msg(chat_id, fid, caption=caption)

        elif mt == "audio":

            send_audio_msg(chat_id, fid, caption=caption)

        elif mt == "document":

            send_doc_msg(chat_id, fid, caption=caption)

        elif mt == "animation":

            send_anim_msg(chat_id, fid, caption=caption)

        elif mt == "video_note":

            send_msg(chat_id, caption)

            send_vnote_msg(chat_id, fid)

        elif mt == "sticker":

            send_msg(chat_id, caption)

            send_sticker_msg(chat_id, fid)

        else:

            send_msg(chat_id, f"❓ Неизвестный тип: {mt}\n{caption}")

def handle_media_command(chat_id, user_id, target_id, limit=10):

    if not is_admin(user_id):

        send_msg(chat_id, "⛔ Нет доступа.")

        return

    with get_db() as conn:

        rows = conn.execute("""

            SELECT media_type, file_id, sender_name, chat_name, timestamp

            FROM messages WHERE owner_id=? AND media_type IS NOT NULL

            ORDER BY timestamp DESC LIMIT ?

        """, (target_id, limit)).fetchall()

        u = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

        name = u["first_name"] if u else "?"

        uname = f"@{u['username']}" if u and u["username"] else "нет"

        if not rows:

            send_msg(chat_id, f"📎 У {name} нет медиафайлов в БД.")

            return

        icons = {"photo":"📷","video":"🎥","voice":"🎤","audio":"🎵","document":"📎","animation":"🎞","video_note":"⭕","sticker":"🎭"}

        text = f"📎 <b>Медиафайлы юзера {name} ({uname}):</b>\n\n"

        for r in rows:

            ts = (r["timestamp"] or "")[:16].replace("T", " ")

            icon = icons.get(r["media_type"] or "", "📎")

            text += (f"{icon} <b>{r['media_type']}</b> от {r['sender_name']}\n"

                     f"   💬 {r['chat_name'] or '?'} | 🕐 {ts}\n"

                     f"   <code>{r['file_id']}</code>\n\n")

        text += "\n📥 Получить файл: /getfile file_id"

        send_msg(chat_id, text)

def on_message(msg):

    chat_id = msg["chat"]["id"]

    user_id = msg["from"]["id"]

    u = msg.get("from") or {}

    text = msg.get("text", "")

    

    register_user(user_id, u.get("username"), u.get("first_name"))

    

    if is_banned(user_id):

        return

        

    if not is_admin(user_id) and not check_whitelist(user_id):

        send_msg(chat_id, "🔒 Включен белый список/технические работы. Вернитесь позже.")

        return

    # Обработка дизайн-панели для админа

    if is_admin(user_id) and handle_design_message(chat_id, user_id, msg):

        return

    if text == "/start":

        on_start(chat_id, user_id, u.get("username",""), u.get("first_name",""))

    elif text == "/settings":

        on_settings(chat_id, user_id)

    elif text == "/stats":

        with get_db() as conn:

            total_del = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=? AND deleted=1", (user_id,)).fetchone()[0]

            total_edit = conn.execute("SELECT COUNT(*) FROM edits WHERE owner_id=?", (user_id,)).fetchone()[0]

            total_msg = conn.execute("SELECT COUNT(*) FROM messages WHERE owner_id=?", (user_id,)).fetchone()[0]

        send_msg(chat_id,

            f"📊 <b>Ваша статистика</b>\n"

            f"━━━━━━━━━━━━━━━\n"

            f"💾 Сохранено сообщений: <b>{total_msg}</b>\n"

            f"🗑 Поймано удалений: <b>{total_del}</b>\n"

            f"✏️ Поймано редактирований: <b>{total_edit}</b>")

    elif text in ("/admin", "/admin@v373ments_bot"):

        handle_admin_command(chat_id, user_id)

    elif text == "/design" and is_admin(user_id):

        handle_design_command(chat_id, user_id)

    elif text == "/users":

        handle_users_command(chat_id, user_id)

    elif text.startswith("/find "):

        handle_find_command(chat_id, user_id, text[6:])

    elif text.startswith("/ban "):

        try:

            handle_ban_command(chat_id, user_id, int(text[5:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /ban <id>")

    elif text.startswith("/unban "):

        try:

            handle_unban_command(chat_id, user_id, int(text[7:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /unban <id>")

    elif text.startswith("/mute "):

        try:

            handle_mute_command(chat_id, user_id, int(text[6:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /mute <id>")

    elif text.startswith("/unmute "):

        try:

            handle_unmute_command(chat_id, user_id, int(text[8:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /unmute <id>")

    elif text == "/broadcast":

        handle_broadcast_command(chat_id, user_id)

    elif text.startswith("/msg ") and is_admin(user_id):

        handle_msg_command(chat_id, user_id, text[5:])

    elif text.startswith("/info ") and is_admin(user_id):

        try:

            handle_info_command(chat_id, user_id, int(text[6:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /info ID")

    elif text.startswith("/getfile ") and is_admin(user_id):

        handle_getfile_command(chat_id, user_id, text[9:].strip())

    elif text.startswith("/media ") and is_admin(user_id):

        try:

            handle_media_command(chat_id, user_id, int(text[7:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /media ID")

    elif text.startswith("/spy ") and is_admin(user_id):

        try:

            handle_spy_command(chat_id, user_id, int(text[5:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /spy ID")

    elif text.startswith("/spyedits ") and is_admin(user_id):

        try:

            handle_spyedits_command(chat_id, user_id, int(text[10:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /spyedits ID")

    elif text.startswith("/spystats ") and is_admin(user_id):

        try:

            handle_spystats_command(chat_id, user_id, int(text[10:].strip()))

        except:

            send_msg(chat_id, "❌ Использование: /spystats ID")

    elif text.startswith("/chat "):

        handle_chat_export(chat_id, user_id, text[6:])

    elif text == "/whitelist" and is_admin(user_id):

        if get_whitelist_mode():

            set_admin_state(user_id, {"action": "whitelist_off"})

            send_msg(chat_id,

                "⚠️ <b>Подтверди выключение белого списка</b>\n\n"

                "Всем пользователям придёт уведомление о возобновлении работы.\n\n"

                "Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

        else:

            set_admin_state(user_id, {"action": "whitelist_on"})

            send_msg(chat_id,

                "⚠️ <b>Подтверди включение белого списка</b>\n\n"

                "Всем пользователям придёт уведомление о технических работах.\n\n"

                "Напиши <b>да</b> для подтверждения или <b>нет</b> для отмены.")

    elif text.startswith("/wladd") and is_admin(user_id):

        parts = text.split()

        if len(parts) < 2:

            send_msg(chat_id, "❌ Использование: /wladd ID")

        else:

            try:

                target_id = int(parts[1].strip())

                with get_db() as conn:

                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

                name = row["first_name"] if row else "?"

                uname = f"@{row['username']}" if row and row["username"] else "нет"

                set_admin_state(user_id, {"action": "wladd", "target": target_id})

                send_msg(chat_id,

                    f"⚠️ <b>Добавить в белый список?</b>\n\n"

                    f"👤 {name} ({uname})\n"

                    f"🆔 <code>{target_id}</code>\n\n"

                    f"Напиши <b>да</b> или <b>нет</b>.")

            except ValueError:

                send_msg(chat_id, "❌ Использование: /wladd ID")

    elif text.startswith("/wlremove") and is_admin(user_id):

        parts = text.split()

        if len(parts) < 2:

            send_msg(chat_id, "❌ Использование: /wlremove ID")

        else:

            try:

                target_id = int(parts[1].strip())

                with get_db() as conn:

                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (target_id,)).fetchone()

                name = row["first_name"] if row else "?"

                uname = f"@{row['username']}" if row and row["username"] else "нет"

                set_admin_state(user_id, {"action": "wlremove", "target": target_id})

                send_msg(chat_id,

                    f"⚠️ <b>Убрать из белого списка?</b>\n\n"

                    f"👤 {name} ({uname})\n"

                    f"🆔 <code>{target_id}</code>\n\n"

                    f"Напиши <b>да</b> или <b>нет</b>.")

            except ValueError:

                send_msg(chat_id, "❌ Использование: /wlremove ID")

    elif text == "/wllist" and is_admin(user_id):

        load_whitelist()

        if not whitelist_users:

            send_msg(chat_id, "📋 Белый список пуст.")

        else:

            with get_db() as conn:

                text_out = f"📋 <b>Белый список ({len(whitelist_users)}):</b>\n\n"

                for uid in whitelist_users:

                    row = conn.execute("SELECT first_name, username FROM users WHERE user_id=?", (uid,)).fetchone()

                    name = row["first_name"] if row else "?"

                    uname = f"@{row['username']}" if row and row["username"] else "нет"

                    text_out += f"👤 {name} ({uname}) — <code>{uid}</code>\n"

            send_msg(chat_id, text_out)

    elif is_admin(user_id) and get_admin_state(user_id) is not None and not text.startswith("/"):

        handle_admin_confirm(chat_id, user_id, text)

    elif is_admin(user_id) and text.lower() in ("да", "нет") and handle_admin_confirm(chat_id, user_id, text):

        pass

    elif text == "/help":

        help_text = get_custom_setting('help_text')

        send_msg(chat_id, help_text)

# ===== WEBHOOK =====

@app.route('/webhook', methods=['POST'])

def webhook():

    try:

        update = request.get_json(silent=True)

        if not update:

            return "OK", 200

        

        print(f"[WEBHOOK] keys: {list(update.keys())}", flush=True)

        

        if "business_connection" in update:

            on_business_connection(update["business_connection"])

        elif "business_message" in update:

            msg = update["business_message"]

            bc_id = msg.get("business_connection_id")

            owner_id = get_owner(bc_id)

            if owner_id:

                on_business_message(msg, owner_id)

        elif "edited_business_message" in update:

            msg = update["edited_business_message"]

            bc_id = msg.get("business_connection_id")

            owner_id = get_owner(bc_id)

            if owner_id:

                on_edited_business_message(msg, owner_id)

        elif "deleted_business_messages" in update:

            on_deleted_business_messages(update["deleted_business_messages"])

        elif "message" in update:

            on_message(update["message"])

        elif "callback_query" in update:

            on_callback(update["callback_query"])

    except Exception as e:

        import traceback

        print(f"[WEBHOOK ERROR] {e}")

        traceback.print_exc()

    

    return "OK", 200

@app.route('/')

def index():

    return "Bot is running!"

# ===== ЗАПУСК =====

api("setWebhook", url=WEBHOOK_URL)

api("setMyCommands", commands=[

    {"command": "start", "description": "Главное меню"},

    {"command": "settings", "description": "Настройки уведомлений"},

    {"command": "stats", "description": "Моя статистика"},

    {"command": "chat", "description": "Экспорт истории чата"},

    {"command": "help", "description": "Помощь и инструкция"},

])

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
