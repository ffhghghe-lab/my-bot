import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662 

# Список спонсоров (добавь сюда еще 2 канала, чтобы рефералка могла сработать на 3 заданиях)
TASKS = [
    {"id": "-1003923958803", "url": "https://t.me", "name": "Спонсор #1 🛡️", "reward": 0.15},
]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # Таблица пользователей: ID, баланс, ID того кто пригласил, кол-во выполненных заданий
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, points REAL DEFAULT 0, referrer_id INTEGER, tasks_done INTEGER DEFAULT 0)''')
    # Таблица выполненных заданий
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
    # Увеличиваем счетчик выполненных заданий у юзера
    cursor.execute('UPDATE users SET tasks_done = tasks_done + 1 WHERE id = ?', (user_id,))
    
    # Проверка реферальной системы
    cursor.execute('SELECT referrer_id, tasks_done FROM users WHERE id = ?', (user_id,))
    ref_data = cursor.fetchone()
    if ref_data and ref_data[0]: # Если есть пригласивший
        ref_id = ref_data[0]
        done_count = ref_data[1]
        if done_count == 3: # Если это ровно 3-е задание
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
        [KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="🛒 Магазин")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    args = command.args # Это ID пригласившего из ссылки

    if is_new_user(user_id):
        referrer = None
        if args and args.isdigit() and int(args) != user_id:
            referrer = int(args)
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (id, points, referrer_id) VALUES (?, 2.0, ?)', (user_id, referrer))
        conn.commit()
        conn.close()
        
        await message.answer("🌟 Добро пожаловать! Начислен бонус **2.0 Stars** ⭐", reply_markup=menu_kb)
        if referrer:
            await bot.send_message(referrer, "🔔 По твоей ссылке зашел новый друг! Как только он выполнит 3 задания, ты получишь 1.5 Stars.")
    else:
        await message.answer("С возвращением!", reply_markup=menu_kb)

@dp.message(F.text == "👥 Рефералы")
async def referral_menu(message: types.Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me{bot_info.username}?start={message.from_user.id}"
    await message.answer(
        f"👥 **Реферальная система**\n\n"
        f"Твоя ссылка: `{ref_link}`\n\n"
        f"За каждого приглашенного друга, который выполнит **3 задания**, ты получишь **1.5 Stars** ⭐",
        parse_mode="Markdown"
    )

@dp.message(F.text == "📝 Задания")
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    available_tasks = [t for t in TASKS if not is_task_done(user_id, t["id"])]
    if not available_tasks:
        return await message.answer("✅ Задания выполнены!")
    
    task = available_tasks[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Подписаться", url=task["url"])],
        [InlineKeyboardButton(text="2. Проверить ✅", callback_data=f"check_{task['id']}")]
    ])
    await message.answer(f"Задание: {task['name']}\nНаграда: {task['reward']} Stars", reply_markup=kb)

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
            await callback.answer("❌ Ты не подписался!", show_alert=True)
    except:
        await callback.answer("⚠️ Ошибка админки!", show_alert=True)

# Остальные функции (магазин, баланс) остаются без изменений
@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    balance = get_points(message.from_user.id)
    await message.answer(f"Твой баланс: {balance} Stars ⭐")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
