"""Oilaviy harajatlar boti - ishga tushirish fayli."""
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from backup import backup_loop
from config import BASE_DIR, Settings, load_settings
from database import Database
from handlers import admin, expense, export, family, feedback, limit, manage, quick, reports, start
from middlewares import AccessMiddleware
from scheduler import reminder_loop
from status import alert_error, notify_admins, set_bot, set_settings, status_loop
from uptime import begin_run, end_run, heartbeat_loop, ping_loop, startup_text
from utils import now_local

logger = logging.getLogger("bot")

COMMANDS = [
    BotCommand(command="start", description="Boshlash va asosiy menyu"),
    BotCommand(command="qosh", description="Harajat qo'shish"),
    BotCommand(command="bugun", description="Bugungi hisobot"),
    BotCommand(command="hafta", description="Haftalik hisobot"),
    BotCommand(command="oy", description="Oylik hisobot"),
    BotCommand(command="kategoriya", description="Kategoriya bo'yicha hisobot"),
    BotCommand(command="statistika", description="Statistika"),
    BotCommand(command="oxirgi", description="Oxirgi harajatni tahrirlash/o'chirish"),
    BotCommand(command="limit", description="Oylik limit"),
    BotCommand(command="eksport", description="Excel / CSV eksport"),
    BotCommand(command="oila", description="Oila va obuna"),
    BotCommand(command="fikr", description="Fikr yoki taklif yuborish"),
    BotCommand(command="bekor", description="Joriy amalni bekor qilish"),
    BotCommand(command="yordam", description="Yordam"),
]


def setup_logging() -> None:
    """Loglar: konsolga va logs/bot.log fayliga (xatolar tarixi saqlanadi)."""
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    file_handler = RotatingFileHandler(
        log_dir / "bot.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [file_handler, console]


async def on_error(event: ErrorEvent) -> bool:
    """Handlerlardagi har qanday xato logga yoziladi, bot esa ishlashda davom etadi."""
    logger.error("Handlerda xatolik: %r", event.exception, exc_info=event.exception)
    update = event.update
    try:
        await alert_error(f"{type(event.exception).__name__}: {event.exception}")
    except Exception:
        logger.exception("Admin'ga xatolik xabarini yuborib bo'lmadi")
    try:
        if update.message:
            await update.message.answer("⚠️ Kutilmagan xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        elif update.callback_query:
            await update.callback_query.answer("⚠️ Xatolik yuz berdi, qayta urinib ko'ring.", show_alert=True)
    except Exception:
        logger.exception("Xatolik haqida foydalanuvchiga xabar berib bo'lmadi")
    return True


def build_dispatcher(db: Database, settings: Settings) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage(), db=db, settings=settings)

    access = AccessMiddleware(db, settings.admin_ids, settings.contact_text)
    dp.message.outer_middleware(access)
    dp.callback_query.outer_middleware(access)

    dp.errors.register(on_error)

    # Tartib muhim: umumiy matn handleri (tezkor kiritish) eng oxirida
    dp.include_routers(
        start.router,
        family.router,
        admin.router,
        feedback.router,
        expense.router,
        manage.router,
        limit.router,
        reports.router,
        export.router,
        quick.router,
    )
    return dp


async def main() -> None:
    setup_logging()
    settings = load_settings()

    db = Database(settings.db_path)
    await db.init()
    # Eski bitta oilali baza bo'lsa, uni "Asosiy oila"ga ko'chiradi. Yangi bazada hech narsa qilmaydi.
    await db.migrate_legacy(settings.allowed_users, now_local().strftime("%Y-%m-%d %H:%M:%S"))

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher(db, settings)

    set_bot(bot)
    set_settings(settings)
    tasks: list = []
    stop_reason = ""
    run_started = False
    try:
        me = await bot.get_me()
        logger.info("Bot ishga tushdi: @%s | admin: %d ta | eski a'zolar: %d ta",
                    me.username, len(settings.admin_ids), len(settings.allowed_users))
        await bot.set_my_commands(COMMANDS)

        # Oldingi ish qanday tugagan: tartibli yoki kutilmaganda (server o'chgan)
        info = await begin_run(db)
        run_started = True

        tasks.append(asyncio.create_task(reminder_loop(bot, db, settings.reminder_times)))
        tasks.append(asyncio.create_task(heartbeat_loop(db)))
        tasks.append(asyncio.create_task(backup_loop(settings.db_path, settings.backup_keep)))
        if settings.heartbeat_url:
            tasks.append(asyncio.create_task(ping_loop(settings.heartbeat_url)))
        if settings.status_interval > 0:
            tasks.append(asyncio.create_task(status_loop(bot, db, settings)))
        await notify_admins(bot, settings, startup_text(info, me.username))
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        stop_reason = f"\n⚠️ Sabab: xatolik — {type(exc).__name__}: {exc}"[:500]
        run_started = False  # kutilmaganda to'xtadi: keyingi ishga tushishda shunday xabar beriladi
        raise
    finally:
        for task in tasks:
            task.cancel()
        try:
            await notify_admins(bot, settings, "🔴 <b>Bot to'xtadi</b>" + stop_reason)
        except Exception:
            pass
        if run_started:
            try:
                await end_run(db)  # tartibli to'xtash belgisi
            except Exception:
                logger.exception("To'xtash belgisini yozib bo'lmadi")
        await bot.session.close()
        await db.close()
        logger.info("Bot to'xtatildi")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)  # Ctrl+C: run.bat qayta ishga tushirmasligi uchun maxsus kod
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(exc)  # sozlash xatosi (BOT_TOKEN va h.k.)
            sys.exit(1)
