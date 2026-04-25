import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662 

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
    cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

# --- КНОПКИ ---
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
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM users WHERE id = ?', (user_id,))
    is_old = cursor.fetchone()
    
    if not is_old:
        ref_id = int(args) if args and args.isdigit() and int(args) != user_id else None
        cursor.execute('INSERT INTO users (id, points, referrer_id, tasks_done) VALUES (?, 2.0, ?, 0)', (user_id, ref_id))
        conn.commit()
        await message.answer("🌟 Добро пожаловать! Начислен бонус **2.0 Stars** ⭐", reply_markup=menu_kb)
        if ref_id:
            try: await bot.send_message(ref_id, "🔔 По твоей ссылке зашел новый друг!")
            except: pass
    else:
        await message.answer("С возвращением в Free Stars! 🌟", reply_markup=menu_kb)
    conn.close()

@dp.message(F.text == "👥 Рефералы")
async def referral_menu(message: types.Message):
    me = await bot.get_me()
    ref_link = f"https://t.me{me.username}?start={message.from_user.id}"
    await message.answer(f"👥 **Реферальная система**\n\nТвоя ссылка: `{ref_link}`\n\nЕсли друг выполнит **3 задания**, ты получишь **1.5 Stars** ⭐", parse_mode="Markdown")

@dp.message(F.text == "📝 Задания")
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT task_id FROM completed_tasks WHERE user_id = ?', (user_id,))
    done_ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    available = [t for t in TASKS if t["id"] not in done_ids]
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
    user_id = callback.from_user.id
    t_data = next((t for t in TASKS if t["id"] == t_id), None)
    
    try:
        m = await bot.get_chat_member(chat_id=t_id, user_id=user_id)
        if m.status in ["member", "administrator", "creator"]:
            # СТРОГАЯ ПРОВЕРКА: только если еще не делал
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM completed_tasks WHERE user_id = ? AND task_id = ?', (user_id, t_id))
            if not cursor.fetchone():
                cursor.execute('INSERT INTO completed_tasks (user_id, task_id) VALUES (?, ?)', (user_id, t_id))
                cursor.execute('UPDATE users SET points = points + ?, tasks_done = tasks_done + 1 WHERE id = ?', (t_data["reward"], user_id))
                
                # Проверка рефералки (награда пригласившему за 3-е задание друга)
                cursor.execute('SELECT referrer_id, tasks_done FROM users WHERE id = ?', (user_id,))
                row = cursor.fetchone()
                if row and row[0] and row[1] == 3:
                    cursor.execute('UPDATE users SET points = points + 1.5 WHERE id = ?', (row[0],))
                    try: await bot.send_message(row[0], "🎁 Реферал выполнил 3 задания! +1.5 Stars!")
                    except: pass
                conn.commit()
                await callback.answer(f"✅ +{t_data['reward']} Stars!", show_alert=True)
                await callback.message.delete()
                await show_tasks(callback.message)
            conn.close()
        else: await callback.answer("❌ Сначала подпишись!", show_alert=True)
    except: await callback.answer("⚠️ Ошибка: бот не админ в канале!", show_alert=True)

@dp.message(F.text == "🛒 Магазин")
async def shop(message: types.Message):
    shop_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧸 Мишка (15)", callback_data="buy_bear")],
        [InlineKeyboardButton(text="🚀 Ракета (44) 🔥", callback_data="buy_rocket")]
    ])
    await message.answer("🛒 Магазин:", reply_markup=shop_kb)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    items = {"buy_bear": ("Мишку", 15), "buy_rocket": ("Ракету", 44)}
    name, price = items[callback.data]
    balance = get_points(callback.from_user.id)
    if balance >= price:
        add_points(callback.from_user.id, -price)
        await callback.message.answer(f"✅ Куплено: {name}!")
        mention = f"[{callback.from_user.first_name}](tg://user?id={callback.from_user.id})"
        await bot.send_message(ADMIN_ID, f"💰 ПОКУПКА: {name}\nЮзер: {mention}", parse_mode="Markdown")
    else: await callback.answer("❌ Мало Stars!", show_alert=True)

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    await message.answer(f"Твой баланс: {get_points(message.from_user.id)} Stars ⭐")

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
