"""Hisobotlar, statistika va limit nazorati matnlari. Barchasi bitta oila (family_id) doirasida."""
from datetime import date, timedelta
from typing import Optional

from categories import CAT_BY_KEY
from database import Database
from utils import (
    WEEKDAYS_SHORT, bar, esc, fmt_date, fmt_money, fmt_num, fmt_short,
    month_range, month_title, prev_month_range, today_local, week_range,
)

LINE = "━━━━━━━━━━━━"


def _cat(key: str):
    return CAT_BY_KEY.get(key, ("📦", "Boshqa"))


# ---------------------------------------------------------------- limit
async def limit_status_text(db: Database, fid: int) -> Optional[str]:
    """Oylik limit holati. Limit belgilanmagan bo'lsa None."""
    limit = await db.get_limit(fid)
    if not limit:
        return None
    today = today_local()
    start, end = month_range(today)
    total, _ = await db.total(fid, start, end)
    pct = total * 100 / limit
    remaining = limit - total

    lines = [
        f"💰 <b>Oylik limit:</b> {fmt_money(limit)}",
        f"📉 Sarflandi: {fmt_money(total)} ({pct:.0f}%)",
        bar(total, limit, 12),
    ]
    if remaining >= 0:
        lines.append(f"✅ Qolgan: <b>{fmt_money(remaining)}</b>")
        days_left = (end - today).days + 1
        if days_left > 0 and remaining > 0:
            lines.append(f"📆 Oy oxirigacha kuniga: ~{fmt_money(remaining // days_left)}")
    else:
        lines.append(f"🚨 Limitdan oshdi: <b>{fmt_money(-remaining)}</b>")
    return "\n".join(lines)


async def check_limit_warning(db: Database, fid: int, silent: bool = False) -> Optional[str]:
    """80% yoki 100% ogohlantirish matni. Har daraja oyiga bir marta yuboriladi.
    silent=True bo'lsa faqat holat saqlanadi."""
    limit = await db.get_limit(fid)
    if not limit:
        return None

    today = today_local()
    month_key = today.strftime("%Y-%m")
    start, end = month_range(today)
    total, _ = await db.total(fid, start, end)
    pct = total * 100 / limit
    level = 100 if pct >= 100 else (80 if pct >= 80 else 0)

    prev_level = 0
    raw = await db.get_setting(fid, "warn_state")
    if raw and ":" in raw:
        prev_month, prev_level_s = raw.split(":", 1)
        if prev_month == month_key and prev_level_s.isdigit():
            prev_level = int(prev_level_s)

    # Joriy darajani doim saqlaymiz: harajat o'chirilib daraja pasaysa, qayta ogohlantirish mumkin
    await db.set_setting(fid, "warn_state", f"{month_key}:{level}")

    if silent or level == 0 or level <= prev_level:
        return None

    remaining = limit - total
    if level == 100:
        return (
            "🚨 <b>Oylik limit oshib ketdi!</b>\n"
            f"💰 Limit: {fmt_money(limit)}\n"
            f"📉 Sarflandi: {fmt_money(total)} ({pct:.0f}%)\n"
            f"❗ Oshgan miqdor: <b>{fmt_money(-remaining)}</b>"
        )
    return (
        "⚠️ <b>Limitga yaqinlashdingiz!</b>\n"
        f"Oylik limitning {pct:.0f}% qismi sarflandi.\n"
        f"💰 Limit: {fmt_money(limit)}\n"
        f"📉 Sarflandi: {fmt_money(total)}\n"
        f"✅ Qolgan: <b>{fmt_money(remaining)}</b>"
    )


# ---------------------------------------------------------------- kartalar
def expense_card(row: dict) -> str:
    emoji, name = _cat(row["category"])
    lines = [
        f"🧾 <b>Harajat #{row['id']}</b>",
        f"{emoji} {esc(name)}",
        f"💵 {fmt_money(row['amount'])}",
        f"📅 {fmt_date(date.fromisoformat(row['spent_on']))}",
    ]
    if row.get("note"):
        lines.append(f"📝 {esc(row['note'])}")
    if row.get("user_name"):
        lines.append(f"👤 {esc(row['user_name'])}")
    return "\n".join(lines)


async def saved_text(db: Database, fid: int, row: dict) -> str:
    emoji, name = _cat(row["category"])
    today = today_local()
    day_total, _ = await db.total(fid, today, today)
    lines = [
        "✅ <b>Saqlandi</b>",
        f"{emoji} {esc(name)}",
        f"💵 <b>{fmt_money(row['amount'])}</b>",
    ]
    if row.get("note"):
        lines.append(f"📝 {esc(row['note'])}")
    lines.append("")
    lines.append(f"📅 Bugungi jami: {fmt_money(day_total)}")

    limit = await db.get_limit(fid)
    if limit:
        start, end = month_range(today)
        month_total, _ = await db.total(fid, start, end)
        left = limit - month_total
        if left >= 0:
            lines.append(f"💰 Oylik limitdan qolgan: {fmt_money(left)}")
        else:
            lines.append(f"🚨 Oylik limitdan oshgan: {fmt_money(-left)}")
    return "\n".join(lines)


