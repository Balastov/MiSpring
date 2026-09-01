import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from flask import Flask

from extensions import db
from models import StudentPayment, Task, TaskStatus, TaskType, User
from routes_payments import _get_balance, sync_prepaid_marks
from routes_tasks import _apply_task_payment_update


class PrepaidLessonsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        cls.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(cls.app)
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.ctx.pop()

    def setUp(self):
        db.create_all()
        self.lesson_type = TaskType(name='Урок')
        self.done_status = TaskStatus(name='Завершён', group='done')
        self.cancelled_status = TaskStatus(name='Отменён', group='cancelled')
        self.student = User(username='student', display_name='Student')
        db.session.add_all([
            self.lesson_type,
            self.done_status,
            self.cancelled_status,
            self.student,
        ])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def _payment(self, count, payment_date):
        db.session.add(StudentPayment(
            student_id=self.student.id,
            lessons_count=count,
            payment_date=payment_date,
        ))

    def _lesson(self, start_date, status=None, paid=False, manual=False):
        lesson = Task(
            student_id=self.student.id,
            task_type_id=self.lesson_type.id,
            start_date=start_date,
            status_id=status.id if status else None,
            is_paid=paid,
            is_paid_manual=manual,
        )
        db.session.add(lesson)
        return lesson

    def test_new_package_after_zero_uses_only_new_credit(self):
        first_payment = datetime(2026, 1, 1)
        self._payment(2, first_payment)
        self._lesson(datetime(2026, 1, 2), self.done_status)
        self._lesson(datetime(2026, 1, 3), self.done_status)
        db.session.commit()

        sync_prepaid_marks(self.student)
        self.assertEqual(_get_balance(self.student)['remaining'], 0)

        second_payment = datetime(2026, 2, 1)
        self._payment(2, second_payment)
        future = [
            self._lesson(second_payment + timedelta(days=offset))
            for offset in range(1, 5)
        ]
        db.session.commit()

        sync_prepaid_marks(self.student)

        self.assertEqual(self.student.prepaid_since, first_payment)
        self.assertEqual([bool(t.is_paid) for t in future], [True, True, False, False])
        self.assertEqual(_get_balance(self.student)['remaining'], 2)

        future[0].status_id = self.done_status.id
        future[1].status_id = self.done_status.id
        db.session.commit()
        sync_prepaid_marks(self.student)

        self.assertEqual(_get_balance(self.student)['remaining'], 0)
        self.assertEqual([bool(t.is_paid) for t in future], [True, True, False, False])

    def test_done_group_consumes_credit_even_with_custom_status_name(self):
        self._payment(1, datetime(2026, 1, 1))
        lesson = self._lesson(datetime(2026, 1, 2), self.done_status)
        db.session.commit()

        sync_prepaid_marks(self.student)

        self.assertTrue(lesson.is_paid)
        self.assertEqual(_get_balance(self.student)['conducted'], 1)
        self.assertEqual(self.student.prepaid_lessons, 0)

    def test_manual_paid_lesson_reserves_an_advance_slot(self):
        self._payment(2, datetime(2026, 1, 1))
        lessons = [
            self._lesson(datetime(2026, 1, day))
            for day in (2, 3)
        ]
        lessons.append(self._lesson(
            datetime(2026, 1, 4),
            paid=True,
            manual=True,
        ))
        db.session.commit()

        sync_prepaid_marks(self.student)

        self.assertEqual([bool(t.is_paid) for t in lessons], [True, False, True])
        self.assertEqual(sum(bool(t.is_paid) for t in lessons), 2)

    def test_cancelled_lesson_releases_credit_to_the_next_lesson(self):
        self._payment(1, datetime(2026, 1, 1))
        cancelled = self._lesson(
            datetime(2026, 1, 2),
            self.cancelled_status,
            paid=True,
            manual=True,
        )
        next_lesson = self._lesson(datetime(2026, 1, 3))
        db.session.commit()

        sync_prepaid_marks(self.student)

        self.assertFalse(cancelled.is_paid)
        self.assertFalse(cancelled.is_paid_manual)
        self.assertTrue(next_lesson.is_paid)
        self.assertEqual(self.student.prepaid_lessons, 1)

    def test_deleting_payments_clears_obsolete_automatic_marks(self):
        first_payment = StudentPayment(
            student_id=self.student.id,
            lessons_count=1,
            payment_date=datetime(2026, 1, 1),
        )
        second_payment = StudentPayment(
            student_id=self.student.id,
            lessons_count=1,
            payment_date=datetime(2026, 2, 1),
        )
        january_lesson = self._lesson(datetime(2026, 1, 2))
        february_lesson = self._lesson(datetime(2026, 2, 2))
        db.session.add_all([first_payment, second_payment])
        db.session.commit()
        sync_prepaid_marks(self.student)
        self.assertEqual(
            [bool(january_lesson.is_paid), bool(february_lesson.is_paid)],
            [True, True],
        )

        db.session.delete(first_payment)
        db.session.flush()
        sync_prepaid_marks(self.student)
        self.assertEqual(self.student.prepaid_since, second_payment.payment_date)
        self.assertEqual(
            [bool(january_lesson.is_paid), bool(february_lesson.is_paid)],
            [False, True],
        )

        db.session.delete(second_payment)
        db.session.flush()
        sync_prepaid_marks(self.student)
        self.assertIsNone(self.student.prepaid_since)
        self.assertFalse(february_lesson.is_paid)


class TaskPaymentUpdateTests(unittest.TestCase):
    def test_unchanged_auto_payment_does_not_become_manual(self):
        payment_date = datetime(2026, 1, 1, 12, 0)
        task = SimpleNamespace(
            is_paid=True,
            payment_date=payment_date,
            is_paid_manual=False,
        )

        _apply_task_payment_update(task, {
            'is_paid': True,
            'payment_date': '2026-01-01T12:00',
        })

        self.assertFalse(task.is_paid_manual)

    def test_real_payment_date_change_becomes_manual(self):
        task = SimpleNamespace(
            is_paid=True,
            payment_date=datetime(2026, 1, 1, 12, 0),
            is_paid_manual=False,
        )

        _apply_task_payment_update(task, {
            'is_paid': True,
            'payment_date': '2026-01-02T12:00',
        })

        self.assertTrue(task.is_paid_manual)


if __name__ == '__main__':
    unittest.main()
