import os
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Русские названия месяцев в родительном падеже
MONTHS_RU = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
    5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
    9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря',
}


def _send_tg_message(token, chat_id, text):
    """Отправляет сообщение в Telegram через asyncio.run."""
    import telegram

    async def _send():
        bot = telegram.Bot(token=token)
        await bot.send_message(chat_id=chat_id, text=text)

    try:
        asyncio.run(_send())
    except Exception as e:
        logger.warning(f'Telegram send error (chat_id={chat_id}): {e}')


def send_lesson_reminders(app):
    """
    Запускается планировщиком каждые 5 минут.
    Ищет уроки с началом через ~24 часа или ~1 час
    и отправляет ученику напоминание в Telegram.
    Дополнительно: сообщения в чат от «Администратор» за ~24 ч и ~30 мин до урока.
    """
    with app.app_context():
        from extensions import db
        from models import Task, TaskType, User, Setting
        from routes_chat import get_chat_administrator_user, send_system_chat_message

        meeting_link = Setting.get('meeting_link', '')

        lesson_type = TaskType.query.filter_by(name='Урок').first()
        if not lesson_type:
            return

        now = datetime.now()
        token = os.environ.get('TELEGRAM_BOT_TOKEN')

        def _lesson_start_label(task):
            if not task.start_date:
                return '—'
            return task.start_date.strftime('%d.%m.%Y %H:%M')

        def _claim_chat_and_send(task_ids, flag_column, build_text):
            admin = get_chat_administrator_user()
            if not admin:
                logger.warning('Не найден или неактивен пользователь id=1 для системных сообщений чата')
                return
            for task_id in task_ids:
                result = db.session.execute(
                    db.update(Task)
                    .where(Task.id == task_id, flag_column == False)  # noqa: E712
                    .values({flag_column.key: True})
                )
                db.session.commit()
                if result.rowcount == 0:
                    continue
                task = db.session.get(Task, task_id)
                if not task or not task.student_id:
                    continue
                student = db.session.get(User, task.student_id)
                if not student or not student.is_active:
                    continue
                text = build_text(task)
                if send_system_chat_message(admin, student.id, text):
                    logger.info(f'Chat lesson reminder sent: task={task_id}, student={student.id}')

        def _claim_and_notify(task_ids, flag_column, build_text):
            """
            Атомарно помечает задачу как уведомлённую через UPDATE ... WHERE notified = False.
            SQLite гарантирует: только один worker получит rowcount=1.
            Остальные получат rowcount=0 и пропустят отправку — дублей не будет.
            """
            for task_id in task_ids:
                result = db.session.execute(
                    db.update(Task)
                    .where(Task.id == task_id, flag_column == False)  # noqa: E712
                    .values({flag_column.key: True})
                )
                db.session.commit()
                if result.rowcount == 0:
                    continue  # другой worker уже обработал эту задачу

                task = db.session.get(Task, task_id)
                if not task:
                    continue
                student = db.session.get(User, task.student_id)
                if not student or not student.telegram_id or not student.telegram_notifications:
                    continue

                text = build_text(task)
                if meeting_link:
                    text += f'\nСсылка на подключение — {meeting_link}'
                _send_tg_message(token, student.telegram_id, text)
                logger.info(f'Reminder sent: task={task_id}, student={student.id}')

        # ── Чат: за 24 часа ───────────────────────────────────────────────────
        ids_chat_24h = [row.id for row in Task.query.filter(
            Task.task_type_id == lesson_type.id,
            Task.start_date >= now + timedelta(hours=23, minutes=45),
            Task.start_date <= now + timedelta(hours=24, minutes=15),
            Task.notified_chat_24h == False,  # noqa: E712
            Task.student_id.isnot(None),
        ).with_entities(Task.id).all()]

        _claim_chat_and_send(
            ids_chat_24h,
            Task.notified_chat_24h,
            lambda t: f'Приветствую! Завтра у вас урок в {_lesson_start_label(t)}',
        )

        # ── Чат: за 30 минут ─────────────────────────────────────────────────
        ids_chat_30m = [row.id for row in Task.query.filter(
            Task.task_type_id == lesson_type.id,
            Task.start_date >= now + timedelta(minutes=25),
            Task.start_date <= now + timedelta(minutes=35),
            Task.notified_chat_30m == False,  # noqa: E712
            Task.student_id.isnot(None),
        ).with_entities(Task.id).all()]

        _claim_chat_and_send(
            ids_chat_30m,
            Task.notified_chat_30m,
            lambda t: 'Приветствую! Через 30 минут у вас урок',
        )

        if not token:
            logger.warning('TELEGRAM_BOT_TOKEN не задан — Telegram-напоминания пропущены')
            return

        # ── 24-часовое напоминание ──────────────────────────────────────────
        ids_24h = [row.id for row in Task.query.filter(
            Task.task_type_id == lesson_type.id,
            Task.start_date >= now + timedelta(hours=23, minutes=45),
            Task.start_date <= now + timedelta(hours=24, minutes=15),
            Task.notified_24h == False,  # noqa: E712
            Task.student_id.isnot(None),
        ).with_entities(Task.id).all()]

        _claim_and_notify(
            ids_24h,
            Task.notified_24h,
            lambda t: f'Здравствуйте!\n Напоминаю, завтра {t.start_date.day} {MONTHS_RU[t.start_date.month]} '
                      f'в {t.start_date.strftime("%H:%M")} у вас урок английского языка.',
        )

        # ── Часовое напоминание ─────────────────────────────────────────────
        ids_1h = [row.id for row in Task.query.filter(
            Task.task_type_id == lesson_type.id,
            Task.start_date >= now + timedelta(minutes=45),
            Task.start_date <= now + timedelta(hours=1, minutes=15),
            Task.notified_1h == False,  # noqa: E712
            Task.student_id.isnot(None),
        ).with_entities(Task.id).all()]

        _claim_and_notify(
            ids_1h,
            Task.notified_1h,
            lambda t: f'Здравствуйте!\n Напоминаю, через час у вас урок английского языка в '
                      f'{t.start_date.strftime("%H:%M")}.',
        )


