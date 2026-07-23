import unittest

from routes_tasks import _take_next_homework_ids


class HomeworkChainTests(unittest.TestCase):
    def test_sequential_one_per_lesson(self):
        ordered = [10, 20, 30, 40]
        prev = None
        assigned = []
        for _ in range(4):
            nxt = _take_next_homework_ids(ordered, prev, count=1)
            self.assertEqual(len(nxt), 1)
            assigned.append(nxt[0])
            prev = nxt[0]
        self.assertEqual(assigned, [10, 20, 30, 40])

    def test_no_double_advance_when_building_series(self):
        """Регрессия: раньше сдвигали цепочку до назначения и ещё раз в цикле → 1,3,5…"""
        ordered = [1, 2, 3, 4, 5]
        src_ids = [1]
        current = src_ids[-1]
        slots = len(src_ids)
        series_assigned = []
        for _lesson in range(3):
            # Правильно: только следующий слот(ы) от current, без предварительного +1
            batch = _take_next_homework_ids(ordered, current, count=slots)
            self.assertTrue(batch)
            series_assigned.append(batch[0])
            current = batch[-1]
        self.assertEqual(series_assigned, [2, 3, 4])

        # Старый баг: предварительный сдвиг + ещё один в цикле
        current = src_ids[-1]
        buggy = []
        for _lesson in range(2):
            current = _take_next_homework_ids(ordered, current, count=1)[0]  # pre-advance
            batch = _take_next_homework_ids(ordered, current, count=slots)  # advance again
            buggy.append(batch[0])
            current = batch[-1]
        self.assertEqual(buggy, [3, 5])  # «перепрыгивание через одно»

    def test_interleaved_two_series_get_unique_sequence(self):
        """Две weekly-серии (пн/ср) должны получать разные ДЗ по общей хронологии."""
        ordered = [1, 2, 3, 4, 5, 6]
        # После прошлого урока с ДЗ=1 будущие пн/ср/пн/ср…
        prev = 1
        assigned = []
        for _ in range(4):
            nxt = _take_next_homework_ids(ordered, prev, count=1)
            self.assertEqual(len(nxt), 1)
            assigned.append(nxt[0])
            prev = nxt[0]
        self.assertEqual(assigned, [2, 3, 4, 5])
        # Регрессия старого поведения «каждая серия с начала»: [2,2,3,3]
        self.assertNotEqual(assigned, [2, 2, 3, 3])


if __name__ == '__main__':
    unittest.main()
