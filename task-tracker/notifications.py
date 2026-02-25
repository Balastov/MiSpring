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
    """
    with app.app_context():
        from extensions import db
        from models import Task, TaskType, User, Setting

        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.warning('TELEGRAM_BOT_TOKEN не задан — уведомления не отправляются')
            return

        meeting_link = Setting.get('meeting_link', '')

        lesson_type = TaskType.query.filter_by(name='Урок').first()
        if not lesson_type:
            return

        now = datetime.now()

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
            lambda t: f'Здравствуйте!\n Напоминаю, завтра у вас урок английского языка '
                      f'{t.start_date.day} {MONTHS_RU[t.start_date.month]} в {t.start_date.strftime("%H:%M")}.',
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
    scheduler.start()
    logger.info('Lesson reminder scheduler started (interval: 5 min)')
    return scheduler
