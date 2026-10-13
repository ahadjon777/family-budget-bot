"""Bot sozlamalari: .env fayldan o'qiladi."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Loyiha papkasi (config.py joylashgan joy)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    allowed_users: frozenset      # doimiy bepul "asosiy oila" (bot egasining oilasi)
    admin_ids: frozenset          # admin buyruqlaridan foydalana oladiganlar
    db_path: Path
    reminder_hour: int
    reminder_minute: int
    trial_days: int = 7           # yangi oila uchun bepul sinov muddati
    max_members: int = 6          # bitta oiladagi a'zolar soni chegarasi
    contact_text: str = "Bot egasi bilan bog'laning."
    price_text: str = ""
    status_interval: int = 60     # holat xabari yangilanish oralig'i (soniya); 0 = o'chirilgan


def _parse_ids(raw: str, var: str) -> frozenset:
    """'123, 456;789' ko'rinishidagi qatordan ID lar to'plamini oladi."""
    ids = set()
    for part in raw.replace(";", ",").replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if not part.lstrip("-").isdigit():
            raise SystemExit(
                f"XATO: {var} ichida noto'g'ri qiymat: '{part}'. "
                "Faqat raqamli Telegram ID kiriting (masalan: 123456789,987654321)."
            )
        ids.add(int(part))
    return frozenset(ids)


def _parse_time(raw: str):
    """'21:00' ko'rinishidagi vaqtni (soat, daqiqa) ga aylantiradi."""
    try:
        hour_s, minute_s = raw.strip().split(":")
        hour, minute = int(hour_s), int(minute_s)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return hour, minute
    except ValueError:
        raise SystemExit(
            f"XATO: REMINDER_TIME noto'g'ri: '{raw}'. Format: SS:DD (masalan 21:00)."
        )


def _parse_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise SystemExit(f"XATO: {name} butun son bo'lishi kerak, hozir: '{raw}'.")
    if not (minimum <= value <= maximum):
        raise SystemExit(f"XATO: {name} {minimum} dan {maximum} gacha bo'lishi kerak.")
    return value


def _status_interval() -> int:
    value = _parse_int("STATUS_INTERVAL", 60, 0, 3600)
    if 0 < value < 10:
        raise SystemExit("XATO: STATUS_INTERVAL kamida 10 soniya bo'lishi kerak (yoki 0 - o'chirish).")
    return value


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "XATO: BOT_TOKEN topilmadi. .env faylini yarating "
            "(.env.example dan nusxa oling) va BOT_TOKEN ni kiriting."
        )

    allowed = _parse_ids(os.getenv("ALLOWED_USERS", ""), "ALLOWED_USERS")
    # ADMIN_IDS ko'rsatilmasa, ALLOWED_USERS dagilar admin hisoblanadi
    admins = _parse_ids(os.getenv("ADMIN_IDS", ""), "ADMIN_IDS") or allowed
    hour, minute = _parse_time(os.getenv("REMINDER_TIME", "21:00"))

    db_raw = os.getenv("DB_PATH", "data/budget.db")
    db_path = Path(db_raw)
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    return Settings(
        bot_token=token,
        allowed_users=allowed,
        admin_ids=admins,
        db_path=db_path,
        reminder_hour=hour,
        reminder_minute=minute,
        trial_days=_parse_int("TRIAL_DAYS", 7, 0, 365),
        max_members=_parse_int("MAX_MEMBERS", 6, 1, 20),
        contact_text=os.getenv("CONTACT_TEXT", "").strip() or "Bot egasi bilan bog'laning.",
        price_text=os.getenv("PRICE_TEXT", "").strip(),
        status_interval=_status_interval(),
    )
