from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.db.database import Database
from app.keyboards.admin import ticket_reply_kb
from app.keyboards.user import cancel_to_menu_kb
from app.states import SupportStates

router = Router()


@router.callback_query(lambda c: c.data == "support")
async def support_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_message)
    await callback.message.answer(
        "Напишите ваш вопрос одним сообщением. Администратор получит его и ответит вам.",
        reply_markup=cancel_to_menu_kb(),
    )
    await callback.answer()


@router.message(SupportStates.waiting_for_message)
async def support_receive(message: Message, state: FSMContext, db: Database):
    text = message.text or message.caption or "[пустое сообщение]"
    await db.create_ticket(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
        question=text,
    )
    await state.clear()
    await message.answer("✅ Ваше сообщение отправлено в поддержку.")

    notify_text = (
        "📬 <b>Новый тикет поддержки</b>\n"
        f"Пользователь: {message.from_user.full_name}\n"
        f"Username: @{message.from_user.username or 'без username'}\n"
        f"ID: <code>{message.from_user.id}</code>\n\n"
        f"💬 {text}"
    )

    targets = []
    if settings.support_chat_id:
        targets.append(settings.support_chat_id)
    targets.extend(settings.admin_ids)

    for target in set(targets):
        try:
            await message.bot.send_message(target, notify_text, reply_markup=ticket_reply_kb(message.from_user.id))
        except Exception:
            pass


@router.message(Command("reply"))
async def reply_command(message: Message):
    if message.from_user.id not in settings.admin_ids:
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /reply <user_id> <текст>")
        return

    user_id = int(parts[1])
    reply_text = parts[2]
    try:
        await message.bot.send_message(user_id, f"💬 Ответ поддержки:\n\n{reply_text}")
        await message.answer("✅ Ответ отправлен пользователю.")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить ответ: {e}")
