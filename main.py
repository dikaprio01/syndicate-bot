import asyncio
import json
import os
import psutil
import traceback
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from config import TOKEN, OWNER_ID, ADMIN_CHAT_ID, RANKS

bot = Bot(token=TOKEN)
dp = Dispatcher()
DATA_FILE = "data.json"

# --- ФУНКЦИЯ ДЛЯ ОТПРАВКИ ОШИБОК В АДМИНКУ ---
async def send_error(error_text):
    try:
        clean_error = traceback.format_exc()
        text = f"❌ <b>КРИТИЧЕСКАЯ ОШИБКА</b>\n<code>---------------------------</code>\n{error_text}\n\n<b>Стек:</b>\n<code>{clean_error[-500:]}</code>"
        await bot.send_message(ADMIN_CHAT_ID, text, parse_mode="HTML")
    except:
        print("Не удалось отправить ошибку в админку")

# --- РАБОТА С ДАННЫМИ ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "admins": {str(OWNER_ID): "Owner"}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(db):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

db = load_data()

# --- ПРИВЕТСТВИЕ ПРИ ДОБАВЛЕНИИ ---
@dp.message(F.new_chat_members)
async def welcome_bot(message: types.Message):
    for member in message.new_chat_members:
        if member.id == (await bot.get_me()).id:
            await message.answer("🦾 <b>Система Синдикат активирована.</b>\nЯ — админ-бот. Назначьте меня администратором, чтобы я мог управлять чатом.")

# --- КОМАНДА ПРОФИЛЬ ---
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    try:
        uid = str(message.from_user.id)
        if uid not in db["users"]:
            db["users"][uid] = {"rep": 2, "msgs": 0}
        
        db["users"][uid]["msgs"] += 1
        save_data(db)
        
        user = db["users"][uid]
        rank = RANKS.get(user["rep"], "😐 Прохожий")
        
        await message.reply(f"👤 <b>ПРОФИЛЬ:</b> {message.from_user.first_name}\n🏷 <b>КЛЕЙМО:</b> {rank}\n💬 <b>МЕССАДЖИ:</b> {user['msgs']}", parse_mode="HTML")
    except Exception as e:
        await send_error(f"Ошибка в /profile: {e}")

# --- МОНИТОРИНГ ---
@dp.message(Command("status"))
async def sys_status(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    try:
        ram = psutil.virtual_memory()
        text = f"📟 <b>STATUS</b>\n<code>---------------------------</code>\n💾 RAM: {ram.percent}%\n📂 Disk: {os.path.getsize(DATA_FILE)} bytes"
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await send_error(f"Ошибка в /status: {e}")

# --- ГЛАВНЫЙ ЗАПУСК ---
async def main():
    try:
        print("Бот стартует...")
        # Уведомление в админку о запуске
        await bot.send_message(ADMIN_CHAT_ID, "✅ <b>Бот успешно запущен на хостинге!</b>", parse_mode="HTML")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка при запуске: {e}")

if __name__ == "__main__":
    asyncio.run(main())
    
