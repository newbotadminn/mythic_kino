import asyncio
import logging
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, CallbackQuery

# Configuration
API_TOKEN = '7539576135:AAGRlLrhveBEwyE3-W8af47h_wdh4ZmnIS8'
ADMIN_IDS = {6891895481}
DB_FILE = "kino_users.db"
DB_PATH = "kino_data.db"
LOG_FILE = "bot_log.log"
CHANNELS = ["@MythicMovie_TV"]
START_TIME = datetime.now(timezone.utc)

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Bot and Dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# State Definitions
class UserState(StatesGroup):
    waiting_for_code = State()
    authenticated = State()

class Reklama(StatesGroup):
    waiting_for_media = State()
    waiting_for_text = State()
    waiting_for_button_count = State()
    waiting_for_button_name = State()
    waiting_for_button_url = State()

class ForwardReklama(StatesGroup):
    waiting_for_forward = State()

class NewKino(StatesGroup):
    code = State()
    name = State()
    video = State()

# Database Utilities
def init_db():
    """Initialize the database with required tables."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kino (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code INTEGER UNIQUE,
                    name TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    size TEXT,
                    duration TEXT,
                    views INTEGER DEFAULT 0,
                    quality TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS kino_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    search_query TEXT
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def add_quality_column():
    """Add quality column to kino table if it doesn't exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(kino)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'quality' not in columns:
                cursor.execute("ALTER TABLE kino ADD COLUMN quality TEXT")
                conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to add quality column: {e}")

def save_user_id(user_id: int):
    """Save a user ID to the database if not already present."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to save user ID {user_id}: {e}")

def get_users() -> list:
    """Retrieve all user IDs from the database."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Failed to retrieve users: {e}")
        return []

