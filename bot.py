import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db.database import Database
from app.handlers import common, user, admin, payments, support
from app.middlewares.admin import AdminMiddleware


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    db = Database(settings.db_path)
    await db.connect()
    await db.init()

    dp["db"] = db
    dp["bot_instance"] = bot

    admin_middleware = AdminMiddleware(settings.admin_ids)
    admin.router.message.middleware(admin_middleware)
    admin.router.callback_query.middleware(admin_middleware)

    dp.include_router(common.router)
    dp.include_router(user.router)
    dp.include_router(payments.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)

    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
