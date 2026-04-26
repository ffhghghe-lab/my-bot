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

# ЗАДАНИЯ СПОНСОРОВ
SPONSORS = [
    {"id": "-1003250003175", "url": "https://t.me/+uatBuhGV_F9jOGZi", "name": "Спонсор #1 🛡️", "reward": 0.15},
    {"id": "-1001234567890", "url": "https://t.me", "name": "Спонсор #2 🎁", "reward": 0.15},
    {"id": "-1001112223334", "url": "https://t.me", "name": "Спонсор #3 🚀", "reward": 0.15},
]

OUR_CHANNELS = [
    {"name": "Наш основной канал 📢", "url": "https://t.me/freestars_vasbot"},
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
        await message.answer("🌟 Бонус **2.0 Stars** начислен!", reply_markup=menu_kb, parse_mode="Markdown")
    else:
        cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        conn.commit()
        await message.answer("С возвращением! 🌟", reply_markup=menu_kb)
    conn.close()

# --- ЛОГИКА ЗАДАНИЙ ПО ПОРЯДКУ ---
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
    
    task = available[0] # Берем строго ПЕРВОЕ по порядку
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
    t_data = next((t for t in SPONSORS if t["id"] == t_id), None)
    
    try:
        m = await bot.get_chat_member(chat_id=t_id, user_id=user_id)
        if m.status in ["member", "administrator", "creator"]:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO completed_tasks (user_id, task_id) VALUES (?, ?)', (user_id, t_id))
            cursor.execute('UPDATE users SET points = points + ?, tasks_done = tasks_done + 1 WHERE id = ?', (t_data["reward"], user_id))
            
            # Проверка рефералки на 3 задания
            cursor.execute('SELECT referrer_id, tasks_done FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            if row and row[0] and row[1] == 3:
                cursor.execute('UPDATE users SET points = points + 1.5 WHERE id = ?', (row[0],))
                try: await bot.send_message(row[0], "🎁 Твой реферал выполнил 3 задания! +1.5 Stars!")
                except: pass
            
            conn.commit()
            conn.close()
            await callback.answer(f"✅ +{t_data['reward']} Stars!", show_alert=True)
            await callback.message.delete()
            await show_tasks(callback.message)
        else:
            await callback.answer("❌ Подписка не найдена!", show_alert=True)
    except:
        await callback.answer("⚠️ Бот не админ в канале!", show_alert=True)

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

# --- МАГАЗИН И УВЕДОМЛЕНИЯ АДМИНУ ---
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    items = {"buy_bear": ("Мишку", 15), "buy_heart": ("Сердечко", 15), "buy_wine": ("Шампанское", 45), "buy_rocket": ("Ракету", 44)}
    name, price = items[callback.data]
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    if get_points(user_id) >= price:
        add_points(user_id, -price)
        await callback.message.answer(f"✅ Куплено: {name}! Админ свяжется с тобой.")
        
        # Красивое уведомление админу
        contact_url = f"https://t.me{username}" if username else f"tg://user?id={user_id}"
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Написать покупателю", url=contact_url)]])
        
        admin_text = (
            f"💰 **НОВАЯ ПОКУПКА!**\n\n"
            f"👤 Юзер: @{username if username else user_id}\n"
            f"🎁 Товар: {name}\n"
            f"🆔 ID: `{user_id}`"
        )
        
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=admin_kb)
    else:
        await callback.answer("❌ Мало Stars!", show_alert=True)

# Остальные кнопки
@dp.message(F.text == "🏆 Топ")
async def show_top(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT username, points FROM users ORDER BY points DESC LIMIT 10')
    top = cursor.fetchall()
    conn.close()
    text = "🏆 **Топ-10 игроков:**\n\n"
    for i, (name, pts) in enumerate(top, 1):
        text += f"{i}. {name or 'Аноним'} — {round(pts, 2)} ⭐\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "👥 Рефералы")
async def show_ref(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (message.from_user.id,))
    cnt = cursor.fetchone()[0]
    conn.close()
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.answer(f"👥 **Рефералы**\n\nСсылка: `{link}`\nПриглашено: **{cnt}** чел.\n\nБонус 1.5 ⭐ за 3 задания друга!", parse_mode="Markdown")

@dp.message(F.text == "📢 Каналы")
async def show_chan(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c['name'], url=c['url'])] for c in OUR_CHANNELS])
    await message.answer("📢 Наши каналы:", reply_markup=kb)

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    await message.answer(f"Твой баланс: {get_points(message.from_user.id)} Stars ⭐")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
