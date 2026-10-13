"""Excel (.xlsx) va CSV eksporti."""
import asyncio

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from database import Database
from exporter import build_csv, build_xlsx
from keyboards import BTN_EXPORT, export_kb
from utils import fmt_money, month_range, today_local

router = Router()


@router.message(Command("eksport"))
@router.message(F.text == BTN_EXPORT)
async def export_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📤 <b>Qaysi davr va formatda eksport qilamiz?</b>", reply_markup=export_kb())


@router.callback_query(F.data.startswith("exp:"))
async def do_export(call: CallbackQuery, db: Database, family_id: int) -> None:
    _, fmt, period = call.data.split(":")
    today = today_local()
    if period == "month":
        start, end = month_range(today)
        label = today.strftime("%Y-%m")
    else:
        start = end = None
        label = f"hammasi_{today.isoformat()}"

    rows = await db.expenses_between(family_id, start, end)
    if not rows:
        await call.answer("Bu davrda harajat yo'q", show_alert=True)
        return
    await call.answer("Fayl tayyorlanmoqda...")

    if fmt == "xlsx":
        data = await asyncio.to_thread(build_xlsx, rows)
        filename = f"harajatlar_{label}.xlsx"
    else:
        data = build_csv(rows)
        filename = f"harajatlar_{label}.csv"

    total = sum(int(r["amount"]) for r in rows)
    await call.message.answer_document(
        BufferedInputFile(data, filename=filename),
        caption=f"📤 {len(rows)} ta yozuv · jami {fmt_money(total)}",
    )
