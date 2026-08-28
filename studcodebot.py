import os
import asyncio
import logging
import json
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ------------------ КОНФИГУРАЦИЯ ------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = 1302410770
MY_USERNAME = "@myhzxc"

BRATSK_TZ = pytz.timezone('Asia/Irkutsk')
ORDERS_FILE = "orders.json"

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    logging.error("BOT_TOKEN не найден!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ------------------ РАБОТА С ФАЙЛОМ ------------------
def load_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logging.warning("Файл orders.json повреждён, создаём новый")
            return {}
    return {}

def save_orders():
    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logging.error(f"Ошибка сохранения заказов: {e}")

orders = load_orders()
logging.info(f"Загружено {len(orders)} заказов")

# ------------------ СОСТОЯНИЯ ------------------
class OrderStates(StatesGroup):
    description = State()
    budget = State()
    priority = State()

class NegotiationStates(StatesGroup):
    admin_price = State()
    client_counter = State()

# ------------------ КЛАВИАТУРЫ ------------------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 Заказать бота", callback_data="new_order")
        ],
        [
            InlineKeyboardButton(text="📊 Мои заказы", callback_data="my_orders"),
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")
        ]
    ])

def priority_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Не срочно", callback_data="priority_low"),
            InlineKeyboardButton(text="🟡 Нормальный", callback_data="priority_mid"),
            InlineKeyboardButton(text="🔴 Срочно", callback_data="priority_high")
        ]
    ])

def negotiation_keyboard(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Согласен с ценой", callback_data=f"accept_price|{order_id}"),
            InlineKeyboardButton(text="💰 Предложить свою цену", callback_data=f"counter_price|{order_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Отказаться", callback_data=f"reject_offer|{order_id}")
        ]
    ])

def admin_negotiation_keyboard(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Предложить цену", callback_data=f"admin_offer|{order_id}"),
            InlineKeyboardButton(text="📩 Написать клиенту", callback_data=f"admin_contact|{order_id}")
        ],
        [
            InlineKeyboardButton(text="📦 В архив", callback_data=f"archive|{order_id}")
        ]
    ])

# ------------------ /START ------------------
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    
    now_bratsk = datetime.now(BRATSK_TZ)
    time_str = now_bratsk.strftime("%H:%M")
    
    await message.answer(
        f"👋 **Привет!** (по Братску сейчас {time_str})\n\n"
        "Я — бот **\"УГОЛОК СТУДЕНТА\"**\n\n"
        "Помогаю заказать разработку Telegram-бота.\n\n"
        "👇 Нажми кнопку, чтобы оставить заявку",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ------------------ ШАГ 1: ОПИСАНИЕ ------------------
@dp.callback_query(F.data == "new_order")
async def new_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 **Шаг 1 из 3: Опишите задачу**\n\n"
        "Что должен уметь ваш будущий бот?\n"
        "- Для чего он нужен?\n"
        "- Какие функции должны быть?\n"
        "- Есть ли примеры похожих ботов?\n\n"
        "Напишите всё подробно 👇",
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.description)
    await callback.answer()

@dp.message(OrderStates.description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    await message.answer(
        "💰 **Шаг 2 из 3: Укажите ваш бюджет**\n\n"
        "Сколько вы готовы заплатить за разработку?\n"
        "Напишите сумму в рублях.\n\n"
        "📌 *Пример: 300* — если вы хотите, как в нашем примере",
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.budget)

# ------------------ ШАГ 2: БЮДЖЕТ ------------------
@dp.message(OrderStates.budget)
async def get_budget(message: Message, state: FSMContext):
    # Проверяем, что введено число
    try:
        budget = int(message.text)
        if budget <= 0:
            await message.answer("❌ Сумма должна быть больше 0. Попробуйте ещё раз.")
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 300). Попробуйте ещё раз.")
        return
    
    await state.update_data(budget=message.text)
    
    await message.answer(
        "⏰ **Шаг 3 из 3: Выберите срочность**\n\n"
        "🟢 **Не срочно** — сделаем в свободное время\n"
        "🟡 **Нормальный** — средний приоритет\n"
        "🔴 **Срочно** — сделаем в первую очередь\n\n"
        "Выберите вариант 👇",
        parse_mode="Markdown",
        reply_markup=priority_buttons()
    )
    await state.set_state(OrderStates.priority)

# ------------------ ШАГ 3: СРОЧНОСТЬ ------------------
priority_names = {
    "priority_low": "🟢 Не срочно",
    "priority_mid": "🟡 Нормальный",
    "priority_high": "🔴 Срочно"
}

