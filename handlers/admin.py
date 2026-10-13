"""Bot egasi (admin) buyruqlari: oilalar ro'yxati, obunani uzaytirish, yopish."""
import logging
from datetime import date, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import Settings
from database import Database
from status import status_text
from utils import esc, fmt_date, now_local, sub_status

logger = logging.getLogger(__name__)
router = Router()

USAGE = (
    "📋 <b>Admin buyruqlari</b>\n\n"
    "/oilalar — oilalar ro'yxati\n"
    "/uzaytir <code>oila_id kun</code> — obunani uzaytirish (masalan <code>/uzaytir 2 30</code>)\n"
    "/fikrlar — yangi fikr-mulohazalar; /fikrok ID — ko'rib chiqildi deb belgilash\n"
    "/holat — bot holati (foydalanuvchilar, oilalar, bugungi harajatlar)\n"
    "/cheksiz <code>oila_id</code> — cheksiz obuna\n"
    "/yopish <code>oila_id</code> — obunani darhol tugatish"
)


def _is_admin(message: Message, settings: Settings) -> bool:
    return message.from_user is not None and message.from_user.id in settings.admin_ids


async def _notify_owner(message: Message, db: Database, fid: int, text: str) -> None:
    members = await db.family_members(fid)
    owner = next((m for m in members if m["is_owner"]), None)
    if not owner:
        return
    try:
        await message.bot.send_message(owner["user_id"], text)
    except Exception as exc:
        logger.warning("Oila egasiga xabar yuborilmadi (family=%s): %s", fid, exc)


def _parse_fid(parts: list):
    if len(parts) < 2 or not parts[1].isdigit():
        return None
    return int(parts[1])


@router.message(Command("holat"))
async def admin_status(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    await message.answer(await status_text(db, settings))


@router.message(Command("fikrlar"))
async def admin_feedback(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    parts = (message.text or "").split()
    only_new = not (len(parts) > 1 and parts[1].lower() == "hammasi")
    rows = await db.list_feedback(status="new" if only_new else None, limit=20)
    if not rows:
        await message.answer("📭 Yangi fikrlar yo'q." if only_new else "📭 Fikrlar yo'q.")
        return
    title = "Yangi fikrlar" if only_new else "Barcha fikrlar"
    lines = [f"💡 <b>{title}</b> (so'nggi {len(rows)} ta):", ""]
    for r in rows:
        mark = "🆕" if r["status"] == "new" else "✔️"
        lines.append(f"{mark} <b>#{r['id']}</b> {esc(r['user_name'])} (oila #{r['family_id']}) · {r['created_at'][:16]}\n{esc(r['text'])}")
    lines.append("\nBelgilash: <code>/fikrok ID</code>")
    await message.answer("\n\n".join(lines))


@router.message(Command("fikrok"))
async def admin_feedback_done(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("❗ Format: <code>/fikrok ID</code>")
        return
    ok = await db.set_feedback_status(int(parts[1]), "done")
    await message.answer(f"✔️ #{parts[1]} fikr ko'rib chiqildi." if ok else f"❗ #{parts[1]} fikr topilmadi.")


@router.message(Command("admin"))
async def admin_home(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    st = await db.stats()
    active = sum(1 for e in st["expires"] if sub_status(e)[0])
    await message.answer(
        "📊 <b>Umumiy holat</b>\n"
        f"Oilalar: {len(st['expires'])} (faol: {active})\n"
        f"A'zolar: {st['users']}\n"
        f"Harajatlar: {st['expenses']}\n\n" + USAGE
    )


@router.message(Command("oilalar"))
async def admin_families(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    rows = await db.list_families(limit=15)
    if not rows:
        await message.answer("Hali birorta oila yo'q.")
        return
    lines = ["📋 <b>Oilalar</b> (so'nggilari):", ""]
    for r in rows:
        active, days = sub_status(r["expires_at"])
        if r["expires_at"] is None:
            status = "♾ cheksiz"
        elif active:
            status = f"✅ {fmt_date(date.fromisoformat(r['expires_at']))} gacha"
        else:
            status = "⛔ tugagan"
        owner = f"@{r['owner_username']}" if r["owner_username"] else str(r["owner_id"] or "-")
        lines.append(
            f"<b>#{r['id']}</b> {esc(r['name'])}\n"
            f"   a'zo: {r['members']} · harajat: {r['expense_count']} · {status}\n"
            f"   egasi: {esc(owner)}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("uzaytir"))
async def admin_extend(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    parts = (message.text or "").split()
    fid = _parse_fid(parts)
    if fid is None or len(parts) < 3 or not parts[2].isdigit() or not (1 <= int(parts[2]) <= 3650):
        await message.answer("❗ Format: <code>/uzaytir oila_id kun</code>, masalan <code>/uzaytir 2 30</code>")
        return
    fam = await db.get_family(fid)
    if not fam:
        await message.answer(f"❗ #{fid} oila topilmadi.")
        return

    today = now_local().date()
    base = today
    if fam["expires_at"]:
        base = max(date.fromisoformat(fam["expires_at"]), today)
    new_exp = (base + timedelta(days=int(parts[2]))).isoformat()
    await db.set_family_expiry(fid, new_exp)

    await message.answer(f"✅ #{fid} {esc(fam['name'])}: obuna {fmt_date(date.fromisoformat(new_exp))} gacha uzaytirildi.")
    await _notify_owner(message, db, fid, f"✅ Obunangiz uzaytirildi: {fmt_date(date.fromisoformat(new_exp))} gacha.")


@router.message(Command("cheksiz"))
async def admin_unlimited(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    fid = _parse_fid((message.text or "").split())
    if fid is None or not await db.get_family(fid):
        await message.answer("❗ Format: <code>/cheksiz oila_id</code>")
        return
    await db.set_family_expiry(fid, None)
    await message.answer(f"♾ #{fid} oila uchun obuna cheksiz qilindi.")
    await _notify_owner(message, db, fid, "♾ Obunangiz cheksiz qilindi.")


@router.message(Command("yopish"))
async def admin_close(message: Message, db: Database, settings: Settings) -> None:
    if not _is_admin(message, settings):
        return
    fid = _parse_fid((message.text or "").split())
    if fid is None or not await db.get_family(fid):
        await message.answer("❗ Format: <code>/yopish oila_id</code>")
        return
    yesterday = (now_local().date() - timedelta(days=1)).isoformat()
    await db.set_family_expiry(fid, yesterday)
    await message.answer(f"⛔ #{fid} oila obunasi darhol tugatildi.")
    await _notify_owner(message, db, fid, "⛔ Obunangiz tugatildi. Bot egasi bilan bog'laning.")
