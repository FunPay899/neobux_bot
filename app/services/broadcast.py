import asyncio
from aiogram import Bot
from aiogram.types import Message


async def _copy_message(bot: Bot, user_id: int, source_message: Message) -> bool:
    try:
        await source_message.send_copy(chat_id=user_id)
        return True
    except Exception:
        return False


async def run_broadcast(bot: Bot, user_ids: list[int], source_message: Message) -> tuple[int, int]:
    success = 0
    failed = 0
    sem = asyncio.Semaphore(25)

    async def worker(uid: int):
        nonlocal success, failed
        async with sem:
            ok = await _copy_message(bot, uid, source_message)
            if ok:
                success += 1
            else:
                failed += 1

    await asyncio.gather(*(worker(uid) for uid in user_ids))
    return success, failed
