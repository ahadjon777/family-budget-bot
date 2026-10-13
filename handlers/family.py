"""Oila: yangi hisob ochish, taklif kodi bilan qo'shilish, oila ma'lumoti va obuna holati."""
from datetime import date, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards import BTN_FAMILY, cancel_kb, main_menu
from states import JoinFamily
from utils import esc, fmt_date, now_local, sub_status

router = Router()


def _now_str() -> str:
    return now_local().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- yangi hisob
@router.callback_query(F.data == "reg:new")
async def reg_new(call: CallbackQuery, state: FSMContext, db: Database, settings: Settings) -> None:
    await state.clear()
    user = call.from_user
    if await db.get_user(user.id):
        await call.answer("Siz allaqachon ro'yxatdan o'tgansiz.", show_alert=True)
        return

    today = now_local().date()
    if user.id in settings.admin_ids:
        expires = None  # bot egasi uchun cheksiz
    elif settings.trial_days > 0:
        expires = (today + timedelta(days=settings.trial_days)).isoformat()
    else:
        expires = (today - timedelta(days=1)).isoformat()  # sinov yo'q: admin faollashtiradi

    fid, code = await db.create_family(f"{user.full_name} oilasi", expires, _now_str())
    await db.add_user(user.id, fid, user.full_name, user.username or "", True, _now_str())

    if expires is None:
        obuna = "♾ cheksiz"
    elif expires < today.isoformat():
        obuna = "⛔ hozircha faol emas. " + settings.contact_text
    else:
        obuna = f"{settings.trial_days} kunlik bepul sinov, {fmt_date(today + timedelta(days=settings.trial_days))} gacha"

    await call.message.answer(
        "✅ <b>Hisobingiz ochildi!</b>\n\n"
        f"📅 Obuna: {obuna}\n"
        f"🔑 Oila taklif kodi: <code>{code}</code>\n"
        "Oila a'zolari /start → <b>Taklif kodi bilan qo'shilish</b> orqali shu kodni kiritadi.\n\n"
        "Endi harajat yozishingiz mumkin: <code>ovqat 45000 tushlik</code>",
        reply_markup=main_menu(),
    )
    await call.answer()


# ---------------------------------------------------------------- taklif kodi bilan qo'shilish
@router.callback_query(F.data == "reg:join")
async def reg_join(call: CallbackQuery, state: FSMContext, db: Database) -> None:
    if await db.get_user(call.from_user.id):
        await call.answer("Siz allaqachon ro'yxatdan o'tgansiz.", show_alert=True)
        return
    await state.set_state(JoinFamily.code)
    await call.message.answer("🔑 Oila taklif kodini yuboring (6 belgi).", reply_markup=cancel_kb())
    await call.answer()


@router.message(JoinFamily.code, F.text)
async def join_code(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    code = message.text.strip().upper().replace(" ", "")
    fam = await db.get_family_by_code(code)
    if not fam:
        await message.answer("❗ Bunday kod topilmadi. Qayta yuboring yoki /bekor deb yozing.",
                             reply_markup=cancel_kb())
        return
    if await db.count_members(fam["id"]) >= settings.max_members:
        await state.clear()
        await message.answer(f"⚠️ Bu oila to'lgan (eng ko'pi {settings.max_members} kishi).",
                             reply_markup=main_menu())
        return

    user = message.from_user
    await db.add_user(user.id, fam["id"], user.full_name, user.username or "", False, _now_str())
    await state.clear()

    active, _ = sub_status(fam["expires_at"])
    text = f"✅ <b>{esc(fam['name'])}</b> oilasiga qo'shildingiz."
    if not active:
        text += "\n⛔ Oila obunasi tugagan. " + settings.contact_text
    await message.answer(text, reply_markup=main_menu())


# ---------------------------------------------------------------- oila ma'lumoti
@router.message(Command("oila"))
@router.message(F.text == BTN_FAMILY)
async def family_info(message: Message, state: FSMContext, db: Database, settings: Settings,
                      family_id: int, is_owner: bool) -> None:
    await state.clear()
    fam = await db.get_family(family_id)
    members = await db.family_members(family_id)
    active, days = sub_status(fam["expires_at"])

    if fam["expires_at"] is None:
        obuna = "♾ cheksiz"
    elif active:
        obuna = f"✅ faol, {fmt_date(date.fromisoformat(fam['expires_at']))} gacha ({days} kun qoldi)"
    else:
        obuna = f"⛔ tugagan ({fmt_date(date.fromisoformat(fam['expires_at']))})"

    lines = [
        f"👨‍👩‍👧 <b>{esc(fam['name'])}</b>",
        "",
        f"📅 Obuna: {obuna}",
        f"👥 A'zolar: {len(members)}/{settings.max_members}",
    ]
    for m in members:
        badge = "👑 " if m["is_owner"] else "• "
        name = esc(m["name"]) or f"ID {m['user_id']}"
        uname = f" (@{esc(m['username'])})" if m["username"] else ""
        lines.append(f"{badge}{name}{uname}")

    if is_owner:
        lines += ["", f"🔑 Taklif kodi: <code>{fam['invite_code']}</code>"]
    else:
        lines += ["", "🔑 Taklif kodi faqat oila egasiga ko'rinadi."]

    if settings.price_text:
        lines += ["", esc(settings.price_text)]
    lines += ["", esc(settings.contact_text)]
    await message.answer("\n".join(lines), reply_markup=main_menu())

