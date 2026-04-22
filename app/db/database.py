import aiosqlite
from datetime import datetime, timedelta
from typing import Any


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def init(self) -> None:
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                roblox_username TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price_stars INTEGER NOT NULL,
                robux_amount INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_title TEXT NOT NULL,
                robux_amount INTEGER NOT NULL,
                price_stars INTEGER NOT NULL,
                roblox_username TEXT NOT NULL,
                telegram_payment_charge_id TEXT,
                provider_payment_charge_id TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                username TEXT,
                question TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )
        await self.conn.commit()

    async def add_or_update_user(self, user_id: int, username: str | None, full_name: str) -> None:
        now = datetime.utcnow().isoformat()
        await self.conn.execute(
            """
            INSERT INTO users (user_id, username, full_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                updated_at=excluded.updated_at
            """,
            (user_id, username, full_name, now, now),
        )
        await self.conn.commit()

    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def update_user_roblox(self, user_id: int, roblox_username: str) -> None:
        await self.conn.execute(
            "UPDATE users SET roblox_username = ?, updated_at = ? WHERE user_id = ?",
            (roblox_username, datetime.utcnow().isoformat(), user_id),
        )
        await self.conn.commit()

    async def get_active_products(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM products WHERE is_active = 1 ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def count_active_products(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) AS cnt FROM products WHERE is_active = 1")
        row = await cur.fetchone()
        return row["cnt"]

    async def get_all_products(self, limit: int = 10, offset: int = 0) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM products ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def count_all_products(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) AS cnt FROM products")
        row = await cur.fetchone()
        return row["cnt"]

    async def add_product(self, title: str, description: str, price_stars: int, robux_amount: int) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO products (title, description, price_stars, robux_amount, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (title, description, price_stars, robux_amount, datetime.utcnow().isoformat()),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_product(self, product_id: int) -> dict[str, Any] | None:
        cur = await self.conn.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

    async def update_product_field(self, product_id: int, field: str, value: Any) -> None:
        await self.conn.execute(f"UPDATE products SET {field} = ? WHERE id = ?", (value, product_id))
        await self.conn.commit()

    async def toggle_product(self, product_id: int) -> None:
        await self.conn.execute(
            "UPDATE products SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (product_id,),
        )
        await self.conn.commit()

    async def delete_product(self, product_id: int) -> None:
        await self.conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        await self.conn.commit()

    async def add_order(
        self,
        user_id: int,
        product_id: int,
        product_title: str,
        robux_amount: int,
        price_stars: int,
        roblox_username: str,
        telegram_payment_charge_id: str | None,
        provider_payment_charge_id: str | None,
        status: str = "Выдан",
    ) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO orders (
                user_id, product_id, product_title, robux_amount, price_stars,
                roblox_username, telegram_payment_charge_id, provider_payment_charge_id,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                product_id,
                product_title,
                robux_amount,
                price_stars,
                roblox_username,
                telegram_payment_charge_id,
                provider_payment_charge_id,
                status,
                datetime.utcnow().isoformat(),
            ),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_user_last_orders(self, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def get_all_user_ids(self) -> list[int]:
        cur = await self.conn.execute("SELECT user_id FROM users")
        rows = await cur.fetchall()
        return [r["user_id"] for r in rows]

    async def create_ticket(self, user_id: int, full_name: str, username: str | None, question: str) -> None:
        now = datetime.utcnow().isoformat()
        await self.conn.execute(
            """
            INSERT INTO support_tickets (user_id, full_name, username, question, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'open', ?, ?)
            """,
            (user_id, full_name, username, question, now, now),
        )
        await self.conn.commit()

    async def get_open_tickets(self) -> list[dict[str, Any]]:
        cur = await self.conn.execute(
            "SELECT * FROM support_tickets WHERE status = 'open' GROUP BY user_id ORDER BY updated_at DESC"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def close_ticket(self, user_id: int) -> None:
        await self.conn.execute(
            "UPDATE support_tickets SET status = 'closed', updated_at = ? WHERE user_id = ? AND status = 'open'",
            (datetime.utcnow().isoformat(), user_id),
        )
        await self.conn.commit()

    async def bot_stats(self) -> dict[str, int]:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        week_start = (now - timedelta(days=7)).isoformat()

        cur = await self.conn.execute("SELECT COUNT(*) AS cnt FROM users")
        total_users = (await cur.fetchone())["cnt"]

        cur = await self.conn.execute("SELECT COUNT(*) AS cnt FROM users WHERE created_at >= ?", (today_start,))
        today_users = (await cur.fetchone())["cnt"]

        cur = await self.conn.execute("SELECT COUNT(*) AS cnt FROM users WHERE created_at >= ?", (week_start,))
        week_users = (await cur.fetchone())["cnt"]

        cur = await self.conn.execute(
            "SELECT COALESCE(SUM(price_stars), 0) AS sum_stars FROM orders WHERE created_at >= ?", (today_start,)
        )
        sales_today = (await cur.fetchone())["sum_stars"]

        cur = await self.conn.execute("SELECT COALESCE(SUM(price_stars), 0) AS sum_stars FROM orders")
        sales_total = (await cur.fetchone())["sum_stars"]

        cur = await self.conn.execute("SELECT COUNT(*) AS cnt FROM orders WHERE status = 'Выдан'")
        success_orders = (await cur.fetchone())["cnt"]

        return {
            "total_users": total_users,
            "today_users": today_users,
            "week_users": week_users,
            "sales_today": sales_today,
            "sales_total": sales_total,
            "success_orders": success_orders,
        }
