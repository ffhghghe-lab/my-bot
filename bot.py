# -*- coding: utf-8 -*-
import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# 1. СПОНСОРЫ (Для заданий) - добавь 3+, чтобы работала рефералка на 1.5 Stars
SPONSORS = [
    {"id": "-1003923958803", "url": "https://t.me/frem4ik1", "name": "Спонсор #1 🛡️", "reward": 0.15},
    {"id": "-1001234567890", "url": "https://t.me", "name": "Спонсор #2 🎁", "reward": 0.15},
    {"id": "-1001112223334", "url": "https://t.me", "name": "Спонсор #3 🚀", "reward": 0.15},
]

# 2. НАШИ КАНАЛЫ (Просто ссылки)
OUR_CHANNELS = [
    {"name": "Наш основной канал 📢", "url": "https://t.me/freestars_vashbot"},
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
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="📢 Каналы")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    args = command.args
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
    if not cursor.fetchone():
        ref_id = int(args) if args and args.isdigit() and int(args) != user_id else None
        cursor.execute('INSERT INTO users (id, points, referrer_id, tasks_done, username) VALUES (?, 2.0, ?, 0, ?)', 
                       (user_id, ref_id, username))
        conn.commit()
        await message.answer("🌟 Добро пожаловать! Бонус **2.0 Stars** начислен!", reply_markup=menu_kb, parse_mode="Markdown")
        if ref_id:
            try: await bot.send_message(ref_id, f"🔔 Друг @{username} зашел по ссылке!")
            except: pass
    else:
        cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        conn.commit()
        await message.answer("С возвращением! 🌟", reply_markup=menu_kb)
    conn.close()

@dp.message(F.text == "📝 Задания")
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT task_id FROM completed_tasks WHERE user_id = ?', (user_id,))
    done_ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    available = [t for t in SPONSORS if t["id"] not in done_ids]
    if not available:
        return await message.answer("✅ Ты выполнил все задания! Новые появятся позже.")
    task = available[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Подписаться 🛡️", url=task["url"])],
        [InlineKeyboardButton(text="2. Проверить ✅", callback_data=f"check_{task['id']}")],
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data=f"skip_{task['id']}")]
    ])
    await message.answer(f"🚀 Задание: {task['name']}\nНаграда: {task['reward']} Stars", reply_markup=kb)

@dp.callback_query(F.data.startswith("check_"))
async def check_sub(callback: types.CallbackQuery):
    t_id = callback.data.replace("check_", "")
    user_id = callback.from_user.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM completed_tasks WHERE user_id = ? AND task_id = ?', (user_id, t_id))
    if cursor.fetchone():
        conn.close()
        await callback.answer("✅ Уже выполнено!")
        return
    t_data = next((t for t in SPONSORS if t["id"] == t_id), None)
    try:
        m = await bot.get_chat_member(chat_id=t_id, user_id=user_id)
        if m.status in ["member", "administrator", "creator"]:
            cursor.execute('INSERT INTO completed_tasks (user_id, task_id) VALUES (?, ?)', (user_id, t_id))
            cursor.execute('UPDATE users SET points = points + ?, tasks_done = tasks_done + 1 WHERE id = ?', (t_data["reward"], user_id))
            cursor.execute('SELECT referrer_id, tasks_done FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            if row and row[0] and row[1] == 3: # Если выполнил 3-е задание
                cursor.execute('UPDATE users SET points = points + 1.5 WHERE id = ?', (row[0],))
                try: await bot.send_message(row[0], "🎁 Твой реферал выполнил 3 задания! +1.5 Stars!")
                except: pass
            conn.commit()
            conn.close()
            await callback.answer(f"✅ +{t_data['reward']} Stars!", show_alert=True)
            await callback.message.delete()
            await show_tasks(callback.message)
        else:
            conn.close()
            await callback.answer("❌ Сначала подпишись!", show_alert=True)
    except:
        conn.close()
        await callback.answer("⚠️ Ошибка: Бот не админ!", show_alert=True)

@dp.callback_query(F.data.startswith("skip_"))
async def skip_task(callback: types.CallbackQuery):
    t_id = callback.data.replace("skip_", "")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO completed_tasks (user_id, task_id) VALUES (?, ?)', (callback.from_user.id, t_id))
    conn.commit()
    conn.close()
    await callback.message.delete()
    await show_tasks(callback.message)

@dp.message(F.text == "👥 Рефералы")
async def show_ref(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (message.from_user.id,))
    cnt = cursor.fetchone()[0]
    conn.close()
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(f"👥 **Рефералы**\nТвоя ссылка: `{link}`\nПриглашено: **{cnt}** чел.\n\nЗа 3 задания друга: **1.5 Stars** ⭐", parse_mode="Markdown")

@dp.message(F.text == "🏆 Топ")
async def show_top(message: types.Message):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Выбираем только тех, у кого имя не пустое и сортируем по очкам
        cursor.execute('SELECT username, points FROM users ORDER BY points DESC LIMIT 10')
        top_users = cursor.fetchall()
        conn.close()
        
        if not top_users:
            return await message.answer("🏆 Таблица лидеров пока пуста!")

        text = "🏆 **Топ-10 игроков:**\n\n"
        for i, (name, pts) in enumerate(top_users, 1):
            # Если ника нет, пишем 'Игрок'
            display_name = str(name) if name else f"Игрок {i}"
            # Убираем символы, которые могут сломать Markdown
            display_name = display_name.replace("_", "\\_").replace("*", "")
            text += f"{i}. {display_name} — **{round(pts, 2)}** ⭐\n"
        
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка в Топе: {e}")
        await message.answer("⚠️ Ошибка при загрузке таблицы лидеров.")


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
    user_id, username = callback.from_user.id, callback.from_user.username
    if get_points(user_id) >= price:
        add_points(user_id, -price)
        await callback.message.answer(f"✅ Куплено: {name}!")
        url = f"https://t.me{username}" if username else f"tg://user?id={user_id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Написать", url=url)]])
        await bot.send_message(ADMIN_ID, f"💰 **КУПИЛИ: {name}**\nЮзер: @{username or user_id}", reply_markup=kb)
    else:
        await callback.answer("❌ Мало Stars!", show_alert=True)

@dp.message(F.text == "📢 Каналы")
async def show_chan(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c['name'], url=c['url'])] for c in OUR_CHANNELS])
    await message.answer("📢 Наши каналы:", reply_markup=kb)

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    await message.answer(f"Твой баланс: {get_points(message.from_user.id)} Stars ⭐")

@dp.message(Command("pay"))
async def admin_pay(message: types.Message, command: CommandObject):
    if message.from_user.id == ADMIN_ID:
        try:
            args = command.args.split()
            add_points(int(args[0]), float(args[1]))
            await message.answer("✅ Успешно!")
        except: await message.answer("Ошибка!")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
