"""Handlerlar uchun umumiy yordamchilar."""
import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message

from database import Database
from keyboards import after_save_kb
from services import check_limit_warning, saved_text
from utils import now_local

logger = logging.getLogger(__name__)


async def safe_edit(message: Message, text: str, reply_markup=None) -> None:
    """Xabarni tahrirlaydi; imkoni bo'lmasa yangi xabar yuboradi."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return
        await message.answer(text, reply_markup=reply_markup)


async def save_and_reply(target: Message, user, db: Database, family_id: int,
                         category: str, amount: int, note: str) -> None:
    """Harajatni oila hisobiga yozadi, tasdiqlash va (kerak bo'lsa) limit ogohlantirishini yuboradi."""
    now = now_local()
    expense_id = await db.add_expense(
        family_id=family_id,
        user_id=user.id,
        user_name=user.full_name,
        category=category,
        amount=amount,
        note=note,
        spent_on=now.date(),
        created_at=now.strftime("%Y-%m-%d %H:%M:%S"),
    )
    row = await db.get_expense(family_id, expense_id)
    await target.answer(await saved_text(db, family_id, row), reply_markup=after_save_kb(expense_id, bool(note)))

    warning = await check_limit_warning(db, family_id)
    if warning:
        await target.answer(warning)
