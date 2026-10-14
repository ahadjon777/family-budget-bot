"""To'liq oqim testi: soxta Telegram sessiyasi orqali dispatcher'ga haqiqiy update'lar beriladi."""
import io
from datetime import datetime

import pytest
import pytest_asyncio
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User

import main as app
from config import Settings
from database import Database

USER_OK = 111
USER_BAD = 999


class FakeSession(BaseSession):
    """Telegram'ga bormaydi, barcha chaqiruvlarni yozib boradi."""

    def __init__(self):
        super().__init__()
        self.calls = []
        self._mid = 1000

    async def close(self):
        pass

    async def stream_content(self, *a, **kw):
        yield b""

    async def make_request(self, bot, method: TelegramMethod, timeout=None):
        self.calls.append(method)
        name = type(method).__name__
        if name in ("SendMessage", "EditMessageText", "SendDocument"):
            self._mid += 1
            return Message(
                message_id=self._mid, date=datetime.now(),
                chat=Chat(id=getattr(method, "chat_id", USER_OK), type="private"),
                text=getattr(method, "text", None),
            )
        return True

    def texts(self):
        out = []
        for c in self.calls:
            t = getattr(c, "text", None) or getattr(c, "caption", None)
            if t:
                out.append(t)
        return out


def make_settings(db_path, **kw):
    base = dict(
        bot_token="123456:TEST", allowed_users=frozenset({USER_OK}),
        admin_ids=frozenset({USER_OK}), db_path=db_path,
        reminder_times=((9, 0), (15, 0), (21, 0)), trial_days=7, max_members=6,
        contact_text="Aloqa: @admin", price_text="",
    )
    base.update(kw)
    return Settings(**base)


@pytest_asyncio.fixture
async def env(tmp_path):
    db = Database(tmp_path / "t.db")
    await db.init()
    settings = make_settings(tmp_path / "t.db")
    # Routerlar modul darajasida yaratilgan: har bir test uchun avvalgi dispatcher'dan ajratamiz
    for mod in (app.start, app.family, app.admin, app.feedback, app.expense, app.manage,
                app.limit, app.reports, app.export, app.quick):
        mod.router._parent_router = None
    # Test oila: USER_OK uning egasi
    fid, _code = await db.create_family("Test oila", None, "2026-10-01 00:00:00")
    await db.add_user(USER_OK, fid, "Ali", "ali", True, "2026-10-01 00:00:00")
    dp = app.build_dispatcher(db, settings)
    session = FakeSession()
    bot = Bot("123456:TEST", session=session)
    ctx = {"db": db, "dp": dp, "bot": bot, "session": session, "uid": 1, "mid": 1,
           "fid": fid, "settings": settings}
    yield ctx
    await db.close()


async def say(env, text, user=USER_OK):
    env["uid"] += 1
    env["mid"] += 1
    msg = Message(
        message_id=env["mid"], date=datetime.now(),
        chat=Chat(id=user, type="private"),
        from_user=User(id=user, is_bot=False, first_name="Ali"),
        text=text,
    )
    env["session"].calls.clear()
    await env["dp"].feed_update(env["bot"], Update(update_id=env["uid"], message=msg))
    return env["session"].texts()


async def press(env, data, user=USER_OK):
    env["uid"] += 1
    msg = Message(
        message_id=env["mid"], date=datetime.now(),
        chat=Chat(id=user, type="private"),
        from_user=User(id=987, is_bot=True, first_name="Bot"),
        text="x",
    )
    cb = CallbackQuery(
        id=str(env["uid"]), chat_instance="ci", data=data, message=msg,
        from_user=User(id=user, is_bot=False, first_name="Ali"),
    )
    env["session"].calls.clear()
    await env["dp"].feed_update(env["bot"], Update(update_id=env["uid"], callback_query=cb))
    return env["session"].texts()


@pytest.mark.asyncio
async def test_unauthorized_user_blocked(env):
    texts = await say(env, "ovqat 45000", user=USER_BAD)
    assert any("/start" in t for t in texts)
    assert await env["db"].last_expense(env["fid"]) is None
    cb = await press(env, "cat:food", user=USER_BAD)
    assert await env["db"].last_expense(env["fid"]) is None