@dp.callback_query(OrderStates.priority, F.data.startswith("priority_"))
async def get_priority(callback: CallbackQuery, state: FSMContext):
    priority = callback.data
    priority_text = priority_names.get(priority, "❓ Неизвестно")
    
    data = await state.get_data()
    data["priority"] = priority_text
    
    order_id = f"ORDER_{callback.from_user.id}_{int(datetime.now().timestamp())}"
    
    order_data = {
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "description": data.get("description", "—"),
        "budget": data.get("budget", "—"),
        "priority": priority_text,
        "status": "negotiation",
        "paid": False,
        "final_price": None,
        "created_at": datetime.now(BRATSK_TZ).strftime("%d.%m.%Y %H:%M")
    }
    orders[order_id] = order_data
    save_orders()
    
    # ---------- ОТПРАВКА ЗАКАЗА АДМИНУ ----------
    username = f"@{callback.from_user.username}" if callback.from_user.username else "без юзернейма"
    
    admin_msg = (
        f"📦 **НОВЫЙ ЗАКАЗ!**\n\n"
        f"📝 **Описание ТЗ:**\n{data.get('description', '—')}\n\n"
        f"💰 **Бюджет клиента:** {data.get('budget', '—')} ₽\n"
        f"⏰ **Срочность:** {priority_text}\n\n"
        f"👤 **Заказчик:** {username}\n"
        f"🆔 **ID:** `{callback.from_user.id}`\n"
        f"🕐 **Время:** {order_data['created_at']}\n\n"
        "💬 **Начните торг:** предложите свою цену или свяжитесь с клиентом.\n"
        "📌 *Пример: если бюджет 300 ₽, можно предложить 500 ₽ или договориться о 300 ₽*",
        parse_mode="Markdown",
        reply_markup=admin_negotiation_keyboard(order_id)
    )
    
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_msg,
        parse_mode="Markdown"
    )
    
    # Ответ пользователю
    await callback.message.edit_text(
        f"✅ **Заказ принят!**\n\n"
        f"🆔 **Заказ:** `{order_id}`\n"
        f"💰 **Ваш бюджет:** {data.get('budget', '—')} ₽\n"
        f"⏰ **Срочность:** {priority_text}\n\n"
        "💬 **Я свяжусь с вами для обсуждения цены.**\n\n"
        "📌 *Пример: если вы указали 300 ₽, мы можем обсудить цену в обе стороны.*\n\n"
        "Цена обсуждаема!",
        parse_mode="Markdown"
    )
    
    await state.clear()
    await callback.answer()

# ------------------ АДМИН: ПРЕДЛОЖИТЬ ЦЕНУ ------------------
@dp.callback_query(F.data.startswith("admin_offer|"))
async def admin_offer_price(callback: CallbackQuery, state: FSMContext):
    order_id = callback.data.split("|")[1]
    
    if order_id not in orders:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    budget = orders[order_id].get("budget", "—")
    
    await state.update_data(negotiation_order_id=order_id)
    await state.set_state(NegotiationStates.admin_price)
    
    await callback.message.answer(
        f"💰 **Введите вашу цену для заказа `{order_id}`**\n\n"
        f"📌 *Бюджет клиента: {budget} ₽*\n"
        f"📌 *Например: 300 — согласиться, 500 — повысить, 200 — снизить*\n\n"
        "Напишите сумму в рублях:",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(NegotiationStates.admin_price)
async def send_admin_price(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("negotiation_order_id")
    
    if not order_id or order_id not in orders:
        await message.answer("❌ Заказ не найден.")
        await state.clear()
        return
    
    try:
        price = int(message.text)
        if price <= 0:
            await message.answer("❌ Сумма должна быть больше 0. Попробуйте ещё раз.")
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число (например: 300). Попробуйте ещё раз.")
        return
    
    order = orders[order_id]
    order["final_price"] = str(price)
    save_orders()
    
    username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"
    
    client_msg = (
        f"💬 **Предложение по цене для заказа `{order_id}`**\n\n"
        f"💰 **Ваш бюджет:** {order.get('budget', '—')} ₽\n"
        f"🔹 **Моё предложение:** {price} ₽\n\n"
        "Вы можете:\n"
        "✅ Согласиться с ценой\n"
        "💰 Предложить свою цену\n"
        "❌ Отказаться\n\n"
        "*Цена обсуждаема! Можем найти компромисс.*",
        parse_mode="Markdown",
        reply_markup=negotiation_keyboard(order_id)
    )
    
    await bot.send_message(
        chat_id=order["user_id"],
        text=client_msg,
        parse_mode="Markdown"
    )
    
    await message.answer(
        f"✅ Цена {price} ₽ отправлена клиенту для заказа `{order_id}`.\n"
        "Ожидайте ответа.",
        parse_mode="Markdown"
    )
    
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"💬 **Предложение отправлено**\n\n"
            f"🆔 Заказ: `{order_id}`\n"
            f"💰 Предложено: {price} ₽"
        ),
        parse_mode="Markdown"
    )
    
    await state.clear()