# ---------------------------------------------------------------- hisobotlar
async def period_report(db: Database, fid: int, title: str, start: date, end: date):
    """(matn, jami, yozuvlar soni) - kategoriyalar bo'yicha hisobot."""
    rows = await db.totals_by_category(fid, start, end)
    if not rows:
        return f"{title}\n\nBu davrda harajat kiritilmagan.", 0, 0

    total = sum(int(r["total"]) for r in rows)
    count = sum(int(r["cnt"]) for r in rows)
    lines = [title, ""]
    for r in rows:
        emoji, name = _cat(r["category"])
        lines.append(f"{emoji} {esc(name)} — <b>{fmt_money(r['total'])}</b>")
    lines += ["", LINE, f"💵 <b>Jami: {fmt_money(total)}</b> ({count} ta yozuv)"]
    return "\n".join(lines), total, count


def _entry_line(row: dict, show_user: bool) -> str:
    """Bitta yozuv: '• 14:20 🍽 30 000 so'm · 📝 tushlik · 👤 Ali'"""
    emoji, _ = _cat(row["category"])
    clock = (row.get("created_at") or "")[11:16]
    parts = [f"• {clock} {emoji} {fmt_money(row['amount'])}".replace("•  ", "• ")]
    if row.get("note"):
        parts.append(f"📝 {esc(row['note'][:40])}")
    if show_user and row.get("user_name"):
        parts.append(f"👤 {esc(row['user_name'].split()[0])}")
    return " · ".join(parts)


TODAY_ENTRIES_LIMIT = 15


async def today_report(db: Database, fid: int) -> str:
    d = today_local()
    text, _, count = await period_report(db, fid, f"📅 <b>Bugungi hisobot</b> — {fmt_date(d)}", d, d)
    lines = [text]

    # Har bir yozuv izoh va kim kiritgani bilan
    rows = await db.expenses_between(fid, d, d, limit=TODAY_ENTRIES_LIMIT, newest_first=True)
    if rows:
        show_user = len({r["user_id"] for r in rows}) > 1
        lines += ["", "🧾 <b>Bugungi yozuvlar:</b>"]
        lines += [_entry_line(r, show_user) for r in rows]
        if count > len(rows):
            lines.append(f"… va yana {count - len(rows)} ta")

    # "Bugun 0" chalkashligi bo'lmasligi uchun kechagi holat ham ko'rsatiladi
    y = d - timedelta(days=1)
    y_total, y_count = await db.total(fid, y, y)
    lines.append("")
    lines.append(f"🕘 Kecha: {fmt_money(y_total)} ({y_count} ta yozuv)" if y_count
                 else "🕘 Kecha: harajat kiritilmagan")
    return "\n".join(lines)


async def week_report(db: Database, fid: int) -> str:
    d = today_local()
    start, end = week_range(d)
    title = f"📆 <b>Haftalik hisobot</b>\n{fmt_short(start)} — {fmt_short(end)}.{end.year}"
    text, total, _ = await period_report(db, fid, title, start, end)
    if total == 0:
        return text

    daily = await db.daily_totals(fid, start, end)
    max_day = max(daily.values()) if daily else 0
    lines = [text, "", "📊 <b>Kunlar bo'yicha:</b>"]
    for i in range(7):
        day = start + timedelta(days=i)
        amount = daily.get(day.isoformat(), 0)
        lines.append(f"{WEEKDAYS_SHORT[i]} {fmt_short(day)}  {bar(amount, max_day, 8)}  {fmt_num(amount)}")
    return "\n".join(lines)


async def month_report(db: Database, fid: int) -> str:
    d = today_local()
    start, end = month_range(d)
    title = f"🗓 <b>Oylik hisobot</b> — {month_title(d)}"
    text, total, _ = await period_report(db, fid, title, start, end)
    if total == 0:
        return text

    lines = [text, f"📈 O'rtacha kunlik: {fmt_money(total // d.day)}"]
    limit_text = await limit_status_text(db, fid)
    if limit_text:
        lines += ["", limit_text]
    return "\n".join(lines)


