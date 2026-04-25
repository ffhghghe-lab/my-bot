import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, points INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def get_points(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def add_points(user_id, amount):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, points) VALUES (?, 0)', (user_id,))
    cursor.execute('UPDATE users SET points = points + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

# --- КНОПКИ ---
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⭐ Мои Stars"), KeyboardButton(text="🎁 Сдать подарок")],
        [KeyboardButton(text="🛒 Забрать Stars"), KeyboardButton(text="ℹ️ О сервисе")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    add_points(message.from_user.id, 0)
    await message.answer("Добро пожаловать в **Free Stars**! 🌟", reply_markup=menu_kb, parse_mode="Markdown")

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    balance = get_points(message.from_user.id)
    await message.answer(f"Твой баланс: {balance} Stars ⭐")

@dp.message(F.text == "🎁 Сдать подарок")
async def give_gift(message: types.Message):
    await message.answer("🛡️ **Инструкция:**\n\nСейчас тебе напишет наш админ. Вы присылаете ему подарок, и после этого он начислит вам Stars на баланс!", parse_mode="Markdown")
    
    user = message.from_user
    mention = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
    
    # Создаем кнопку для админа в любом случае
    url = f"t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать человеку", url=url)]
    ])
    
    await bot.send_message(
        ADMIN_ID, 
        f"🛡️ **ЗАЯВКА НА СДАЧУ!**\nОт: {mention}\nID: `{user.id}`\n\nНажми кнопку ниже, чтобы написать человеку.", 
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "🛒 Забрать Stars")
async def shop(message: types.Message):
    shop_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧸 Мишка (15)", callback_data="buy_bear")],
        [InlineKeyboardButton(text="❤️ Сердечко (15)", callback_data="buy_heart")],
        [InlineKeyboardButton(text="🍾 Шампанское (45)", callback_data="buy_wine")],
        [InlineKeyboardButton(text="🚀 Ракету (44)", callback_data="buy_rocket")]
    ])
    await message.answer("🛒 **Магазин Free Stars**\nВыберите подарок:", reply_markup=shop_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    items = {"buy_bear": ("Мишку", 15), "buy_heart": ("Сердечко", 15), "buy_wine": ("Шампанское", 45), "buy_rocket": ("Ракету", 44)}
    name, price = items[callback.data]
    user_balance = get_points(callback.from_user.id)
    
    if user_balance >= price:
        await callback.answer("Заявка отправлена!")
        await callback.message.answer(f"✅ Заявка на **{name}** принята! Админ скоро напишет.")
        
        user = callback.from_user
        url = f"t.me/{user.username}" if user.username else f"tg://user?id={user.id}"
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Написать покупателю", url=url)]])
        
        await bot.send_message(ADMIN_ID, f"💰 **ПОКУПКА!**\nЮзер: {user.first_name}\nТовар: {name}\nСпиши баланс: `/pay {user.id} -{price}`", reply_markup=admin_kb, parse_mode="Markdown")
    else:
        await callback.answer(f"❌ Нужно {price} Stars!", show_alert=True)

@dp.message(Command("pay"))
async def pay_points(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            _, u_id, amount = message.text.split()
            add_points(int(u_id), int(amount))
            await message.answer(f"Готово! Изменили баланс {u_id} на {amount}")
        except:
            await message.answer("Ошибка! Формат: `/pay ID СУММА`")

async def main():
    init_db(); await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
