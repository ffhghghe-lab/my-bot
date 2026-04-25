import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662 

# Список твоих спонсоров с твоим ID
TASKS = [
    {
        "id": "-1003923958803", 
        "url": "https://t.me", # Твоя ссылка на канал
        "name": "Спонсор #1 🛡️", 
        "reward": 0.15
    },
]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points REAL DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS completed_tasks (user_id INTEGER, task_id TEXT, PRIMARY KEY (user_id, task_id))')
    conn.commit()
    conn.close()

def get_points(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return round(res[0], 2) if res else 0.0

def add_points(user_id, amount):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, points) VALUES (?, 0)', (user_id,))
    cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def is_task_done(user_id, task_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM completed_tasks WHERE user_id = ? AND task_id = ?', (user_id, str(task_id)))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def mark_task_done(user_id, task_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO completed_tasks (user_id, task_id) VALUES (?, ?)', (user_id, str(task_id)))
    conn.commit()
    conn.close()

# --- МЕНЮ ---
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Мои Stars"), KeyboardButton(text="📝 Задания")],
        [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="ℹ️ Инфо")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    add_points(message.from_user.id, 0)
    await message.answer("🌟 Добро пожаловать в **Free Stars**!", reply_markup=menu_kb, parse_mode="Markdown")

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    balance = get_points(message.from_user.id)
    await message.answer(f"Твой баланс: {balance} Stars ⭐")

@dp.message(F.text == "📝 Задания")
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    available_tasks = [t for t in TASKS if not is_task_done(user_id, t["id"])]
    
    if not available_tasks:
        return await message.answer("✅ Ты выполнил все задания!")

    task = available_tasks[0]
    task_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Подписаться 🛡️", url=task["url"])],
        [InlineKeyboardButton(text="2. Проверить ✅", callback_data=f"check_{task['id']}")]
    ])
    
    await message.answer(f"🚀 **Задание:**\nПодпишись и получи **{task['reward']} Stars**!", reply_markup=task_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("check_"))
async def check_sub(callback: types.CallbackQuery):
    task_id = callback.data.replace("check_", "")
    user_id = callback.from_user.id
    task_data = next((t for t in TASKS if str(t["id"]) == task_id), None)
    
    try:
        member = await bot.get_chat_member(chat_id=task_id, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            add_points(user_id, task_data["reward"])
            mark_task_done(user_id, task_id)
            await callback.answer(f"✅ +{task_data['reward']} Stars!", show_alert=True)
            await callback.message.delete()
            await show_tasks(callback.message)
        else:
            await callback.answer("❌ Подписка не найдена!", show_alert=True)
    except Exception as e:
        await callback.answer(f"⚠️ Бот не видит админку в канале {task_id}", show_alert=True)

@dp.message(F.text == "ℹ️ Инфо")
async def info(message: types.Message):
    await message.answer("ℹ️ **Free Stars** — заработок Stars за подписки!\nПо вопросам: @твой_ник", parse_mode="Markdown")

@dp.message(F.text == "🛒 Магазин")
async def shop(message: types.Message):
    shop_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧸 Мишка (15)", callback_data="buy_bear")],
        [InlineKeyboardButton(text="🚀 Ракета (44)", callback_data="buy_rocket")]
    ])
    await message.answer("🛒 Магазин:", reply_markup=shop_kb)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    items = {"buy_bear": ("Мишку", 15), "buy_rocket": ("Ракету", 44)}
    name, price = items[callback.data]
    if get_points(callback.from_user.id) >= price:
        add_points(callback.from_user.id, -price)
        await callback.message.answer(f"✅ Куплено: {name}!")
        await bot.send_message(ADMIN_ID, f"💰 КУПКА: {name} от {callback.from_user.id}")
    else:
        await callback.answer("❌ Мало Stars!", show_alert=True)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
