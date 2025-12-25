# task-003-secrets-storage.md

## Мета
Реалізувати безпечний механізм зберігання та використання облікових даних (паролів) для мережевого обладнання Cisco та MikroTik у проєкті **NetConfigBackup**.

Секрети **не повинні** зберігатися у git та **не повинні** потрапляти в логи.

---

## Загальні вимоги
- Секрети зберігаються **поза git**
- `devices.yml` не містить жодних паролів
- Підтримується файл з секретами та override через змінні середовища
- Паролі ніколи не логуються (навіть у debug)

---

## Файли

### Обовʼязкові
- `config/secrets.yml` — реальні секрети (**НЕ комітиться**)
- `config/secrets.yml.example` — приклад структури (комітиться)
- `src/app/core/secrets.py` — логіка роботи з секретами

---

## Формат secrets.yml

```yml
secrets:
  hq-core-sw1:
    password: "CHANGE_ME"
  travel-mikrotik:
    password: "CHANGE_ME"
```

### Пояснення
- Ключ (`hq-core-sw1`) відповідає значенню `auth.secret_ref` з `devices.yml`
- Значення `password` — пароль для SSH підключення

---

## Підтримка змінних середовища

Дозволити override секретів через environment variables.

### Формат
```
NETCONFIGBACKUP_SECRET_<SECRET_REF>=<password>
```

### Приклад
```bash
export NETCONFIGBACKUP_SECRET_HQ_CORE_SW1="SuperSecretPassword"
```

> Примітка: імʼя secret_ref має бути приведене до `UPPER_SNAKE_CASE`

---

## Реалізація в коді

### Файл
- `src/app/core/secrets.py`

### Вимоги до реалізації
- Спроба завантажити `config/secrets.yml`, якщо файл існує
- Якщо файл відсутній — працювати лише з env
- Пріоритет:
  1. Environment variable
  2. secrets.yml
- Функція:
```python
def get_password(secret_ref: str) -> str:
    ...
```

---

## Поведінка при помилках
- Якщо секрет не знайдено:
  - логувати помилку (без значення секрету)
  - зупинити виконання для цього пристрою
- Поведінка (fail-fast або skip) має бути задокументована в коді

---

## Вимоги до .gitignore
Переконатися, що виключено:
```
config/secrets.yml
.env
```

---

## Критерії приймання
- Секрети відсутні у репозиторії
- secrets.yml.example містить лише шаблон
- Паролі не зʼявляються в логах
- Env override працює
- Відсутній секрет коректно обробляється

---

## Результат
NetConfigBackup використовує безпечний, передбачуваний і розширюваний механізм роботи з секретами без ризику витоку облікових даних.
