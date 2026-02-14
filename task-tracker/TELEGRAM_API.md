# Telegram Integration API

## Эндпоинты

### 1. Генерация кода привязки
**POST** `/api/telegram/generate-code`

Требует авторизации (login_required)

**Ответ:**
```json
{
  "code": "ABC123"
}
```

**Ошибки:**
- 400: Telegram уже привязан к этому аккаунту

---

### 2. Привязка Telegram аккаунта
**POST** `/api/telegram/bind`

Публичный эндпоинт (вызывается ботом)

**Запрос:**
```json
{
  "code": "ABC123",
  "telegram_id": "123456789",
  "telegram_username": "username"
}
```

**Ответ:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "display_name": "Иван Иванов",
    "username": "ivan"
  }
}
```

**Ошибки:**
- 400: Код и Telegram ID обязательны
- 404: Неверный код привязки
- 400: Этот Telegram аккаунт уже привязан к другому пользователю

---

### 3. Отвязка Telegram аккаунта
**DELETE** `/api/telegram/unbind`

Требует авторизации (login_required)

**Ответ:**
```json
{
  "success": true
}
```

**Ошибки:**
- 400: Telegram не привязан

---

### 4. Переключение уведомлений
**PATCH** `/api/telegram/notifications`

Требует авторизации (login_required)

**Запрос:**
```json
{
  "enabled": true
}
```

**Ответ:**
```json
{
  "success": true,
  "enabled": true
}
```

**Ошибки:**
- 400: Параметр enabled обязателен
- 400: Telegram не привязан

---

### 5. Получение статуса
**GET** `/api/telegram/status`

Требует авторизации (login_required)

**Ответ:**
```json
{
  "is_bound": true,
  "telegram_id": "123456789",
  "telegram_username": "username",
  "notifications_enabled": true,
  "pending_code": null
}
```

---

## Логика привязки

1. Пользователь на сайте: `POST /api/telegram/generate-code` → получает код "ABC123"
2. Пользователь в боте: `/start ABC123`
3. Бот: `POST /api/telegram/bind` с кодом и telegram_id
4. Сайт: привязывает аккаунты, очищает код
5. Пользователь: может отвязать через `DELETE /api/telegram/unbind`

---

## Поля модели User

```python
telegram_id = db.Column(db.String(50), unique=True, nullable=True)
telegram_username = db.Column(db.String(100), nullable=True)
telegram_code = db.Column(db.String(10), unique=True, nullable=True)
telegram_notifications = db.Column(db.Boolean, default=True)
```
