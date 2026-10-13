"""Hisobotlar: bugun, hafta, oy, kategoriya bo'yicha va statistika."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from categories import CAT_BY_KEY
from database import Database
from keyboards import (
    BTN_CATEGORY, BTN_MONTH, BTN_STATS, BTN_TODAY, BTN_WEEK, category_kb,
)
from services import (
    category_report, month_report, stats_report, today_report, week_report,
)

router = Router()


@router.message(Command("bugun"))
@router.message(F.text == BTN_TODAY)
async def report_today(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    await state.clear()
    await message.answer(await today_report(db, family_id))


@router.message(Command("hafta"))
@router.message(F.text == BTN_WEEK)
async def report_week(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    await state.clear()
    await message.answer(await week_report(db, family_id))


@router.message(Command("oy"))
@router.message(F.text == BTN_MONTH)
async def report_month(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    await state.clear()
    await message.answer(await month_report(db, family_id))


@router.message(Command("statistika"))
@router.message(F.text == BTN_STATS)
async def report_stats(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    await state.clear()
    await message.answer(await stats_report(db, family_id))


@router.message(Command("kategoriya"))
@router.message(F.text == BTN_CATEGORY)
async def report_category_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📂 <b>Qaysi kategoriya bo'yicha hisobot kerak?</b>",
                         reply_markup=category_kb("rcat"))


@router.callback_query(F.data.startswith("rcat:"))
async def report_category(call: CallbackQuery, db: Database, family_id: int) -> None:
    key = call.data.split(":", 1)[1]
    if key not in CAT_BY_KEY:
        await call.answer("Noma'lum kategoriya", show_alert=True)
        return
    await call.answer()
    await call.message.answer(await category_report(db, family_id, key))
