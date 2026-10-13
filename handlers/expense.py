"""Harajat qo'shish: kategoriya tanlash -> summa -> ixtiyoriy izoh."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from categories import CAT_BY_KEY, cat_title
from database import Database
from handlers.common import safe_edit, save_and_reply
from keyboards import (
    BTN_ADD, MENU_BUTTONS, cancel_kb, category_kb, skip_note_kb,
)
from quick_parser import parse_amount
from states import AddExpense
from utils import esc, fmt_money

router = Router()

# Holatlarda matn kutilganda menyu tugmalari va buyruqlar o'tkazib yuboriladi
TEXT_INPUT = (F.text, ~F.text.in_(MENU_BUTTONS), ~F.text.startswith("/"))

ASK_AMOUNT = (
    "{title}\n\n💵 <b>Summani kiriting</b> (so'mda).\n"
    "Masalan: <code>45000</code>, <code>45 000</code> yoki <code>45k</code>"
)


@router.message(Command("qosh"))
@router.message(F.text == BTN_ADD)
async def start_add(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🏷 <b>Kategoriyani tanlang:</b>", reply_markup=category_kb("cat"))


@router.callback_query(F.data == "add")
async def cb_add(call: CallbackQuery, state: FSMContext) -> None:
    """Kechki eslatmadagi '➕ Harajat qo'shish' tugmasi."""
    await state.clear()
    await call.message.answer("🏷 <b>Kategoriyani tanlang:</b>", reply_markup=category_kb("cat"))
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def choose_category(call: CallbackQuery, state: FSMContext) -> None:
    key = call.data.split(":", 1)[1]
    if key not in CAT_BY_KEY:
        await call.answer("Noma'lum kategoriya", show_alert=True)
        return
    await state.set_state(AddExpense.amount)
    await state.update_data(category=key)
    await safe_edit(call.message, ASK_AMOUNT.format(title=cat_title(key)), cancel_kb())
    await call.answer()


@router.message(AddExpense.amount, *TEXT_INPUT)
async def got_amount(message: Message, state: FSMContext) -> None:
    amount = parse_amount(message.text)
    if not amount:
        await message.answer(
            "❗ Summani tushunmadim. Faqat musbat son kiriting, masalan: <code>45000</code>",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(amount=amount)
    await state.set_state(AddExpense.note)
    await message.answer(
        f"💵 {fmt_money(amount)}\n\n📝 Izoh yozing (ixtiyoriy) yoki tugmani bosing.",
        reply_markup=skip_note_kb(),
    )


async def _finish(target: Message, user, state: FSMContext, db: Database, family_id: int, note: str) -> None:
    data = await state.get_data()
    await state.clear()
    category, amount = data.get("category"), data.get("amount")
    if not category or not amount:
        await target.answer("⚠️ Ma'lumot topilmadi. Iltimos, qaytadan boshlang: /qosh")
        return
    await save_and_reply(target, user, db, family_id, category, amount, note)


@router.message(AddExpense.note, *TEXT_INPUT)
async def got_note(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    await _finish(message, message.from_user, state, db, family_id, message.text.strip()[:200])


@router.callback_query(AddExpense.note, F.data == "skip_note")
async def skip_note(call: CallbackQuery, state: FSMContext, db: Database, family_id: int) -> None:
    await call.answer()
    await _finish(call.message, call.from_user, state, db, family_id, "")