def get_kino_count() -> int:
    """Get the total number of movies in the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM kino")
            return cursor.fetchone()[0]
    except sqlite3.Error as e:
        logger.error(f"Failed to get kino count: {e}")
        return 0

def determine_quality(file_size_gb: float) -> str:
    """Determine video quality based on file size."""
    if file_size_gb < 0.5:
        return "480p"
    elif 0.5 <= file_size_gb < 1:
        return "720p"
    elif 1 <= file_size_gb < 1.5:
        return "720p + HD"
    elif 1.5 <= file_size_gb < 2:
        return "1080p"
    elif 2 <= file_size_gb < 2.5:
        return "1080p + HD"
    elif 2.5 <= file_size_gb < 3.5:
        return "2K"
    elif 3.5 <= file_size_gb < 10:
        return "4K"
    return "8K"

# Utility Functions
def is_valid_url(url: str) -> bool:
    """Validate URL format."""
    url_pattern = re.compile(r'^(https?://|t\.me/|@)[a-zA-Z0-9._-]+/?[a-zA-Z0-9._-]*$')
    return bool(url_pattern.match(url))

async def check_subscription(user_id: int) -> list:
    """Check if a user is subscribed to required channels."""
    not_subscribed = []
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                not_subscribed.append(channel)
        except TelegramBadRequest as e:
            logger.error(f"Error checking subscription for {channel}: {e}")
            not_subscribed.append(channel)
        except Exception as e:
            logger.warning(f"Unexpected error checking subscription for {channel}: {e}")
            not_subscribed.append(channel)
    return not_subscribed

async def prompt_subscription(message: types.Message, not_subscribed: list):
    """Prompt user to subscribe to required channels."""
    buttons = [[InlineKeyboardButton(text="📢 Kanal", url=f"https://t.me/{channel[1:]}")] for channel in not_subscribed]
    buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("🚀 Botdan foydalanish uchun quyidagi kanallarga a'zo bo‘ling.", reply_markup=keyboard)

def subscription_required(func):
    """Decorator to ensure user is subscribed to required channels."""
    async def wrapper(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        not_subscribed = await check_subscription(user_id)
        if not_subscribed:
            await prompt_subscription(message, not_subscribed)
        else:
            await func(message, state)
    return wrapper

# Handlers
@dp.message(Command("start"))
async def start_command(message: types.Message):
    """Handle /start command."""
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name or "Foydalanuvchi"
    not_subscribed = await check_subscription(user_id)

    if not_subscribed:
        await prompt_subscription(message, not_subscribed)
        return

    save_user_id(user_id)
    welcome_message = (
        f"🎉 <b>Assalomu alaykum, {user_first_name}!</b>\n"
        "🎬 <b>Kino Botiga xush kelibsiz!</b>\n\n"
        "<code>🔍 Qanday ishlaydi?</code>\n"
        "- Kino nomini yoki kodini yuborasiz.\n"
        "- Bot sizga kerakli kinoni topib beradi.\n\n"
        "⚡️ Endi kino izlashni boshlashingiz mumkin!\n\n"
        "<b>💡 Taklif:</b>\n"
        "<a href='https://t.me/MythicMovieBot'>🎥 @MythicMovieBot</a>\n"
        "<i>(Kino va seriallar uchun eng yaxshi bot)</i>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 Kinolar kanali", url="https://t.me/MythicMovie_TV")]
    ])
    await message.answer(welcome_message, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, state: FSMContext):
    """Handle subscription check callback."""
    user_id = callback.from_user.id
    not_subscribed = await check_subscription(user_id)

    if not not_subscribed:
        await callback.message.delete()
        save_user_id(user_id)
        await callback.message.answer(
            "✅ Obuna muvaffaqiyatli tasdiqlandi!\n"
            "🎉 Botdan foydalanishga tayyormisiz!\n"
            "🔍 Kino nomini yoki kodini yuboring.",
            parse_mode="HTML"
        )
        await state.set_state(UserState.waiting_for_code)
    else:
        await prompt_subscription(callback.message, not_subscribed)
    await callback.answer()

@dp.message(Command("status"))
@subscription_required
async def get_status(message: types.Message, state: FSMContext):
    """Handle /status command for admins."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 <b>Bu komanda faqat adminlar uchun!</b>", parse_mode="HTML")
        return

    user_count = len(get_users())
    kino_count = get_kino_count()
    uptime = str(timedelta(seconds=int((datetime.now(timezone.utc) - START_TIME).total_seconds())))
    server_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    status_message = (
        "<b>📊 BOT HOLATI:</b>\n\n"
        "───────────────────────\n"
        f"👥 Foydalanuvchilar soni: <b>{user_count}</b> ta\n"
        f"🎬 Kinolar soni: <b>{kino_count}</b> ta\n"
        f"⏰ Ish vaqti: <b>{uptime}</b>\n"
        f"🌐 Server vaqti (UTC): <b>{server_time}</b>\n"
        f"🤖 Bot ishga tushgan vaqti: <b>{START_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')}</b>\n"
        "───────────────────────\n"
        "🌟 Holat: <b>Ishlayapti</b>\n"
        "💡 Izoh: Muvaffaqiyatli ishlayapti!"
    )
    await message.answer(status_message, parse_mode="HTML")

@dp.message(Command("logs"))
async def logs_handler(message: types.Message):
    """Handle /logs command for admins."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Siz bu buyruqdan foydalanishga ruxsatga ega emassiz.")
        return

    try:
        error_count, info_count, warning_count, debug_count, total_logs = 0, 0, 0, 0, 0
        date_counter = Counter()

        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as log_file:
                lines = log_file.readlines()
                total_logs = len(lines)
                for line in lines[:-5]:
                    match = re.search(r"(\d{4}-\d{2}-\d{2})", line)
                    if match:
                        date_counter[match.group(1)] += 1
                    if "ERROR" in line:
                        error_count += 1
                    elif "INFO" in line:
                        info_count += 1
                    elif "WARNING" in line:
                        warning_count += 1
                    elif "DEBUG" in line:
                        debug_count += 1

        most_common_date, most_common_count = date_counter.most_common(1)[0] if date_counter else ("Noma'lum", 0)
        log_stats = (
            "📊 *Log Statistikasi:*\n"
            f"📝 *Umumiy loglar:* {total_logs}\n"
            "--------------------------------\n"
            f"ℹ️ *INFO:* {info_count}\n"
            f"⚠️ *WARNING:* {warning_count}\n"
            f"🐞 *DEBUG:* {debug_count}\n"
            f"❌ *ERROR:* {error_count}\n"
            "--------------------------------\n"
            f"📅 *Eng ko‘p log yozilgan sana:* {most_common_date} ({most_common_count} ta log)"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Loglarni tozalash", callback_data="clear_logs")],
            [InlineKeyboardButton(text="📥 Loglarni yuklab olish", callback_data="download_logs")],
            [InlineKeyboardButton(text="📥 IDlarni yuklash", callback_data="download_ids")]
        ])
        await message.answer(log_stats, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in /logs command: {e}")
        await message.answer("❌ Loglarni o‘qishda xatolik yuz berdi.")

@dp.callback_query(F.data == "clear_logs")
async def confirm_clear_logs(callback: CallbackQuery):
    """Confirm log clearing action."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Siz bu funksiyadan foydalana olmaysiz!", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha", callback_data="confirm_clear_logs")],
        [InlineKeyboardButton(text="❌ Yo‘q", callback_data="cancel_clear_logs")]
    ])
    await callback.message.edit_text("🗑 *Aniq loglarni tozalaysizmi?*", parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "confirm_clear_logs")
