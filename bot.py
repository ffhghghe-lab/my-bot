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

# Добавь 3+ спонсора для работы бонуса 1.5 звезды
SPONSORS = [
    {"id": "-1003250003175", "url": "https://t.me/+uatBuhGV_F9jOGZi", "name": "Спонсор #1 🛡️", "reward": 0.15},
    {"id": "-1003923958803", "url": "https://t.me/frem4ik1", "name": "Спонсор #2 🎁", "reward": 0.15},

]

OUR_CHANNELS = [
    {"name": "Наш основной канал 📢", "url": "https://t.me/freestars_vashbot"},
]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points REAL DEFAULT 0, referrer_id INTEGER, tasks_done INTEGER DEFAULT 0, username TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS completed_tasks (user_id INTEGER, task_id TEXT, PRIMARY KEY (user_id, task_id))''')

def get_points(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
        res = cursor.fetchone()
        return round(res[0], 2) if res else 0.0

def add_points(user_id, amount):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (id, points, tasks_done) VALUES (?, 0, 0)', (user_id,))
        cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (amount, user_id))

# --- МЕНЮ ---
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Мои Stars"), KeyboardButton(text="📝 Задания")],
        [KeyboardButton(text="👥 Рефералы"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="📢 Каналы")]
    ],
    resize_keyboard=True
)

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    args = command.args
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            ref_id = int(args) if args and args.isdigit() and int(args) != user_id else None
            cursor.execute('INSERT INTO users (id, points, referrer_id, tasks_done, username) VALUES (?, 2.0, ?, 0, ?)', (user_id, ref_id, username))
            await message.answer("🌟 Бонус **2.0 Stars** начислен!", reply_markup=menu_kb, parse_mode="Markdown")
            if ref_id:
                try: await bot.send_message(ref_id, f"🔔 Друг @{username} зашел по ссылке!")
                except: pass
        else:
            cursor.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
            await message.answer("С возвращением! 🌟", reply_markup=menu_kb)

@dp.message(F.text == "👥 Рефералы")
async def show_ref(message: types.Message):
    user_id = message.from_user.id
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (user_id,))
        cnt = cursor.fetchone()[0]
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user_id}"
    await message.answer(f"👥 **Рефералы**\n\nТвоя ссылка: `{link}`\nПриглашено: **{cnt}** чел.\n\nЗа каждого друга, который выполнит 3 задания, ты получишь **1.5 Stars**! ⭐", parse_mode="Markdown")

@dp.message(F.text == "📝 Задания")
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT task_id FROM completed_tasks WHERE user_id = ?', (user_id,))
        done_ids = [r[0] for r in cursor.fetchall()]
    available = [t for t in SPONSORS if t["id"] not in done_ids]
    if not available: return await message.answer("✅ Все задания выполнены!")
    task = available[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1. Подписаться", url=task["url"])],
        [InlineKeyboardButton(text="2. Проверить ✅", callback_data=f"check_{task['id']}")],
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data=f"skip_{task['id']}")]
    ])
    await message.answer(f"🚀 Задание: {task['name']}", reply_markup=kb)

@dp.callback_query(F.data.startswith("check_"))
async def check_sub(callback: types.CallbackQuery):
    t_id = callback.data.replace("check_", "")
    user_id = callback.from_user.id
    t_data = next((t for t in SPONSORS if t["id"] == t_id), None)
    try:
        m = await bot.get_chat_member(chat_id=t_id, user_id=user_id)
        if m.status in ["member", "administrator", "creator"]:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO completed_tasks (user_id, task_id) VALUES (?, ?)', (user_id, t_id))
                cursor.execute('UPDATE users SET points = points + ?, tasks_done = tasks_done + 1 WHERE id = ?', (t_data["reward"], user_id))
                # Выдача 1.5 Stars рефереру на 3-м задании
                cursor.execute('SELECT referrer_id, tasks_done FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                if row and row[0] and row[1] == 3:
                    cursor.execute('UPDATE users SET points = points + 1.5 WHERE id = ?', (row[0],))
                    try: await bot.send_message(row[0], "🎁 Реферал выполнил 3 задания! +1.5 Stars!")
                    except: pass
            await callback.answer(f"✅ +{t_data['reward']} Stars!", show_alert=True)
            await callback.message.delete()
            await show_tasks(callback.message)
        else:
            await callback.answer("❌ Сначала подпишись!", show_alert=True)
    except: await callback.answer("⚠️ Ошибка проверки.", show_alert=True)

@dp.callback_query(F.data.startswith("skip_"))
async def skip(c: types.CallbackQuery):
    t_id = c.data.replace("skip_", "")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('INSERT OR IGNORE INTO completed_tasks (user_id, task_id) VALUES (?, ?)', (c.from_user.id, t_id))
    await c.message.delete()
    await show_tasks(c.message)

@dp.message(F.text == "🏆 Топ")
async def show_top(m: types.Message):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT username, points FROM users ORDER BY points DESC LIMIT 10')
        data = cursor.fetchall()
    text = "🏆 **Топ игроков:**\n\n"
    for i, (name, pts) in enumerate(data, 1):
        text += f"{i}. {name or 'Аноним'} — {round(pts, 2)} ⭐\n"
    await m.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    # Список товаров
    items = {
        "buy_bear": ("Мишку 🧸", 15), 
        "buy_heart": ("Сердечко ❤️", 15), 
        "buy_wine": ("Шампанское 🍾", 45), 
        "buy_rocket": ("Ракету 🚀", 44)
    }
    
    if callback.data not in items:
        return

    name, price = items[callback.data]
    user_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name
    
    # 1. Проверяем баланс
    balance = get_points(user_id)
    
    if balance >= price:
        # 2. Списываем звёзды
        add_points(user_id, -price)
        
        # 3. Ответ пользователю
        await callback.message.answer(f"✅ Успешно куплено: {name}!\nАдмин свяжется с тобой для выдачи подарка.")

        # 4. ГОТОВИМ СМС ДЛЯ АДМИНА (ТЕБЯ)
        # Формируем ссылку на покупателя
        contact_url = f"https://t.me{username}" if username else f"tg://user?id={user_id}"
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать покупателю", url=contact_url)]
        ])

        admin_text = (
            f"💰 **НОВАЯ ПОКУПКА В МАГАЗИНЕ!**\n\n"
            f"🎁 Товар: {name}\n"
            f"👤 Покупатель: {first_name} (@{username if username else 'нет никнейма'})\n"
            f"🆔 ID: `{user_id}`\n"
            f"💳 Остаток баланса: {round(balance - price, 2)} ⭐"
        )

        # 5. ОТПРАВКА АДМИНУ
        try:
            await bot.send_message(
                chat_id=ADMIN_ID, 
                text=admin_text, 
                parse_mode="Markdown", 
                reply_markup=admin_kb
            )
            print(f"✅ Уведомление о покупке {name} отправлено админу.")
        except Exception as e:
            # Если не пришло, бот напишет ошибку в черном окне на ПК
            print(f"❌ ОШИБКА ОТПРАВКИ АДМИНУ: {e}")
            await callback.message.answer("⚠️ Ошибка уведомления админа, но покупка засчитана.")
            
    else:
        await callback.answer(f"❌ Недостаточно Stars! У тебя {balance}, а нужно {price}", show_alert=True)


@dp.message(F.text == "📢 Каналы")
async def show_chan(m: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c['name'], url=c['url'])] for c in OUR_CHANNELS])
    await m.answer("📢 Наши каналы:", reply_markup=kb)

@dp.message(F.text == "⭐ Мои Stars")
async def check_bal(m: types.Message):
    await m.answer(f"Твой баланс: {get_points(m.from_user.id)} Stars ⭐")

@dp.message(Command("pay"))
async def admin_pay(m: types.Message, command: CommandObject):
    if m.from_user.id == ADMIN_ID:
        try:
            args = command.args.split()
            add_points(int(args[0]), float(args[1]))
            await m.answer("✅ Начислено!")
        except: await m.answer("Ошибка! /pay ID сумма")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