# ------------------ КЛИЕНТ: СОГЛАСИТЬСЯ ------------------
@dp.callback_query(F.data.startswith("accept_price|"))
async def accept_price(callback: CallbackQuery):
    order_id = callback.data.split("|")[1]
    
    if order_id not in orders:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    order = orders[order_id]
    order["status"] = "accepted"
    order["paid"] = True
    save_orders()
    
    final_price = order.get("final_price", order.get("budget", "—"))
    
    await callback.message.edit_text(
        f"✅ **Вы согласились с ценой!**\n\n"
        f"🆔 Заказ: `{order_id}`\n"
        f"💰 Итоговая цена: {final_price} ₽\n\n"
        "Я свяжусь с вами для уточнения деталей и начала работы.\n\n"
        "📩 Если нужна срочная связь: @myhzxc",
        parse_mode="Markdown"
    )
    
    username = f"@{callback.from_user.username}" if callback.from_user.username else "без юзернейма"
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"✅ **Клиент согласился на цену!**\n\n"
            f"🆔 Заказ: `{order_id}`\n"
            f"💰 Итоговая цена: {final_price} ₽\n"
            f"👤 Клиент: {username}\n\n"
            "Можно приступать к работе!"
        ),
        parse_mode="Markdown"
    )
    
    await callback.answer()

# ------------------ КЛИЕНТ: ПРЕДЛОЖИТЬ СВОЮ ЦЕНУ ------------------
@dp.callback_query(F.data.startswith("counter_price|"))
async def counter_price(callback: CallbackQuery, state: FSMContext):
    order_id = callback.data.split("|")[1]
    
    if order_id not in orders:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    await state.update_data(negotiation_order_id=order_id)
    await state.set_state(NegotiationStates.client_counter)
    
    await callback.message.edit_text(
        f"💰 **Введите вашу цену для заказа `{order_id}`**\n\n"
        "Напишите сумму в рублях, которую вы готовы заплатить.\n"
        "Администратор увидит ваше предложение.",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(NegotiationStates.client_counter)
async def send_client_counter(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("negotiation_order_id")
    
    if not order_id or order_id not in orders:
        await message.answer("❌ Заказ не найден.")
        await state.clear()
        return
    
    try:
        price = int(message.text)
        if price <= 0:
            await message.answer("❌ Сумма должна быть больше 0. Попробуйте ещё раз.")
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число. Попробуйте ещё раз.")
        return
    
    order = orders[order_id]
    order["final_price"] = str(price)
    save_orders()
    
    username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"
    
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"💰 **Клиент предложил свою цену!**\n\n"
            f"🆔 Заказ: `{order_id}`\n"
            f"👤 Клиент: {username}\n"
            f"💰 Предложено: {price} ₽\n\n"
            "Используйте кнопки ниже для ответа.",
            parse_mode="Markdown"
        ),
        reply_markup=admin_negotiation_keyboard(order_id)
    )
    
    await message.answer(
        f"✅ Ваше предложение ({price} ₽) отправлено!\n\n"
        "Ожидайте ответа от администратора.",
        parse_mode="Markdown"
    )
    
    await state.clear()

# ------------------ КЛИЕНТ: ОТКАЗАТЬСЯ ------------------
@dp.callback_query(F.data.startswith("reject_offer|"))
async def reject_offer(callback: CallbackQuery):
    order_id = callback.data.split("|")[1]
    
    if order_id not in orders:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    order = orders[order_id]
    order["status"] = "rejected"
    save_orders()
    
    await callback.message.edit_text(
        f"❌ **Вы отказались от заказа `{order_id}`**\n\n"
        "Если передумаете, просто напишите мне — @myhzxc",
        parse_mode="Markdown"
    )
    
    username = f"@{callback.from_user.username}" if callback.from_user.username else "без юзернейма"
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            f"❌ **Клиент отказался**\n\n"
            f"🆔 Заказ: `{order_id}`\n"
            f"👤 Клиент: {username}"
        ),
        parse_mode="Markdown"
    )
    
    await callback.answer()

