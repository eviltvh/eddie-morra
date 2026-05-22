"""
database.py — Persistencia SQLite para Eddie Morra Bot
"""
import sqlite3
import json
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "eddie.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id     INTEGER PRIMARY KEY,
            username    TEXT,
            active      INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_substances (
            chat_id     INTEGER PRIMARY KEY,
            available   TEXT DEFAULT '[]',
            FOREIGN KEY(chat_id) REFERENCES users(chat_id)
        );

        CREATE TABLE IF NOT EXISTS streaks (
            chat_id         INTEGER PRIMARY KEY,
            current_streak  INTEGER DEFAULT 0,
            longest_streak  INTEGER DEFAULT 0,
            last_check_date TEXT,
            total_doses     INTEGER DEFAULT 0,
            FOREIGN KEY(chat_id) REFERENCES users(chat_id)
        );

        CREATE TABLE IF NOT EXISTS cycles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id         INTEGER,
            phase           TEXT DEFAULT 'loading',
            week_in_phase   INTEGER DEFAULT 1,
            cycle_day       INTEGER DEFAULT 1,
            on_weeks        INTEGER DEFAULT 8,
            off_weeks       INTEGER DEFAULT 2,
            start_date      TEXT,
            phase_end_date  TEXT,
            FOREIGN KEY(chat_id) REFERENCES users(chat_id)
        );

        CREATE TABLE IF NOT EXISTS dose_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id     INTEGER,
            dose_slot   TEXT,
            confirmed   INTEGER DEFAULT 0,
            skipped     INTEGER DEFAULT 0,
            log_date    TEXT,
            logged_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(chat_id) REFERENCES users(chat_id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            chat_id         INTEGER PRIMARY KEY,
            morning_hour    INTEGER DEFAULT 7,
            morning_min     INTEGER DEFAULT 30,
            boost_hour      INTEGER DEFAULT 11,
            boost_min       INTEGER DEFAULT 0,
            night_hour      INTEGER DEFAULT 21,
            night_min       INTEGER DEFAULT 30,
            FOREIGN KEY(chat_id) REFERENCES users(chat_id)
        );
        """)


def upsert_user(chat_id: int, username: str):
    from substances import SUBSTANCES
    all_ids = json.dumps([s["id"] for s in SUBSTANCES])
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users(chat_id, username) VALUES(?,?)
            ON CONFLICT(chat_id) DO UPDATE SET username=excluded.username
        """, (chat_id, username))
        conn.execute("INSERT OR IGNORE INTO streaks(chat_id) VALUES(?)", (chat_id,))
        conn.execute("INSERT OR IGNORE INTO settings(chat_id) VALUES(?)", (chat_id,))
        conn.execute("""
            INSERT OR IGNORE INTO user_substances(chat_id, available) VALUES(?,?)
        """, (chat_id, all_ids))


def get_all_active_users():
    with get_conn() as conn:
        return conn.execute("SELECT chat_id FROM users WHERE active=1").fetchall()


def get_available_substances(chat_id: int) -> list:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT available FROM user_substances WHERE chat_id=?", (chat_id,)
        ).fetchone()
        if not row:
            return []
        return json.loads(row["available"])


