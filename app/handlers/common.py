from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from app.db.database import Database
from app.keyboards.user import main_menu_kb
from app.utils.texts import START_TEXT

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database):
    await db.add_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(START_TEXT, reply_markup=main_menu_kb())


@router.callback_query(lambda c: c.data == "main_menu")
async def back_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(START_TEXT, reply_markup=main_menu_kb())
    await callback.answer()
