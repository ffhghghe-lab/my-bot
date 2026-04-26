# -*- coding: utf-8 -*-
import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662  # ПРОВЕРЬ: Это твой ID?

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

TASKS = [
    {"id": "-1003923958803", "url": "https://t.me/frem4ik1", "name": "Спонсор #1 🛡️", "reward": 0.15},
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
    cursor.execute('INSERT OR IGNORE INTO users (id, points) VALUES (?, 0)', (user_id,))
    cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

# --- МЕНЮ ---
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Мои Stars"), KeyboardButton(text="📝 Задания")],
        [KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="🏆 Топ")]
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
    is_old = cursor.fetchone()
    
    if not is_old:
        # Реферальная логика
        ref_id = None
        if args and args.isdigit():
            potential_ref = int(args)
            if potential_ref != user_id:
                ref_id = potential_ref
        
        cursor.execute('INSERT INTO users (id, points, referrer_id, tasks_done, username) VALUES (?, 2.0, ?, 0, ?)', 
                       (user_id, ref_id, username))
        conn.commit()
        await message.answer("🌟 Бонус **2.0 Stars** начислен!", reply_markup=menu_kb, parse_mode="Markdown")
        
        if ref_id:
            try:
                await bot.send_message(ref_id, f"👍 По твоей ссылке зашел новый друг (@{username})!")
            except: pass
    else:
        cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        conn.commit()
        await message.answer("С возвращением! 🌟", reply_markup=menu_kb)
    conn.close()

@dp.message(F.text == "👥 Рефералы")
async def referral_menu(message: types.Message):
    me = await bot.get_me()
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    
    ref_link = f"https://t.me/{me.username}?start={user_id}"
    await message.answer(
        f"👥 **Рефералы**\n\n"
        f"Твоя ссылка: `{ref_link}`\n"
        f"Приглашено друзей: **{count}**\n\n"
        f"За каждого друга ты получаешь бонус!", 
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    items = {"buy_bear": ("Мишку", 15), "buy_heart": ("Сердечко", 15), "buy_wine": ("Шампанское", 45), "buy_rocket": ("Ракету", 44)}
    name, price = items[callback.data]
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    if get_points(user_id) >= price:
        add_points(user_id, -price)
        await callback.message.answer(f"✅ Куплено: {name}!")
        
        # Кнопка для админа
        url = f"https://t.me{username}" if username else f"tg://user?id={user_id}"
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Написать", url=url)]])
        
        # УВЕДОМЛЕНИЕ АДМИНУ
        try:
            await bot.send_message(
                ADMIN_ID, 
                f"💰 **НОВАЯ ПОКУПКА!**\n\n👤 Юзер: @{username if username else user_id}\n🎁 Товар: {name}\n🆔 ID: `{user_id}`", 
                parse_mode="Markdown", 
                reply_markup=admin_kb
            )
        except Exception as e:
            print(f"Ошибка отправки админу: {e}")
    else:
        await callback.answer("❌ Мало Stars!", show_alert=True)

# ОСТАЛЬНЫЕ ФУНКЦИИ (Топ, Задания и т.д.) ОСТАЮТСЯ ТАКИМИ ЖЕ

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
