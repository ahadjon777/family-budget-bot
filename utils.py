"""Yordamchi funksiyalar: pul formati, sana/vaqt, matn bezaklari."""
import html
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _get_tz():
    """Asia/Tashkent vaqt zonasi. Windows'da tzdata yo'q bo'lsa UTC+5 ishlatiladi
    (Toshkentda yozgi vaqtga o'tish yo'q, shuning uchun natija bir xil)."""
    try:
        return ZoneInfo("Asia/Tashkent")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=5), "Asia/Tashkent")


TZ = _get_tz()

MONTHS = [
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
]
WEEKDAYS = [
    "Dushanba", "Seshanba", "Chorshanba", "Payshanba",
    "Juma", "Shanba", "Yakshanba",
]
WEEKDAYS_SHORT = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]


def now_local() -> datetime:
    return datetime.now(TZ)


def today_local() -> date:
    return now_local().date()


def fmt_num(amount) -> str:
    """45000 -> '45 000'"""
    return f"{int(amount):,}".replace(",", " ")


def fmt_money(amount) -> str:
    """45000 -> '45 000 so'm'"""
    return f"{fmt_num(amount)} so'm"


def fmt_date(d: date) -> str:
    """date(2026,10,11) -> '11 oktabr 2026'"""
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def fmt_short(d: date) -> str:
    """date -> '11.10'"""
    return f"{d.day:02d}.{d.month:02d}"


def month_title(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.year}"


def fmt_duration(seconds) -> str:
    """4380 -> '1 soat 13 daqiqa'; 45 -> '45 soniya'"""
    seconds = max(int(seconds), 0)
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    parts = []
    if days:
        parts.append(f"{days} kun")
    if hours:
        parts.append(f"{hours} soat")
    if minutes:
        parts.append(f"{minutes} daqiqa")
    return " ".join(parts) if parts else f"{secs} soniya"


def user_label(user) -> str:
    """Admin xabarlari uchun: 'Ali (@ali) · ID 123' (HTML uchun xavfsiz)."""
    name = esc(user.full_name or "Noma'lum")
    uname = f" (@{esc(user.username)})" if getattr(user, "username", None) else ""
    return f"{name}{uname} · ID <code>{user.id}</code>"


def sub_status(expires_at):
    """Obuna holati: (faolmi, qolgan kunlar). expires_at None bo'lsa cheksiz: (True, None).
    Tugash kuni ham faol hisoblanadi (qolgan kun = 0)."""
    if not expires_at:
        return True, None
    days = (date.fromisoformat(expires_at) - today_local()).days
    return days >= 0, days


def week_range(d: date):
    """Haftaning dushanbadan yakshanbagacha oralig'i."""
    start = d - timedelta(days=d.weekday())
    return start, start + timedelta(days=6)


def month_range(d: date):
    """Oyning birinchi va oxirgi kuni."""
    start = d.replace(day=1)
    next_month = (start + timedelta(days=32)).replace(day=1)
    return start, next_month - timedelta(days=1)


def prev_month_range(d: date):
    first = d.replace(day=1)
    return month_range(first - timedelta(days=1))


def bar(part, total, width: int = 10) -> str:
    """Matnli progress chizig'i: ▓▓▓░░░░░░░"""
    if not total or total <= 0:
        filled = 0
    else:
        filled = round(width * min(max(part / total, 0), 1))
    return "▓" * filled + "░" * (width - filled)


def esc(text) -> str:
    """Foydalanuvchi matnini HTML uchun xavfsiz qiladi."""
    return html.escape(str(text), quote=False)
