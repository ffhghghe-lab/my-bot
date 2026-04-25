import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Твои данные уже здесь
API_TOKEN = '8602042724:AAEWsiiG7wbDz6ZyQbAHEQiMjUWD8ad-I3c'
ADMIN_ID = 8227495662 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# База данных (пока в памяти)
users_db = {}

# Кнопки (в новой версии делаются чуть иначе)
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 Мой баланс"), KeyboardButton(text="🎁 Сдать подарок")],
        [KeyboardButton(text="🛒 Купить подарок"), KeyboardButton(text="ℹ️ Как это работает?")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = 0
    await message.answer(
        "Добро пожаловать в Барахолку Подарков! 🎁\nЗдесь можно обменять свои подарки на баллы или купить новые.", 
        reply_markup=menu_kb
    )

@dp.message(F.text == "💎 Мой баланс")
async def check_balance(message: types.Message):
    balance = users_db.get(message.from_user.id, 0)
    await message.answer(f"Твой текущий баланс: {balance} баллов 💎")

@dp.message(F.text == "🎁 Сдать подарок")
async def give_gift(message: types.Message):
    await message.answer("Чтобы сдать подарок:\n1. Отправь его на мой аккаунт.\n2. Напиши мне.\n\nПосле проверки получишь 1000 баллов!")
    await bot.send_message(ADMIN_ID, f"Юзер @{message.from_user.username} (ID: {message.from_user.id}) хочет сдать подарок!")

@dp.message(F.text == "🛒 Купить подарок")
async def shop(message: types.Message):
    await message.answer("В наличии пока 0 подарков. Заходи позже! 📭")

@dp.message(F.text == "ℹ️ Как это работает?")
async def info(message: types.Message):
    await message.answer("Всё просто: ты даришь подарок админу — он дает тебе баллы. За баллы можно забрать другой подарок!")

@dp.message(Command("pay"))
async def pay_points(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split()
            user_id = int(parts[1])
            amount = int(parts[2])
            users_db[user_id] = users_db.get(user_id, 0) + amount
            await message.answer(f"Выдали {amount} баллов пользователю {user_id}")
            await bot.send_message(user_id, f"Баланс пополнен на {amount} баллов! 🎉")
        except:
            await message.answer("Ошибка. Пиши так: /pay ID СУММА")

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
