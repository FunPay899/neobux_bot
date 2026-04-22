from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder



def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Товары", callback_data="admin_products")
    builder.button(text="📬 Активные тикеты", callback_data="admin_tickets")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.adjust(1)
    return builder.as_markup()



def admin_products_kb(products: list[dict], page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить товар", callback_data="admin_product_add")
    for item in products:
        status = "🟢" if item["is_active"] else "🔴"
        builder.button(text=f"{status} {item['title']}", callback_data=f"admin_product:{item['id']}")
    if has_prev:
        builder.button(text="⬅️", callback_data=f"admin_products_page:{page - 1}")
    if has_next:
        builder.button(text="➡️", callback_data=f"admin_products_page:{page + 1}")
    builder.button(text="⬅️ В админку", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()



def admin_product_manage_kb(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Название", callback_data=f"edit_product_field:{product_id}:title")
    builder.button(text="📝 Описание", callback_data=f"edit_product_field:{product_id}:description")
    builder.button(text="⭐ Цена", callback_data=f"edit_product_field:{product_id}:price_stars")
    builder.button(text="🎮 Robux", callback_data=f"edit_product_field:{product_id}:robux_amount")
    builder.button(
        text="🙈 Скрыть" if is_active else "👁️ Показать",
        callback_data=f"toggle_product:{product_id}",
    )
    builder.button(text="🗑️ Удалить", callback_data=f"delete_product:{product_id}")
    builder.button(text="⬅️ К товарам", callback_data="admin_products")
    builder.adjust(2, 2, 1, 1, 1)
    return builder.as_markup()



def tickets_kb(tickets: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ticket in tickets:
        builder.button(
            text=f"👤 {ticket['full_name']} ({ticket['user_id']})",
            callback_data=f"ticket:{ticket['user_id']}",
        )
    builder.button(text="⬅️ В админку", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()



def ticket_reply_kb(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✉️ Ответить", callback_data=f"ticket_reply:{user_id}")
    builder.button(text="✅ Закрыть тикет", callback_data=f"ticket_close:{user_id}")
    builder.button(text="⬅️ К тикетам", callback_data="admin_tickets")
    builder.adjust(1)
    return builder.as_markup()
