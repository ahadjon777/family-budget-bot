"""Oylik limit: belgilash, ko'rish, olib tashlash."""
from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards import BTN_LIMIT, MENU_BUTTONS, cancel_kb, limit_kb
from quick_parser import parse_amount
from services import check_limit_warning, limit_status_text
from states import SetLimit
from utils import fmt_money

router = Router()

TEXT_INPUT = (F.text, ~F.text.in_(MENU_BUTTONS), ~F.text.startswith("/"))
ASK_LIMIT = (
    "💰 <b>Oylik limitni kiriting</b> (so'mda).\n"
    "Masalan: <code>5000000</code>, <code>5 000 000</code> yoki <code>5 mln</code>"
)


async def _show_limit(target: Message, db: Database, family_id: int) -> None:
    status = await limit_status_text(db, family_id)
    if status:
        await target.answer(status, reply_markup=limit_kb(True))
    else:
        await target.answer(
            "💰 Oylik limit hali belgilanmagan.\n\n"
            "Limit belgilasangiz, unga yaqinlashganda (80%) va oshganda ogohlantiraman.",
            reply_markup=limit_kb(False),
        )


async def _apply_limit(target: Message, db: Database, family_id: int, amount: int) -> None:
    await db.set_limit(family_id, amount)
    # Hozirgi daraja saqlanadi: faqat keyingi o'tishlarda ogohlantiriladi
    await check_limit_warning(db, family_id, silent=True)
    status = await limit_status_text(db, family_id)
    await target.answer(f"✅ Oylik limit belgilandi: <b>{fmt_money(amount)}</b>\n\n{status}")


@router.message(Command("limit"))
@router.message(F.text == BTN_LIMIT)
async def cmd_limit(message: Message, state: FSMContext, db: Database, family_id: int,
                    command: CommandObject = None) -> None:
    await state.clear()
    if command and command.args:
        amount = parse_amount(command.args)
        if not amount:
            await message.answer("❗ Summani tushunmadim. Masalan: <code>/limit 5000000</code>")
            return
        await _apply_limit(message, db, family_id, amount)
        return
    await _show_limit(message, db, family_id)


@router.callback_query(F.data == "limit:set")
async def limit_set_start(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SetLimit.amount)
    await call.message.answer(ASK_LIMIT, reply_markup=cancel_kb())
    await call.answer()


@router.message(SetLimit.amount, *TEXT_INPUT)
async def limit_set_done(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    amount = parse_amount(message.text)
    if not amount:
        await message.answer("❗ Summani tushunmadim. Masalan: <code>5000000</code>", reply_markup=cancel_kb())
        return
    await state.clear()
    await _apply_limit(message, db, family_id, amount)


@router.callback_query(F.data == "limit:clear")
async def limit_clear(call: CallbackQuery, db: Database, family_id: int) -> None:
    await db.set_limit(family_id, None)
    await call.message.answer("🗑 Oylik limit olib tashlandi.")
    await call.answer("Olib tashlandi")
