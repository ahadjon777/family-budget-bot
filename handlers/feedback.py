"""Foydalanuvchilar fikr-mulohaza va takliflarini yuboradi (/fikr)."""
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import Settings
from database import Database
from keyboards import cancel_kb, main_menu
from states import Feedback
from status import notify_admins
from utils import esc, now_local

logger = logging.getLogger(__name__)
router = Router()

MAX_LEN = 1000
ASK_TEXT = (
    "💡 <b>Fikr va takliflar</b>\n\n"
    "Botga nima yetishmayapti yoki nimani yaxshilash kerak? Yozib yuboring.\n"
    "(Bekor qilish: /bekor)"
)


async def _save(message: Message, db: Database, settings: Settings, family_id: int, text: str) -> None:
    user = message.from_user
    text = text.strip()
    if not text:
        await message.answer("❗ Fikr matnini yozing.")
        return
    if len(text) > MAX_LEN:
        await message.answer(f"❗ Fikr {MAX_LEN} belgidan oshmasin (hozir: {len(text)}).")
        return
    created = now_local().strftime("%Y-%m-%d %H:%M:%S")
    fid = await db.add_feedback(family_id, user.id, user.full_name, text, created)
    await message.answer(f"✅ Rahmat! Fikringiz qabul qilindi (#{fid}).", reply_markup=main_menu())
    try:
        await notify_admins(
            message.bot, settings,
            f"💡 <b>Yangi fikr #{fid}</b>\n"
            f"Kimdan: {esc(user.full_name)} (oila #{family_id})\n\n{esc(text)}"
        )
    except Exception:
        logger.exception("Fikr haqida admin'ga xabar yuborilmadi")


@router.message(Command("fikr"))
async def cmd_feedback(message: Message, state: FSMContext, db: Database, settings: Settings,
                       family_id: int, command: CommandObject) -> None:
    if command.args:
        await _save(message, db, settings, family_id, command.args)
        return
    await state.set_state(Feedback.text)
    await message.answer(ASK_TEXT, reply_markup=cancel_kb())


@router.message(Feedback.text, F.text)
async def feedback_text(message: Message, state: FSMContext, db: Database, settings: Settings,
                        family_id: int) -> None:
    await state.clear()
    await _save(message, db, settings, family_id, message.text or "")
