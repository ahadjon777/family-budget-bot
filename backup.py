"""Bazaning kunlik zaxira nusxasi: data/backups/budget_YYYY-MM-DD.db (oxirgi N ta saqlanadi).

SQLite'ning o'zining backup mexanizmi ishlatiladi: bot ishlab turganda ham nusxa butun va buzilmagan chiqadi."""
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from utils import now_local

logger = logging.getLogger(__name__)

BACKUP_HOUR, BACKUP_MINUTE = 3, 30


def backup_dir(db_path: Path) -> Path:
    return Path(db_path).parent / "backups"


def _backup_sync(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    source = sqlite3.connect(src)
    target = sqlite3.connect(tmp)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    tmp.replace(dest)  # tayyor bo'lgandan keyingina asl nomga o'tkazamiz


def rotate(directory: Path, keep: int) -> None:
    """Eng yangi `keep` ta nusxani qoldirib, qolganini o'chiradi."""
    files = sorted(directory.glob("budget_*.db"))
    for old in files[:-keep] if keep > 0 else []:
        try:
            old.unlink()
        except OSError:
            logger.warning("Eski zaxirani o'chirib bo'lmadi: %s", old)


async def backup_once(db_path: Path, keep: int = 14, day=None) -> Optional[Path]:
    """Bitta zaxira nusxa oladi. Muvaffaqiyatli bo'lsa fayl yo'lini qaytaradi."""
    db_path = Path(db_path)
    if keep <= 0 or not db_path.exists():
        return None
    day = day or now_local().date()
    dest = backup_dir(db_path) / f"budget_{day:%Y-%m-%d}.db"
    await asyncio.to_thread(_backup_sync, db_path, dest)
    await asyncio.to_thread(rotate, dest.parent, keep)
    logger.info("Zaxira nusxa olindi: %s", dest)
    return dest


def _next_backup(now: datetime) -> datetime:
    target = now.replace(hour=BACKUP_HOUR, minute=BACKUP_MINUTE, second=0, microsecond=0)
    return target + timedelta(days=1) if target <= now else target


async def backup_loop(db_path: Path, keep: int) -> None:
    """Ishga tushganda (bugungi nusxa hali yo'q bo'lsa) va keyin har kuni 03:30 da zaxira oladi."""
    if keep <= 0:
        return
    while True:
        try:
            today_file = backup_dir(db_path) / f"budget_{now_local().date():%Y-%m-%d}.db"
            if not today_file.exists():
                await backup_once(db_path, keep)
            target = _next_backup(now_local())
            while (remaining := (target - now_local()).total_seconds()) > 0:
                await asyncio.sleep(min(remaining, 60))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Zaxira nusxa olishda xato; 10 daqiqadan keyin qayta uriniladi")
            await asyncio.sleep(600)
