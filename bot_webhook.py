import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ---------------- CONFIG ----------------
TOKEN = "8244139819:AAFYeGiH5H0-W3A1RSeWY6iozOdfYBxiw6A"  # вставь токен от BotFather
CHANNELS = ["MysliTreydera", "+T8GFH6W_LB04Yzgy"]
REF_BONUS = 21
DB_FILENAME = "data.db"
# ----------------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ---------- Database ----------
def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER UNIQUE,
        username TEXT,
        balance INTEGER DEFAULT 0,
        referrals_count INTEGER DEFAULT 0,
        ref_by INTEGER,
        registered_at TEXT
    )
    """)
    conn.commit()
    conn.close()

def get_user(tg_id):
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    return row

def create_user(tg_id, username, ref_by=None):
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    try:
        cur.execute("INSERT INTO users (tg_id, username, ref_by, registered_at) VALUES (?,?,?,?)",
                    (tg_id, username, ref_by, now))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

# ---------- Helpers ----------
async def is_subscribed_all_channels(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Заработать")
    kb.add("Баланс")
    kb.add("Рефераль")
    return kb

# ---------- Handlers ----------
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    if not get_user(tg_id):
        create_user(tg_id, username)

    subscribed = await is_subscribed_all_channels(tg_id)
    if not subscribed:
        ch_text = "\n".join([f"https://t.me/{c}" for c in CHANNELS])
        msg = f"Подпишитесь на каналы:\n{ch_text}\nПосле подписки нажмите /check"
        await message.answer(msg, reply_markup=types.ReplyKeyboardRemove())
        return

    await message.answer("Доступ открыт.", reply_markup=main_menu())

@dp.message_handler(commands=['check'])
async def cmd_check(message: types.Message):
    uid = message.from_user.id
    if await is_subscribed_all_channels(uid):
        await message.answer("Проверка пройдена — доступ открыт.", reply_markup=main_menu())
    else:
        await message.answer("Вы всё ещё не подписаны на все каналы.")

@dp.message_handler(lambda m: m.text == "Заработать")
async def cmd_earn(message: types.Message):
    uid = message.from_user.id
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={uid}"
    await message.answer(f"Реферальная ссылка:\n{ref_link}\nБонус за реферала: {REF_BONUS}₽")

@dp.message_handler(lambda m: m.text == "Баланс")
async def cmd_balance(message: types.Message):
    uid = message.from_user.id
    user = get_user(uid)
    if user:
        await message.answer(f"Баланс: {user[3]}₽\nРефералов: {user[4]}")
    else:
        await message.answer("Сначала нажмите /start")

@dp.message_handler(lambda m: m.text == "Рефераль")
async def cmd_referral(message: types.Message):
    uid = message.from_user.id
    user = get_user(uid)
    if user:
        await message.answer(f"Рефералов: {user[4]}\nБаланс: {user[3]}₽")

# ---------- Run Bot ----------
if __name__ == "__main__":
    init_db()
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)