async def clear_logs_handler(callback: CallbackQuery):
    """Handle log clearing."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Siz bu funksiyadan foydalana olmaysiz!", show_alert=True)
        return
    try:
        if os.path.exists(LOG_FILE):
            open(LOG_FILE, "w").close()
            logger.info("Log file cleared.")
            await callback.message.edit_text("✅ Barcha loglar muvaffaqiyatli tozalandi.")
        else:
            await callback.message.edit_text("ℹ️ Log fayli allaqachon bo'sh.")
    except Exception as e:
        logger.error(f"Error clearing Logs: {e}")
        await callback.message.edit_text("❌ Loglarni tozalashda xatolik yuz berdi.")

@dp.callback_query(F.data == "cancel_clear_logs")
async def cancel_clear_logs(callback: CallbackQuery):
    """Cancel log clearing."""
    await callback.message.edit_text("❌ Loglarni tozalash bekor qilindi.")

@dp.callback_query(F.data == "download_logs")
async def download_logs_handler(callback: CallbackQuery):
    """Handle log download."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Siz bu funksiyadan foydalana olmaysiz!", show_alert=True)
        return
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
            log_file = FSInputFile(LOG_FILE, filename="Loglar.log")
            await callback.message.answer_document(log_file, caption="📂 Log faylingiz.")
        else:
            await callback.answer("ℹ️ Log fayli mavjud emas yoki bo'sh.", show_alert=True)
    except Exception as e:
        logger.error(f"Error downloading logs: {e}")
        await callback.message.answer("❌ Loglarni yuklab olishda xatolik yuz berdi.")

@dp.callback_query(F.data == "download_ids")
async def download_ids_handler(callback: CallbackQuery):
    """Handle user IDs download."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Siz bu funksiyadan foydalana olmaysiz!", show_alert=True)
        return
    try:
        if os.path.exists("users.json") and os.path.getsize("users.json") > 0:
            id_file = FSInputFile("users.json", filename="IDlar.json")
            await callback.message.answer_document(id_file, caption="📂 ID faylingiz.")
        else:
            await callback.answer("ℹ️ ID fayli mavjud emas yoki bo'sh.", show_alert=True)
    except Exception as e:
        logger.error(f"Error downloading IDs: {e}")
        await callback.message.answer("❌ IDlarni yuklab olishda xatolik yuz berdi.")

@dp.message(Command("rek"))
@subscription_required
async def start_reklama(message: types.Message, state: FSMContext):
    """Handle /rek command for sending advertisements."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 Bu komanda faqat adminlar uchun!")
        return
    await message.answer(
        "📎 Iltimos, quyidagi fayllardan birini yuboring:\n🎨 Rasm | 🎥 Video | 🎞 GIF | 🎵 Audio | 📂 Fayl\n"
        "/allrek - Barcha turdagi reklamalarni yuborish (Uzatilgan habar usulida)!"
    )
    await state.set_state(Reklama.waiting_for_media)