@pytest.mark.asyncio
async def test_start_and_help(env):
    assert any("Assalomu alaykum" in t for t in await say(env, "/start"))
    assert any("Tezkor kiritish" in t for t in await say(env, "/yordam"))


@pytest.mark.asyncio
async def test_quick_entry_and_reports(env):
    texts = await say(env, "ovqat 45000 tushlik")
    assert any("Saqlandi" in t and "45 000 so'm" in t for t in texts)
    await say(env, "benzin 200 000")
    row = await env["db"].last_expense(env["fid"])
    assert row["category"] == "fuel" and row["amount"] == 200000

    today = "\n".join(await say(env, "📅 Bugun"))
    assert "Mashina yoqilg'isi" in today and "245 000 so'm" in today

    for cmd in ("/hafta", "/oy", "/statistika"):
        out = "\n".join(await say(env, cmd))
        assert "245 000" in out, cmd


@pytest.mark.asyncio
async def test_quick_without_category_asks_buttons(env):
    texts = await say(env, "45000 mehmon")
    assert any("Kategoriyani tanlang" in t for t in texts)
    assert await env["db"].last_expense(env["fid"]) is None
    texts = await press(env, "qcat:gifts")
    row = await env["db"].last_expense(env["fid"])
    assert row["category"] == "gifts" and row["amount"] == 45000 and row["note"] == "mehmon"


@pytest.mark.asyncio
async def test_guided_add_flow(env):
    await say(env, "➕ Harajat qo'shish")
    await press(env, "cat:health")
    texts = await say(env, "abc")
    assert any("tushunmadim" in t for t in texts)
    texts = await say(env, "85k")
    assert any("Izoh" in t for t in texts)
    texts = await say(env, "dori-darmon")
    assert any("Saqlandi" in t for t in texts)
    row = await env["db"].last_expense(env["fid"])
    assert (row["category"], row["amount"], row["note"]) == ("health", 85000, "dori-darmon")


@pytest.mark.asyncio
async def test_guided_flow_skip_note_and_menu_button_in_state(env):
    await say(env, "/qosh")
    await press(env, "cat:clothes")
    await say(env, "150 000")
    await press(env, "skip_note")
    row = await env["db"].last_expense(env["fid"])
    assert row["category"] == "clothes" and row["note"] == ""

    # Holat ichida menyu tugmasi bosilsa, holat tozalanadi va hisobot chiqadi
    await say(env, "/qosh")
    await press(env, "cat:food")
    out = "\n".join(await say(env, "📅 Bugun"))
    assert "Bugungi hisobot" in out
    texts = await say(env, "ovqat 10000")
    assert any("Saqlandi" in t for t in texts)


@pytest.mark.asyncio
async def test_edit_and_delete_last(env):
    await say(env, "taksi 15000")
    row = await env["db"].last_expense(env["fid"])
    eid = row["id"]

    assert any("Harajat" in t for t in await say(env, "/oxirgi"))

    await press(env, f"eamt:{eid}")
    texts = await say(env, "20k")
    assert any("Summa yangilandi" in t for t in texts)
    assert (await env["db"].get_expense(env["fid"], eid))["amount"] == 20000

    await press(env, f"setcat:{eid}:food")
    assert (await env["db"].get_expense(env["fid"], eid))["category"] == "food"

    await press(env, f"enote:{eid}")
    await say(env, "peshin")
    assert (await env["db"].get_expense(env["fid"], eid))["note"] == "peshin"

    await press(env, f"del:{eid}")
    assert await env["db"].get_expense(env["fid"], eid) is not None  # hali tasdiqlanmagan
    await press(env, f"delok:{eid}")
    assert await env["db"].get_expense(env["fid"], eid) is None


@pytest.mark.asyncio
async def test_limit_warnings(env):
    texts = await say(env, "/limit 1 000 000")
    assert any("limit belgilandi" in t.lower() for t in texts)

    out = await say(env, "ovqat 500000")
    assert not any("yaqinlashdingiz" in t or "oshib ketdi" in t for t in out)

    out = await say(env, "ovqat 350000")  # 850 000 = 85%
    assert any("yaqinlashdingiz" in t for t in out)

    out = await say(env, "ovqat 10000")  # 860 000 - qayta ogohlantirmaydi
    assert not any("yaqinlashdingiz" in t for t in out)

    out = await say(env, "ovqat 200000")  # 1 060 000 > limit
    assert any("oshib ketdi" in t for t in out)

    out = await say(env, "ovqat 1000")  # qayta ogohlantirmaydi
    assert not any("oshib ketdi" in t for t in out)

    status = "\n".join(await say(env, "💰 Limit"))
    assert "oshdi" in status


