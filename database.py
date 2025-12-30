"""
База данных для хранения заказов (SQLite)
"""
import aiosqlite
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "orders.db"


@dataclass
class Order:
    """Модель заказа"""
    id: int
    order_id: int
    user_id: int
    username: Optional[str]
    tariff_id: int
    tariff_name: str
    operator_id: int
    operator_name: str
    monthly_fee: Optional[int]
    connection_price: int
    mode: str  # 'transfer' or 'new'
    transfer_phone: Optional[str]
    full_name: str
    region_city: str
    passport_photo_1: str
    passport_photo_2: str
    status: str  # 'pending', 'paid', 'cancelled'
    created_at: str


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                tariff_id INTEGER NOT NULL,
                tariff_name TEXT NOT NULL,
                operator_id INTEGER NOT NULL,
                operator_name TEXT NOT NULL,
                monthly_fee INTEGER,
                connection_price INTEGER NOT NULL,
                mode TEXT NOT NULL,
                transfer_phone TEXT,
                full_name TEXT NOT NULL,
                region_city TEXT NOT NULL,
                passport_photo_1 TEXT NOT NULL,
                passport_photo_2 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                payment_receipt TEXT,
                payment_method_name TEXT,
                payment_confirmed_at TEXT
            )
        """)
        
        # Миграция: добавляем новые колонки если их нет
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN payment_receipt TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN payment_method_name TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN payment_confirmed_at TEXT")
        except Exception:
            pass
        
        await db.commit()


async def create_order(
    order_id: int,
    user_id: int,
    username: Optional[str],
    tariff_id: int,
    tariff_name: str,
    operator_id: int,
    operator_name: str,
    monthly_fee: Optional[int],
    connection_price: int,
    mode: str,
    transfer_phone: Optional[str],
    full_name: str,
    region_city: str,
    passport_photo_1: str,
    passport_photo_2: str,
) -> int:
    """Создать новый заказ"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders (
                order_id, user_id, username, tariff_id, tariff_name,
                operator_id, operator_name, monthly_fee, connection_price,
                mode, transfer_phone, full_name, region_city,
                passport_photo_1, passport_photo_2, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', datetime('now'))
            """,
            (
                order_id, user_id, username, tariff_id, tariff_name,
                operator_id, operator_name, monthly_fee, connection_price,
                mode, transfer_phone, full_name, region_city,
                passport_photo_1, passport_photo_2
            )
        )
        await db.commit()
        return cursor.lastrowid


async def get_order_by_id(order_id: int) -> Optional[dict]:
    """Получить заказ по ID"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE order_id = ?",
            (order_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None


async def update_order_status(order_id: int, status: str) -> bool:
    """Обновить статус заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE orders SET status = ? WHERE order_id = ?",
            (status, order_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_orders_by_user(user_id: int) -> List[dict]:
    """Получить заказы пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_orders(limit: int = 100) -> List[dict]:
    """Получить все заказы (для админа)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_order_receipt(
    order_id: int,
    receipt_file_id: str,
    payment_method_name: str,
) -> bool:
    """Сохранить чек оплаты"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """UPDATE orders 
               SET payment_receipt = ?, payment_method_name = ?, status = 'awaiting_confirmation'
               WHERE order_id = ?""",
            (receipt_file_id, payment_method_name, order_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def confirm_order_payment(order_id: int) -> bool:
    """Подтвердить оплату заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """UPDATE orders 
               SET status = 'paid', payment_confirmed_at = datetime('now')
               WHERE order_id = ?""",
            (order_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def reject_order_payment(order_id: int) -> bool:
    """Отклонить оплату заказа"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """UPDATE orders 
               SET status = 'payment_rejected', payment_receipt = NULL
               WHERE order_id = ?""",
            (order_id,)
        )
        await db.commit()
        return cursor.rowcount > 0

