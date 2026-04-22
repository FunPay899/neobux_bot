from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_ids: list[int]
    provider_token: str
    support_chat_id: int | None
    db_path: str


def _parse_admin_ids(raw: str) -> list[int]:
    if not raw.strip():
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


settings = Settings(
    bot_token=os.getenv("BOT_TOKEN", ""),
    admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
    provider_token=os.getenv("PROVIDER_TOKEN", ""),
    support_chat_id=int(os.getenv("SUPPORT_CHAT_ID")) if os.getenv("SUPPORT_CHAT_ID") else None,
    db_path=os.getenv("DB_PATH", str(BASE_DIR / "data" / "bot.db")),
)
