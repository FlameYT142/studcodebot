import os
import asyncio
import logging
from typing import Dict, Set
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from evolution_openai import AsyncCloud

# ------------------ КОНФИГУРАЦИЯ ------------------
BOT_TOKEN = "8992369673:AAH099klTiftB_tgA2pK3aBb1PWvHgSnRcE"
ADMIN_CHAT_ID = -5205066255

# ----- НАСТРОЙКИ CLOUD.RU -----
KEY_ID = "YjNjMDI0Y2QtMGJiNy00NTllLTgxMGYtMjRmZGFkZDRlNDM3"
SECRET = "510fc61b207f948fe8c5641336aa504a"
BASE_URL = "https://foundation-models.api.cloud.ru/v1"
MODEL_NAME = "deepseek-ai/DeepSeek-V4-Pro"

# Временная зона Братска (UTC+8)
BRATSK_TZ = pytz.timezone('Asia/Irkutsk')

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Инициализация клиента Cloud.ru
client = AsyncCloud(
    key_id=KEY_ID,
    secret=SECRET,
    base_url=BASE_URL
)

# ------------------ СОСТОЯНИЯ ДЛЯ FSM ------------------
class OrderStates(StatesGroup):
    description = State()
    budget = State()
    deadline = State()

class AIState(StatesGroup):
    chat = State()

# ------------------ ХРАНИЛИЩА ------------------
user_histories: Dict[int, list] = {}
waiting_for_reply: Dict[int, int] = {}

# ------------------ КЛАВИАТУРЫ ------------------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 Заказать бота", callback_data="new_order"),
            InlineKeyboardButton(text="🧠 ИИ-консультант", callback_data="ai_chat")
        ],
        [
            InlineKeyboardButton(text="📊 Мои заказы", callback_data="my_orders"),
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")
        ]
    ])

def order_admin_keyboard(user_id: int, username: str = None):
    data = f"{user_id}"
    if username:
        data += f"|{username}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💬 Связаться", callback_data=f"contact|{data}"),
            InlineKeyboardButton(text="📦 В архив", callback_data=f"archive|{data}")
        ],
        [
            InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_order|{data}")
        ]
    ])

# ------------------ КОМАНДА /START ------------------
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    
    now_bratsk = datetime.now(BRATSK_TZ)
    time_str = now_bratsk.strftime("%H:%M")
    
    await message.answer(
        f"👋 **Привет!** (по Братску сейчас {time_str})\n\n"
        "Я — бот проекта **\"УГОЛОК СТУДЕНТА\"**\n\n"
        "Я помогаю:\n"
        "🤖 **Заказывать ботов на заказ**\n"
        "🧠 **Консультироваться с ИИ** по разработке\n\n"
        "Выбери действие ниже 👇",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ------------------ ЗАКАЗ БОТА (FSM) ------------------
@dp.callback_query(F.data == "new_order")
async def new_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 **Расскажите, что нужно сделать:**\n\n"
        "Опишите функционал будущего бота максимально подробно:\n"
        "- Для чего нужен бот?\n"
        "- Какие функции должны быть?\n"
        "- Есть ли примеры похожих ботов?\n\n"
        "Напишите всё одним сообщением 👇",
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.description)
    await callback.answer()

@dp.message(OrderStates.description)
async def get_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer(
        "💰 **Какой бюджет?**\n\n"
        "Напишите сумму или диапазон (например: 15 000–20 000 ₽)",
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.budget)

@dp.message(OrderStates.budget)
async def get_budget(message: Message, state: FSMContext):
    await state.update_data(budget=message.text)
    await message.answer(
        "⏰ **Какие сроки?**\n\n"
        "Когда нужен готовый бот? (например: через 2 недели)",
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.deadline)

@dp.message(OrderStates.deadline)
async def get_deadline(message: Message, state: FSMContext):
    await state.update_data(deadline=message.text)
    data = await state.get_data()
    
    now_bratsk = datetime.now(BRATSK_TZ)
    time_str = now_bratsk.strftime("%d.%m.%Y %H:%M")
    
    username = f"@{message.from_user.username}" if message.from_user.username else "без юзернейма"
    admin_msg = (
        f"🤖 **НОВЫЙ ЗАКАЗ**\n\n"
        f"📝 **Описание:**\n{data['description']}\n\n"
        f"💰 **Бюджет:** {data['budget']}\n"
        f"⏰ **Сроки:** {data['deadline']}\n\n"
        f"👤 **Клиент:** {username}\n"
        f"🆔 **ID:** `{message.from_user.id}`\n"
        f"🕐 **Время (Братск):** {time_str}"
    )
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=admin_msg,
        reply_markup=order_admin_keyboard(message.from_user.id, message.from_user.username),
        parse_mode="Markdown"
    )
    
    await message.answer(
        "✅ **Заказ принят!**\n\n"
        "Мы свяжемся с вами в ближайшее время.\n"
        "А пока можете задать вопросы ИИ-консультанту.",
        parse_mode="Markdown"
    )
    await state.clear()

