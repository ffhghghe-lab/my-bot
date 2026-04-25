import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Твои данные
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
    await message.answer(
        "Добро пожаловать в **Free Stars**! 🌟\n\nЗдесь ты можешь обменять свои подарки на Stars!", 
        reply_markup=menu_kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    balance = get_points(message.from_user.id)
    await message.answer(f"Твой баланс: {balance} Stars ⭐")

@dp.message(F.text == "🎁 Сдать подарок")
async def give_gift(message: types.Message):
    await message.answer("🛡️ **Инструкция:**\n\nСейчас тебе напишет наш админ. Вы присылаете ему подарок, и после этого он начислит вам Stars на баланс!", parse_mode="Markdown")
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    admin_kb = None
    if message.from_user.username:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать юзеру", url=f"t.me/{message.from_user.username}")]
        ])
    await bot.send_message(ADMIN_ID, f"🛡️ **ЗАЯВКА НА СДАЧУ!**\nЮзер {user_info} готов сдать подарок.", reply_markup=admin_kb, parse_mode="Markdown")

# --- ОБНОВЛЕННЫЙ МАГАЗИН ---
@dp.message(F.text == "🛒 Забрать Stars")
async def shop(message: types.Message):
    shop_text = (
        "🛒 **Магазин Free Stars**\n\n"
        "🧸 **Мишка** — 15 Stars\n"
        "❤️ **Сердечко** — 15 Stars\n"
        "🍾 **Шампанское** — 45 Stars 🔥 *СКИДКА!*\n"
        "🚀 **Ракета** — 44 Stars 🔥 *СКИДКА!*\n\n"
        "Нажми на кнопку ниже, чтобы заказать:"
    )
    
    shop_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧸 Купить Мишку (15)", callback_data="buy_bear")],
        [InlineKeyboardButton(text="❤️ Купить Сердечко (15)", callback_data="buy_heart")],
        [InlineKeyboardButton(text="🍾 Купить Шампанское (45)", callback_data="buy_wine")],
        [InlineKeyboardButton(text="🚀 Купить Ракету (44)", callback_data="buy_rocket")]
    ])
    
    await message.answer(shop_text, reply_markup=shop_kb, parse_mode="Markdown")

# Обработка нажатий в магазине
@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    items = {
        "buy_bear": ("Мишку", 15),
        "buy_heart": ("Сердечко", 15),
        "buy_wine": ("Шампанское", 45),
        "buy_rocket": ("Ракету", 44)
    }
    
    name, price = items[callback.data]
    user_balance = get_points(callback.from_user.id)
    
    if user_balance >= price:
        await callback.answer("Заявка отправлена!")
        await callback.message.answer(f"✅ Заявка на покупку **{name}** принята! Админ напишет тебе для передачи подарка.")
        # Уведомление админу
        await bot.send_message(ADMIN_ID, f"💰 **ПОКУПКА!**\nЮзер @{callback.from_user.username} (ID: {callback.from_user.id}) хочет купить {name} за {price} Stars. Спиши баллы через /pay и напиши ему!")
    else:
        await callback.answer(f"❌ Недостаточно Stars! Нужно {price}, а у тебя {user_balance}.", show_alert=True)

@dp.message(F.text == "ℹ️ О сервисе")
async def info(message: types.Message):
    await message.answer("Free Stars — безопасный обменник подарков. Вы сдаете подарки нам — мы начисляем вам валюту!")

@dp.message(Command("pay"))
async def pay_points(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            u_id = int(parts[1])
            amount = int(parts[2])
            add_points(u_id, amount)
            await message.answer(f"Изменили баланс на {amount} Stars юзеру {u_id} ✅")
            await bot.send_message(u_id, f"Твой баланс изменен на {amount} ⭐!")
        except:
            await message.answer("Ошибка! Пиши: `/pay ID СУММА` (чтобы отнять, пиши минус перед числом)", parse_mode="Markdown")

async def main():
    init_db()
    print("Бот Free Stars запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