async def category_report(db: Database, fid: int, key: str) -> str:
    d = today_local()
    emoji, name = _cat(key)
    m_start, m_end = month_range(d)
    w_start, w_end = week_range(d)
    t_day, _ = await db.total(fid, d, d, key)
    t_week, _ = await db.total(fid, w_start, w_end, key)
    t_month, c_month = await db.total(fid, m_start, m_end, key)

    lines = [
        f"📂 <b>{emoji} {esc(name)}</b>",
        "",
        f"📅 Bugun: {fmt_money(t_day)}",
        f"📆 Shu hafta: {fmt_money(t_week)}",
        f"🗓 Shu oy: <b>{fmt_money(t_month)}</b> ({c_month} ta)",
    ]
    last = await db.expenses_between(fid, m_start, m_end, category=key, limit=10, newest_first=True)
    if last:
        lines += ["", "🕘 <b>Oxirgi yozuvlar (shu oy):</b>"]
        for row in last:
            note = f" · {esc(row['note'])}" if row["note"] else ""
            lines.append(
                f"• {fmt_short(date.fromisoformat(row['spent_on']))} — {fmt_money(row['amount'])}{note}"
            )
    else:
        lines += ["", "Shu oyda bu kategoriya bo'yicha harajat yo'q."]
    return "\n".join(lines)


# ---------------------------------------------------------------- statistika
async def stats_report(db: Database, fid: int) -> str:
    d = today_local()
    m_start, m_end = month_range(d)
    total, count = await db.total(fid, m_start, m_end)

    lines = [f"📊 <b>Statistika</b> — {month_title(d)}", ""]
    if total == 0:
        lines.append("Bu oyda hali harajat kiritilmagan.")
        return "\n".join(lines)

    days_in_month = m_end.day
    avg = total // d.day
    lines += [
        f"💵 Jami: <b>{fmt_money(total)}</b> ({count} ta yozuv)",
        f"📈 O'rtacha kunlik: {fmt_money(avg)}",
        f"🔮 Oy oxirigacha prognoz: ~{fmt_money(avg * days_in_month)}",
    ]

    daily = await db.daily_totals(fid, m_start, d)
    if daily:
        top_day, top_amount = max(daily.items(), key=lambda kv: kv[1])
        lines.append(f"🔥 Eng qimmat kun: {fmt_date(date.fromisoformat(top_day))} — {fmt_money(top_amount)}")

    # O'tgan oyning xuddi shu davri bilan solishtirish
    p_start, p_end = prev_month_range(d)
    p_to = min(p_start + timedelta(days=d.day - 1), p_end)
    prev_total, _ = await db.total(fid, p_start, p_to)
    if prev_total > 0:
        diff = (total - prev_total) * 100 / prev_total
        arrow = "🔺" if diff > 0 else ("🔻" if diff < 0 else "▫️")
        lines.append(f"🆚 O'tgan oyning shu davriga nisbatan: {arrow} {abs(diff):.0f}% ({fmt_money(prev_total)})")
    else:
        lines.append("🆚 O'tgan oy bilan solishtirish uchun ma'lumot yo'q")

    by_cat = await db.totals_by_category(fid, m_start, m_end)
    lines += ["", "🏆 <b>Top kategoriyalar:</b>"]
    for r in by_cat[:5]:
        emoji, name = _cat(r["category"])
        share = int(r["total"]) * 100 / total
        lines.append(f"{emoji} {esc(name)}\n   {bar(int(r['total']), total)} {share:.0f}% · {fmt_money(r['total'])}")

    # Oxirgi 7 kun
    w_start = d - timedelta(days=6)
    week_daily = await db.daily_totals(fid, w_start, d)
    max_day = max(week_daily.values()) if week_daily else 0
    lines += ["", "📅 <b>Oxirgi 7 kun:</b>"]
    for i in range(7):
        day = w_start + timedelta(days=i)
        amount = week_daily.get(day.isoformat(), 0)
        lines.append(f"{WEEKDAYS_SHORT[day.weekday()]} {fmt_short(day)}  {bar(amount, max_day, 8)}  {fmt_num(amount)}")

    limit_text = await limit_status_text(db, fid)
    if limit_text:
        lines += ["", limit_text]
    return "\n".join(lines)


# ---------------------------------------------------------------- eslatma
def reminder_slot(hour: int):
    """Eslatma vaqtiga qarab sarlavha va matn: ertalab / kunduz / kechki."""
    if hour < 12:
        return "🌅 <b>Ertalabki eslatma</b>", "Kechagi va bugungi harajatlarni kiritishni unutmang."
    if hour < 18:
        return "☀️ <b>Kunduzgi eslatma</b>", "Tushlik, transport va boshqa harajatlarni kiritdingizmi?"
    return "🔔 <b>Kechki eslatma</b>", "Bugungi harajatlarni kiritishni unutmang."


async def reminder_text(db: Database, fid: int, hour: int = 21) -> str:
    d = today_local()
    total, count = await db.total(fid, d, d)
    title, hint = reminder_slot(hour)
    lines = [title, "", hint]
    if count:
        lines.append(f"\n📅 Bugun kiritilgan: <b>{fmt_money(total)}</b> ({count} ta yozuv)")
    else:
        lines.append("\n📅 Bugun hali harajat kiritilmagan.")
    return "\n".join(lines)
