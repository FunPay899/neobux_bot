from aiogram import Router, F
from aiogram.types import Message, PreCheckoutQuery

from app.config import settings
from app.db.database import Database

router = Router()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, db: Database):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("buy_product_"):
        return

    product_id = int(payload.replace("buy_product_", ""))
    product = await db.get_product(product_id)
    user = await db.get_user(message.from_user.id)
    roblox_username = user.get("roblox_username") if user else "не указан"

    # TODO: Логика выдачи Robux через Roblox API или ручное зачисление
    order_id = await db.add_order(
        user_id=message.from_user.id,
        product_id=product_id,
        product_title=product["title"],
        robux_amount=product["robux_amount"],
        price_stars=product["price_stars"],
        roblox_username=roblox_username,
        telegram_payment_charge_id=message.successful_payment.telegram_payment_charge_id,
        provider_payment_charge_id=message.successful_payment.provider_payment_charge_id,
        status="Выдан",
    )

    await message.answer(
        "✅ Оплата прошла успешно!\n"
        f"Robux зачислены на ваш аккаунт Roblox: <b>{roblox_username}</b>\n"
        f"🧾 Номер заказа: <b>#{order_id}</b>"
    )

    if settings.admin_ids:
        admin_text = (
            "💸 <b>Новая покупка!</b>\n"
            f"Пользователь: @{message.from_user.username or 'без username'} (ID: {message.from_user.id})\n"
            f"Товар: {product['title']}\n"
            f"Сумма: {product['price_stars']} ⭐️"
        )
        for admin_id in settings.admin_ids:
            try:
                await message.bot.send_message(admin_id, admin_text)
            except Exception:
                pass
