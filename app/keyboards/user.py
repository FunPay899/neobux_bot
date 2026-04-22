from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍️ Каталог", callback_data="catalog")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.button(text="📞 Поддержка", callback_data="support")
    builder.adjust(1)
    return builder.as_markup()


def catalog_kb(products: list[dict], page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in products:
        builder.button(
            text=f"🛒 {item['title']} — {item['price_stars']}⭐",
            callback_data=f"product:{item['id']}",
        )
    if has_prev:
        builder.button(text="⬅️", callback_data=f"catalog_page:{page - 1}")
    if has_next:
        builder.button(text="➡️", callback_data=f"catalog_page:{page + 1}")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def product_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Купить", callback_data=f"buy:{product_id}")
    builder.button(text="⬅️ Назад в каталог", callback_data="catalog")
    builder.adjust(1)
    return builder.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎟️ Промокод", callback_data="promo_enter")
    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def cancel_to_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_state")
    return builder.as_markup()
