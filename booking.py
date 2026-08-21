"""Appointments, in SQLite.

Small on purpose. The point of the example is the call, not the calendar —
swap this module for your real booking system and nothing above it changes,
because the agent only ever calls the four functions at the bottom.

The one behaviour worth keeping if you do swap it: `hold` reserves a slot for
the length of the call. Without it, two callers offered the same slot at the
same moment both get told it is theirs.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

DB_PATH = os.getenv("BOOKING_DB", "appointments.db")

# How long a slot stays reserved once it has been offered out loud.
HOLD_SECONDS = int(os.getenv("HOLD_SECONDS", "180"))


@dataclass
class Slot:
    id: int
    starts_at: datetime
    practitioner: str
    service: str

    def spoken_ar(self) -> str:
        """Arabic day and time, as a receptionist would say it."""
        days = {
            0: "الاثنين", 1: "الثلاثاء", 2: "الأربعاء", 3: "الخميس",
            4: "الجمعة", 5: "السبت", 6: "الأحد",
        }
        hour = self.starts_at.hour
        suffix = "صباحاً" if hour < 12 else "عصراً"
        h12 = hour if 1 <= hour <= 12 else abs(hour - 12) or 12
        minute = f":{self.starts_at.minute:02d}" if self.starts_at.minute else ""
        return f"{days[self.starts_at.weekday()]} الساعة {h12}{minute} {suffix}"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed: bool = True) -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS slots (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                starts_at    TEXT    NOT NULL,
                practitioner TEXT    NOT NULL,
                service      TEXT    NOT NULL,
                held_until   TEXT,
                booked_by    TEXT
            );
            CREATE TABLE IF NOT EXISTS appointments (
                reference  TEXT PRIMARY KEY,
                slot_id    INTEGER NOT NULL REFERENCES slots(id),
                caller     TEXT    NOT NULL,
                created_at TEXT    NOT NULL
            );
            """
        )
        if seed and not conn.execute("SELECT 1 FROM slots LIMIT 1").fetchone():
            _seed(conn)


def _seed(conn: sqlite3.Connection) -> None:
    """A fortnight of half-hour slots, so the example runs out of the box."""
    start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    rows = []
    for day in range(1, 15):
        date = start + timedelta(days=day)
        if date.weekday() == 4:  # Friday
            continue
        for half_hour in range(0, 16):  # 09:00 to 16:30
            when = date + timedelta(minutes=30 * half_hour)
            rows.append((when.isoformat(), "د. سارة القحطاني", "dentistry"))
            rows.append((when.isoformat(), "د. خالد العتيبي", "general"))
    conn.executemany(
        "INSERT INTO slots (starts_at, practitioner, service) VALUES (?, ?, ?)", rows
    )


def _row_to_slot(row: sqlite3.Row) -> Slot:
    return Slot(
        id=row["id"],
        starts_at=datetime.fromisoformat(row["starts_at"]),
        practitioner=row["practitioner"],
        service=row["service"],
    )


# --------------------------------------------------------------- the four


def availability(service: str, *, within_days: int = 7, limit: int = 2) -> list[Slot]:
    """The next few genuinely free slots — not a canned list.

    Anything already booked, or held by a call still in progress, is excluded.

    At most one slot per day is returned. Offering "nine o'clock or half past
    nine" is not a choice; a caller who cannot make the morning needs to hear
    a different day, so the options are spread out before they are read.
    """
    now = datetime.now()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM slots
             WHERE service = ?
               AND booked_by IS NULL
               AND starts_at > ?
               AND starts_at < ?
               AND (held_until IS NULL OR held_until < ?)
             ORDER BY starts_at
            """,
            (
                service,
                now.isoformat(),
                (now + timedelta(days=within_days)).isoformat(),
                now.isoformat(),
            ),
        ).fetchall()

    spread: list[Slot] = []
    seen_days: set[str] = set()
    for row in rows:
        slot = _row_to_slot(row)
        day = slot.starts_at.date().isoformat()
        if day in seen_days:
            continue
        seen_days.add(day)
        spread.append(slot)
        if len(spread) == limit:
            break
    return spread


def hold(slot_id: int) -> bool:
    """Reserve a slot while the caller decides. Returns False if it went."""
    until = (datetime.now() + timedelta(seconds=HOLD_SECONDS)).isoformat()
    with connect() as conn:
        changed = conn.execute(
            """
            UPDATE slots SET held_until = ?
             WHERE id = ? AND booked_by IS NULL
               AND (held_until IS NULL OR held_until < ?)
            """,
            (until, slot_id, datetime.now().isoformat()),
        ).rowcount
    return changed == 1


def book(slot_id: int, caller: str) -> str | None:
    """Take the slot. Returns the reference, or None if it was taken first."""
    reference = f"APT-{20000 + slot_id}"
    with connect() as conn:
        changed = conn.execute(
            "UPDATE slots SET booked_by = ?, held_until = NULL WHERE id = ? AND booked_by IS NULL",
            (caller, slot_id),
        ).rowcount
        if changed != 1:
            return None
        conn.execute(
            "INSERT INTO appointments (reference, slot_id, caller, created_at) VALUES (?, ?, ?, ?)",
            (reference, slot_id, caller, datetime.now().isoformat()),
        )
    return reference


def lookup(reference: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT a.reference, a.caller, s.starts_at, s.practitioner, s.service
              FROM appointments a JOIN slots s ON s.id = a.slot_id
             WHERE a.reference = ?
            """,
            (reference,),
        ).fetchone()
    return dict(row) if row else None