@dp.message(Reklama.waiting_for_media)
async def handle_media(message: types.Message, state: FSMContext):
    """Handle media input for advertisements."""
    media_types = {
        ContentType.PHOTO: message.photo[-1].file_id if message.photo else None,
        ContentType.VIDEO: message.video.file_id if message.video else None,
        ContentType.ANIMATION: message.animation.file_id if message.animation else None,
        ContentType.AUDIO: message.audio.file_id if message.audio else None,
        ContentType.DOCUMENT: message.document.file_id if message.document else None
    }
    media = next((file_id for content_type, file_id in media_types.items() if file_id), None)

    if not media:
        await message.answer("❌ Noto‘g‘ri format! Iltimos, rasm, video, gif, audio yoki fayl yuboring.")
        return

    await state.update_data(media=media, media_type=message.content_type)
    await message.answer("📝 Endi reklama matnini yuboring:")
    await state.set_state(Reklama.waiting_for_text)

@dp.message(Reklama.waiting_for_text)
async def handle_text(message: types.Message, state: FSMContext):
    """Handle text input for advertisements."""
    if not message.text:
        await message.answer("❌ Iltimos, reklama matnini kiriting!")
        return
    await state.update_data(text=message.text)
    await message.answer("🔢 Tugmalar sonini kiriting (1-10):")
    await state.set_state(Reklama.waiting_for_button_count)

@dp.message(Reklama.waiting_for_button_count)
async def handle_button_count(message: types.Message, state: FSMContext):
    """Handle button count input for advertisements."""
    try:
        button_count = int(message.text)
        if not 1 <= button_count <= 10:
            await message.answer("❌ Tugmalar soni 1 dan 10 gacha bo‘lishi kerak.")
            return
    except ValueError:
        await message.answer("❌ Iltimos, tugma sonini raqam sifatida kiriting!")
        return

    await state.update_data(button_count=button_count, buttons=[])
    await message.answer("🔗 1-tugma nomini kiriting:")
    await state.set_state(Reklama.waiting_for_button_name)

@dp.message(Reklama.waiting_for_button_name)
async def handle_button_name(message: types.Message, state: FSMContext):
    """Handle button name input for advertisements."""
    if not message.text:
        await message.answer("❌ Tugma nomini kiriting!")
        return
    data = await state.get_data()
    buttons = data.get("buttons", [])
    buttons.append({"name": message.text})
    await state.update_data(buttons=buttons)
    await message.answer(f"🌐 \"{message.text}\" tugmasining URL manzilini kiriting:\nFormatlar: https://, http://, t.me/, @")
    await state.set_state(Reklama.waiting_for_button_url)

@dp.message(Reklama.waiting_for_button_url)
async def handle_button_url(message: types.Message, state: FSMContext):
    """Handle button URL input for advertisements."""
    url = message.text.strip()
    if not is_valid_url(url):
        await message.answer("❌ Noto‘g‘ri URL formati! Quyidagi formatlardan foydalaning: https://, http://, t.me/, @")
        return

    data = await state.get_data()
    buttons = data.get("buttons", [])
    buttons[-1]["url"] = url
    if len(buttons) < data.get("button_count"):
        await message.answer(f"🔗 {len(buttons) + 1}-tugma nomini kiriting:")
        await state.set_state(Reklama.waiting_for_button_name)
    else:
        await send_reklama(message, state)

async def send_reklama(message: types.Message, state: FSMContext):
    """Send advertisement to all users."""
    data = await state.get_data()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn["name"], url=btn["url"])] for btn in data.get("buttons", [])
    ])
    users = get_users()
    if not users:
        await message.answer("❌ Foydalanuvchilar ro‘yxati bo‘sh!")
        await state.clear()
        return

    successful_sends, failed_sends = 0, 0
    send_methods = {
        ContentType.PHOTO: bot.send_photo,
        ContentType.VIDEO: bot.send_video,
        ContentType.ANIMATION: bot.send_animation,
        ContentType.AUDIO: bot.send_audio,
        ContentType.DOCUMENT: bot.send_document
    }
    send_method = send_methods.get(data["media_type"])

    for user_id in users:
        try:
            await send_method(chat_id=user_id, **{data["media_type"]: data["media"]}, caption=data["text"], reply_markup=keyboard)
            successful_sends += 1
            await asyncio.sleep(0.05)  # Rate limiting to avoid Telegram API restrictions
        except Exception as e:
            logger.error(f"Failed to send reklama to {user_id}: {e}")
            failed_sends += 1

    await state.clear()
    await message.answer(
        f"✅ Reklama yuborildi!\n"
        f"📊 Yuborilganlar: {successful_sends}\n"
        f"❌ Xatolar: {failed_sends}"
    )

