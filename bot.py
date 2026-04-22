import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.db.database import Database
from app.handlers import common, user, admin, payments, support
from app.middlewares.admin import AdminMiddleware


async def healthcheck(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def start_http_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", healthcheck)
    app.router.add_get("/healthz", healthcheck)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logging.info("HTTP health server started on port %s", port)
    return runner


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    http_runner = await start_http_server()

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
        await http_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())