from math import ceil

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message
from aiogram.exceptions import TelegramBadRequest

from app.db.database import Database
from app.keyboards.user import catalog_kb, product_kb, profile_kb, cancel_to_menu_kb
from app.states import PromoStates

router = Router()
PAGE_SIZE = 5


async def safe_edit_text(callback: CallbackQuery, text: str, reply_markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


async def _render_catalog(callback: CallbackQuery, db: Database, page: int = 1):
    total = await db.count_active_products()
    offset = (page - 1) * PAGE_SIZE
    products = await db.get_active_products(limit=PAGE_SIZE, offset=offset)
    pages = max(1, ceil(total / PAGE_SIZE))
    text = "🛍️ <b>Каталог Robux</b>\n\nВыберите подходящий пакет:"
    await safe_edit_text(
        callback,
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

    user = await db.get_user(callback.from_user.id)
    discount = user["discount_percent"] if user else 0
    final_price = max(product["price_stars"] - (product["price_stars"] * discount // 100), 1)
    text = (
        f"📦 <b>{product['title']}</b>\n\n"
        f"🎮 Robux: <b>{product['robux_amount']}</b>\n"
        f"⭐ Цена: <b>{product['price_stars']}</b>\n"
        f"💳 К оплате: <b>{final_price}</b>⭐\n"
    )
    if discount:
        text += f"🎟️ Активная скидка: <b>{discount}%</b>\n"
    text += f"\n📝 {product['description']}"
    await safe_edit_text(callback, text, reply_markup=product_kb(product_id))
    await callback.answer()


@router.callback_query(lambda c: c.data == "profile")
async def profile(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    orders = await db.get_user_last_orders(callback.from_user.id, 5)

    history = "\n".join(
        f"• #{o['id']} | {o['created_at'][:16].replace('T', ' ')} | {o['robux_amount']} Robux | {o['status']}"
        for o in orders
    ) if orders else "Покупок пока нет."

    text = (
        "👤 <b>Профиль</b>\n\n"
        f"🆔 Telegram ID: <code>{callback.from_user.id}</code>\n"
        f"⭐ Баланс: <b>{user['balance'] if user else 0}</b>\n"
        f"🎟️ Скидка: <b>{user['discount_percent'] if user else 0}%</b>\n\n"
        "🧾 <b>Последние 5 покупок:</b>\n"
        f"{history}"
    )
    await safe_edit_text(callback, text, reply_markup=profile_kb())
    await callback.answer()


@router.callback_query(lambda c: c.data == "promo_enter")
async def promo_enter(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoStates.user_enter_code)
    await callback.message.answer(
        "Введите промокод:",
        reply_markup=cancel_to_menu_kb(),
    )
    await callback.answer()


@router.message(PromoStates.user_enter_code)
async def promo_apply(message: Message, state: FSMContext, db: Database):
    code = message.text.strip().upper()
    promo = await db.get_promo_by_code(code)
    if not promo or not promo["is_active"]:
        await message.answer("❌ Промокод не найден или отключён.")
        await state.clear()
        return

    if promo["used_count"] >= promo["usage_limit"]:
        await message.answer("❌ Лимит использований промокода исчерпан.")
        await state.clear()
        return

    if await db.user_used_promo(promo["id"], message.from_user.id):
        await message.answer("❌ Вы уже использовали этот промокод.")
        await state.clear()
        return

    await db.apply_promo(promo["id"], message.from_user.id)
    if promo["promo_type"] == "discount":
        await db.set_discount(message.from_user.id, promo["value"])
        await message.answer(f"✅ Промокод активирован. Скидка {promo['value']}% применится к следующей оплате.")
    else:
        await db.add_balance(message.from_user.id, promo["value"])
        await message.answer(f"✅ Промокод активирован. На баланс начислено {promo['value']}⭐.")
    await state.clear()


@router.callback_query(lambda c: c.data == "cancel_state")
async def cancel_state(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Действие отменено.")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("buy:"))
async def buy_product(callback: CallbackQuery, db: Database, state: FSMContext):
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    user = await db.get_user(callback.from_user.id)

    if not product or not product["is_active"]:
        await callback.answer("Товар недоступен", show_alert=True)
        return

    discount = user["discount_percent"] if user else 0
    final_price = max(product["price_stars"] - (product["price_stars"] * discount // 100), 1)

    # внутренний баланс только для отображения/промокодов
    if user and user["balance"] >= final_price:
        await db.deduct_balance(callback.from_user.id, final_price)
        order_id = await db.add_order(
            user_id=callback.from_user.id,
            product_id=product_id,
            product_title=product["title"],
            robux_amount=product["robux_amount"],
            price_stars=product["price_stars"],
            final_price_stars=final_price,
            paid_via_balance=final_price,
            paid_via_stars=0,
            promo_code=None if discount == 0 else f"discount_{discount}",
            telegram_payment_charge_id=None,
            provider_payment_charge_id=None,
            status="Выдан",
        )
        if discount:
            await db.clear_discount(callback.from_user.id)
        await callback.message.answer(
            f"✅ Оплата прошла успешно!\n"
            f"Заказ <b>#{order_id}</b> оформлен.\n"
            f"🎮 Товар: <b>{product['title']}</b>\n"
            f"📦 Выдача будет произведена вручную."
        )
        await callback.bot.send_message(
            callback.from_user.id,
            f"🔔 Уведомление\nВаш платёж по заказу <b>#{order_id}</b> подтверждён. Ожидайте ручную выдачу.",
        )
        await notify_admins(callback, product, final_price, order_id)
        await callback.answer()
        return

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=product["title"],
        description=f"{product['description']}\nВыдача производится вручную.",
        payload=f"buy_product_{product_id}_{final_price}",
        currency="XTR",
        prices=[LabeledPrice(label=product["title"], amount=final_price)],
        provider_token="",
    )
    await callback.answer()


async def notify_admins(callback: CallbackQuery, product: dict, final_price: int, order_id: int):
    from app.config import settings
    text = (
        "💸 <b>Новая покупка!</b>\n"
        f"Пользователь: @{callback.from_user.username or 'без username'} (ID: {callback.from_user.id})\n"
        f"Товар: {product['title']}\n"
        f"Сумма: {final_price} ⭐️\n"
        f"Заказ: #{order_id}"
    )
    for admin_id in settings.admin_ids:
        try:
            await callback.bot.send_message(admin_id, text)
        except Exception:
            pass