# ------------------ ИИ-КОНСУЛЬТАНТ ------------------
@dp.callback_query(F.data == "ai_chat")
async def ai_chat_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    user_id = callback.from_user.id
    
    if user_id not in user_histories:
        user_histories[user_id] = [
            {
                "role": "system",
                "content": (
                    "Ты — ИИ-консультант в проекте 'УГОЛОК СТУДЕНТА'. "
                    "Твоя задача — помогать клиентам сформулировать техническое задание на разработку ботов. "
                    "Отвечай на русском языке, дружелюбно, структурированно и по делу."
                )
            }
        ]
    
    await state.set_state(AIState.chat)
    
    await callback.message.edit_text(
        "🧠 **ИИ-консультант по разработке ботов**\n\n"
        "Задайте вопрос или опишите, что хотите автоматизировать.\n"
        "Я помогу уточнить требования и подготовить ТЗ.\n\n"
        "📌 Напишите /clear чтобы начать новый диалог.",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(AIState.chat)
async def ai_chat_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_message = message.text
    
    if user_message.lower() == "/clear":
        user_histories[user_id] = [
            {
                "role": "system",
                "content": (
                    "Ты — ИИ-консультант в проекте 'УГОЛОК СТУДЕНТА'. "
                    "Твоя задача — помогать клиентам сформулировать техническое задание на разработку ботов. "
                    "Отвечай на русском языке, дружелюбно и по делу."
                )
            }
        ]
        await message.answer("🧹 История очищена. Задавайте новый вопрос!")
        return
    
    if user_id not in user_histories:
        user_histories[user_id] = [
            {
                "role": "system",
                "content": (
                    "Ты — ИИ-консультант в проекте 'УГОЛОК СТУДЕНТА'. "
                    "Твоя задача — помогать клиентам сформулировать техническое задание на разработку ботов. "
                    "Отвечай на русском языке, дружелюбно и по делу."
                )
            }
        ]
    
    user_histories[user_id].append({"role": "user", "content": user_message})
    
    try:
        await bot.send_chat_action(message.chat.id, action="typing")
        
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=user_histories[user_id],
            max_tokens=2500,
            temperature=0.5,
            presence_penalty=0,
            top_p=0.95
        )
        
        assistant_reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": assistant_reply})
        
        if len(user_histories[user_id]) > 20:
            system_prompt = user_histories[user_id][0]
            user_histories[user_id] = [system_prompt] + user_histories[user_id][-10:]
        
        await message.answer(assistant_reply, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        await message.answer(
            f"⚠️ Ошибка: `{str(e)}`\n\nПопробуйте /clear",
            parse_mode="Markdown"
        )

# ------------------ ДЕЙСТВИЯ АДМИНОВ ------------------
@dp.callback_query(F.data.startswith("contact|"))
async def contact_order(callback: CallbackQuery):
    data_part = callback.data.split("|")[1]
    user_id = int(data_part.split("|")[0])
    
    await callback.message.answer(
        f"✏️ Напишите сообщение для клиента (ID: {user_id}):"
    )
    waiting_for_reply[callback.from_user.id] = user_id
    await callback.answer()

@dp.callback_query(F.data.startswith("archive|"))
async def archive_order(callback: CallbackQuery):
    await callback.answer("📦 Заказ в архиве")
    await callback.message.edit_text(
        f"{callback.message.text or callback.message.caption}\n\n📦 **В архиве**",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("reject_order|"))
async def reject_order(callback: CallbackQuery):
    data_part = callback.data.split("|")[1]
    user_id = int(data_part.split("|")[0])
    
    await callback.answer("❌ Заказ отклонён")
    await callback.message.edit_text(
        f"{callback.message.text or callback.message.caption}\n\n❌ **Отклонён**",
        parse_mode="Markdown"
    )
    try:
        await bot.send_message(
            user_id,
            "❌ К сожалению, мы не можем взяться за ваш заказ."
        )
    except:
        pass

@dp.message()
async def handle_admin_reply(message: Message):
    admin_id = message.from_user.id
    if admin_id in waiting_for_reply:
        target_user_id = waiting_for_reply.pop(admin_id)
        reply_text = message.text
        try:
            await bot.send_message(
                target_user_id,
                f"✉️ **Сообщение от модерации:**\n\n{reply_text}",
                parse_mode="Markdown"
            )
            await message.answer(f"✅ Отправлено (ID: {target_user_id})")
        except Exception as e:
            await message.answer(f"❌ Ошибка: {e}")

# ------------------ ЗАПУСК БОТА ------------------
async def main():
    print("✅ Бот 'УГОЛОК СТУДЕНТА' запущен!")
    print(f"🤖 Модель: {MODEL_NAME}")
    print(f"🕐 Часовой пояс: Asia/Irkutsk (Братск)")
    print(f"👥 Админ-чат: {ADMIN_CHAT_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())