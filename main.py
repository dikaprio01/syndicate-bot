import asyncio
import os
import json
import time
import psutil
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from config import TOKEN, OWNER_ID, ADMIN_CHAT_ID, RANKS

# Инициализация
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
start_time = time.time()
DATA_FILE = "data.json"

# Хранилища
court_sessions = {}
active_chats = set()

# --- СИСТЕМА ДАННЫХ ---
def get_db():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f: 
            json.dump({"users": {}, "stats": {"total_msgs": 0}, "logs": []}, f)
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {"users": {}, "stats": {"total_msgs": 0}, "logs": []}

def save_db(data):
    if "logs" in data and len(data["logs"]) > 50:
        data["logs"] = data["logs"][-50:]
    with open(DATA_FILE, "w") as f: 
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def get_user_shared_groups(user_id):
    shared = []
    for chat_id in active_chats:
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status not in ["left", "kicked"]:
                chat = await bot.get_chat(chat_id)
                shared.append(chat.title or "Приватный сектор")
        except: continue
    return shared if shared else ["Связи не обнаружены"]

def get_admin_log_keys(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 БАН", callback_data=f"adm_ban_{user_id}"),
         InlineKeyboardButton(text="👢 КИК", callback_data=f"adm_kick_{user_id}")],
        [InlineKeyboardButton(text="⚖️ ПЕРЕДАТЬ В СУД", callback_data=f"start_court_{user_id}")],
        [InlineKeyboardButton(text="🔍 ДОСЬЕ", callback_data=f"user_info_{user_id}"),
         InlineKeyboardButton(text="🗑 УДАЛИТЬ", callback_data="delete_log")]
    ])

