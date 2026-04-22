from math import ceil

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message

from app.db.database import Database
from app.keyboards.user import catalog_kb, product_kb, profile_kb, cancel_to_menu_kb
from app.states import ProfileStates

router = Router()
PAGE_SIZE = 5


async def _render_catalog(callback: CallbackQuery, db: Database, page: int = 1):
    total = await db.count_active_products()
    offset = (page - 1) * PAGE_SIZE
    products = await db.get_active_products(limit=PAGE_SIZE, offset=offset)
    pages = max(1, ceil(total / PAGE_SIZE))
    text = "🛍️ <b>Каталог Robux</b>\n\nВыберите подходящий пакет:"
    await callback.message.edit_text(
        text,
        reply_markup=catalog_kb(
            products=products,
            page=page,
            has_prev=page > 1,
            has_next=page < pages,
        ),
    )


@router.callback_query(lambda c: c.data == "catalog")
async def open_catalog(callback: CallbackQuery, db: Database):
    await _render_catalog(callback, db, 1)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("catalog_page:"))
async def paginate_catalog(callback: CallbackQuery, db: Database):
    page = int(callback.data.split(":")[1])
    await _render_catalog(callback, db, page)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("product:"))
async def product_card(callback: CallbackQuery, db: Database):
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    if not product or not product["is_active"]:
        await callback.answer("Товар недоступен", show_alert=True)
        return

    text = (
        f"📦 <b>{product['title']}</b>\n\n"
        f"🎮 Robux: <b>{product['robux_amount']}</b>\n"
        f"⭐ Цена: <b>{product['price_stars']}</b>\n\n"
        f"📝 {product['description']}"
    )
    await callback.message.edit_text(text, reply_markup=product_kb(product_id))
    await callback.answer()


@router.callback_query(lambda c: c.data == "profile")
async def profile(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    orders = await db.get_user_last_orders(callback.from_user.id, 5)
    roblox_username = user.get("roblox_username") if user else None

    history = "\n".join(
        f"• #{o['id']} | {o['created_at'][:16].replace('T', ' ')} | {o['robux_amount']} Robux | {o['status']}"
        for o in orders
    ) if orders else "Покупок пока нет."

    text = (
        "👤 <b>Профиль</b>\n\n"
        f"🆔 Telegram ID: <code>{callback.from_user.id}</code>\n"
        f"🎮 Roblox username: <b>{roblox_username or 'не указан'}</b>\n\n"
        "⭐ <b>Баланс Telegram Stars:</b> звезды покупаются через официальный интерфейс Telegram.\n"
        "Бот не пополняет Stars напрямую, а принимает их при оплате заказа.\n\n"
        "🧾 <b>Последние 5 покупок:</b>\n"
        f"{history}"
    )
    await callback.message.edit_text(text, reply_markup=profile_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "topup_stars")
async def topup_stars(callback: CallbackQuery):
    text = (
        "⭐ <b>Как пополнить Stars</b>\n\n"
        "1. Откройте Telegram Settings / Настройки.\n"
        "2. Найдите раздел Telegram Stars.\n"
        "3. Купите нужное количество звезд через встроенный интерфейс Telegram.\n"
        "4. Вернитесь в бота и оплатите выбранный товар."
    )
    await callback.message.edit_text(text, reply_markup=profile_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "set_roblox")
async def ask_roblox(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_roblox_username)
    await callback.message.answer(
        "Введите ваш Roblox username или Roblox ID, на который нужно зачислять Robux:",
        reply_markup=cancel_to_menu_kb(),
    )
    await callback.answer()


@router.message(ProfileStates.waiting_for_roblox_username)
async def save_roblox(message: Message, state: FSMContext, db: Database):
    await db.update_user_roblox(message.from_user.id, message.text.strip())
    await state.clear()
    await message.answer("✅ Roblox username сохранён. Теперь можно оплачивать покупки.")


@router.callback_query(lambda c: c.data == "cancel_state")
async def cancel_state(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("buy:"))
async def buy_product(callback: CallbackQuery, db: Database, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    user = await db.get_user(callback.from_user.id)

    if not product or not product["is_active"]:
        await callback.answer("Товар недоступен", show_alert=True)
        return

    if not user or not user.get("roblox_username"):
        await state.set_state(ProfileStates.waiting_for_roblox_username_before_payment)
        await state.update_data(product_id=product_id)
        await callback.message.answer(
            "Перед оплатой укажите ваш Roblox username или Roblox ID для зачисления Robux:",
            reply_markup=cancel_to_menu_kb(),
        )
        await callback.answer()
        return

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=product["title"],
        description=product["description"],
        payload=f"buy_product_{product_id}",
        currency="XTR",
        prices=[LabeledPrice(label=product["title"], amount=product["price_stars"])],
        provider_token="",
    )
    await callback.answer()


@router.message(ProfileStates.waiting_for_roblox_username_before_payment)
async def save_roblox_and_pay(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    product_id = data["product_id"]
    product = await db.get_product(product_id)

    await db.update_user_roblox(message.from_user.id, message.text.strip())
    await state.clear()

    await message.bot.send_invoice(
        chat_id=message.from_user.id,
        title=product["title"],
        description=product["description"],
        payload=f"buy_product_{product_id}",
        currency="XTR",
        prices=[LabeledPrice(label=product["title"], amount=product["price_stars"])],
        provider_token="",
    )
