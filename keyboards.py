"""Reply va inline tugmalar."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from categories import CATEGORIES, CAT_BY_KEY

# ---- asosiy menyu tugmalari matni
BTN_ADD = "➕ Harajat qo'shish"
BTN_TODAY = "📅 Bugun"
BTN_WEEK = "📆 Hafta"
BTN_MONTH = "🗓 Oy"
BTN_CATEGORY = "📂 Kategoriya bo'yicha"
BTN_STATS = "📊 Statistika"
BTN_LAST = "✏️ Oxirgi harajat"
BTN_LIMIT = "💰 Limit"
BTN_EXPORT = "📤 Eksport"
BTN_FAMILY = "👨‍👩‍👧 Oila va obuna"
BTN_HELP = "ℹ️ Yordam"

MENU_BUTTONS = {
    BTN_ADD, BTN_TODAY, BTN_WEEK, BTN_MONTH, BTN_CATEGORY,
    BTN_STATS, BTN_LAST, BTN_LIMIT, BTN_EXPORT, BTN_FAMILY, BTN_HELP,
}


def main_menu():
    kb = ReplyKeyboardBuilder()
    for text in (BTN_ADD, BTN_TODAY, BTN_WEEK, BTN_MONTH, BTN_CATEGORY,
                 BTN_STATS, BTN_LAST, BTN_LIMIT, BTN_EXPORT, BTN_FAMILY, BTN_HELP):
        kb.button(text=text)
    kb.adjust(1, 3, 2, 2, 3)
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Masalan: ovqat 45000 tushlik")


def reg_kb(trial_days: int) -> InlineKeyboardMarkup:
    """Yangi foydalanuvchi uchun: yangi hisob ochish yoki taklif kodi bilan qo'shilish."""
    trial = f" ({trial_days} kun bepul)" if trial_days > 0 else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✨ Yangi hisob ochish{trial}", callback_data="reg:new")],
        [InlineKeyboardButton(text="🔑 Taklif kodi bilan qo'shilish", callback_data="reg:join")],
    ])


def cancel_row() -> list:
    return [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]


def category_kb(prefix: str, with_cancel: bool = True) -> InlineKeyboardMarkup:
    """Kategoriya tanlash tugmalari. callback_data: '<prefix>:<kalit>'."""
    kb = InlineKeyboardBuilder()
    for key, emoji, _name, short in CATEGORIES:
        kb.button(text=f"{emoji} {short}", callback_data=f"{prefix}:{key}")
    kb.adjust(2)
    if with_cancel:
        kb.row(*cancel_row())
    return kb.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[cancel_row()])


def skip_note_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Izohsiz saqlash", callback_data="skip_note")],
        cancel_row(),
    ])


def after_save_kb(expense_id: int, has_note: bool = True) -> InlineKeyboardMarkup:
    """Saqlangandan keyingi tugmalar. Izoh yozilmagan bo'lsa, '📝 Izoh qo'shish' tugmasi ham chiqadi."""
    rows = []
    if not has_note:
        rows.append([InlineKeyboardButton(text="📝 Izoh qo'shish", callback_data=f"enote:{expense_id}")])
    rows.append([InlineKeyboardButton(text="✏️ Tahrirlash / 🗑 O'chirish", callback_data=f"view:{expense_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def expense_actions_kb(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 Summa", callback_data=f"eamt:{expense_id}"),
            InlineKeyboardButton(text="🏷 Kategoriya", callback_data=f"ecat:{expense_id}"),
        ],
        [
            InlineKeyboardButton(text="📝 Izoh", callback_data=f"enote:{expense_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del:{expense_id}"),
        ],
        [InlineKeyboardButton(text="📋 Oxirgi 10 ta harajat", callback_data="list_last")],
    ])


def confirm_delete_kb(expense_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"delok:{expense_id}"),
        InlineKeyboardButton(text="↩️ Yo'q", callback_data=f"view:{expense_id}"),
    ]])


def limit_kb(has_limit: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="✏️ Limitni belgilash / o'zgartirish", callback_data="limit:set")]]
    if has_limit:
        rows.append([InlineKeyboardButton(text="🗑 Limitni olib tashlash", callback_data="limit:clear")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def export_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📗 Shu oy (Excel)", callback_data="exp:xlsx:month"),
            InlineKeyboardButton(text="📄 Shu oy (CSV)", callback_data="exp:csv:month"),
        ],
        [
            InlineKeyboardButton(text="📗 Hammasi (Excel)", callback_data="exp:xlsx:all"),
            InlineKeyboardButton(text="📄 Hammasi (CSV)", callback_data="exp:csv:all"),
        ],
        cancel_row(),
    ])


def add_expense_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Harajat qo'shish", callback_data="add")]
    ])


def short_title(key: str) -> str:
    emoji, name = CAT_BY_KEY.get(key, ("📦", "Boshqa"))
    return f"{emoji} {name}"
