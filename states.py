"""FSM holatlari (suhbat bosqichlari)."""
from aiogram.fsm.state import State, StatesGroup


class AddExpense(StatesGroup):
    """Harajat qo'shish: kategoriya (tugma) -> summa -> izoh."""
    amount = State()
    note = State()


class QuickEntry(StatesGroup):
    """Tezkor kiritishda kategoriya aniqlanmasa, tugma orqali tanlanadi."""
    category = State()


class EditExpense(StatesGroup):
    """Mavjud harajatni tahrirlash."""
    amount = State()
    note = State()


class SetLimit(StatesGroup):
    amount = State()


class JoinFamily(StatesGroup):
    """Mavjud oilaga taklif kodi bilan qo'shilish."""
    code = State()


class Feedback(StatesGroup):
    """Foydalanuvchi fikr/taklifini yozadi."""
    text = State()
