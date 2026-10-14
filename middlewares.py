"""Kirish nazorati: ro'yxatdan o'tganmi, oila obunasi faolmi, admin buyruqlarimi.
Shuningdek, foydalanuvchining oxirgi faollik vaqtini yozib boradi (admin /foydalanuvchilar uchun)."""
import logging
import time

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards import BTN_FAMILY, BTN_HELP
from utils import now_local, sub_status

logger = logging.getLogger(__name__)

# Ro'yxatdan o'tmaganlarga ochiq buyruqlar
ONBOARDING_TEXT = {"/start", "/yordam", "/help"}
# Obuna tugagan oila a'zolariga ochiq: faqat ma'lumot va oila bo'limi
EXPIRED_OK_TEXT = ONBOARDING_TEXT | {BTN_HELP, BTN_FAMILY, "/oila", "/menu"}
ADMIN_PREFIXES = ("/admin", "/oilalar", "/uzaytir", "/cheksiz", "/yopish",
                  "/holat", "/fikrlar", "/fikrok", "/foydalanuvchilar")
TOUCH_INTERVAL = 60  # oxirgi faollikni bazaga ko'pi bilan daqiqada bir marta yozamiz


class AccessMiddleware(BaseMiddleware):
    def __init__(self, db: Database, admin_ids, contact_text: str):
        self.db = db
        self.admin_ids = frozenset(admin_ids)
        self.contact_text = contact_text
        self._touched: dict = {}  # user_id -> oxirgi yozilgan vaqt (monotonic)

    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        if user is None:
            return None  # foydalanuvchisiz hodisalar e'tiborsiz

        text = event.text or "" if isinstance(event, Message) else ""
        cdata = event.data or "" if isinstance(event, CallbackQuery) else ""

        # Admin buyruqlari o'z tekshiruvini handlerda qiladi
        if user.id in self.admin_ids and text.startswith(ADMIN_PREFIXES):
            return await handler(event, data)

        state = data.get("state")
        state_name = ((await state.get_state()) or "") if state else ""

        member = await self.db.get_user(user.id)
        if member is None:
            allowed = (
                text in ONBOARDING_TEXT
                or cdata.startswith("reg:") or cdata == "cancel"
                or state_name.startswith("JoinFamily")
            )
            if allowed:
                return await handler(event, data)
            await self._deny(event, "👋 Avval /start buyrug'ini yuboring.")
            return None

        await self._touch(user.id)

        family = await self.db.get_family(member["family_id"])
        active, _ = sub_status(family["expires_at"] if family else None)
        data["family_id"] = member["family_id"]
        data["is_owner"] = bool(member["is_owner"])

        if not active:
            allowed = text in EXPIRED_OK_TEXT or cdata == "cancel" or cdata.startswith("fam:")
            if not allowed:
                await self._deny(
                    event,
                    "⛔ Oila obunasi muddati tugagan.\n" + self.contact_text,
                )
                return None

        return await handler(event, data)

    async def _touch(self, user_id: int) -> None:
        """Oxirgi faollik vaqtini yangilaydi (xato bo'lsa asosiy ishga to'sqinlik qilmaydi)."""
        now = time.monotonic()
        if now - self._touched.get(user_id, -TOUCH_INTERVAL) < TOUCH_INTERVAL:
            return
        self._touched[user_id] = now
        try:
            await self.db.touch_user(user_id, now_local().strftime("%Y-%m-%d %H:%M:%S"))
        except Exception:
            logger.exception("Oxirgi faollikni yozib bo'lmadi (user_id=%s)", user_id)

    async def _deny(self, event, text: str) -> None:
        try:
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
        except Exception:
            logger.exception("Rad etish xabarini yuborib bo'lmadi")
