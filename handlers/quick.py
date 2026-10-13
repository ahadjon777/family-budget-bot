"""Tezkor kiritish ('ovqat 45000 tushlik') va qolgan barcha xabarlar uchun zaxira handlerlar.
Bu router eng oxirida ulanadi."""
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery, Message

from categories import CAT_BY_KEY
from database import Database
from handlers.common import safe_edit, save_and_reply
from keyboards import category_kb, main_menu
from quick_parser import parse_quick
from states import QuickEntry
from utils import esc, fmt_money

router = Router()

HINT = (
    "🤔 Tushunmadim. Harajatni shunday yozing:\n"
    "<code>ovqat 45000 tushlik</code>\n"
    "<code>taksi 15k</code>\n\n"
    "Yoki menyudan <b>➕ Harajat qo'shish</b> tugmasini bosing."
)


@router.message(StateFilter(default_state), F.text, ~F.text.startswith("/"))
async def quick_entry(message: Message, state: FSMContext, db: Database, family_id: int) -> None:
    parsed = parse_quick(message.text)
    if not parsed:
        await message.answer(HINT, reply_markup=main_menu())
        return

    if parsed.category:
        await save_and_reply(message, message.from_user, db, family_id,
                             parsed.category, parsed.amount, parsed.note)
        return

    # Kategoriya aniqlanmadi - tugmalar orqali so'raymiz
    await state.set_state(QuickEntry.category)
    await state.update_data(amount=parsed.amount, note=parsed.note)
    note_line = f"\n📝 {esc(parsed.note)}" if parsed.note else ""
    await message.answer(
        f"💵 <b>{fmt_money(parsed.amount)}</b>{note_line}\n\n🏷 Kategoriyani tanlang:",
        reply_markup=category_kb("qcat"),
    )


@router.callback_query(QuickEntry.category, F.data.startswith("qcat:"))
async def quick_category(call: CallbackQuery, state: FSMContext, db: Database, family_id: int) -> None:
    key = call.data.split(":", 1)[1]
    if key not in CAT_BY_KEY:
        await call.answer("Noma'lum kategoriya", show_alert=True)
        return
    data = await state.get_data()
    await state.clear()
    amount, note = data.get("amount"), data.get("note", "")
    if not amount:
        await call.answer("Ma'lumot topilmadi, qaytadan yozing", show_alert=True)
        return
    await call.answer()
    await safe_edit(call.message, "✅ Kategoriya tanlandi.")
    await save_and_reply(call.message, call.from_user, db, family_id, key, amount, note)


@router.callback_query()
async def stale_button(call: CallbackQuery) -> None:
    """Eskirgan yoki holati yo'qolgan tugmalar (masalan, bot qayta ishga tushgandan keyin)."""
    await call.answer("Bu tugma eskirgan. Menyudan qaytadan boshlang.", show_alert=True)