@dp.message(Command("allrek"))
@subscription_required
async def start_forward_reklama(message: types.Message, state: FSMContext):
    """Handle /allrek command for forwarding advertisements."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 Bu komanda faqat adminlar uchun!")
        return
    await message.answer("📝 Iltimos, forward qilgan habaringizni yuboring:")
    await state.set_state(ForwardReklama.waiting_for_forward)

@dp.message(ForwardReklama.waiting_for_forward)
async def handle_forward_reklama(message: types.Message, state: FSMContext):
    """Handle forwarded advertisement message."""
    if not message.forward_from and not message.forward_from_chat:
        await message.answer("❌ Iltimos, forward qilingan habar yuboring!")
        return
    await state.update_data(forward_message=message.model_dump_json())
    await send_forward_reklama(message, state)

async def send_forward_reklama(message: types.Message, state: FSMContext):
    """Forward advertisement to all users."""
    data = await state.get_data()
    forward_message = types.Message.model_validate_json(data.get("forward_message"))
    users = get_users()
    if not users:
        await message.answer("❌ Foydalanuvchilar ro‘yxati bo‘sh!")
        await state.clear()
        return

    successful_sends, failed_sends = 0, 0
    for user_id in users:
        try:
            await bot.forward_message(
                chat_id=user_id,
                from_chat_id=forward_message.chat.id,
                message_id=forward_message.message_id
            )
            successful_sends += 1
            await asyncio.sleep(0.05)  # Rate limiting
        except Exception as e:
            logger.error(f"Failed to forward reklama to {user_id}: {e}")
            failed_sends += 1

    await state.clear()
    await message.answer(
        f"✅ Forward qilingan habar yuborildi!\n"
        f"📊 Yuborilganlar: {successful_sends}\n"
        f"❌ Xatolar: {failed_sends}"
    )

@dp.message(Command("help"))
@subscription_required
async def help_command(message: types.Message, state: FSMContext):
    """Handle /help command."""
    user_commands = (
        "📌 <b>Foydalanuvchilar uchun buyruqlar:</b>\n\n"
        "🚀 <b>/start</b> - Botni ishga tushirish\n"
        "ℹ️ <b>/help</b> - Bot haqida ma'lumot\n"
        "👑 <b>/admin</b> - Admin bilan bog‘lanish, hamkorlik uchun\n"
        "🎥 <b>/top</b> - Eng ko‘p ko‘rilgan kinolar ro‘yxati\n"
        "🔗 <b>/kerakli</b> - Kerakli kanallar ro‘yxati\n"
    )
    admin_commands = (
        "\n🎩 <b>Adminlar uchun buyruqlar:</b>\n\n"
        "🎬 <b>/newkino</b> - Yangi kino qo‘shish\n"
        "🎁 <b>/rek</b> - Reklama yuborish\n"
        "📤 <b>/allrek</b> - Forward qilingan reklama yuborish\n"
        "⚡️ <b>/status</b> - Bot holatini ko‘rsatish\n"
        "📑 <b>/logs</b> - Log fayllarni ko‘rsatish\n"
    )
    help_text = user_commands + (admin_commands if message.from_user.id in ADMIN_IDS else "")
    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("admin"))
@subscription_required
async def admin_command(message: types.Message, state: FSMContext):
    """Handle /admin command."""
    admin_info = {
        "name": "Mukhammadsolixon",
        "surname": "Muminov",
        "phone": "+998 95 150 64 65",
        "gmail": "uzsenior0@gmail.com",
    }
    admin_text = (
        f"👤 <b>Admin haqida ma'lumot:</b>\n\n"
        f"👨‍💼 <b>Ismi:</b> {admin_info['name']}\n"
        f"👨‍💼 <b>Familya:</b> {admin_info['surname']}\n"
        f"📞 <b>Telefon raqam:</b> <code>{admin_info['phone']}</code>\n"
        f"📧 <b>Gmail pochta:</b> {admin_info['gmail']}\n\n"
        f"📲 <b>Bog'lanish uchun tugmalardan foydalaning:</b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Telegram", url="https://t.me/Mr_MomimovJonah")],
        [InlineKeyboardButton(text="📸 Instagram", url="https://www.instagram.com/kinochiman_tv/")],
        [InlineKeyboardButton(text="📧 Gmail orqali bog‘lanish", url=f"https://mail.google.com/mail/?view=cm&fs=1&to={admin_info['gmail']}")]
    ])
    await message.answer(admin_text, parse_mode="HTML", reply_markup=keyboard)

@dp.message(Command("newkino"))
@subscription_required
async def start_new_kino(message: types.Message, state: FSMContext):
    """Boshlang‘ich yangi kino qo‘shish funksiyasi, faqat adminlar uchun."""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>Sizga bu buyruqdan foydalanish taqiqlangan!</b>", parse_mode="HTML")
        return

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT code, name FROM kino ORDER BY id DESC LIMIT 1")
            last_kino = cursor.fetchone()
            kino_count = get_kino_count()

        if last_kino:
            kino_text = (
                f"🎬 <b>Oxirgi kino:</b> {last_kino[1]} | 📌 <b>Kod:</b> <code>{last_kino[0]}</code>\n"
                f"📊 <b>Jami kinolar soni:</b> <code>{kino_count}</code>"
            )
        else:
            kino_text = (
                "📭 <i>Hozircha hech qanday kino mavjud emas.</i>\n"
                f"📊 <b>Jami kinolar soni:</b> <code>{kino_count}</code>"
            )

        await message.answer(
            f"{kino_text}\n\n📌 <b>Yangi kino uchun <u>kod</u> kiriting:</b>",
            parse_mode="HTML"
        )
        await state.set_state(NewKino.code)
    except sqlite3.Error as e:
        logger.error(f"Error fetching last kino: {e}")
        await message.answer("❌ Ma'lumotlarni olishda xatolik yuz berdi.")

@dp.message(NewKino.code)
async def get_kino_code(message: types.Message, state: FSMContext):
    """Kino kodi kiritilganda tekshirish va keyingi bosqichga o'tish."""
    if not message.text.isdigit():
        await message.answer("<b>⚠️ Kino kodi faqat raqam bo‘lishi kerak! Qayta kiriting:</b>", parse_mode="HTML")
        return

    code = int(message.text)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM kino WHERE code = ?", (code,))
            if cursor.fetchone():
                await message.answer("<b>❌ Bunday kod bilan kino allaqachon mavjud!</b>", parse_mode="HTML")
                await state.clear()
                return

        await state.update_data(code=code)
        await message.answer("<b>📌 Kino nomini kiriting:</b>", parse_mode="HTML")
        await state.set_state(NewKino.name)
    except sqlite3.Error as e:
        logger.error(f"Error checking kino code: {e}")
        await message.answer("❌ Kodni tekshirishda xatolik yuz berdi.")