# ------------------ АДМИН: СВЯЗАТЬСЯ С КЛИЕНТОМ ------------------
@dp.callback_query(F.data.startswith("admin_contact|"))
async def admin_contact(callback: CallbackQuery):
    order_id = callback.data.split("|")[1]
    
    if order_id not in orders:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return
    
    order = orders[order_id]
    
    await callback.message.answer(
        f"📩 **Связь с клиентом**\n\n"
        f"🆔 Заказ: `{order_id}`\n"
        f"👤 Клиент: @{order.get('username') or 'без юзернейма'}\n"
        f"🆔 ID: `{order['user_id']}`\n\n"
        "Напишите сообщение, и оно будет отправлено клиенту.",
        parse_mode="Markdown"
    )
    waiting_for_reply[callback.from_user.id] = order["user_id"]
    await callback.answer()

# ------------------ АДМИН: В АРХИВ ------------------
@dp.callback_query(F.data.startswith("archive|"))
async def archive_order(callback: CallbackQuery):
    order_id = callback.data.split("|")[1]
    
    if order_id in orders:
        orders[order_id]["status"] = "archived"
        save_orders()
    
    await callback.answer("📦 Заказ в архиве")
    await callback.message.edit_text(
        f"{callback.message.text or callback.message.caption}\n\n📦 **В архиве**",
        parse_mode="Markdown"
    )

# ------------------ ОТВЕТЫ АДМИНА ПОЛЬЗОВАТЕЛЮ ------------------
waiting_for_reply = {}

@dp.message()
async def handle_admin_reply(message: Message):
    admin_id = message.from_user.id
    if admin_id in waiting_for_reply:
        target_user_id = waiting_for_reply.pop(admin_id)
        reply_text = message.text
        try:
            await bot.send_message(
                target_user_id,
                f"✉️ **Сообщение от администратора:**\n\n{reply_text}\n\n"
                f"📩 Если нужно — напишите @myhzxc",
                parse_mode="Markdown"
            )
            await message.answer(f"✅ Отправлено пользователю")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")

# ------------------ ИСТОРИЯ ЗАКАЗОВ ------------------
@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: CallbackQuery):
    user_orders = []
    for oid, data in orders.items():
        if data["user_id"] == callback.from_user.id:
            status = data.get("status", "new")
            status_emoji = {
                "negotiation": "💬",
                "accepted": "✅",
                "rejected": "❌",
                "archived": "📦",
                "new": "🆕"
            }.get(status, "🆕")
            price = data.get("final_price") or data.get("budget", "—")
            user_orders.append(f"`{oid}` — {status_emoji} {status} ({price} ₽)")
    
    if user_orders:
        text = (
            "📊 **Ваши заказы:**\n\n"
            + "\n".join(user_orders)
            + f"\n\n📌 **Всего заказов:** {len(user_orders)}"
        )
    else:
        text = "📊 **У вас пока нет заказов.**\n\nНажмите '🤖 Заказать бота', чтобы оставить заявку."
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

# ------------------ О ПРОЕКТЕ ------------------
@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ **О проекте**\n\n"
        "**\"УГОЛОК СТУДЕНТА\"** — сервис по разработке Telegram-ботов.\n\n"
        "💬 **Как мы работаем:**\n"
        "1. Вы оставляете заявку с описанием и бюджетом\n"
        "2. Мы обсуждаем цену (можно поторговаться!)\n"
        "3. Договариваемся и начинаем работу\n\n"
        "📌 *Пример: бюджет 300 ₽ → обсуждаем, приходим к общей цене*\n\n"
        "📩 **Связь:** @myhzxc",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

# ------------------ ЗАПУСК ------------------
async def main():
    print("✅ Бот 'УГОЛОК СТУДЕНТА' запущен!")
    print(f"📨 Заказы приходят в: {ADMIN_CHAT_ID}")
    print(f"📁 Загружено заказов: {len(orders)}")
    print("💬 Система торгов включена!")
    print("📌 Пример бюджета: 300 ₽")
    print(f"📩 Ваш юзернейм: {MY_USERNAME}")
    print(f"🕐 Часовой пояс: Asia/Irkutsk (Братск)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