# --- КОМАНДЫ УПРАВЛЕНИЯ ЧАТОМ ---
@dp.message(Command("lock"))
async def cmd_lock(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    await bot.set_chat_permissions(message.chat.id, permissions=types.ChatPermissions(can_send_messages=False))
    await message.answer("🛑 <b>ПРОТОКОЛ «ТИШИНА» АКТИВИРОВАН</b>\nЧат заблокирован для рядовых участников.")

@dp.message(Command("unlock"))
async def cmd_unlock(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    await bot.set_chat_permissions(message.chat.id, permissions=types.ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
    await message.answer("🔋 <b>ПРОТОКОЛ «ТИШИНА» ДЕАКТИВИРОВАН</b>\nДоступ к связи восстановлен.")

# --- ОБРАБОТКА СПАМА ---
@dp.message(F.text)
async def message_handler(message: types.Message):
    if message.chat.type == "private" or message.chat.id == ADMIN_CHAT_ID: return
    active_chats.add(message.chat.id)

    db = get_db()
    uid = str(message.from_user.id)
    now = time.time()

    if uid not in db["users"]:
        db["users"][uid] = {"msgs": 0, "rep": 2, "last_ts": 0, "warns": 0, "joined": datetime.now().strftime("%d.%m.%Y")}
    
    user = db["users"][uid]
    user["msgs"] += 1
    db["stats"]["total_msgs"] += 1

    if now - user.get("last_ts", 0) < 2.2:
        user["warns"] = user.get("warns", 0) + 1
        if user["warns"] > 4:
            log_text = f"⚠️ <b>ОПОВЕЩЕНИЕ О НАРУШЕНИИ</b>\n\n👤 <b>Объект:</b> {message.from_user.full_name}\n🆔 <b>ID:</b> <code>{uid}</code>\n🚨 <b>Причина:</b> Аномальная активность (Спам)"
            await bot.send_message(ADMIN_CHAT_ID, log_text, reply_markup=get_admin_log_keys(uid))
            user["warns"] = 0
    else: user["warns"] = 0
    
    user["last_ts"] = now
    save_db(db)

# --- КРАСИВЫЙ ПРОФИЛЬ ---
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    db = get_db()
    uid = str(message.from_user.id)
    user = db["users"].get(uid, {"msgs": 0, "rep": 2, "joined": "Неизвестно"})
    
    rank = RANKS.get(user["rep"], "😐 Прохожий")
    premium = "💎 VIP" if message.from_user.is_premium else "Standard"
    role = "👑 Создатель" if message.from_user.id == OWNER_ID else "👤 Участник"

    text = (
        f"🌐 <b>ЛИЧНОЕ ДЕЛО: {message.from_user.first_name.upper()}</b>\n"
        f"<code>⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯</code>\n"
        f"🛡 <b>СТАТУС:</b> {role}\n"
        f"🏷 <b>КЛЕЙМО:</b> {rank}\n"
        f"💳 <b>ТАРИФ:</b> <code>{premium}</code>\n"
        f"<code>⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯</code>\n"
        f"📊 <b>АКТИВНОСТЬ:</b>\n"
        f"└  💬 Сообщений: <code>{user['msgs']}</code>\n"
        f"└  📅 В сети с: <code>{user.get('joined', 'Недавно')}</code>\n"
        f"🆔 <b>ID:</b> <code>{uid}</code>\n"
        f"<code>⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯</code>"
    )
    await message.reply(text)

# --- МОНИТОРИНГ ---
@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    t1 = time.time()
    m = await message.answer("📡 <i>Синхронизация с узлами...</i>")
    ping = round((time.time() - t1) * 1000)
    db = get_db()
    
    keys = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 ОЧИСТИТЬ ЛОГИ", callback_data="clear_logs_only")],
        [InlineKeyboardButton(text="🗑 ЗАКРЫТЬ", callback_data="delete_log")]
    ])
    
    await m.edit_text(
        f"⚙️ <b>СИСТЕМНЫЕ ПОКАЗАТЕЛИ</b>\n"
        f"<code>⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯</code>\n"
        f"📡 <b>ОТКЛИК:</b> <code>{ping}ms</code>\n"
        f"🧠 <b>RAM:</b> <code>{psutil.virtual_memory().percent}%</code>\n"
        f"📦 <b>БАЗА ДАННЫХ:</b> <code>{os.path.getsize(DATA_FILE)} B</code>\n"
        f"⌛ <b>АПТАЙМ:</b> <code>{round(time.time()-start_time)}s</code>\n"
        f"<code>⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯</code>", 
        reply_markup=keys
    )

# --- ОБРАБОТКА CALLBACK ---
@dp.callback_query(F.data == "clear_logs_only")
async def cb_clear_logs(callback: types.CallbackQuery):
    db = get_db()
    db["logs"] = []
    save_db(db)
    await callback.answer("🧹 История нарушений в базе зачищена.", show_alert=True)

@dp.callback_query(F.data.startswith("user_info_"))
async def cb_user_info(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    groups = await get_user_shared_groups(user_id)
    await callback.message.reply(f"🔍 <b>АНАЛИЗ СЕТЕЙ ЮЗЕРА</b> <code>{user_id}</code>:\n" + "\n".join([f"• {g}" for g in groups]))
    await callback.answer()

@dp.callback_query(F.data.startswith("adm_"))
async def admin_actions(callback: types.CallbackQuery):
    action, user_id = callback.data.split("_")[1], int(callback.data.split("_")[2])
    try:
        if action == "ban": await bot.ban_chat_member(callback.message.chat.id, user_id)
        elif action == "kick": await bot.unban_chat_member(callback.message.chat.id, user_id)
        await callback.message.edit_text(callback.message.text + f"\n\n🏁 <b>ВЕРДИКТ: {action.upper()} ПРИВЕДЕН В ИСПОЛНЕНИЕ</b>")
    except Exception as e: await callback.answer(f"Ошибка доступа: {e}")

@dp.callback_query(F.data.startswith("start_court_"))
async def start_court(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    court_msg = await bot.send_message(callback.message.chat.id, f"⚖️ <b>СУДЕБНЫЙ ПРОЦЕСС</b>\n\nОбъект: <code>{user_id}</code>\nТребуется голос присяжных для определения срока мута.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="⏳ 1м", callback_data=f"vote_1_{user_id}"),
            InlineKeyboardButton(text="⏳ 5м", callback_data=f"vote_5_{user_id}"),
            InlineKeyboardButton(text="⏳ 1ч", callback_data=f"vote_60_{user_id}")
        ]]))
    court_sessions[court_msg.message_id] = {"target_id": user_id, "votes": {"1":0,"5":0,"60":0}, "voters": []}
    await callback.answer("⚖️ Процесс запущен.")
    await asyncio.sleep(30)
    session = court_sessions.pop(court_msg.message_id, None)
    if session and sum(session["votes"].values()) > 0:
        win = max(session["votes"], key=session["votes"].get)
        await bot.restrict_chat_member(callback.message.chat.id, user_id, permissions=types.ChatPermissions(can_send_messages=False), until_date=int(time.time() + int(win)*60))
        await court_msg.edit_text(f"⚖️ <b>ПРИГОВОР ВЫНЕСЕН</b>\nНаказание: Ограничение связи на {win} мин.")
    else: await court_msg.edit_text("⚖️ <b>ПРОЦЕСС АННУЛИРОВАН</b>\nПричина: Отсутствие голосов.")

@dp.callback_query(F.data.startswith("vote_"))
async def handle_vote(callback: types.CallbackQuery):
    t_val, m_id = callback.data.split("_")[1], callback.message.message_id
    if m_id in court_sessions and callback.from_user.id not in court_sessions[m_id]["voters"]:
        court_sessions[m_id]["votes"][t_val] += 1
        court_sessions[m_id]["voters"].append(callback.from_user.id)
        await callback.answer("Голос учтен.")
    else: await callback.answer("Голос не принят (вы уже голосовали или время вышло).")

@dp.callback_query(F.data == "delete_log")
async def cb_delete(callback: types.CallbackQuery):
    await callback.message.delete()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.send_message(ADMIN_CHAT_ID, "💠 <b>СИНДИКАТ: Ядро системы активировано.</b>")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