@dp.message(NewKino.name)
async def get_kino_name(message: types.Message, state: FSMContext):
    """Kino nomi qabul qilinadi."""
    name = message.text.strip()
    if not name:
        await message.answer("<b>⚠️ Iltimos, kino nomini kiriting!</b>", parse_mode="HTML")
        return

    await state.update_data(name=name)
    await message.answer("<b>📌 Kino videosini yuboring:</b>", parse_mode="HTML")
    await state.set_state(NewKino.video)

@dp.message(NewKino.video)
async def get_kino_video(message: types.Message, state: FSMContext):
    """Video qabul qilinib, kinoni bazaga qo'shish."""
    if not message.video:
        await message.answer("<b>⚠️ Iltimos, video fayl yuboring!</b>", parse_mode="HTML")
        return

    data = await state.get_data()
    file_id = message.video.file_id
    file_size_gb = round(message.video.file_size / (1024**3), 2)
    duration_min = round(message.video.duration / 60, 2)
    quality = determine_quality(file_size_gb)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO kino (code, name, file_id, size, duration, quality) VALUES (?, ?, ?, ?, ?, ?)",
                (data['code'], data['name'], file_id, f"{file_size_gb} GB", f"{duration_min} daqiqa", quality)
            )
            conn.commit()

        kino_count = get_kino_count()
        await message.answer(
            f"<b>✅ Kino muvaffaqiyatli qo‘shildi!</b>\n"
            f"🎬 <b>{data['name']}</b>\n"
            f"📌 <b>Kod:</b> <code>{data['code']}</code>\n"
            f"🎞️ <b>Sifat:</b> {quality}\n"
            f"📊 <b>Jami kinolar soni:</b> <code>{kino_count}</code>",
            parse_mode="HTML"
        )
    except sqlite3.IntegrityError:
        await message.answer("<b>❌ Bunday kod bilan kino allaqachon mavjud!</b>", parse_mode="HTML")
    except sqlite3.Error as e:
        logger.error(f"Error adding kino: {e}")
        await message.answer("❌ Kino qo‘shishda xatolik yuz berdi.")
    finally:
        await state.clear()

