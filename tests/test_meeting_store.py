import csv
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from meeting_store import (
    MeetingRepository,
    ValidationError,
    elapsed_seconds,
    format_duration,
    normalize_date,
    normalize_time,
)


class MeetingStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.repository = MeetingRepository(self.root / "meeting_times.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_sample(self, **overrides):
        values = {
            "name": "txl",
            "meeting_date": "2026-08-06",
            "start_time": "09:00",
            "end_time": "09:20",
            "question_time": "09:35",
        }
        values.update(overrides)
        return self.repository.save(**values)

    def test_insert_normalizes_and_calculates_durations(self):
        meeting_id = self.add_sample(start_time="9:00")
        meeting = self.repository.get(meeting_id)
        self.assertIsNotNone(meeting)
        self.assertEqual(meeting.start_time, "09:00")
        self.assertEqual(meeting.duration, "0:20:00")
        self.assertEqual(meeting.question_duration, "0:15:00")
        self.assertEqual(meeting.total_seconds, 35 * 60)

    def test_blank_question_time_means_no_question_segment(self):
        meeting_id = self.add_sample(question_time="")
        meeting = self.repository.get(meeting_id)
        self.assertEqual(meeting.question_time, "09:20")
        self.assertEqual(meeting.question_duration, "0:00:00")

    def test_cross_midnight_duration(self):
        meeting_id = self.add_sample(
            meeting_date="2026-08-07",
            start_time="23:50",
            end_time="00:10",
            question_time="00:25",
        )
        meeting = self.repository.get(meeting_id)
        self.assertEqual(meeting.report_seconds, 20 * 60)
        self.assertEqual(meeting.question_seconds, 15 * 60)

    def test_update_keeps_id_and_recalculates(self):
        meeting_id = self.add_sample()
        returned_id = self.repository.save(
            meeting_id=meeting_id,
            name="txl",
            meeting_date="2026-08-06",
            start_time="10:00",
            end_time="10:30",
            question_time="10:40",
        )
        self.assertEqual(returned_id, meeting_id)
        self.assertEqual(self.repository.get(meeting_id).duration, "0:30:00")

    def test_search_statistics_latest_end_and_delete(self):
        first = self.add_sample(name="txl")
        self.add_sample(name="zz", start_time="10:00", end_time="10:10", question_time="10:20")
        self.assertEqual([item.name for item in self.repository.list_meetings(search="tx")], ["txl"])
        self.assertEqual(self.repository.latest_end_time("2026-08-06"), "10:20")
        stats = self.repository.statistics("2026-08-01", "2026-08-31")
        self.assertEqual({item.name for item in stats}, {"txl", "zz"})
        self.assertTrue(self.repository.delete(first))
        self.assertIsNone(self.repository.get(first))

    def test_backup_and_csv_export(self):
        self.add_sample()
        backup = self.repository.backup_to(self.root / "backup.db")
        with closing(sqlite3.connect(backup)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM meeting_times").fetchone()[0], 1)

        csv_path = self.repository.export_csv(self.repository.list_meetings(), self.root / "records.csv")
        with csv_path.open(encoding="utf-8-sig") as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(rows[0][1], "汇报人")
        self.assertEqual(rows[1][1], "txl")

    def test_validation_helpers(self):
        self.assertEqual(normalize_time("9:05"), "09:05")
        self.assertEqual(normalize_date("2026-08-06"), "2026-08-06")
        self.assertEqual(elapsed_seconds("23:55", "00:05"), 600)
        self.assertEqual(format_duration(65), "0:01:05")
        for invalid in ("9", "25:00", "09:60"):
            with self.assertRaises(ValidationError):
                normalize_time(invalid)
        with self.assertRaises(ValidationError):
            self.add_sample(start_time="09:00", end_time="09:00")


if __name__ == "__main__":
    unittest.main()