@pytest.mark.asyncio
async def test_category_report_and_export(env):
    await say(env, "taksi 15000")
    await say(env, "taksi 25000 ish")
    await say(env, "ovqat 10000")

    await say(env, "/kategoriya")
    out = "\n".join(await press(env, "rcat:transport"))
    assert "40 000 so'm" in out

    await press(env, "exp:xlsx:month")
    docs = [c for c in env["session"].calls if type(c).__name__ == "SendDocument"]
    assert docs and docs[0].document.filename.endswith(".xlsx")
    await press(env, "exp:csv:all")
    docs = [c for c in env["session"].calls if type(c).__name__ == "SendDocument"]
    assert docs and docs[0].document.filename.endswith(".csv")


@pytest.mark.asyncio
async def test_unknown_text_and_stale_button(env):
    texts = await say(env, "salom qalaysan")
    assert any("Tushunmadim" in t for t in texts)
    await press(env, "skip_note")  # holat yo'q - xato bermasligi kerak
    assert await env["db"].last_expense(env["fid"]) is None


@pytest.mark.asyncio
async def test_error_handler_keeps_bot_alive(env, monkeypatch):
    import handlers.quick as quick_mod

    async def boom(*a, **kw):
        raise RuntimeError("sinov xatosi")

    monkeypatch.setattr(quick_mod, "save_and_reply", boom)
    texts = await say(env, "ovqat 45000")
    assert any("xatolik" in t.lower() for t in texts)
    monkeypatch.undo()
    texts = await say(env, "ovqat 45000")
    assert any("Saqlandi" in t for t in texts)


@pytest.mark.asyncio
async def test_reminder_sent_to_all_even_if_one_fails(env):
    import scheduler
    from aiogram.exceptions import TelegramForbiddenError

    await env["db"].add_user(5, env["fid"], "Bloklagan", "", False, "2026-10-01 00:00:00")
    session = env["session"]
    original = session.make_request

    async def flaky(bot, method, timeout=None):
        if getattr(method, "chat_id", None) == 5:
            raise TelegramForbiddenError(method=method, message="Forbidden: bot was blocked")
        return await original(bot, method, timeout)

    session.make_request = flaky
    session.calls.clear()
    await scheduler.send_reminders(env["bot"], env["db"])
    sent = [c for c in session.calls if type(c).__name__ == "SendMessage"]
    assert any(c.chat_id == USER_OK and "Kechki eslatma" in c.text for c in sent)


# ---------------------------------------------------------------- ko'p oilali
@pytest.mark.asyncio
async def test_new_family_registration_and_isolation(env):
    USER_NEW = 222
    texts = await say(env, "/start", user=USER_NEW)
    assert any("Yangi hisob ochish" in t or "Assalomu" in t for t in texts)

    await press(env, "reg:new", user=USER_NEW)
    member = await env["db"].get_user(USER_NEW)
    assert member is not None and member["family_id"] != env["fid"]

    await say(env, "ovqat 30000 nonushta", user=USER_NEW)
    # Birinchi oilaning ma'lumoti yangi oilada ko'rinmasligi kerak
    await say(env, "taksi 5000", user=USER_OK)
    out = "\n".join(await say(env, "📅 Bugun", user=USER_NEW))
    assert "30 000" in out and "5 000" not in out.replace("30 000", "")


@pytest.mark.asyncio
async def test_join_by_invite_code(env):
    USER_JOIN = 333
    code_row = await env["db"].get_family(env["fid"])
    code = code_row["invite_code"]
    await say(env, "/start", user=USER_JOIN)
    await press(env, "reg:join", user=USER_JOIN)
    texts = await say(env, "нотўғри", user=USER_JOIN)
    assert any("topilmadi" in t for t in texts)
    texts = await say(env, code.lower(), user=USER_JOIN)
    assert any("qo'shildingiz" in t for t in texts)
    member = await env["db"].get_user(USER_JOIN)
    assert member["family_id"] == env["fid"] and member["is_owner"] == 0

    await say(env, "ovqat 12000", user=USER_JOIN)
    row = await env["db"].last_expense(env["fid"])
    assert row["user_id"] == USER_JOIN and row["amount"] == 12000