@dp.message(F.text)
async def search_kino(message: types.Message):
    """Kino qidirish — kod yoki nom bo'yicha."""
    search_query = message.text.strip()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            if search_query.isdigit():
                # Kod bo'yicha qidirish
                cursor.execute(
                    "SELECT name, file_id, size, views, quality FROM kino WHERE code = ?",
                    (int(search_query),)
                )
                kino = cursor.fetchone()
                if kino:
                    name, file_id, size, views, quality = kino
                    code = int(search_query)
                else:
                    kino = None
            else:
                # Nom bo'yicha qidirish
                cursor.execute(
                    "SELECT code, file_id, size, views, quality FROM kino WHERE name = ?",
                    (search_query,)
                )
                kino = cursor.fetchone()
                if kino:
                    code, file_id, size, views, quality = kino
                    name = search_query
                else:
                    # To'liq mos kelmaydiganlarni qidirish
                    cursor.execute(
                        "SELECT code, name, file_id, size, views, quality FROM kino WHERE name LIKE ?",
                        (f"%{search_query}%",)
                    )
                    results = cursor.fetchall()
                    if results:
                        for code, name, file_id, size, views, quality in results:
                            new_views = views + 1
                            cursor.execute("UPDATE kino SET views = ? WHERE code = ?", (new_views, code))
                            caption = (
                                f"🎬 <b>{name}</b>\n"
                                "━━━━━━━━━━━━━━━\n"
                                f"📌 <b>Kod:</b> {code}\n"
                                f"📂 <b>Hajmi:</b> {size}\n"
                                f"🎥 <b>Sifat:</b> {quality}\n"
                                f"👀 <b>Ko‘rishlar:</b> {new_views}\n"
                                "━━━━━━━━━━━━━━━\n"
                                "🔥 <i>@MythicMovieBot</i> <b>orqali yuklandi</b>"
                            )
                            await message.answer_video(file_id, caption=caption, parse_mode="HTML")
                        conn.commit()
                        return
                    kino = None

            if kino:
                new_views = views + 1
                cursor.execute("UPDATE kino SET views = ? WHERE code = ?", (new_views, code))
                conn.commit()
                caption = (
                    f"🎬 <b>{name}</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    f"📌 <b>Kod:</b> {code}\n"
                    f"📂 <b>Hajmi:</b> {size}\n"
                    f"🎥 <b>Sifat:</b> {quality}\n"
                    f"👀 <b>Ko‘rishlar:</b> {new_views}\n"
                    "━━━━━━━━━━━━━━━\n"
                    "🔥 <i>@MythicMovieBot</i> <b>orqali yuklandi</b>"
                )
                await message.answer_video(file_id, caption=caption, parse_mode="HTML")
            else:
                await message.answer(f"🚫 <b>Kechirasiz, <u>{search_query}</u> bo‘yicha kino topilmadi!</b>", parse_mode="HTML")

    except sqlite3.Error as e:
        logger.error(f"Error searching kino: {e}")
        await message.answer("❌ Kino qidirishda xatolik yuz berdi.")