def toggle_substance(chat_id: int, substance_id: str) -> bool:
    current = get_available_substances(chat_id)
    if substance_id in current:
        current.remove(substance_id)
        new_state = False
    else:
        current.append(substance_id)
        new_state = True
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_substances(chat_id, available) VALUES(?,?)
            ON CONFLICT(chat_id) DO UPDATE SET available=excluded.available
        """, (chat_id, json.dumps(current)))
    return new_state


def get_streak(chat_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM streaks WHERE chat_id=?", (chat_id,)).fetchone()


def update_streak(chat_id: int, confirmed: bool):
    from datetime import date as _date, timedelta
    today     = _date.today().isoformat()
    yesterday = (_date.today() - timedelta(days=1)).isoformat()
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO streaks(chat_id) VALUES(?)", (chat_id,))
        row     = conn.execute("SELECT * FROM streaks WHERE chat_id=?", (chat_id,)).fetchone()
        current = row["current_streak"]
        longest = row["longest_streak"]
        total   = row["total_doses"]
        last    = row["last_check_date"]
        if confirmed:
            if last == today:
                return row
            current = (current + 1) if last == yesterday else 1
            longest = max(longest, current)
            total  += 1
            conn.execute("""
                UPDATE streaks
                SET current_streak=?, longest_streak=?, last_check_date=?, total_doses=?
                WHERE chat_id=?
            """, (current, longest, today, total, chat_id))
        else:
            if last != today:
                conn.execute("""
                    UPDATE streaks SET current_streak=0, last_check_date=?
                    WHERE chat_id=?
                """, (today, chat_id))
        return conn.execute("SELECT * FROM streaks WHERE chat_id=?", (chat_id,)).fetchone()


def get_cycle(chat_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM cycles WHERE chat_id=? ORDER BY id DESC LIMIT 1",
            (chat_id,)
        ).fetchone()


def create_cycle(chat_id: int, on_weeks=8, off_weeks=2):
    from datetime import date as _date, timedelta
    start = _date.today().isoformat()
    end   = (_date.today() + timedelta(weeks=2)).isoformat()
    with get_conn() as conn:
        conn.execute("DELETE FROM cycles WHERE chat_id=?", (chat_id,))
        conn.execute("""
            INSERT INTO cycles(chat_id,phase,week_in_phase,cycle_day,on_weeks,off_weeks,start_date,phase_end_date)
            VALUES(?,?,?,?,?,?,?,?)
        """, (chat_id, 'loading', 1, 1, on_weeks, off_weeks, start, end))


def advance_cycle(chat_id: int):
    from datetime import date as _date, timedelta
    cycle = get_cycle(chat_id)
    if not cycle:
        create_cycle(chat_id)
        return get_cycle(chat_id)
    today     = _date.today()
    phase_end = _date.fromisoformat(cycle["phase_end_date"])
    with get_conn() as conn:
        if today < phase_end:
            conn.execute("""
                UPDATE cycles SET cycle_day=cycle_day+1,
                week_in_phase=((cycle_day)/7)+1
                WHERE chat_id=? AND id=?
            """, (chat_id, cycle["id"]))
        else:
            transitions = {
                "loading":     ("maintenance", cycle["on_weeks"] - 2),
                "maintenance": ("washout",     cycle["off_weeks"]),
                "washout":     ("loading",     2),
            }
            new_phase, weeks = transitions.get(cycle["phase"], ("loading", 2))
            new_end = (today + timedelta(weeks=weeks)).isoformat()
            conn.execute("""
                UPDATE cycles SET phase=?, week_in_phase=1, cycle_day=1,
                start_date=?, phase_end_date=?
                WHERE chat_id=? AND id=?
            """, (new_phase, today.isoformat(), new_end, chat_id, cycle["id"]))
    return get_cycle(chat_id)


def force_phase(chat_id: int, phase: str):
    from datetime import date as _date, timedelta
    weeks_map = {"loading": 2, "maintenance": 6, "washout": 2}
    end = (_date.today() + timedelta(weeks=weeks_map.get(phase, 2))).isoformat()
    with get_conn() as conn:
        conn.execute("""
            UPDATE cycles SET phase=?, week_in_phase=1, cycle_day=1,
            start_date=date('now'), phase_end_date=?
            WHERE chat_id=?
        """, (phase, end, chat_id))


def log_dose(chat_id: int, slot: str, confirmed: bool):
    today = date.today().isoformat()
    with get_conn() as conn:
        existing = conn.execute("""
            SELECT id FROM dose_log
            WHERE chat_id=? AND dose_slot=? AND log_date=?
        """, (chat_id, slot, today)).fetchone()
        if existing:
            conn.execute("""
                UPDATE dose_log SET confirmed=?, skipped=?, logged_at=datetime('now')
                WHERE id=?
            """, (1 if confirmed else 0, 0 if confirmed else 1, existing["id"]))
        else:
            conn.execute("""
                INSERT INTO dose_log(chat_id,dose_slot,confirmed,skipped,log_date)
                VALUES(?,?,?,?,?)
            """, (chat_id, slot, 1 if confirmed else 0, 0 if confirmed else 1, today))


def get_today_doses(chat_id: int):
    today = date.today().isoformat()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM dose_log WHERE chat_id=? AND log_date=?",
            (chat_id, today)
        ).fetchall()


def get_settings(chat_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM settings WHERE chat_id=?", (chat_id,)).fetchone()


def update_setting(chat_id: int, key: str, value):
    with get_conn() as conn:
        conn.execute(f"UPDATE settings SET {key}=? WHERE chat_id=?", (value, chat_id))