@pytest.mark.asyncio
async def test_expired_family_is_blocked_but_info_allowed(env):
    await env["db"].set_family_expiry(env["fid"], "2000-01-01")
    texts = await say(env, "ovqat 1000")
    assert any("muddati tugagan" in t and "Aloqa" in t for t in texts)
    assert await env["db"].last_expense(env["fid"]) is None
    texts = await say(env, "/oila")
    assert any("tugagan" in t for t in texts)


@pytest.mark.asyncio
async def test_admin_extend_and_list(env):
    await env["db"].set_family_expiry(env["fid"], "2000-01-01")
    texts = await say(env, "/uzaytir {} 30".format(env["fid"]))
    assert any("uzaytirildi" in t for t in texts)
    row = await env["db"].get_family(env["fid"])
    assert row["expires_at"] > "2026-10-01"
    texts = await say(env, "ovqat 1000")
    assert any("Saqlandi" in t for t in texts)
    texts = await say(env, "/oilalar")
    assert any("Test oila" in t for t in texts)


@pytest.mark.asyncio
async def test_non_admin_cannot_use_admin_commands(env):
    USER_X = 444
    await env["db"].add_user(USER_X, env["fid"], "Oddiy", "", False, "2026-10-01 00:00:00")
    texts = await say(env, "/oilalar", user=USER_X)
    assert not any("Oilalar" in t for t in texts)
    await say(env, "/yopish {}".format(env["fid"]), user=USER_X)
    assert (await env["db"].get_family(env["fid"]))["expires_at"] is None


@pytest.mark.asyncio
async def test_holat_for_admin_only(env):
    texts = await say(env, "/holat")
    assert any("Bot holati" in t and "Foydalanuvchilar" in t and "Oilalar" in t for t in texts)
    USER_X = 444
    await env["db"].add_user(USER_X, env["fid"], "Oddiy", "", False, "2026-10-01 00:00:00")
    texts = await say(env, "/holat", user=USER_X)
    assert not any("Bot holati" in t for t in texts)


@pytest.mark.asyncio
async def test_status_text_counts_users_and_families(env):
    from status import status_text
    text = await status_text(env["db"], env["settings"])
    assert "Foydalanuvchilar: <b>1</b>" in text
    assert "Oilalar: <b>1</b>" in text


def test_status_interval_validation(monkeypatch):
    from config import _status_interval
    monkeypatch.setenv("STATUS_INTERVAL", "0")
    assert _status_interval() == 0
    monkeypatch.setenv("STATUS_INTERVAL", "60")
    assert _status_interval() == 60
    monkeypatch.setenv("STATUS_INTERVAL", "3")
    with pytest.raises(SystemExit):
        _status_interval()


@pytest.mark.asyncio
async def test_feedback_direct_and_admin_review(env):
    texts = await say(env, "/fikr Kategoriya nomlarini o'zgartiring")
    assert any("qabul qilindi" in t for t in texts)
    texts = await say(env, "/fikr")
    assert any("Fikr va takliflar" in t for t in texts)
    texts = await say(env, "Eksport tezroq bo'lsin")
    assert any("qabul qilindi" in t for t in texts)
    rows = await env["db"].list_feedback()
    assert len(rows) == 2 and rows[0]["text"] == "Eksport tezroq bo'lsin"
    assert all(r["family_id"] == env["fid"] for r in rows)
    texts = await say(env, "/fikrlar")
    assert any("Kategoriya nomlarini" in t for t in texts)
    texts = await say(env, "/fikrok {}".format(rows[1]["id"]))
    assert any("ko'rib chiqildi" in t for t in texts)
    assert len(await env["db"].list_feedback(status="new")) == 1


@pytest.mark.asyncio
async def test_feedback_not_visible_to_non_admin(env):
    USER_X = 444
    await env["db"].add_user(USER_X, env["fid"], "Oddiy", "", False, "2026-10-01 00:00:00")
    await say(env, "/fikr Test", user=USER_X)
    texts = await say(env, "/fikrlar", user=USER_X)
    assert not any("Yangi fikrlar" in t or "Fikr" in t and "#" in t for t in texts)
    assert len(await env["db"].list_feedback()) == 1


