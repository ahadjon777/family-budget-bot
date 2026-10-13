"""Harajatni tahrirlash va o'chirish (oxirgi harajat yoki ro'yxatdan tanlangan)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from categories import CAT_BY_KEY, cat_title
from database import Database
from handlers.common import safe_edit
from keyboards import (
    BTN_LAST, MENU_BUTTONS, cancel_kb, category_kb, confirm_delete_kb,
    expense_actions_kb,
)
from quick_parser import parse_amount
from services import check_limit_warning, expense_card
from states import EditExpense
from utils import fmt_num, fmt_short

from datetime import date

router = Router()

TEXT_INPUT = (F.text, ~F.text.in_(MENU_BUTTONS), ~F.text.startswith("/"))
NOT_FOUND = "⚠️ Bu harajat topilmadi (ehtimol o'chirilgan)."


def _expense_id(data: str, index: int = 1) -> int:
    return int(data.split(":")[index])


# ---------------------------------------------------------------- ko'rish
@router.message(Command("oxirgi"))
@router.message(F.text == BTN_LAST)
async def show_last(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    await state.clear()
    row = await db.last_expense(family_id)
    if not row:
        await message.answer("Hali birorta harajat kiritilmagan.")
        return
    await message.answer(expense_card(row), reply_markup=expense_actions_kb(row["id"]))


@router.callback_query(F.data.startswith("view:"))
async def view_expense(call: CallbackQuery, state: FSMContext, db: Database, family_id: int) -> None:
    await state.clear()
    row = await db.get_expense(family_id, _expense_id(call.data))
    if not row:
        await call.answer(NOT_FOUND, show_alert=True)
        return
    await safe_edit(call.message, expense_card(row), expense_actions_kb(row["id"]))
    await call.answer()


@router.callback_query(F.data == "list_last")
async def list_last(call: CallbackQuery, db: Database, family_id: int) -> None:
    rows = await db.recent(family_id, 10)
    if not rows:
        await call.answer("Harajat yo'q", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    for row in rows:
        emoji = CAT_BY_KEY.get(row["category"], ("📦", ""))[0]
        label = row["note"][:14] if row["note"] else CAT_BY_KEY.get(row["category"], ("", "Boshqa"))[1][:14]
        day = fmt_short(date.fromisoformat(row["spent_on"]))
        kb.button(text=f"{emoji} {fmt_num(row['amount'])} · {label} · {day}",
                  callback_data=f"view:{row['id']}")
    kb.adjust(1)
    await safe_edit(call.message, "📋 <b>Oxirgi 10 ta harajat.</b> Tanlang:", kb.as_markup())
    await call.answer()


# ---------------------------------------------------------------- o'chirish
@router.callback_query(F.data.startswith("del:"))
async def ask_delete(call: CallbackQuery, db: Database, family_id: int) -> None:
    row = await db.get_expense(family_id, _expense_id(call.data))
    if not row:
        await call.answer(NOT_FOUND, show_alert=True)
        return
    await safe_edit(call.message,
                    expense_card(row) + "\n\n❓ <b>Rostdan ham o'chirasizmi?</b>",
                    confirm_delete_kb(row["id"]))
    await call.answer()


@router.callback_query(F.data.startswith("delok:"))
async def do_delete(call: CallbackQuery, db: Database, family_id: int) -> None:
    expense_id = _expense_id(call.data)
    if await db.delete_expense(family_id, expense_id):
        await check_limit_warning(db, family_id, silent=True)  # limit holatini yangilash
        await safe_edit(call.message, f"🗑 Harajat #{expense_id} o'chirildi.")
        await call.answer("O'chirildi")
    else:
        await call.answer(NOT_FOUND, show_alert=True)


# ---------------------------------------------------------------- summani tahrirlash
@router.callback_query(F.data.startswith("eamt:"))
async def edit_amount_start(call: CallbackQuery, state: FSMContext, db: Database, family_id: int) -> None:
    expense_id = _expense_id(call.data)
    if not await db.get_expense(family_id, expense_id):
        await call.answer(NOT_FOUND, show_alert=True)
        return
    await state.set_state(EditExpense.amount)
    await state.update_data(expense_id=expense_id)
    await call.message.answer(
        f"💵 Harajat #{expense_id} uchun <b>yangi summani</b> kiriting:", reply_markup=cancel_kb())
    await call.answer()


@router.message(EditExpense.amount, *TEXT_INPUT)
async def edit_amount_done(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    amount = parse_amount(message.text)
    if not amount:
        await message.answer("❗ Summani tushunmadim. Masalan: <code>45000</code>", reply_markup=cancel_kb())
        return
    expense_id = (await state.get_data()).get("expense_id")
    await state.clear()
    if not expense_id or not await db.update_amount(family_id, expense_id, amount):
        await message.answer(NOT_FOUND)
        return
    row = await db.get_expense(family_id, expense_id)
    await message.answer("✅ Summa yangilandi.\n\n" + expense_card(row),
                         reply_markup=expense_actions_kb(expense_id))
    warning = await check_limit_warning(db, family_id)
    if warning:
        await message.answer(warning)


# ---------------------------------------------------------------- kategoriyani tahrirlash
@router.callback_query(F.data.startswith("ecat:"))
async def edit_category_start(call: CallbackQuery, db: Database, family_id: int) -> None:
    expense_id = _expense_id(call.data)
    if not await db.get_expense(family_id, expense_id):
        await call.answer(NOT_FOUND, show_alert=True)
        return
    await safe_edit(call.message, f"🏷 Harajat #{expense_id} uchun <b>yangi kategoriya</b>ni tanlang:",
                    category_kb(f"setcat:{expense_id}"))
    await call.answer()


@router.callback_query(F.data.startswith("setcat:"))
async def edit_category_done(call: CallbackQuery, db: Database, family_id: int) -> None:
    _, expense_id, key = call.data.split(":")
    if key not in CAT_BY_KEY:
        await call.answer("Noma'lum kategoriya", show_alert=True)
        return
    if not await db.update_category(family_id, int(expense_id), key):
        await call.answer(NOT_FOUND, show_alert=True)
        return
    row = await db.get_expense(family_id, int(expense_id))
    await safe_edit(call.message, f"✅ Kategoriya: {cat_title(key)}\n\n" + expense_card(row),
                    expense_actions_kb(row["id"]))
    await call.answer("Yangilandi")


# ---------------------------------------------------------------- izohni tahrirlash
@router.callback_query(F.data.startswith("enote:"))
async def edit_note_start(call: CallbackQuery, state: FSMContext, db: Database, family_id: int) -> None:
    expense_id = _expense_id(call.data)
    if not await db.get_expense(family_id, expense_id):
        await call.answer(NOT_FOUND, show_alert=True)
        return
    await state.set_state(EditExpense.note)
    await state.update_data(expense_id=expense_id)
    await call.message.answer(
        f"📝 Harajat #{expense_id} uchun <b>yangi izohni</b> yozing.\n"
        "Izohni o'chirish uchun <code>-</code> yuboring.",
        reply_markup=cancel_kb())
    await call.answer()


@router.message(EditExpense.note, *TEXT_INPUT)
async def edit_note_done(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    expense_id = (await state.get_data()).get("expense_id")
    await state.clear()
    note = message.text.strip()
    note = "" if note == "-" else note[:200]
    if not expense_id or not await db.update_note(family_id, expense_id, note):
        await message.answer(NOT_FOUND)
        return
    row = await db.get_expense(family_id, expense_id)
    await message.answer("✅ Izoh yangilandi.\n\n" + expense_card(row),
                         reply_markup=expense_actions_kb(expense_id))
