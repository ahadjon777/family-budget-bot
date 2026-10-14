"""Kunlik eslatmalar: har kuni belgilangan vaqtlarda (standart 09:00, 15:00, 21:00, Asia/Tashkent).
Har bir oila a'zosiga o'z oilasining jami summasi bilan eslatma boradi. Obunasi tugagan oilaga yubormaydi."""
import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import Database
from services import reminder_text
from utils import now_local, sub_status

logger = logging.getLogger(__name__)


def next_reminder(now: datetime, times) -> datetime:
    """`now` dan keyingi eng yaqin eslatma vaqti. times: ((soat, daqiqa), ...)"""
    candidates = []
    for hour, minute in times:
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        candidates.append(target)
    return min(candidates)


async def send_reminders(bot: Bot, db: Database, hour: int = 21) -> None:
    """Obunasi faol oilalar a'zolariga eslatma yuboradi. `hour` eslatma matnini (ertalab/kunduz/kechki) belgilaydi."""
    rows = await db.users_for_reminders()
    texts: dict = {}
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Harajat qo'shish", callback_data="add")]
    ])
    for row in rows:
        active, _ = sub_status(row["expires_at"])
        if not active:
            continue
        fid = row["family_id"]
        if fid not in texts:
            texts[fid] = await reminder_text(db, fid, hour)
        try:
            await bot.send_message(row["user_id"], texts[fid], reply_markup=kb)
        except Exception as exc:  # bitta foydalanuvchidagi xato boshqalarga to'sqinlik qilmasin
            logger.warning("Eslatma yuborilmadi (user_id=%s): %s", row["user_id"], exc)


async def _sleep_until(target: datetime) -> None:
    """Soat vaqti bo'yicha kutadi. Kompyuter uyqu rejimiga o'tib qaytsa ham kechikmaslik uchun
    uzoq kutish o'rniga qisqa bo'laklarda real vaqtni tekshirib boradi."""
    while True:
        remaining = (target - now_local()).total_seconds()
        if remaining <= 0:
            return
        await asyncio.sleep(min(remaining, 30))


async def reminder_loop(bot: Bot, db: Database, times) -> None:
    """Cheksiz tsikl: keyingi eslatma vaqtigacha kutadi, keyin yuboradi."""
    shown = ", ".join(f"{h:02d}:{m:02d}" for h, m in times)
    logger.info("Kunlik eslatmalar yoqildi: har kuni %s (Asia/Tashkent)", shown)
    while True:
        try:
            target = next_reminder(now_local(), times)
            logger.info("Keyingi eslatma: %s", target.strftime("%Y-%m-%d %H:%M"))
            await _sleep_until(target)
            await send_reminders(bot, db, target.hour)
            # Bir daqiqadan ko'proq kutamiz: bir xil eslatma ikki marta ketmasligi uchun
            await asyncio.sleep(61)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Eslatma tsiklida xato; 60 soniyadan keyin qayta uriniladi")
            await asyncio.sleep(60)
