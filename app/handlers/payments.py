from aiogram import F, Router
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
    if not payload.startswith("buy_product:"):
        return

    _, product_id, final_price = payload.split(":")
    product = await db.get_product(int(product_id))
    user = await db.get_user(message.from_user.id)
    discount = user.get("discount_percent", 0) if user else 0
    promo_code = None if discount == 0 else f"discount_{discount}"

    order_id = await db.add_order(
        user_id=message.from_user.id,
        product_id=int(product_id),
        product_title=product["title"],
        robux_amount=product["robux_amount"],
        price_stars=product["price_stars"],
        final_price_stars=int(final_price),
        paid_via_balance=0,
        paid_via_stars=int(final_price),
        promo_code=promo_code,
        telegram_payment_charge_id=message.successful_payment.telegram_payment_charge_id,
        provider_payment_charge_id=message.successful_payment.provider_payment_charge_id,
        status="Выдан",
    )
    if discount:
        await db.clear_discount(message.from_user.id)

    await message.answer(
        "✅ Оплата прошла успешно!\n"
        f"Заказ <b>#{order_id}</b> оформлен.\n"
        f"🎮 Товар: <b>{product['title']}</b>\n"
        "📦 Выдача будет произведена вручную."
    )

    await message.bot.send_message(
        message.from_user.id,
        f"🔔 Уведомление\nВаш платёж по заказу <b>#{order_id}</b> подтверждён. Ожидайте ручную выдачу.",
    )

    admin_text = (
        "💸 <b>Новая покупка!</b>\n"
        f"Пользователь: @{message.from_user.username or 'без username'} (ID: {message.from_user.id})\n"
        f"Товар: {product['title']}\n"
        f"Сумма: {final_price} ⭐️\n"
        f"Заказ: #{order_id}"
    )
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception:
            pass
