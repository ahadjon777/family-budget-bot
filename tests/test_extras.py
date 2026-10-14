"""Eslatma vaqtlari, server holati (uptime), zaxira nusxa va sozlamalar testlari."""
import asyncio
import sqlite3
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

import backup
import uptime
from config import _heartbeat_url, _reminder_times
from database import Database
from scheduler import next_reminder
from services import reminder_slot
from utils import TZ, fmt_duration

TIMES = ((9, 0), (15, 0), (21, 0))


def _at(h, m=0):
    return datetime(2026, 10, 14, h, m, 0, tzinfo=TZ)


def test_next_reminder_picks_closest_slot():
    assert next_reminder(_at(6, 25), TIMES) == _at(9, 0)
    assert next_reminder(_at(9, 0), TIMES) == _at(15, 0)       # aynan vaqtida: keyingisi
    assert next_reminder(_at(14, 59), TIMES) == _at(15, 0)
    assert next_reminder(_at(21, 30), TIMES) == _at(9, 0) + timedelta(days=1)


def test_reminder_slots_differ_by_time_of_day():
    assert "Ertalabki" in reminder_slot(9)[0]
    assert "Kunduzgi" in reminder_slot(15)[0]
    assert "Kechki" in reminder_slot(21)[0]


def test_reminder_times_config(monkeypatch):
    monkeypatch.delenv("REMINDER_TIMES", raising=False)
    monkeypatch.delenv("REMINDER_TIME", raising=False)
    assert _reminder_times() == TIMES                       # standart: kuniga 3 marta
    monkeypatch.setenv("REMINDER_TIME", "20:30")             # eski sozlama ishlayveradi
    assert _reminder_times() == ((20, 30),)
    monkeypatch.setenv("REMINDER_TIMES", "21:00, 08:15;21:00")
    assert _reminder_times() == ((8, 15), (21, 0))           # tartiblangan, takrorsiz
    monkeypatch.setenv("REMINDER_TIMES", "25:00")
    with pytest.raises(SystemExit):
        _reminder_times()


def test_heartbeat_url_validation(monkeypatch):
    monkeypatch.setenv("HEARTBEAT_URL", "")
    assert _heartbeat_url() == ""
    monkeypatch.setenv("HEARTBEAT_URL", "https://hc-ping.com/abc")
    assert _heartbeat_url() == "https://hc-ping.com/abc"
    monkeypatch.setenv("HEARTBEAT_URL", "hc-ping.com/abc")
    with pytest.raises(SystemExit):
        _heartbeat_url()


def test_fmt_duration():
    assert fmt_duration(45) == "45 soniya"
    assert fmt_duration(4380) == "1 soat 13 daqiqa"
    assert fmt_duration(90000) == "1 kun 1 soat"


@pytest_asyncio.fixture
async def db(tmp_path):
    database = Database(tmp_path / "u.db")
    await database.init()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_uptime_first_run_then_clean_stop_then_crash(db):
    info = await uptime.begin_run(db)
    assert info["first"] is True
    assert "birinchi marta" in uptime.startup_text(info, "bot")

    # Tartibli to'xtash
    await uptime.end_run(db)
    info = await uptime.begin_run(db)
    assert info["clean"] is True and not info["first"]
    text = uptime.startup_text(info, "bot")
    assert "tartibli" in text and "O'chiq turdi" in text

    # Kutilmaganda to'xtash (end_run chaqirilmagan): server o'chgan deb xabar beriladi
    await db.global_set(uptime.KEY_LAST, (datetime.now(TZ) - timedelta(hours=3, minutes=12)).strftime(uptime.FMT))
    info = await uptime.begin_run(db)
    assert info["clean"] is False
    text = uptime.startup_text(info, "bot")
    assert "Server qayta ishga tushdi" in text and "kutilmaganda" in text
    assert "3 soat 1" in text  # ~3 soat 12 daqiqa


@pytest.mark.asyncio
async def test_heartbeat_loop_updates_timestamp(db):
    await db.global_set(uptime.KEY_LAST, "2000-01-01 00:00:00")
    task = asyncio.create_task(uptime.heartbeat_loop(db, interval=1))
    await asyncio.sleep(0.2)
    task.cancel()
    assert (await db.global_get(uptime.KEY_LAST)) > "2020-01-01 00:00:00"


@pytest.mark.asyncio
async def test_ping_loop_hits_url_and_survives_errors():
    from aiohttp import web
    from aiohttp.test_utils import TestServer

    hits = []

    async def handler(request):
        hits.append(1)
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/ping", handler)
    server = TestServer(app)
    await server.start_server()
    try:
        task = asyncio.create_task(uptime.ping_loop(str(server.make_url("/ping")), interval=1))
        await asyncio.sleep(0.4)
        task.cancel()
        assert len(hits) >= 1
    finally:
        await server.close()

    # Manzil ishlamasa ham tsikl yiqilmaydi
    task = asyncio.create_task(uptime.ping_loop("http://127.0.0.1:9/x", interval=1))
    await asyncio.sleep(0.3)
    assert not task.done()
    task.cancel()


@pytest.mark.asyncio
async def test_backup_creates_valid_copy_and_rotates(tmp_path, db):
    await db.create_family("Test", None, "2026-10-01 00:00:00")
    db_path = tmp_path / "u.db"
    first = None
    for i in range(5):
        day = datetime(2026, 10, 10 + i).date()
        path = await backup.backup_once(db_path, keep=3, day=day)
        first = first or path
    files = sorted(p.name for p in (tmp_path / "backups").glob("budget_*.db"))
    assert files == ["budget_2026-10-12.db", "budget_2026-10-13.db", "budget_2026-10-14.db"]

    conn = sqlite3.connect(tmp_path / "backups" / files[-1])
    try:
        assert conn.execute("SELECT COUNT(*) FROM families").fetchone()[0] == 1
    finally:
        conn.close()
    assert not list((tmp_path / "backups").glob("*.tmp"))
    assert await backup.backup_once(db_path, keep=0) is None  # o'chirilgan
