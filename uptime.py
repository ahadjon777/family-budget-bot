"""Server holati: bot qachon o'chib qolgani va qachon qayta yoqilgani haqida ma'lumot.

Ishlash tartibi:
* bot ishlab turganda har 30 soniyada bazaga "men tirikman" vaqtini yozadi (heartbeat);
* tartibli to'xtatilganda (Ctrl+C, systemctl stop) buni alohida belgilaydi;
* qayta ishga tushganda oxirgi yozuvga qarab admin'ga "o'chiq turgan vaqt" haqida xabar yuboradi.

Muhim: o'chib qolgan dastur o'zi haqida xabar bera olmaydi. O'chgan paytning o'zida ogohlantirish
olish uchun ixtiyoriy HEARTBEAT_URL (healthchecks.io, UptimeRobot) ishlatiladi: bot har daqiqa
shu manzilga "ping" yuboradi, ping to'xtasa, xizmat sizga Telegram orqali xabar beradi.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

import aiohttp

from database import Database
from utils import TZ, fmt_duration, now_local

logger = logging.getLogger(__name__)

KEY_LAST = "hb_last"      # oxirgi "tirikman" vaqti
KEY_CLEAN = "hb_clean"    # "1" - oxirgi to'xtash tartibli bo'lgan, "0" - ishlab turgan yoki kutilmaganda to'xtagan
HEARTBEAT_INTERVAL = 30
PING_INTERVAL = 60
FMT = "%Y-%m-%d %H:%M:%S"


def _stamp() -> str:
    return now_local().strftime(FMT)


def _parse(ts: str) -> Optional[datetime]:
    try:
        return datetime.strptime(ts, FMT).replace(tzinfo=TZ)
    except (TypeError, ValueError):
        return None


async def begin_run(db: Database) -> dict:
    """Bot ishga tushganda chaqiriladi: oldingi ish haqida ma'lumot qaytaradi va yangi ishni boshlaydi.

    Qaytadi: {"first": bool, "clean": bool, "last": datetime | None, "down_seconds": float | None}
    """
    last = _parse(await db.global_get(KEY_LAST) or "")
    clean = (await db.global_get(KEY_CLEAN)) == "1"
    now = now_local()
    info = {
        "first": last is None,
        "clean": clean,
        "last": last,
        "down_seconds": max((now - last).total_seconds(), 0) if last else None,
    }
    await db.global_set(KEY_CLEAN, "0")
    await db.global_set(KEY_LAST, _stamp())
    return info


async def end_run(db: Database) -> None:
    """Bot tartibli to'xtatilganda chaqiriladi."""
    await db.global_set(KEY_LAST, _stamp())
    await db.global_set(KEY_CLEAN, "1")


def startup_text(info: dict, username: str = "") -> str:
    """Ishga tushganda admin'ga yuboriladigan xabar."""
    who = f" (@{username})" if username else ""
    if info["first"]:
        return f"🟢 <b>Bot birinchi marta ishga tushdi</b>{who}"

    last = info["last"]
    down = fmt_duration(info["down_seconds"])
    when = last.strftime("%d.%m %H:%M:%S")
    if info["clean"]:
        return (
            f"🟢 <b>Bot ishga tushdi</b>{who}\n"
            f"⏸ Oxirgi to'xtash: {when} (tartibli to'xtatilgan)\n"
            f"⏱ O'chiq turdi: {down}"
        )
    return (
        f"🟢 <b>Server qayta ishga tushdi</b>{who}\n"
        f"⚠️ Bot kutilmaganda to'xtagan edi. Oxirgi faollik: {when}\n"
        f"⏱ Taxminan {down} ishlamadi.\n"
        "Sabab: server yoki kompyuter o'chgan, internet uzilgan yoki dastur xatolik bilan to'xtagan bo'lishi mumkin."
    )


async def heartbeat_loop(db: Database, interval: int = HEARTBEAT_INTERVAL) -> None:
    """Har `interval` soniyada bazaga oxirgi faollik vaqtini yozadi."""
    while True:
        try:
            await db.global_set(KEY_LAST, _stamp())
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Heartbeat yozilmadi")
        await asyncio.sleep(interval)


async def ping_loop(url: str, interval: int = PING_INTERVAL) -> None:
    """Tashqi kuzatuv xizmatiga har daqiqa ping yuboradi (HEARTBEAT_URL). Ping to'xtasa, xizmat ogohlantiradi."""
    timeout = aiohttp.ClientTimeout(total=10)
    ok = True
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                async with session.get(url) as resp:
                    good = resp.status < 400
                    if not good and ok:
                        logger.warning("HEARTBEAT_URL javobi: HTTP %s", resp.status)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                good = False
                if ok:
                    logger.warning("HEARTBEAT_URL ga ping yuborilmadi: %s", exc)
            if good and not ok:
                logger.info("HEARTBEAT_URL ga ping qayta ishlayapti")
            ok = good
            await asyncio.sleep(interval)
