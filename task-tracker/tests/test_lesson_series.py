import unittest
from datetime import datetime

from routes_tasks import (
    _build_series_starts,
    _build_weekly_multi_starts,
    _encode_stored_recurrence_rule,
    _normalize_recurrence_rule,
    _parse_weekly_schedule_from_rule,
    _parse_weekly_schedule_payload,
)


class LessonSeriesRecurrenceTests(unittest.TestCase):
    def test_weekly_regression_keeps_anchor_start(self):
        start = datetime(2026, 1, 5, 15, 0)
        until = datetime(2026, 2, 2, 23, 59)
        starts = _build_series_starts(start, until, 'WEEKLY')
        self.assertEqual(starts[0], start)
        self.assertEqual(len(starts), 5)
        self.assertEqual(starts[1], datetime(2026, 1, 12, 15, 0))

    def test_biweekly_regression(self):
        start = datetime(2026, 1, 5, 10, 0)
        until = datetime(2026, 2, 28, 23, 59)
        starts = _build_series_starts(start, until, 'BIWEEKLY')
        self.assertEqual(starts, [
            datetime(2026, 1, 5, 10, 0),
            datetime(2026, 1, 19, 10, 0),
            datetime(2026, 2, 2, 10, 0),
            datetime(2026, 2, 16, 10, 0),
        ])

    def test_weekly_multi_first_lesson_on_earliest_selected_day(self):
        # Wed 15:00 anchor, Mon 09:00 and Wed 14:00 selected -> Wed 14:00 is before anchor, next Fri 11:00
        start = datetime(2026, 1, 7, 15, 0)  # Wednesday
        until = datetime(2026, 1, 31, 23, 59)
        schedule = {0: '09:00', 2: '14:00', 4: '11:00'}
        starts = _build_weekly_multi_starts(start, until, schedule)
        self.assertEqual(starts[0], datetime(2026, 1, 9, 11, 0))  # Friday
        self.assertIn(datetime(2026, 1, 12, 9, 0), starts)  # Monday
        self.assertIn(datetime(2026, 1, 14, 14, 0), starts)  # Wednesday

    def test_weekly_multi_same_day_after_anchor_time(self):
        start = datetime(2026, 1, 5, 8, 0)  # Monday
        until = datetime(2026, 1, 20, 23, 59)
        schedule = {0: '09:00'}
        starts = _build_weekly_multi_starts(start, until, schedule)
        self.assertEqual(starts[0], datetime(2026, 1, 5, 9, 0))
        self.assertEqual(starts[1], datetime(2026, 1, 12, 9, 0))

    def test_weekly_multi_same_day_before_anchor_time_skips_to_next_week(self):
        start = datetime(2026, 1, 5, 10, 0)  # Monday 10:00
        until = datetime(2026, 1, 20, 23, 59)
        schedule = {0: '09:00'}
        starts = _build_weekly_multi_starts(start, until, schedule)
        self.assertEqual(starts[0], datetime(2026, 1, 12, 9, 0))

    def test_encode_and_parse_weekly_schedule(self):
        schedule = {0: '09:00', 2: '14:30', 5: '18:15'}
        stored = _encode_stored_recurrence_rule('WEEKLY_MULTI', schedule)
        self.assertEqual(stored, 'WEEKLY_MULTI:0=09:00,2=14:30,5=18:15')
        self.assertEqual(_normalize_recurrence_rule(stored), 'WEEKLY_MULTI')
        self.assertEqual(_parse_weekly_schedule_from_rule(stored), schedule)

    def test_parse_weekly_schedule_payload(self):
        payload = {'0': '09:00', '3': '12:45'}
        self.assertEqual(_parse_weekly_schedule_payload(payload), {0: '09:00', 3: '12:45'})
        self.assertIsNone(_parse_weekly_schedule_payload({'0': 'bad'}))

    def test_build_series_starts_weekly_multi_integration(self):
        start = datetime(2026, 1, 7, 15, 0)
        until = datetime(2026, 1, 20, 23, 59)
        schedule = {0: '09:00', 4: '11:00'}
        starts = _build_series_starts(start, until, 'WEEKLY_MULTI', weekly_schedule=schedule)
        self.assertEqual(starts[0], datetime(2026, 1, 9, 11, 0))


if __name__ == '__main__':
    unittest.main()
