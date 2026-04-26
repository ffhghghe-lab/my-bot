import asyncio
import sqlite3
import os
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662 

# Пытаемся найти место для сохранения
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# ТЕСТ ПРОВЕРКА: Создаем пустой файл, чтобы увидеть его в списке файлов
try:
    with open(os.path.join(BASE_DIR, "PROVERKA.txt"), "w") as f:
        f.write("Файлы создаются!")
except Exception as e:
    print(f"Ошибка записи файла: {e}")

TASKS = [
    {"id": "-1003923958803", "url": "https://t.me", "name": "Спонсор #1 🛡️", "reward": 0.15},
]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, points REAL DEFAULT 0, referrer_id INTEGER, tasks_done INTEGER DEFAULT 0, username TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS completed_tasks 
                      (user_id INTEGER, task_id TEXT, PRIMARY KEY (user_id, task_id))''')
    conn.commit()
    conn.close()

def get_points(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return round(res[0], 2) if res else 0.0

def add_points(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, points, tasks_done) VALUES (?, 0, 0)', (user_id,))
    cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

# --- МЕНЮ ---
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Мои Stars"), KeyboardButton(text="📝 Задания")],
        [KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="📁 Где база?")]
    ],
    resize_keyboard=True
)

@dp.message(F.text == "📁 Где база?")
async def where_is_db(message: types.Message):
    exists = "ЕСТЬ" if os.path.exists(DB_PATH) else "НЕТУ"
    await message.answer(f"📍 **Путь к папке:** `{BASE_DIR}`\n\n📄 **Файл базы:** `{DB_PATH}`\n\n🔎 **Статус:** {exists}", parse_mode="Markdown")

@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    args = command.args
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
    is_old = cursor.fetchone()
    
    if not is_old:
        ref_id = int(args) if args and args.isdigit() and int(args) != user_id else None
        cursor.execute('INSERT INTO users (id, points, referrer_id, tasks_done, username) VALUES (?, 2.0, ?, 0, ?)', 
                       (user_id, ref_id, username))
        conn.commit()
        await message.answer("🌟 Добро пожаловать! Начислен бонус **2.0 Stars** ⭐", reply_markup=menu_kb, parse_mode="Markdown")
    else:
        cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        conn.commit()
        await message.answer("С возвращением в Free Stars! 🌟", reply_markup=menu_kb)
    conn.close()

@dp.message(Command("pay"))
async def admin_pay(message: types.Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID: return 
    try:
        args = command.args.split()
        target_id, amount = int(args[0]), float(args[1])
        add_points(target_id, amount)
        await message.answer(f"✅ Начислено {amount} пользователю {target_id}")
    except:
        await message.answer("Ошибка! Пример: `/pay 12345 100`", parse_mode="Markdown")

@dp.message(F.text == "🏆 Топ")
async def show_leaderboard(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT username, points FROM users ORDER BY points DESC LIMIT 10')
    top_users = cursor.fetchall()
    conn.close()
    text = "🏆 **Таблица лидеров**\n\n"
    for i, (name, points) in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {name} — `{round(points, 2)}` ⭐\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance_btn(message: types.Message):
    balance = get_points(message.from_user.id)
    await message.answer(f"Твой баланс: {balance} Stars ⭐")

@dp.message(F.text == "🛒 Магазин")
async def shop(message: types.Message):
    shop_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧸 Мишка (15)", callback_data="buy_bear")],
        [InlineKeyboardButton(text="❤️ Сердечко (15)", callback_data="buy_heart")],
        [InlineKeyboardButton(text="🍾 Шампанское (45)", callback_data="buy_wine")],
        [InlineKeyboardButton(text="🚀 Ракета (44)", callback_data="buy_rocket")]
    ])
    await message.answer("🛒 **Магазин Подарков**", reply_markup=shop_kb)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    items = {"buy_bear": ("Мишку", 15), "buy_heart": ("Сердечко", 15), "buy_wine": ("Шампанское", 45), "buy_rocket": ("Ракету", 44)}
    name, price = items[callback.data]
    if get_points(callback.from_user.id) >= price:
        add_points(callback.from_user.id, -price)
        await callback.message.answer(f"✅ Куплено: {name}!")
        await bot.send_message(ADMIN_ID, f"💰 КУПИЛИ: {name}\nID: `{callback.from_user.id}`", parse_mode="Markdown")
    else:
        await callback.answer("❌ Мало Stars!", show_alert=True)

@dp.message(F.text == "📝 Задания")
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT task_id FROM completed_tasks WHERE user_id = ?', (user_id,))
    done_ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    available = [t for t in TASKS if t["id"] not in done_ids]
    if not available: return await message.answer("✅ Все задания выполнены!")
    task = available[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Подписаться", url=task["url"])],
        [InlineKeyboardButton(text="2. Проверить ✅", callback_data=f"check_{task['id']}")]
    ])
    await message.answer(f"🚀 Задание: {task['name']}\nНаграда: {task['reward']} Stars", reply_markup=kb)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