# ---------------------------------------------------------------- izoh, hisobot, admin xabarlari
def _sent(env):
    return [c for c in env["session"].calls if type(c).__name__ == "SendMessage"]


@pytest.mark.asyncio
async def test_quick_entry_without_note_offers_note_button(env):
    await say(env, "ovqat 45000")
    markup = _sent(env)[-1].reply_markup
    buttons = [b.callback_data for row in markup.inline_keyboard for b in row]
    row = await env["db"].last_expense(env["fid"])
    assert f"enote:{row['id']}" in buttons  # "📝 Izoh qo'shish"

    # Izoh bilan kiritilsa, qo'shimcha tugma kerak emas
    await say(env, "ovqat 30000 tushlik")
    markup = _sent(env)[-1].reply_markup
    buttons = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert not any(b.startswith("enote:") for b in buttons)

    # Tugma orqali izoh qo'shish
    await press(env, f"enote:{row['id']}")
    await say(env, "kechki ovqat")
    assert (await env["db"].get_expense(env["fid"], row["id"]))["note"] == "kechki ovqat"


@pytest.mark.asyncio
async def test_today_report_lists_notes_and_yesterday(env):
    await say(env, "ovqat 45000 tushlik")
    await say(env, "taksi 15000")
    out = "\n".join(await say(env, "📅 Bugun"))
    assert "Bugungi yozuvlar" in out and "tushlik" in out
    assert "Kecha: harajat kiritilmagan" in out

    # Kechagi yozuv "Bugun" da emas, lekin "Kecha" qatorida ko'rinadi
    from datetime import timedelta
    from utils import now_local
    yesterday = now_local().date() - timedelta(days=1)
    await env["db"].add_expense(env["fid"], USER_OK, "Ali", "food", 70000, "", yesterday,
                                f"{yesterday} 12:00:00")
    out = "\n".join(await say(env, "/bugun"))
    assert "Kecha: 70 000 so'm (1 ta yozuv)" in out


@pytest.mark.asyncio
async def test_admin_notified_about_new_user_family_and_member(env):
    NEW, JOINER = 222, 333
    app.start._announced.clear()  # boshqa testlar bu ID larni allaqachon ishlatgan bo'lishi mumkin
    await say(env, "/start", user=NEW)
    sent = [c for c in env["session"].calls if getattr(c, "chat_id", None) == USER_OK]
    assert any("Yangi foydalanuvchi" in c.text and "222" in c.text for c in sent)

    # Takroriy /start admin'ni bezovta qilmaydi
    await say(env, "/start", user=NEW)
    assert not any("Yangi foydalanuvchi" in (getattr(c, "text", "") or "") for c in env["session"].calls)

    await press(env, "reg:new", user=NEW)
    sent = [c for c in env["session"].calls if getattr(c, "chat_id", None) == USER_OK]
    assert any("Yangi oila" in c.text and "222" in c.text for c in sent)

    code = (await env["db"].get_family(env["fid"]))["invite_code"]
    await say(env, "/start", user=JOINER)
    await press(env, "reg:join", user=JOINER)
    await say(env, code, user=JOINER)
    sent = [c for c in env["session"].calls if getattr(c, "chat_id", None) == USER_OK]
    assert any("yangi a'zo" in c.text and "333" in c.text for c in sent)


@pytest.mark.asyncio
async def test_users_command_admin_only_and_tracks_activity(env):
    await say(env, "ovqat 1000")
    texts = "\n".join(await say(env, "/foydalanuvchilar"))
    assert "Foydalanuvchilar" in texts and "Ali" in texts and "oxirgi faollik" in texts
    row = await env["db"].get_user(USER_OK)
    assert row["last_active"]  # middleware yozib bordi

    USER_X = 444
    await env["db"].add_user(USER_X, env["fid"], "Oddiy", "", False, "2026-10-01 00:00:00")
    texts = await say(env, "/foydalanuvchilar", user=USER_X)
    assert not any("Foydalanuvchilar" in t for t in texts)


@pytest.mark.asyncio
async def test_help_mentions_three_reminders(env):
    out = "\n".join(await say(env, "/yordam"))
    assert "3 marta" in out and "09:00" in out and "21:00" in out
