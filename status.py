"""Bot holati: admin'larga bitta xabar ko'rinishida (tahrirlanib turadi), ishga tushish/to'xtash
va xatolik haqida xabarlar. Har 3 soniyada yangi xabar emas, bitta xabar yangilanadi."""
import asyncio
import logging
import time
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

from config import Settings
from database import Database
from utils import fmt_money, now_local, sub_status, today_local

logger = logging.getLogger(__name__)

_STARTED = time.monotonic()
_msg_ids: dict = {}          # admin_id -> holat xabari message_id
_bot: Optional[Bot] = None   # xatolik xabarlari uchun
_last_error_alert = 0.0
_settings_ref: Optional[Settings] = None
ERROR_ALERT_COOLDOWN = 300   # bir xil xatolik haqida 5 daqiqada bir marta


def set_bot(bot: Bot) -> None:
    global _bot
    _bot = bot


def _uptime() -> str:
    total = int(time.monotonic() - _STARTED)
    hours, rest = divmod(total, 3600)
    minutes = rest // 60
    return f"{hours} soat {minutes} daqiqa"


async def status_text(db: Database, settings: Settings) -> str:
    st = await db.stats()
    active = sum(1 for e in st["expires"] if sub_status(e)[0])
    today = await db.today_overview(today_local())
    size_kb = settings.db_path.stat().st_size / 1024 if settings.db_path.exists() else 0
    return "\n".join([
        "📡 <b>Bot holati</b>",
        f"🕒 Yangilandi: {now_local():%d.%m %H:%M:%S}",
        f"⏱ Ishlash vaqti: {_uptime()}",
        "",
        f"👥 Foydalanuvchilar: <b>{st['users']}</b>",
        f"🏠 Oilalar: <b>{len(st['expires'])}</b> (faol: {active})",
        f"🧾 Jami harajatlar: <b>{st['expenses']}</b>",
        f"📅 Bugun: {today['count']} ta yozuv, {fmt_money(today['sum'])}, {today['families']} oilada",
        f"💾 Baza hajmi: {size_kb:.0f} KB",
    ])


async def _send_or_edit(bot: Bot, admin_id: int, text: str) -> None:
    mid = _msg_ids.get(admin_id)
    if mid:
        try:
            await bot.edit_message_text(text, chat_id=admin_id, message_id=mid)
            return
        except TelegramRetryAfter:
            return  # Telegram cheklovi: keyingi tsiklda qayta urinamiz
        except TelegramBadRequest as exc:
            if "not modified" in str(exc):
                return
            # xabar o'chirilgan bo'lishi mumkin: yangisini yuboramiz
    sent = await bot.send_message(admin_id, text)
    _msg_ids[admin_id] = sent.message_id


async def push_status(bot: Bot, db: Database, settings: Settings) -> None:
    text = await status_text(db, settings)
    for admin_id in settings.admin_ids:
        try:
            await _send_or_edit(bot, admin_id, text)
        except Exception as exc:
            logger.warning("Holat xabari yuborilmadi (admin=%s): %s", admin_id, exc)


async def notify_admins(bot: Bot, settings: Settings, text: str) -> None:
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception as exc:
            logger.warning("Admin xabari yuborilmadi (admin=%s): %s", admin_id, exc)


async def status_loop(bot: Bot, db: Database, settings: Settings) -> None:
    while True:
        try:
            await push_status(bot, db, settings)
        except Exception:
            logger.exception("Holat tsiklida xato")
        await asyncio.sleep(settings.status_interval)


async def alert_error(text: str) -> None:
    """Xatolik haqida admin'ga xabar. Bir necha marta ketma-ket chiqsa, cheklangan."""
    global _last_error_alert
    if _bot is None or _settings_ref is None:
        return
    now = time.monotonic()
    if now - _last_error_alert < ERROR_ALERT_COOLDOWN:
        return
    _last_error_alert = now
    await notify_admins(_bot, _settings_ref, "⚠️ <b>Xatolik</b>\n" + text[:800])


def set_settings(settings: Settings) -> None:
    global _settings_ref
    _settings_ref = settings
