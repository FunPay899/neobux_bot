import asyncio
from math import ceil

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.db.database import Database
from app.keyboards.admin import (
    admin_menu_kb,
    admin_products_kb,
    admin_product_manage_kb,
    tickets_kb,
    ticket_reply_kb,
)
from app.services.broadcast import run_broadcast
from app.states import AdminProductStates, BroadcastStates, AdminReplyStates

router = Router()
PAGE_SIZE = 5


@router.message(Command("admin"))
async def admin_menu(message: Message):
    await message.answer("⚙️ <b>Админ-панель</b>", reply_markup=admin_menu_kb())


@router.callback_query(lambda c: c.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ <b>Админ-панель</b>", reply_markup=admin_menu_kb())
    await callback.answer()


async def _render_admin_products(callback: CallbackQuery, db: Database, page: int = 1):
    total = await db.count_all_products()
    offset = (page - 1) * PAGE_SIZE
    items = await db.get_all_products(limit=PAGE_SIZE, offset=offset)
    pages = max(1, ceil(total / PAGE_SIZE))
    await callback.message.edit_text(
        "📦 <b>Управление товарами</b>",
        reply_markup=admin_products_kb(items, page, page > 1, page < pages),
    )


@router.callback_query(lambda c: c.data == "admin_products")
async def admin_products(callback: CallbackQuery, db: Database):
    await _render_admin_products(callback, db, 1)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("admin_products_page:"))
async def admin_products_page(callback: CallbackQuery, db: Database):
    page = int(callback.data.split(":")[1])
    await _render_admin_products(callback, db, page)
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_product_add")
async def admin_product_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminProductStates.waiting_title)
    await callback.message.answer("Введите название товара:")
    await callback.answer()


@router.message(AdminProductStates.waiting_title)
async def add_product_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminProductStates.waiting_description)
    await message.answer("Введите описание товара:")


@router.message(AdminProductStates.waiting_description)
async def add_product_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AdminProductStates.waiting_price)
    await message.answer("Введите цену в Stars (целое число):")


@router.message(AdminProductStates.waiting_price)
async def add_product_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое число.")
        return
    await state.update_data(price_stars=int(message.text))
    await state.set_state(AdminProductStates.waiting_robux_amount)
    await message.answer("Введите количество Robux:")


@router.message(AdminProductStates.waiting_robux_amount)
async def add_product_robux(message: Message, state: FSMContext, db: Database):
    if not message.text.isdigit():
        await message.answer("Введите целое число.")
        return
    data = await state.get_data()
    product_id = await db.add_product(
        title=data["title"],
        description=data["description"],
        price_stars=data["price_stars"],
        robux_amount=int(message.text),
    )
    await state.clear()
    await message.answer(f"✅ Товар #{product_id} добавлен.")


@router.callback_query(lambda c: c.data.startswith("admin_product:"))
async def admin_product_view(callback: CallbackQuery, db: Database):
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return
    text = (
        f"📦 <b>{product['title']}</b>\n\n"
        f"ID: <code>{product['id']}</code>\n"
        f"Описание: {product['description']}\n"
        f"Цена: {product['price_stars']} ⭐\n"
        f"Robux: {product['robux_amount']}\n"
        f"Статус: {'Активен' if product['is_active'] else 'Скрыт'}"
    )
    await callback.message.edit_text(text, reply_markup=admin_product_manage_kb(product_id, bool(product['is_active'])))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("toggle_product:"))
async def toggle_product(callback: CallbackQuery, db: Database):
    product_id = int(callback.data.split(":")[1])
    await db.toggle_product(product_id)
    product = await db.get_product(product_id)
    await callback.message.edit_reply_markup(reply_markup=admin_product_manage_kb(product_id, bool(product['is_active'])))
    await callback.answer("Статус обновлен")


@router.callback_query(lambda c: c.data.startswith("delete_product:"))
async def delete_product(callback: CallbackQuery, db: Database):
    product_id = int(callback.data.split(":")[1])
    await db.delete_product(product_id)
    await callback.message.edit_text("🗑️ Товар удалён.", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("edit_product_field:"))
