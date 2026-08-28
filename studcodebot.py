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
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

# ------------------ КОНФИГУРАЦИЯ ------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = 1302410770

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
    payment = State()
    priority = State()

# ------------------ КЛАВИАТУРЫ ------------------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Заказать бота", callback_data="new_order")],
        [InlineKeyboardButton(text="📊 Мои заказы", callback_data="my_orders"),
         InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")]
    ])

def payment_methods():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 200 Stars", callback_data="pay_stars"),
         InlineKeyboardButton(text="💳 На карту", callback_data="pay_card")]
    ])

def priority_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Не срочно", callback_data="priority_low"),
         InlineKeyboardButton(text="🟡 Нормальный", callback_data="priority_mid"),
         InlineKeyboardButton(text="🔴 Срочно", callback_data="priority_high")]
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
        "💳 **Шаг 2 из 3: Выберите способ оплаты**\n\n"
        "⭐ **200 Stars** — оплата внутри Telegram (мгновенно)\n"
        "💳 **На карту** — я пришлю реквизиты в личку\n\n"
        "*Если выберете 'На карту', я напишу вам сам*",
        parse_mode="Markdown",
        reply_markup=payment_methods()
    )
    await state.set_state(OrderStates.payment)

# ------------------ ШАГ 2: ОПЛАТА ------------------
@dp.callback_query(OrderStates.payment, F.data == "pay_stars")
async def pay_stars(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment="stars")
    await callback.message.edit_text(
        "⏰ **Шаг 3 из 3: Выберите срочность**\n\n"
        "🟢 **Не срочно** — сделаем в свободное время\n"
        "🟡 **Нормальный** — средний приоритет\n"
        "🔴 **Срочно** — сделаем в первую очередь\n\n"
        "Выберите вариант 👇",
        parse_mode="Markdown",
        reply_markup=priority_buttons()
    )
    await state.set_state(OrderStates.priority)
    await callback.answer()

@dp.callback_query(OrderStates.payment, F.data == "pay_card")
async def pay_card(callback: CallbackQuery, state: FSMContext):
    await state.update_data(payment="card")
    await callback.message.edit_text(
        "⏰ **Шаг 3 из 3: Выберите срочность**\n\n"
        "🟢 **Не срочно** — сделаем в свободное время\n"
        "🟡 **Нормальный** — средний приоритет\n"
        "🔴 **Срочно** — сделаем в первую очередь\n\n"
        "Выберите вариант 👇",
        parse_mode="Markdown",
        reply_markup=priority_buttons()
    )
    await state.set_state(OrderStates.priority)
    await callback.answer()

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
    
    payment_type = data.get("payment", "—")
    if payment_type == "stars":
        payment_text = "⭐ 200 Stars"
        status_text = "⏳ Ожидает оплаты Stars"
        total_sum = "200 Stars"
    else:
        payment_text = "💳 На карту"
        status_text = "⏳ Ждёт реквизиты"
        total_sum = "— (будет указана позже)"
    
    order_data = {
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "description": data.get("description", "—"),
        "payment_type": payment_type,
        "payment_text": payment_text,
        "priority": priority_text,
        "status": "new",
        "paid": False,
        "total_sum": total_sum,
        "created_at": datetime.now(BRATSK_TZ).strftime("%d.%m.%Y %H:%M")
    }
    orders[order_id] = order_data
    save_orders()
    
    username = f"@{callback.from_user.username}" if callback.from_user.username else "без юзернейма"
    
    admin_msg = (
        f"📦 **ПРИШЁЛ НОВЫЙ ЗАКАЗ!**\n\n"
        f"📝 **Описание ТЗ:**\n{data.get('description', '—')}\n\n"
        f"💰 **Оплата:** {payment_text}\n"
        f"⏰ **Приоритетность:** {priority_text}\n\n"
        f"👤 **Заказчик:** {username}\n"
        f"🆔 **ID:** `{callback.from_user.id}`\n"
        f"🕐 **Время заказа:** {order_data['created_at']}\n\n"
        f"💳 **Статус оплаты:** {status_text}"
    )
    
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_msg,
        parse_mode="Markdown"
    )
    
    # ✅ ИСПРАВЛЕННЫЙ БЛОК ОПЛАТЫ
    if data.get("payment") == "stars":
        await callback.message.edit_text(
            f"✅ **Заказ принят!**\n\n"
            f"🆔 **Заказ:** `{order_id}`\n"
            f"⏰ **Срочность:** {priority_text}\n\n"
            "💳 **Внесите предоплату 200 Stars**\n\n"
            "Нажмите кнопку ниже, чтобы оплатить 👇",
            parse_mode="Markdown"
        )
        
        try:
            await bot.send_invoice(
                chat_id=callback.from_user.id,
                title="Предоплата за разработку бота",
                description=f"Заказ #{order_id}\nСрочность: {priority_text}",
                payload=f"payment_{order_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="⭐ 200 Stars", amount=200)],  # ← amount=200
                need_name=True,
                need_phone_number=True,
                start_parameter="pay",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⭐ Оплатить 200 Stars", pay=True)]
                ])
            )
        except Exception as e:
            logging.error(f"Ошибка send_invoice: {e}")
            await callback.message.answer(
                f"⚠️ Ошибка при создании счёта: `{str(e)}`\n\n"
                "Пожалуйста, напишите @studcodebot вручную.",
                parse_mode="Markdown"
            )
    else:
        await callback.message.edit_text(
            f"✅ **Заказ принят!**\n\n"
            f"🆔 **Заказ:** `{order_id}`\n"
            f"⏰ **Срочность:** {priority_text}\n\n"
            "💳 **Способ оплаты:** На карту\n\n"
            "Я напишу вам в ближайшее время с реквизитами карты.\n\n"
            "*Проверьте, что у вас открыты личные сообщения.*",
            parse_mode="Markdown"
        )
    
    await state.clear()
    await callback.answer()

