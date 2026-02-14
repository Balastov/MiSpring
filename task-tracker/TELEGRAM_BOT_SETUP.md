# Настройка Telegram Бота

## 1. Установка зависимостей

На сервере установите библиотеку для работы с Telegram:

```bash
pip3 install python-telegram-bot==20.7 --upgrade
```

## 2. Настройка переменных окружения

Создайте systemd service файл для бота:

```bash
sudo nano /etc/systemd/system/engspring-bot.service
```

Содержимое файла:

```ini
[Unit]
Description=EngSpring Telegram Bot
After=network.target task-tracker.service

[Service]
Type=simple
User=user1
WorkingDirectory=/home/user1/projects/MiSpring/task-tracker
Environment="TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE"
Environment="API_BASE_URL=http://localhost:5000"
ExecStart=/usr/bin/python3 /home/user1/projects/MiSpring/task-tracker/telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Важно:** Замените `YOUR_BOT_TOKEN_HERE` на реальный токен вашего бота!

## 3. Запуск бота

```bash
# Перезагрузите systemd
sudo systemctl daemon-reload

# Включите автозапуск
sudo systemctl enable engspring-bot

# Запустите бота
sudo systemctl start engspring-bot

# Проверьте статус
sudo systemctl status engspring-bot

# Просмотр логов
sudo journalctl -u engspring-bot -f
```

## 4. Проверка работы

1. Откройте Telegram
2. Найдите вашего бота (@EngSpring_bot или как вы назвали)
3. Отправьте `/start`
4. Бот должен ответить приветственным сообщением

## 5. Тестирование привязки

1. На сайте: Настройки → Telegram → Сгенерировать код
2. Получите код (например, "ABC123")
3. В боте: `/start ABC123`
4. Бот должен подтвердить привязку

## Структура проекта

```
task-tracker/
├── telegram_bot.py          # Код бота
├── routes_telegram.py       # API эндпоинты
├── TELEGRAM_BOT_SETUP.md    # Эта инструкция
└── TELEGRAM_API.md          # Документация API
```

## Troubleshooting

### Бот не запускается

```bash
# Проверьте логи
sudo journalctl -u engspring-bot -n 50

# Проверьте что токен установлен
sudo systemctl show engspring-bot | grep Environment
```

### Бот не привязывает аккаунт

1. Проверьте что Flask API доступен: `curl http://localhost:5000/api/telegram/status`
2. Проверьте логи Flask: `sudo journalctl -u task-tracker -f`
3. Проверьте логи бота: `sudo journalctl -u engspring-bot -f`

### API_BASE_URL

- Для production на том же сервере: `http://localhost:5000`
- Если Flask на другом порту: измените в service файле
- Если Flask на другом сервере: используйте полный URL

## Команды бота

- `/start` - Приветствие и инструкция
- `/start КОД` - Привязать аккаунт
- `/help` - Помощь
- `/status` - Проверить статус привязки

## Следующие шаги

После успешной установки можно добавить:
- [ ] Уведомления о занятиях (за 24 часа и за 1 час)
- [ ] Подтверждение уроков (inline-кнопки)
- [ ] Отправка домашних заданий
- [ ] Напоминания об оплате
- [ ] Команды `/lessons`, `/payment`, `/stats`
