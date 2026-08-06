"""Database and validation helpers for the ZhangLab meeting timer."""

from __future__ import annotations

import csv
import re
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS meeting_times (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration TEXT NOT NULL,
    question_time TEXT,
    question_duration TEXT
)
"""


class ValidationError(ValueError):
    """Raised when a meeting form contains invalid data."""


@dataclass(frozen=True)
class Meeting:
    id: int
    name: str
    date: str
    start_time: str
    end_time: str
    duration: str
    question_time: str
    question_duration: str

    @property
    def report_seconds(self) -> int:
        return parse_duration(self.duration)

    @property
    def question_seconds(self) -> int:
        return parse_duration(self.question_duration)

    @property
    def total_seconds(self) -> int:
        return self.report_seconds + self.question_seconds


@dataclass(frozen=True)
class PersonStats:
    name: str
    count: int
    average_report_seconds: float
    average_question_seconds: float

    @property
    def average_total_seconds(self) -> float:
        return self.average_report_seconds + self.average_question_seconds


def normalize_date(value: str) -> str:
    value = value.strip()
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("日期格式应为 YYYY-MM-DD，例如 2026-08-06") from exc
    if parsed.year < 2000 or parsed.year > date.today().year + 2:
        raise ValidationError("请检查日期年份是否正确")
    return parsed.isoformat()


def normalize_time(value: str, label: str = "时间") -> str:
    value = value.strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
    if not match:
        raise ValidationError(f"{label}格式应为 HH:MM，例如 09:05")
    hours, minutes = map(int, match.groups())
    if hours > 23 or minutes > 59:
        raise ValidationError(f"{label}不是有效的时间")
    return f"{hours:02d}:{minutes:02d}"


def elapsed_seconds(start: str, end: str) -> int:
    """Return elapsed seconds, treating an earlier end time as next day."""
    start_time = datetime.strptime(normalize_time(start), "%H:%M")
    end_time = datetime.strptime(normalize_time(end), "%H:%M")
    if end_time < start_time:
        end_time += timedelta(days=1)
    return int((end_time - start_time).total_seconds())


def format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def format_minutes(seconds: float) -> str:
    total_minutes = max(0, int(round(seconds / 60)))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours} 小时 {minutes:02d} 分"
    return f"{minutes} 分钟"


def parse_duration(value: str | None) -> int:
    if not value:
        return 0
    parts = str(value).strip().split(":")
    if len(parts) != 3:
        return 0
    try:
        hours, minutes, seconds = (float(part) for part in parts)
    except ValueError:
        return 0
    return max(0, int(round(hours * 3600 + minutes * 60 + seconds)))


class MeetingRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).resolve()
        self.ensure_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def session(self):
        """Commit or roll back one operation, then always release the DB file."""
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def ensure_schema(self) -> None:
        with self.session() as connection:
            connection.execute(SCHEMA)

    @staticmethod
    def _meeting_from_row(row: sqlite3.Row) -> Meeting:
        return Meeting(
            id=row["id"],
            name=row["name"],
            date=row["date"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            duration=row["duration"],
            question_time=row["question_time"] or row["end_time"],
            question_duration=row["question_duration"] or "0:00:00",
        )

    def get(self, meeting_id: int) -> Meeting | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT * FROM meeting_times WHERE id = ?", (meeting_id,)
            ).fetchone()
        return self._meeting_from_row(row) if row else None

    def names(self) -> list[str]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT name, MAX(id) AS latest_id FROM meeting_times "
                "GROUP BY name ORDER BY latest_id DESC"
            ).fetchall()
        return [row["name"] for row in rows]

    def save(
        self,
        *,
        name: str,
        meeting_date: str,
        start_time: str,
        end_time: str,
        question_time: str = "",
        meeting_id: int | None = None,
    ) -> int:
        name = name.strip()
        if not name:
            raise ValidationError("请选择或填写汇报人")
        if len(name) > 30:
            raise ValidationError("汇报人名称过长")

        meeting_date = normalize_date(meeting_date)
        start_time = normalize_time(start_time, "报告开始时间")
        end_time = normalize_time(end_time, "报告结束时间")
        question_time = normalize_time(question_time or end_time, "提问结束时间")

        report_seconds = elapsed_seconds(start_time, end_time)
        question_seconds = elapsed_seconds(end_time, question_time)
        if report_seconds == 0:
            raise ValidationError("报告时长不能为 0 分钟")
        if report_seconds > 6 * 3600 or question_seconds > 6 * 3600:
            raise ValidationError("单段时长超过 6 小时，请检查时间是否填反")

        values = (
            name,
            meeting_date,
            start_time,
            end_time,
            format_duration(report_seconds),
            question_time,
            format_duration(question_seconds),
        )
        with self.session() as connection:
            if meeting_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO meeting_times
                        (name, date, start_time, end_time, duration,
                         question_time, question_duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                return int(cursor.lastrowid)

            if not connection.execute(
                "SELECT 1 FROM meeting_times WHERE id = ?", (meeting_id,)
            ).fetchone():
                raise ValidationError("这条记录已经不存在，请刷新后重试")
            connection.execute(
                """
                UPDATE meeting_times
                SET name = ?, date = ?, start_time = ?, end_time = ?,
                    duration = ?, question_time = ?, question_duration = ?
                WHERE id = ?
                """,
                (*values, meeting_id),
            )
            return meeting_id

    def delete(self, meeting_id: int) -> bool:
        with self.session() as connection:
            cursor = connection.execute(
                "DELETE FROM meeting_times WHERE id = ?", (meeting_id,)
            )
            return cursor.rowcount > 0

    def list_meetings(
        self,
        *,
        search: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int | None = None,
    ) -> list[Meeting]:
        clauses: list[str] = []
        parameters: list[object] = []
        if search.strip():
            clauses.append("name LIKE ?")
            parameters.append(f"%{search.strip()}%")
        if start_date.strip():
            clauses.append("date >= ?")
            parameters.append(normalize_date(start_date))
        if end_date.strip():
            clauses.append("date <= ?")
            parameters.append(normalize_date(end_date))

        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = "SELECT * FROM meeting_times" + where + " ORDER BY date DESC, id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            parameters.append(max(1, int(limit)))
        with self.session() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [self._meeting_from_row(row) for row in rows]

    def latest_end_time(self, meeting_date: str) -> str | None:
        meeting_date = normalize_date(meeting_date)
        with self.session() as connection:
            row = connection.execute(
                """
                SELECT question_time, end_time
                FROM meeting_times
                WHERE date = ?
                ORDER BY id DESC LIMIT 1
                """,
                (meeting_date,),
            ).fetchone()
        if not row:
            return None
        return row["question_time"] or row["end_time"]

    def statistics(self, start_date: str = "", end_date: str = "") -> list[PersonStats]:
        meetings = self.list_meetings(start_date=start_date, end_date=end_date)
        buckets: dict[str, list[Meeting]] = {}
        for meeting in meetings:
            buckets.setdefault(meeting.name, []).append(meeting)

        results = []
        for name, records in buckets.items():
            count = len(records)
            results.append(
                PersonStats(
                    name=name,
                    count=count,
                    average_report_seconds=sum(m.report_seconds for m in records) / count,
                    average_question_seconds=sum(m.question_seconds for m in records) / count,
                )
            )
        return sorted(results, key=lambda item: item.average_total_seconds, reverse=True)

    def backup_to(self, destination: str | Path) -> Path:
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.session() as source, closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            target.commit()
        return destination

    @staticmethod
    def export_csv(meetings: Iterable[Meeting], destination: str | Path) -> Path:
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["ID", "汇报人", "日期", "报告开始", "报告结束", "报告时长", "提问结束", "提问时长"]
            )
            for item in meetings:
                writer.writerow(
                    [
                        item.id,
                        item.name,
                        item.date,
                        item.start_time,
                        item.end_time,
                        item.duration,
                        item.question_time,
                        item.question_duration,
                    ]
                )
        return destination
