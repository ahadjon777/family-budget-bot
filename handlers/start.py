"""/start, yordam, menyu va bekor qilish."""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Settings
from database import Database
from keyboards import BTN_HELP, main_menu, reg_kb
from status import notify_admins
from utils import user_label

router = Router()
_announced: set = set()  # admin'ga allaqachon xabar berilgan yangi foydalanuvchilar

WELCOME_NEW = (
    "👋 Assalomu alaykum, <b>{name}</b>!\n\n"
    "Men oilaviy kunlik harajatlar hisobini yurituvchi botman.\n\n"
    "Davom etish uchun:\n"
    "✨ <b>Yangi hisob ochish</b> — siz oila egasi bo'lasiz\n"
    "🔑 <b>Taklif kodi bilan qo'shilish</b> — oila egasidan kod olgan bo'lsangiz"
)

WELCOME_MEMBER = (
    "👋 Assalomu alaykum, <b>{name}</b>!\n\n"
    "⚡ <b>Tezkor kiritish:</b> shunchaki yozing —\n"
    "<code>ovqat 45000 tushlik</code>\n"
    "<code>taksi 15k</code>\n\n"
    "Yoki pastdagi menyudan <b>➕ Harajat qo'shish</b> tugmasini bosing."
)

HELP_TEXT = (
    "ℹ️ <b>Yordam</b>\n\n"
    "<b>Tezkor kiritish</b> (kategoriya + summa + izoh):\n"
    "<code>ovqat 45000 tushlik</code>\n"
    "<code>benzin 200 000</code>\n"
    "<code>kredit 1.5 mln</code>\n"
    "Summa: <code>45000</code>, <code>45 000</code>, <code>45k</code>, <code>45 ming</code>, <code>1.2 mln</code>.\n\n"
    "<b>Buyruqlar:</b>\n"
    "/qosh — harajat qo'shish\n"
    "/bugun — bugungi hisobot\n"
    "/hafta — haftalik hisobot\n"
    "/oy — oylik hisobot\n"
    "/kategoriya — kategoriya bo'yicha hisobot\n"
    "/statistika — statistika\n"
    "/oxirgi — oxirgi harajatni tahrirlash / o'chirish\n"
    "/limit — oylik limit (masalan: <code>/limit 5000000</code>)\n"
    "/fikr — botga fikr yoki taklif yuborish\n"
    "/eksport — Excel yoki CSV fayl\n"
    "/oila — oila a'zolari va obuna holati\n"
    "/bekor — joriy amalni bekor qilish\n\n"
    "📝 Izoh: harajatdan keyingi <b>📝 Izoh qo'shish</b> tugmasi orqali yoki tezkor kiritishda matn bilan.\n\n"
    "🔔 Kuniga {count} marta ({times}, Toshkent vaqti) eslatma yuboriladi.\n"
    "👨‍👩‍👧 Oila a'zolari bitta umumiy hisobni yuritadi."
)


def help_text(settings: Settings) -> str:
    times = ", ".join(f"{h:02d}:{m:02d}" for h, m in settings.reminder_times)
    return HELP_TEXT.format(count=len(settings.reminder_times), times=times)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database, settings: Settings) -> None:
    await state.clear()
    user = message.from_user
    name = user.first_name or "do'stim"
    member = await db.get_user(user.id)
    if member is None:
        # Bot egasiga: kim botni birinchi marta ochdi (bir foydalanuvchi uchun bir marta)
        if user.id not in _announced and user.id not in settings.admin_ids:
            _announced.add(user.id)
            await notify_admins(
                message.bot, settings,
                "👤 <b>Yangi foydalanuvchi botni ochdi</b>\n" + user_label(user) +
                "\nHali ro'yxatdan o'tmagan.")
        await message.answer(WELCOME_NEW.format(name=name), reply_markup=reg_kb(settings.trial_days))
        return
    await db.update_user_name(user.id, user.full_name, user.username or "")
    await message.answer(WELCOME_MEMBER.format(name=name), reply_markup=main_menu())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu())


@router.message(Command("yordam", "help"))
@router.message(F.text == BTN_HELP)
async def cmd_help(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    await message.answer(help_text(settings), reply_markup=main_menu())


@router.message(Command("bekor", "cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Bekor qilinadigan amal yo'q.", reply_markup=main_menu())
        return
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=main_menu())


@router.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer("Bekor qilindi")
    try:
        await call.message.edit_text("❌ Bekor qilindi.")
    except Exception:
        await call.message.answer("❌ Bekor qilindi.", reply_markup=main_menu())