async def edit_product_field(callback: CallbackQuery, state: FSMContext):
    _, product_id, field = callback.data.split(":")
    await state.set_state(AdminProductStates.editing_field)
    await state.update_data(product_id=int(product_id), field=field)
    prompts = {
        "title": "Введите новое название:",
        "description": "Введите новое описание:",
        "price_stars": "Введите новую цену в Stars:",
        "robux_amount": "Введите новое количество Robux:",
    }
    await callback.message.answer(prompts[field])
    await callback.answer()


@router.message(AdminProductStates.editing_field)
async def save_product_field(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    product_id = data["product_id"]
    field = data["field"]
    value = message.text.strip()

    if field in {"price_stars", "robux_amount"}:
        if not value.isdigit():
            await message.answer("Введите целое число.")
            return
        value = int(value)

    await db.update_product_field(product_id, field, value)
    await state.clear()
    await message.answer("✅ Поле обновлено.")


@router.message(Command("broadcast"))
async def broadcast_command(message: Message, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_content)
    await message.answer("Отправьте сообщение, фото или видео для рассылки.")


@router.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_button(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastStates.waiting_content)
    await callback.message.answer("Отправьте сообщение, фото или видео для рассылки.")
    await callback.answer()


@router.message(BroadcastStates.waiting_content)
async def process_broadcast(message: Message, state: FSMContext, db: Database):
    await state.clear()
    user_ids = await db.get_all_user_ids()
    await message.answer(f"📢 Запускаю рассылку по {len(user_ids)} пользователям...")

    async def bg():
        success, failed = await run_broadcast(message.bot, user_ids, message)
        await message.answer(f"✅ Рассылка завершена.\nУспешно: {success} / Ошибок: {failed}")

    asyncio.create_task(bg())


@router.callback_query(lambda c: c.data == "admin_tickets")
async def admin_tickets(callback: CallbackQuery, db: Database):
    tickets = await db.get_open_tickets()
    if not tickets:
        await callback.message.edit_text("📬 Активных тикетов нет.", reply_markup=admin_menu_kb())
    else:
        await callback.message.edit_text("📬 <b>Активные тикеты</b>", reply_markup=tickets_kb(tickets))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("ticket:"))
async def ticket_view(callback: CallbackQuery, db: Database):
    user_id = int(callback.data.split(":")[1])
    tickets = await db.get_open_tickets()
    target = next((t for t in tickets if t["user_id"] == user_id), None)
    if not target:
        await callback.answer("Тикет не найден", show_alert=True)
        return
    text = (
        f"📬 <b>Тикет пользователя</b>\n\n"
        f"Имя: {target['full_name']}\n"
        f"Username: @{target['username'] or 'без username'}\n"
        f"ID: <code>{target['user_id']}</code>\n\n"
        f"💬 {target['question']}"
    )
    await callback.message.edit_text(text, reply_markup=ticket_reply_kb(user_id))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("ticket_reply:"))
async def ticket_reply_start(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await state.set_state(AdminReplyStates.waiting_reply)
    await state.update_data(reply_user_id=user_id)
    await callback.message.answer(f"Введите ответ для пользователя {user_id}:")
    await callback.answer()


@router.message(AdminReplyStates.waiting_reply)
async def ticket_reply_send(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data["reply_user_id"]
    try:
        await message.bot.send_message(user_id, f"💬 Ответ поддержки:\n\n{message.text}")
        await message.answer("✅ Ответ отправлен.")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    await state.clear()


@router.callback_query(lambda c: c.data.startswith("ticket_close:"))
async def ticket_close(callback: CallbackQuery, db: Database):
    user_id = int(callback.data.split(":")[1])
    await db.close_ticket(user_id)
    await callback.message.edit_text("✅ Тикет закрыт.", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, db: Database):
    stats = await db.bot_stats()
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"🆕 Новых за сегодня: <b>{stats['today_users']}</b>\n"
        f"📅 Новых за неделю: <b>{stats['week_users']}</b>\n"
        f"💰 Продажи сегодня: <b>{stats['sales_today']}</b> ⭐\n"
        f"💎 Продажи за всё время: <b>{stats['sales_total']}</b> ⭐\n"
        f"📦 Успешных заказов: <b>{stats['success_orders']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_menu_kb())
    await callback.answer()