# ------------------ ОБРАБОТКА ПЛАТЕЖЕЙ ------------------
@dp.pre_checkout_query()
async def pre_checkout_query(query: types.PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment_info = message.successful_payment
    order_id = payment_info.invoice_payload.replace("payment_", "")
    
    if order_id in orders:
        orders[order_id]["paid"] = True
        orders[order_id]["total_sum"] = "200 Stars"
        orders[order_id]["status"] = "paid"
        save_orders()
        
        await message.answer(
            f"✅ **Оплата получена!**\n\n"
            f"🆔 Заказ: `{order_id}`\n"
            "Спасибо за оплату! Мы начинаем работу над вашим заказом.",
            parse_mode="Markdown"
        )
        
        username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"
        
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"💰 **ОПЛАТА ПОЛУЧЕНА!**\n\n"
                f"🆔 Заказ: `{order_id}`\n"
                f"👤 Клиент: {username}\n"
                f"⭐ Сумма: 200 Stars\n\n"
                f"✅ Можно приступать к работе!"
            ),
            parse_mode="Markdown"
        )

# ------------------ ИСТОРИЯ ЗАКАЗОВ ------------------
@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: CallbackQuery):
    user_orders = []
    for oid, data in orders.items():
        if data["user_id"] == callback.from_user.id:
            if data.get("paid"):
                status = "✅ Оплачен"
            else:
                status = "⏳ Ожидает оплаты"
            
            if data.get("total_sum"):
                sum_text = data["total_sum"]
            elif data.get("payment_type") == "stars":
                sum_text = "200 Stars (ожидает оплаты)"
            else:
                sum_text = "На карту (сумма будет позже)"
            
            user_orders.append(f"`{oid}` — {status} ({sum_text})")
    
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
        "Помогаем автоматизировать бизнес и личные задачи.\n\n"
        "📩 **По вопросам:** @studcodebot",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

# ------------------ ЗАПУСК ------------------
async def main():
    print("✅ Бот 'УГОЛОК СТУДЕНТА' запущен!")
    print(f"📨 Заказы приходят в: {ADMIN_CHAT_ID}")
    print(f"📁 Загружено заказов: {len(orders)}")
    print("⭐ Оплата через Telegram Stars: 200 Stars")
    print("💳 Оплата на карту: реквизиты в личку")
    print(f"🕐 Часовой пояс: Asia/Irkutsk (Братск)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
