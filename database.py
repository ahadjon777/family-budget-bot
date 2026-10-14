"""SQLite (aiosqlite): oilalar, foydalanuvchilar, harajatlar va sozlamalar.

Har bir oila alohida hisob: barcha so'rovlar family_id bo'yicha chegaralanadi,
shuning uchun bir oila boshqa oilaning ma'lumotini ko'ra olmaydi.
"""
import secrets
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

import aiosqlite

# Taklif kodi belgilari: adashtiriladigan 0/O, 1/I harflarsiz
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

SCHEMA = """
CREATE TABLE IF NOT EXISTS families (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL DEFAULT '',
    invite_code TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL,
    expires_at  TEXT              -- obuna tugash sanasi (YYYY-MM-DD); NULL = cheksiz
);

CREATE TABLE IF NOT EXISTS users (
    user_id   INTEGER PRIMARY KEY,
    family_id INTEGER NOT NULL REFERENCES families (id),
    name      TEXT    NOT NULL DEFAULT '',
    username  TEXT    NOT NULL DEFAULT '',
    is_owner  INTEGER NOT NULL DEFAULT 0,
    joined_at TEXT    NOT NULL,
    last_active TEXT  NOT NULL DEFAULT ''   -- oxirgi faollik (YYYY-MM-DD HH:MM:SS, Toshkent)
);
CREATE INDEX IF NOT EXISTS idx_users_family ON users (family_id);

CREATE TABLE IF NOT EXISTS family_settings (
    family_id INTEGER NOT NULL,
    key       TEXT    NOT NULL,
    value     TEXT    NOT NULL,
    PRIMARY KEY (family_id, key)
);

CREATE TABLE IF NOT EXISTS expenses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id  INTEGER,
    user_id    INTEGER NOT NULL,
    user_name  TEXT    NOT NULL DEFAULT '',
    category   TEXT    NOT NULL,
    amount     INTEGER NOT NULL CHECK (amount > 0),
    note       TEXT    NOT NULL DEFAULT '',
    spent_on   TEXT    NOT NULL,   -- harajat sanasi (YYYY-MM-DD, Toshkent vaqti)
    created_at TEXT    NOT NULL    -- kiritilgan vaqt (YYYY-MM-DD HH:MM:SS)
);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses (spent_on);

CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    family_id  INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    user_name  TEXT    NOT NULL DEFAULT '',
    text       TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'new',   -- new | done
    created_at TEXT    NOT NULL
);

-- Eski (bitta oilali) versiyadan qolgan umumiy sozlamalar jadvali
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _iso(d) -> str:
    return d.isoformat() if isinstance(d, date) else str(d)


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._conn: Optional[aiosqlite.Connection] = None

    # ---------- ulanish ----------
    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.executescript(SCHEMA)
        await self._migrate()
        await self._conn.commit()

    async def _migrate(self) -> None:
        """Eski bazaga family_id ustunini qo'shadi va kerakli indekslarni yaratadi."""
        cols = [r["name"] for r in await self._fetchall("PRAGMA table_info(expenses)")]
        if "family_id" not in cols:
            await self._conn.execute("ALTER TABLE expenses ADD COLUMN family_id INTEGER")
        user_cols = [r["name"] for r in await self._fetchall("PRAGMA table_info(users)")]
        if "last_active" not in user_cols:
            await self._conn.execute("ALTER TABLE users ADD COLUMN last_active TEXT NOT NULL DEFAULT ''")
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_fam_date ON expenses (family_id, spent_on)")
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_fam_cat ON expenses (family_id, category, spent_on)")

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    # ---------- ichki yordamchilar ----------
    async def _fetchall(self, sql: str, params: tuple = ()) -> list:
        async with self._conn.execute(sql, params) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def _fetchone(self, sql: str, params: tuple = ()) -> Optional[dict]:
        async with self._conn.execute(sql, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def _execute(self, sql: str, params: tuple = ()) -> int:
        cur = await self._conn.execute(sql, params)
        await self._conn.commit()
        rowcount = cur.rowcount
        lastrowid = cur.lastrowid
        await cur.close()
        return lastrowid if sql.lstrip().upper().startswith("INSERT") else rowcount

    # ---------- oilalar ----------
    async def create_family(self, name: str, expires_at: Optional[str], created_at: str):
        """Yangi oila yaratadi. (family_id, taklif_kodi) qaytaradi."""
        for _ in range(30):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            try:
                fid = await self._execute(
                    "INSERT INTO families (name, invite_code, created_at, expires_at) VALUES (?, ?, ?, ?)",
                    (name, code, created_at, expires_at),
                )
                return fid, code
            except sqlite3.IntegrityError:
                continue  # kod to'qnashdi, boshqasini sinaymiz
        raise RuntimeError("Taklif kodini yaratib bo'lmadi")

    async def get_family(self, family_id: int) -> Optional[dict]:
        return await self._fetchone("SELECT * FROM families WHERE id = ?", (family_id,))

    async def get_family_by_code(self, code: str) -> Optional[dict]:
        return await self._fetchone("SELECT * FROM families WHERE invite_code = ?", (code,))

    async def set_family_expiry(self, family_id: int, expires_at: Optional[str]) -> None:
        await self._execute("UPDATE families SET expires_at = ? WHERE id = ?", (expires_at, family_id))

    async def list_families(self, limit: int = 15, offset: int = 0) -> list:
        return await self._fetchall(
            "SELECT f.id, f.name, f.invite_code, f.created_at, f.expires_at, "
            " (SELECT COUNT(*) FROM users u WHERE u.family_id = f.id) AS members, "
            " (SELECT COUNT(*) FROM expenses e WHERE e.family_id = f.id) AS expense_count, "
            " (SELECT u.user_id  FROM users u WHERE u.family_id = f.id ORDER BY u.is_owner DESC, u.joined_at LIMIT 1) AS owner_id, "
            " (SELECT u.name     FROM users u WHERE u.family_id = f.id ORDER BY u.is_owner DESC, u.joined_at LIMIT 1) AS owner_name, "
            " (SELECT u.username FROM users u WHERE u.family_id = f.id ORDER BY u.is_owner DESC, u.joined_at LIMIT 1) AS owner_username "
            "FROM families f ORDER BY f.id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )

    async def count_families(self) -> int:
        return int((await self._fetchone("SELECT COUNT(*) AS c FROM families"))["c"])

    async def stats(self) -> dict:
        families = await self._fetchall("SELECT expires_at FROM families")
        users = await self._fetchone("SELECT COUNT(*) AS c FROM users")
        expenses = await self._fetchone("SELECT COUNT(*) AS c FROM expenses")
        return {
            "expires": [r["expires_at"] for r in families],
            "users": int(users["c"]),
            "expenses": int(expenses["c"]),
        }

    # ---------- foydalanuvchilar ----------
    async def get_user(self, user_id: int) -> Optional[dict]:
        return await self._fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))

    async def add_user(self, user_id: int, family_id: int, name: str, username: str,
                       is_owner: bool, joined_at: str) -> None:
        await self._execute(
            "INSERT INTO users (user_id, family_id, name, username, is_owner, joined_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, family_id, name, username, 1 if is_owner else 0, joined_at),
        )

    async def update_user_name(self, user_id: int, name: str, username: str) -> None:
        await self._execute("UPDATE users SET name = ?, username = ? WHERE user_id = ?",
                            (name, username, user_id))

    async def family_members(self, family_id: int) -> list:
        return await self._fetchall(
            "SELECT * FROM users WHERE family_id = ? ORDER BY is_owner DESC, joined_at, user_id",
            (family_id,),
        )

    async def count_members(self, family_id: int) -> int:
        row = await self._fetchone("SELECT COUNT(*) AS c FROM users WHERE family_id = ?", (family_id,))
        return int(row["c"])

    async def touch_user(self, user_id: int, ts: str) -> None:
        """Foydalanuvchining oxirgi faollik vaqtini yozadi."""
        await self._execute("UPDATE users SET last_active = ? WHERE user_id = ?", (ts, user_id))

    async def count_active_since(self, ts: str) -> int:
        """Berilgan vaqtdan (YYYY-MM-DD HH:MM:SS) beri faol bo'lgan foydalanuvchilar soni."""
        row = await self._fetchone("SELECT COUNT(*) AS c FROM users WHERE last_active >= ?", (ts,))
        return int(row["c"])

    async def list_users(self, limit: int = 20, offset: int = 0) -> list:
        """Foydalanuvchilar, oxirgi faolligi bo'yicha (yangilari birinchi)."""
        return await self._fetchall(
            "SELECT u.user_id, u.name, u.username, u.family_id, u.is_owner, u.joined_at, u.last_active, "
            " f.name AS family_name, "
            " (SELECT COUNT(*) FROM expenses e WHERE e.user_id = u.user_id) AS expense_count "
            "FROM users u LEFT JOIN families f ON f.id = u.family_id "
            "ORDER BY CASE WHEN u.last_active = '' THEN u.joined_at ELSE u.last_active END DESC, u.user_id "
            "LIMIT ? OFFSET ?",
            (limit, offset),
        )

    async def count_users(self) -> int:
        return int((await self._fetchone("SELECT COUNT(*) AS c FROM users"))["c"])

    async def users_for_reminders(self) -> list:
        return await self._fetchall(
            "SELECT u.user_id, u.family_id, f.expires_at "
            "FROM users u JOIN families f ON f.id = u.family_id"
        )

    # ---------- harajatlar (hammasi family_id bilan chegaralangan) ----------
    async def add_expense(self, family_id: int, user_id: int, user_name: str, category: str,
                          amount: int, note: str, spent_on, created_at: str) -> int:
        return await self._execute(
            "INSERT INTO expenses (family_id, user_id, user_name, category, amount, note, spent_on, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (family_id, user_id, user_name, category, int(amount), note, _iso(spent_on), created_at),
        )

    async def get_expense(self, family_id: int, expense_id: int) -> Optional[dict]:
        return await self._fetchone(
            "SELECT * FROM expenses WHERE id = ? AND family_id = ?", (expense_id, family_id))

    async def last_expense(self, family_id: int) -> Optional[dict]:
        return await self._fetchone(
            "SELECT * FROM expenses WHERE family_id = ? ORDER BY id DESC LIMIT 1", (family_id,))

    async def recent(self, family_id: int, limit: int = 10) -> list:
        return await self._fetchall(
            "SELECT * FROM expenses WHERE family_id = ? ORDER BY id DESC LIMIT ?", (family_id, limit))

    async def delete_expense(self, family_id: int, expense_id: int) -> bool:
        return (await self._execute(
            "DELETE FROM expenses WHERE id = ? AND family_id = ?", (expense_id, family_id))) > 0

    async def update_amount(self, family_id: int, expense_id: int, amount: int) -> bool:
        return (await self._execute(
            "UPDATE expenses SET amount = ? WHERE id = ? AND family_id = ?",
            (int(amount), expense_id, family_id))) > 0

    async def update_category(self, family_id: int, expense_id: int, category: str) -> bool:
        return (await self._execute(
            "UPDATE expenses SET category = ? WHERE id = ? AND family_id = ?",
            (category, expense_id, family_id))) > 0

    async def update_note(self, family_id: int, expense_id: int, note: str) -> bool:
        return (await self._execute(
            "UPDATE expenses SET note = ? WHERE id = ? AND family_id = ?",
            (note, expense_id, family_id))) > 0

    # ---------- hisobotlar ----------
    async def total(self, family_id: int, start, end, category: Optional[str] = None):
        """(jami summa, yozuvlar soni)"""
        sql = ("SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
               "FROM expenses WHERE family_id = ? AND spent_on BETWEEN ? AND ?")
        params = [family_id, _iso(start), _iso(end)]
        if category:
            sql += " AND category = ?"
            params.append(category)
        row = await self._fetchone(sql, tuple(params))
        return int(row["total"]), int(row["cnt"])

    async def totals_by_category(self, family_id: int, start, end) -> list:
        return await self._fetchall(
            "SELECT category, SUM(amount) AS total, COUNT(*) AS cnt FROM expenses "
            "WHERE family_id = ? AND spent_on BETWEEN ? AND ? GROUP BY category ORDER BY total DESC",
            (family_id, _iso(start), _iso(end)),
        )

    async def daily_totals(self, family_id: int, start, end) -> dict:
        rows = await self._fetchall(
            "SELECT spent_on, SUM(amount) AS total FROM expenses "
            "WHERE family_id = ? AND spent_on BETWEEN ? AND ? GROUP BY spent_on",
            (family_id, _iso(start), _iso(end)),
        )
        return {r["spent_on"]: int(r["total"]) for r in rows}

    async def expenses_between(self, family_id: int, start=None, end=None,
                               category: Optional[str] = None, limit: Optional[int] = None,
                               newest_first: bool = False) -> list:
        sql = "SELECT * FROM expenses WHERE family_id = ?"
        params = [family_id]
        if start is not None:
            sql += " AND spent_on >= ?"
            params.append(_iso(start))
        if end is not None:
            sql += " AND spent_on <= ?"
            params.append(_iso(end))
        if category:
            sql += " AND category = ?"
            params.append(category)
        order = "DESC" if newest_first else "ASC"
        sql += f" ORDER BY spent_on {order}, id {order}"
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        return await self._fetchall(sql, tuple(params))

    # ---------- oila sozlamalari ----------
    async def get_setting(self, family_id: int, key: str) -> Optional[str]:
        row = await self._fetchone(
            "SELECT value FROM family_settings WHERE family_id = ? AND key = ?", (family_id, key))
        return row["value"] if row else None

    async def set_setting(self, family_id: int, key: str, value: str) -> None:
        await self._execute(
            "INSERT INTO family_settings (family_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(family_id, key) DO UPDATE SET value = excluded.value",
            (family_id, key, value),
        )

    async def delete_setting(self, family_id: int, key: str) -> None:
        await self._execute(
            "DELETE FROM family_settings WHERE family_id = ? AND key = ?", (family_id, key))

    async def get_limit(self, family_id: int) -> Optional[int]:
        raw = await self.get_setting(family_id, "monthly_limit")
        return int(raw) if raw else None

    async def set_limit(self, family_id: int, amount: Optional[int]) -> None:
        """Oylik limitni belgilaydi (None - olib tashlaydi) va ogohlantirish holatini tiklaydi."""
        if amount:
            await self.set_setting(family_id, "monthly_limit", str(int(amount)))
        else:
            await self.delete_setting(family_id, "monthly_limit")
        await self.delete_setting(family_id, "warn_state")

    async def today_overview(self, day) -> dict:
        """Berilgan kun bo'yicha barcha oilalar: yozuvlar soni, jami summa, oilalar soni."""
        row = await self._fetchone(
            "SELECT COUNT(*) AS c, COALESCE(SUM(amount), 0) AS s, COUNT(DISTINCT family_id) AS f "
            "FROM expenses WHERE spent_on = ?", (_iso(day),))
        return {"count": int(row["c"]), "sum": int(row["s"]), "families": int(row["f"])}

    # ---------- fikr-mulohazalar ----------
    async def add_feedback(self, family_id: int, user_id: int, user_name: str,
                           text: str, created_at: str) -> int:
        return await self._execute(
            "INSERT INTO feedback (family_id, user_id, user_name, text, status, created_at) "
            "VALUES (?, ?, ?, ?, 'new', ?)",
            (family_id, user_id, user_name, text, created_at))

    async def list_feedback(self, status: Optional[str] = None, limit: int = 20) -> list:
        if status:
            return await self._fetchall(
                "SELECT * FROM feedback WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit))
        return await self._fetchall("SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (limit,))

    async def set_feedback_status(self, feedback_id: int, status: str) -> bool:
        cur = await self._conn.execute("UPDATE feedback SET status = ? WHERE id = ?", (status, feedback_id))
        await self._conn.commit()
        return cur.rowcount > 0

    # ---------- umumiy (oilaga bog'liq bo'lmagan) sozlamalar ----------
    async def global_get(self, key: str) -> Optional[str]:
        return await self._global_get(key)

    async def global_set(self, key: str, value: str) -> None:
        await self._global_set(key, value)

    # ---------- eski versiyadan ko'chirish ----------
    async def _global_get(self, key: str) -> Optional[str]:
        row = await self._fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else None

    async def _global_set(self, key: str, value: str) -> None:
        await self._execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))

    async def migrate_legacy(self, user_ids, now_str: str) -> None:
        """Bot egasining 'Asosiy oila'si: eski (family_id siz) harajatlar va ALLOWED_USERS dagi
        foydalanuvchilar shu oilaga biriktiriladi. Oila obunasi cheksiz. Qayta chaqirish xavfsiz."""
        orphans = await self._fetchone("SELECT COUNT(*) AS c FROM expenses WHERE family_id IS NULL")
        if not user_ids and not orphans["c"]:
            return

        fid = None
        raw = await self._global_get("legacy_family_id")
        if raw and await self.get_family(int(raw)):
            fid = int(raw)
        if fid is None:
            fid, _code = await self.create_family("Asosiy oila", None, now_str)
            await self._global_set("legacy_family_id", str(fid))
            old_limit = await self._global_get("monthly_limit")
            if old_limit:
                await self.set_setting(fid, "monthly_limit", old_limit)

        await self._execute("UPDATE expenses SET family_id = ? WHERE family_id IS NULL", (fid,))

        for uid in sorted(user_ids):
            if await self.get_user(uid):
                continue  # allaqachon boshqa (yoki shu) oilada
            is_owner = (await self.count_members(fid)) == 0
            await self.add_user(uid, fid, "", "", is_owner, now_str)
