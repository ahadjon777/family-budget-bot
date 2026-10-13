"""Kunlik eslatma: har kuni belgilangan vaqtda (standart 21:00, Asia/Tashkent).
Har bir oila a'zosiga o'z oilasining jami summasi bilan eslatma boradi. Obunasi tugagan oilaga yubormaydi."""
import asyncio
import logging
from datetime import timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import Database
from services import reminder_text
from utils import now_local, sub_status

logger = logging.getLogger(__name__)


async def send_reminders(bot: Bot, db: Database) -> None:
    """Obunasi faol oilalar a'zolariga eslatma yuboradi."""
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
            texts[fid] = await reminder_text(db, fid)
        try:
            await bot.send_message(row["user_id"], texts[fid], reply_markup=kb)
        except Exception as exc:  # bitta foydalanuvchidagi xato boshqalarga to'sqinlik qilmasin
            logger.warning("Eslatma yuborilmadi (user_id=%s): %s", row["user_id"], exc)


async def reminder_loop(bot: Bot, db: Database, hour: int, minute: int) -> None:
    """Cheksiz tsikl: keyingi eslatma vaqtigacha kutadi, keyin yuboradi."""
    logger.info("Kunlik eslatma yoqildi: har kuni %02d:%02d (Asia/Tashkent)", hour, minute)
    while True:
        try:
            now = now_local()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            wait = (target - now).total_seconds()
            logger.info("Keyingi eslatma: %s (%d soniyadan keyin)", target.strftime("%Y-%m-%d %H:%M"), wait)
            await asyncio.sleep(wait)
            await send_reminders(bot, db)
            # Bir daqiqadan ko'proq kutamiz: bir xil eslatma ikki marta ketmasligi uchun
            await asyncio.sleep(61)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Eslatma tsiklida xato; 60 soniyadan keyin qayta uriniladi")
            await asyncio.sleep(60)
