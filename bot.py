import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662 

# Список спонсоров (Чтобы рефералка работала на 3 заданиях, добавь сюда еще каналы)
TASKS = [
    {"id": "-1003923958803", "url": "https://t.me", "name": "Спонсор #1 🛡️", "reward": 0.15},
]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, points REAL DEFAULT 0, referrer_id INTEGER, tasks_done INTEGER DEFAULT 0)''')
    cursor.execute('CREATE TABLE IF NOT EXISTS completed_tasks (user_id INTEGER, task_id TEXT, PRIMARY KEY (user_id, task_id))')
    conn.commit()
    conn.close()

def is_new_user(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is None

def add_points(user_id, amount):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, points) VALUES (?, 0)', (user_id,))
    cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_points(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return round(res[0], 2) if res else 0.0

def mark_task_done(user_id, task_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO completed_tasks (user_id, task_id) VALUES (?, ?)', (user_id, str(task_id)))
    cursor.execute('UPDATE users SET tasks_done = tasks_done + 1 WHERE id = ?', (user_id,))
    
    cursor.execute('SELECT referrer_id, tasks_done FROM users WHERE id = ?', (user_id,))
    ref_data = cursor.fetchone()
    if ref_data and ref_data[0]:
        ref_id = ref_data[0]
        done_count = ref_data[1]
        if done_count == 3:
            cursor.execute('UPDATE users SET points = points + 1.5 WHERE id = ?', (ref_id,))
            asyncio.create_task(bot.send_message(ref_id, "🎁 Твой реферал выполнил 3 задания! Тебе начислено **1.5 Stars** ⭐", parse_mode="Markdown"))
    conn.commit()
    conn.close()

def is_task_done(user_id, task_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM completed_tasks WHERE user_id = ? AND task_id = ?', (user_id, str(task_id)))
    res = cursor.fetchone()
    conn.close()
    return res is not None

# --- МЕНЮ ---
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Мои Stars"), KeyboardButton(text="📝 Задания")],
        [KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="ℹ️ Инфо")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args
    if is_new_user(user_id):
        ref_id = int(args) if args and args.isdigit() and int(args) != user_id else None
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (id, points, referrer_id) VALUES (?, 2.0, ?)', (user_id, ref_id))
        conn.commit()
        conn.close()
        await message.answer("🌟 Добро пожаловать! Начислен бонус **2.0 Stars** ⭐", reply_markup=menu_kb)
        if ref_id:
            await bot.send_message(ref_id, "🔔 По твоей ссылке зашел новый друг! Как только он выполнит 3 задания, ты получишь 1.5 Stars.")
    else:
        await message.answer("С возвращением в Free Stars! 🌟", reply_markup=menu_kb)

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    await message.answer(f"Твой баланс: {get_points(message.from_user.id)} Stars ⭐")

@dp.message(F.text == "👥 Рефералы")
async def referral_menu(message: types.Message):
    me = await bot.get_me()
    await message.answer(f"👥 **Реферальная система**\n\nТвоя ссылка: `https://t.me{me.username}?start={message.from_user.id}`\n\nПригласи друга: если он выполнит **3 задания**, ты получишь **1.5 Stars** ⭐", parse_mode="Markdown")

@dp.message(F.text == "📝 Задания")
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    available = [t for t in TASKS if not is_task_done(user_id, t["id"])]
    if not available: return await message.answer("✅ Задания выполнены!")
    task = available[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Подписаться 🛡️", url=task["url"])],
        [InlineKeyboardButton(text="2. Проверить ✅", callback_data=f"check_{task['id']}")]
    ])
    await message.answer(f"🚀 Задание: {task['name']}\nНаграда: {task['reward']} Stars", reply_markup=kb)

@dp.callback_query(F.data.startswith("check_"))
async def check_sub(callback: types.CallbackQuery):
    t_id = callback.data.replace("check_", "")
    t_data = next((t for t in TASKS if str(t["id"]) == t_id), None)
    try:
        m = await bot.get_chat_member(chat_id=t_id, user_id=callback.from_user.id)
        if m.status in ["member", "administrator", "creator"]:
            add_points(callback.from_user.id, t_data["reward"])
            mark_task_done(callback.from_user.id, t_id)
            await callback.answer(f"✅ +{t_data['reward']} Stars!", show_alert=True)
            await callback.message.delete()
            await show_tasks(callback.message)
        else: await callback.answer("❌ Не подписан!", show_alert=True)
    except: await callback.answer("⚠️ Ошибка админки!", show_alert=True)

# --- ВОЗВРАЩЕННЫЙ МАГАЗИН ---
@dp.message(F.text == "🛒 Магазин")
async def shop(message: types.Message):
    shop_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧸 Мишка (15)", callback_data="buy_bear")],
        [InlineKeyboardButton(text="❤️ Сердечко (15)", callback_data="buy_heart")],
        [InlineKeyboardButton(text="🍾 Шампанское (45) 🔥", callback_data="buy_wine")],
        [InlineKeyboardButton(text="🚀 Ракета (44) 🔥", callback_data="buy_rocket")]
    ])
    await message.answer("🛒 **Магазин Free Stars**\n\n🧸 Мишка — 15\n❤️ Сердечко — 15\n🍾 Шампанское — 45 (СКИДКА!)\n🚀 Ракета — 44 (СКИДКА!)", reply_markup=shop_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    items = {"buy_bear": ("Мишку", 15), "buy_heart": ("Сердечко", 15), "buy_wine": ("Шампанское", 45), "buy_rocket": ("Ракету", 44)}
    name, price = items[callback.data]
    if get_points(callback.from_user.id) >= price:
        add_points(callback.from_user.id, -price)
        await callback.message.answer(f"✅ Куплено: {name}! Админ свяжется с тобой.")
        await bot.send_message(ADMIN_ID, f"💰 ПОКУПКА: {name} от {callback.from_user.id}\nСпиши: `/pay {callback.from_user.id} -{price}`")
    else: await callback.answer("❌ Мало Stars!", show_alert=True)

@dp.message(F.text == "ℹ️ Инфо")
async def info(message: types.Message):
    await message.answer("🛡️ **Free Stars**\nЗадания -> Stars -> Подарки!")

@dp.message(Command("pay"))
async def pay_points(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            _, u_id, amt = message.text.split()
            add_points(int(u_id), float(amt))
            await message.answer("✅ Баланс обновлен!")
        except: await message.answer("ID СУММА")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
