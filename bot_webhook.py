# bot_webhook.py
# Минимальный Telegram-бот через webhook для AlwaysData
# Aiogram 3.x, база SQLite

import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ---------------- CONFIG ----------------
TOKEN = "YOUR_BOT_TOKEN_HERE"  # <- вставь сюда токен от BotFather
CHANNELS = ["MysliTreydera", "+T8GFH6W_LB04Yzgy"]  # username публичного и приватного канала
REF_BONUS = 21  # рубли за приглашённого
DB_FILENAME = "data.db"
WEBHOOK_PATH = "/webhook"  # URL для webhook
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 3000
# ----------------------------------------

bot = Bot(token=TOKEN)
dp = Dispatcher()

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
        registered_at TEXT,
        credited_ref INTEGER DEFAULT 0
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
        cur.execute("INSERT INTO users (tg_id,username,ref_by,registered_at) VALUES (?,?,?,?)",
                    (tg_id, username, ref_by, now))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    return row


def credit_referrer(referrer_tg_id):
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + ?, referrals_count = referrals_count + 1 WHERE tg_id=?",
                (REF_BONUS, referrer_tg_id))
    conn.commit()
    conn.close()


def mark_ref_credited(tg_id):
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET credited_ref=1 WHERE tg_id=?", (tg_id,))
    conn.commit()
    conn.close()


def update_balance(tg_id, amount):
    conn = sqlite3.connect(DB_FILENAME)
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = balance + ? WHERE tg_id=?", (amount, tg_id))
    conn.commit()
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
    kb.add("Купить Hack Aviator")
    kb.add("Рефераль")
    kb.add("Баланс")
    return kb


# ---------- Handlers ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = message.text or ""
    parts = text.split()
    ref = None
    if len(parts) > 1:
        ref = parts[1].strip()

    tg_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    user = get_user(tg_id)
    if user is None:
        ref_by = None
        if ref:
            try:
                ref_by = int(ref)
                if ref_by == tg_id:
                    ref_by = None
            except:
                ref_by = None
        create_user(tg_id, username, ref_by)

        if ref_by:
            ref_user = get_user(ref_by)
            if ref_user:
                credit_referrer(ref_by)
                mark_ref_credited(tg_id)
                await bot.send_message(ref_by, f"Вам начислено {REF_BONUS}₽ за приглашение {username}!")

    # Проверка подписки
    subscribed = await is_subscribed_all_channels(tg_id)
    if not subscribed:
        ch_text = "\n".join([f"https://t.me/{c}" for c in CHANNELS])
        msg = f"Прежде чем получить доступ, подпишитесь на каналы:\n{ch_text}\n\nПосле подписки нажмите /check"
        await message.answer(msg, reply_markup=types.ReplyKeyboardRemove())
        return

    await message.answer("Добро пожаловать! Доступ открыт.", reply_markup=main_menu())


@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    uid = message.from_user.id
    if await is_subscribed_all_channels(uid):
        await message.answer("Проверка пройдена — доступ открыт.", reply_markup=main_menu())
    else:
        await message.answer("Вы всё ещё не подписаны на все каналы.")


@dp.message(lambda m: m.text == "Заработать")
async def cmd_earn(message: types.Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start={uid}"
    text = f"За каждого приглашённого реферала вы получаете {REF_BONUS}₽.\nВаша ссылка:\n{ref_link}\nПриглашайте друзей!"
    await message.answer(text)


@dp.message(lambda m: m.text == "Баланс")
async def cmd_balance(message: types.Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    balance = user[3]
    referrals = user[4]
    await message.answer(f"Баланс: {balance}₽\nРефералов: {referrals}")


@dp.message(lambda m: m.text == "Рефераль")
async def cmd_referral(message: types.Message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        await message.answer("Сначала нажми /start")
        return
    balance = user[3]
    referrals = user[4]

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Вывести средства")
    kb.add("Назад")
    await message.answer(f"Ваши рефералы: {referrals}\nБаланс: {balance}₽", reply_markup=kb)


@dp.message(lambda m: m.text == "Вывести средства")
async def cmd_withdraw(message: types.Message):
    uid = message.from_user.id
    user = get_user(uid)
    balance = user[3]
    referrals = user[4]

    if balance < 100:
        await message.answer("Минимальный вывод — 100₽. Доведите баланс до 100₽.")
        return
    if referrals < 10:
        await message.answer("Чтобы вывести, пригласите 10 рефералов.")
        return

    await message.answer("Поздравляем! Чтобы вывести средства, зарегистрируйтесь на сайте:\nhttps://your-site.example/withdraw")


@dp.message(lambda m: m.text == "Назад")
async def cmd_back(message: types.Message):
    await message.answer("Возвращаемся в меню.", reply_markup=main_menu())


@dp.message(lambda m: m.text == "Купить Hack Aviator")
async def cmd_buy(message: types.Message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("1 месяц — 320₽")
    kb.add("Год — 2688₽")
    kb.add("Назад")
    await message.answer("Выберите план:", reply_markup=kb)


@dp.message(lambda m: m.text in ["1 месяц — 320₽", "Год — 2688₽"])
async def cmd_buy_plan(message: types.Message):
    uid = message.from_user.id
    user = get_user(uid)
    balance = user[3]
    referrals = user[4]
    plan = message.text
    price = 320 if "1 месяц" in plan else 2688

    if balance < 100:
        await message.answer("У вас на балансе недостаточно средств (минимум 100₽ необходим).")
        return
    if referrals < 10:
        await message.answer("Для покупки плана требуется минимум 10 рефералов.")
        return

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Пополнить баланс", url="https://t.me/your_payment_bot_or_link"))
    kb.add(InlineKeyboardButton("Связаться с поддержкой", callback_data="contact_support"))
    await message.answer(f"Чтобы купить план ({plan}) нужно {price}₽.\nНажмите пополнить, чтобы оплатить.", reply_markup=kb)


# ---------- Webhook ----------
from aiohttp import web

async def handle(request):
    data = await request.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return web.Response(text="ok")

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)

if __name__ == "__main__":
    import asyncio
    init_db()
    print("Webhook bot started")
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