@dp.message(Command("top"))
async def top_kino(message: types.Message):
    """Eng ko'p ko'rilgan kinolarni ro'yxatini ko'rsatish uchun /top buyrug'ini ishlaydi."""
    user_id = message.from_user.id
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Foydalanuvchi so'rovini kino_users jadvaliga qo'shish
            cursor.execute("INSERT INTO kino_users (user_id, search_query) VALUES (?, ?)", (user_id, "top"))
            # Eng ko'p ko'rilgan 10 ta kinoni olish
            cursor.execute("SELECT code, name, views FROM kino ORDER BY views DESC LIMIT 10")
            top_movies = cursor.fetchall()
            conn.commit()

        if top_movies:
            # Medallar ro'yxati (1-o'rin: 🥇, 2-o'rin: 🥈, 3-o'rin: 🥉, qolganlari: ⭐)
            medals = ["🥇", "🥈", "🥉"] + ["⭐"] * 7
            inline_buttons = [
                [InlineKeyboardButton(
                    text=f"{medals[i]} {name}  | 👀 {views}",
                    callback_data=f"show_kino_{code}"  # Kino kodini callback_data sifatida ishlatish
                )] for i, (code, name, views) in enumerate(top_movies)
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
            await message.answer(
                "🏆 <b>Eng Mashhur Kinolar Top 10</b>\n\n"
                "🎬 Quyidagi kinolardan birini tanlang va videosini tomosha qiling!\n"
                "👇 Tugmalardan birini bosing:",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await message.answer(
                "📭 <b>Hozircha mashhur kinolar mavjud emas!</b>\n"
                "🔄 Iltimos, keyinroq qayta urinib ko'ring.",
                parse_mode="HTML"
            )
    except sqlite3.Error as e:
        logger.error(f"Top kinolarni olishda xatolik: {e}")
        await message.answer("❌ Top kinolarni olishda xatolik yuz berdi!")

@dp.callback_query(lambda c: c.data.startswith("show_kino_"))
async def show_kino_callback(callback: types.CallbackQuery):
    """Tugma bosilganda kino videosini va ma'lumotlarini yuborish."""
    try:
        # Callback_data'dan kino kodini olish
        kino_code = int(callback.data.split("_")[-1])
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            # Kino ma'lumotlarini olish
            cursor.execute("SELECT name, file_id, size, views, quality FROM kino WHERE code = ?", (kino_code,))
            kino = cursor.fetchone()
            if kino:
                name, file_id, size, views, quality = kino
                # Ko'rishlar sonini yangilash
                new_views = views + 1
                cursor.execute("UPDATE kino SET views = ? WHERE code = ?", (new_views, kino_code))
                conn.commit()

                # Kino ma'lumotlarini tayyorlash
                caption = (
                    f"🎬 <b>{name}</b>\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"📌 <b>Kod:</b> {kino_code}\n"
                    f"📂 <b>Hajmi:</b> {size}\n"
                    f"🎥 <b>Sifat:</b> {quality}\n"
                    f"👀 <b>Ko‘rishlar:</b> {new_views}\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"🔥 <b>@MythicMovieBot</b> orqali yuklandi"
                )
                # Avvalgi xabarni o'chirish
                await callback.message.delete()
                # Kino videosini yuborish
                await callback.message.answer_video(
                    file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                await callback.message.edit_text(
                    f"🚫 <b>Kod: {kino_code} bo‘yicha kino topilmadi!</b>",
                    parse_mode="HTML"
                )
    except sqlite3.Error as e:
        logger.error(f"Kino ma'lumotlarini olishda xatolik: {e}")
        await callback.message.edit_text(
            "❌ Kino ma'lumotlarini olishda xatolik yuz berdi!",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Kino videosini yuborishda xatolik: {e}")
        await callback.message.edit_text(
            "❌ Kino videosini yuborishda xatolik yuz berdi!",
            parse_mode="HTML"
        )
    await callback.answer()

@dp.message(Command("kerakli"))
async def send_channel_link(message: types.Message):
    """Handle /kerakli command to share channel links."""
    text = (
        "🌟 <b>Kerakli Kanalimiz:</b>\n\n"
        "Siz uchun eng yaxshi kontentlar bizning kanalda kutib o'tiradi! 🎬\n"
        "Kanalga obuna bo'ling va yangiliklardan birinchi bo'lib xabardor bo'ling! 🔔\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kanalga o'tish", url="https://t.me/korean_dramma_uuz")],
        [InlineKeyboardButton(text="🎬 Kanalga o'tish", url="https://t.me/MythicMovie_TV")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

# Main Function
async def main():
    """Main function to start the bot."""
    try:
        init_db()
        add_quality_column()
        logger.info("Bot successfully started!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
