import asyncio
import json
import os
import psutil
import time
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from config import TOKEN, OWNER_ID, ADMIN_CHAT_ID, RANKS

bot = Bot(token=TOKEN)
dp = Dispatcher()
DATA_FILE = "data.json"

# --- РАБОТА С ДАННЫМИ ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "admins": {str(OWNER_ID): "Owner"}, "logs": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(db):
    # Ограничение логов до 50 записей (чистка мусора)
    if len(db["logs"]) > 50:
        db["logs"] = db["logs"][-50:]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

db = load_data()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_user_rank(uid):
    user = db["users"].get(str(uid), {"rep": 2})
    return RANKS.get(user["rep"], "😐 Прохожий")

# --- КОМАНДА ПРОФИЛЬ ---
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    uid = str(message.from_user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"rep": 2, "msgs": 0, "name": message.from_user.first_name}
    
    user = db["users"][uid]
    user["msgs"] += 1
    save_data(db)
    
    role = "Владелец" if int(uid) == OWNER_ID else db["admins"].get(uid, "Участник")
    
    text = (
        f"👤 <b>ПРОФИЛЬ:</b> {message.from_user.first_name}\n"
        f"<code>---------------------------</code>\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"🏷 <b>КЛЕЙМО:</b> {RANKS[user['rep']]}\n"
        f"💬 <b>СООБЩЕНИЙ:</b> {user['msgs']}\n"
        f"🛡 <b>РОЛЬ:</b> {role}"
    )
    await message.answer(text, parse_mode="HTML")

# --- МОНИТОРИНГ (ДЛЯ АДМИН-ЧАТА) ---
@dp.message(Command("status"), F.chat.id == ADMIN_CHAT_ID)
async def sys_status(message: types.Message):
    start_time = time.time()
    msg = await message.answer("📡 Замеряю отклик...")
    ping = round((time.time() - start_time) * 1000)
    
    ram = psutil.virtual_memory()
    storage = os.path.getsize(DATA_FILE) / 1024
    
    text = (
        f"📟 <b>CORE MONITORING</b>\n"
        f"<code>---------------------------</code>\n"
        f"📡 <b>PING:</b> <code>{ping}ms</code>\n"
        f"💾 <b>RAM:</b> <code>{ram.used // 1024 // 1024}MB / 256MB</code>\n"
        f"📂 <b>DATA:</b> <code>{storage:.2f}KB</code>\n"
        f"<code>---------------------------</code>"
    )
    await msg.edit_text(text, parse_mode="HTML")

# --- АДМИН-КОМАНДЫ СЛОВАМИ (REPLY) ---
@dp.message(F.reply_to_message, F.chat.id != ADMIN_CHAT_ID)
async def admin_words(message: types.Message):
    # Проверка, админ ли написавший
    if str(message.from_user.id) not in db["admins"] and message.from_user.id != OWNER_ID:
        return

    cmd = message.text.lower()
    target = message.reply_to_message.from_user
    t_id = str(target.id)

    if cmd == "мут":
        await bot.restrict_chat_member(message.chat.id, target.id, permissions=types.ChatPermissions(can_send_messages=False))
        await message.answer(f"🤐 {target.first_name} отправлен в мут.")
        
    elif cmd == "размут":
        await bot.restrict_chat_member(message.chat.id, target.id, permissions=types.ChatPermissions(can_send_messages=True))
        await message.answer(f"🔊 {target.first_name} снова может говорить.")

    elif cmd == "клеймо -":
        if t_id in db["users"]:
            db["users"][t_id]["rep"] = max(db["users"][t_id]["rep"] - 1, -1)
            save_data(db)
            await message.answer(f"📉 Клеймо {target.first_name} понижено до: {get_user_rank(t_id)}")

    # Лог в админ-чат
    log_text = (
        f"🛡 <b>ACTION LOG</b>\n"
        f"👤 Мод: {message.from_user.first_name}\n"
        f"🎯 Цель: {target.first_name}\n"
        f"⚡️ Действие: {cmd.upper()}"
    )
    await bot.send_message(ADMIN_CHAT_ID, log_text, parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