def cleanup_old_homework_evidence(app):
    """Удаляет файлы подтверждений ДЗ по срокам хранения."""
    with app.app_context():
        from extensions import db
        from models import HomeworkEvidence

        now = datetime.now()
        student_cutoff = now - timedelta(days=14)
        teacher_cutoff = now - timedelta(days=20)
        stale = HomeworkEvidence.query.filter(
            db.or_(
                db.and_(HomeworkEvidence.uploader_role == 'teacher', HomeworkEvidence.created_at < teacher_cutoff),
                db.and_(HomeworkEvidence.uploader_role != 'teacher', HomeworkEvidence.created_at < student_cutoff),
            )
        ).all()
        if not stale:
            return

        removed = 0
        for row in stale:
            file_path = os.path.join(app.root_path, 'static', row.relative_path.replace('/', os.sep))
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    logger.warning(f'Failed to remove homework evidence file: {file_path}')
            db.session.delete(row)
            removed += 1

        db.session.commit()
        logger.info(f'Homework evidence cleanup removed: {removed}')


def start_scheduler(app):
    """Запускает фоновый планировщик внутри Flask-процесса."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        send_lesson_reminders,
        'interval',
        minutes=5,
        args=[app],
        id='lesson_reminders',
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(seconds=30),  # первый запуск через 30 сек
    )
    scheduler.add_job(
        cleanup_old_homework_evidence,
        'interval',
        hours=24,
        args=[app],
        id='homework_evidence_cleanup',
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(minutes=2),
    )
    scheduler.start()
    logger.info('Lesson reminder scheduler started (interval: 5 min)')
    return scheduler
