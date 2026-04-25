import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

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

# --- КНОПКИ (С НОВЫМ НАЗВАНИЕМ) ---
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
        "Добро пожаловать в **Free Stars**! 🌟\n\nЗдесь ты можешь обменять свои обычные подарки на внутренние Stars и забирать крутые призы!", 
        reply_markup=menu_kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "⭐ Мои Stars")
async def check_balance(message: types.Message):
    balance = get_points(message.from_user.id)
    await message.answer(f"Твой баланс: {balance} Stars ⭐")

@dp.message(F.text == "🎁 Сдать подарок")
async def give_gift(message: types.Message):
    await message.answer("Чтобы получить Stars:\n1. ЖДИТЕ КОДА ВАМ НАПИШИТ АДМИН.\n2.ОТПРАВТЕ ПОДАРОК.\n\nЗа каждый подарок даем 10 ⭐! ПОДАРОК ОТПРАВЛЕННЫЙ ВАМИ ДОЛЖЕН СТОИТЬ 15 ⭐!")
    await bot.send_message(ADMIN_ID, f"Юзер @{message.from_user.username} (ID: {message.from_user.id}) хочет сдать подарок в Free Stars!")

@dp.message(F.text == "🛒 Забрать Stars")
async def shop(message: types.Message):
    await message.answer("В магазине Free Stars пока пусто. Новые поступления будут скоро! 🔥")

@dp.message(F.text == "ℹ️ О сервисе")
async def info(message: types.Message):
    await message.answer("Free Stars — это площадка для обмена подарками. Мы помогаем пользователям передаривать то, что им не нужно, за внутреннюю валюту!")

@dp.message(Command("pay"))
async def pay_points(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            u_id = int(parts[1])
            amount = int(parts[2])
            add_points(u_id, amount)
            await message.answer(f"Начислили {amount} Stars юзеру {u_id} ✅")
            await bot.send_message(u_id, f"Твой баланс в Free Stars пополнен на {amount} ⭐!")
        except:
            await message.answer("Ошибка! Пиши: `/pay ID СУММА`", parse_mode="Markdown")

async def main():
    init_db()
    print("Бот Free Stars запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
