# task-017-fix-logging-extra-filename-conflict.md

## Мета
Виправити помилку Python logging:

```
KeyError: "Attempt to overwrite 'filename' in LogRecord"
```

яка виникає під час логування, коли в `logger.*(..., extra=...)` передається ключ `filename`
(зарезервований атрибут `logging.LogRecord`).

---

## Контекст
Після виконання task-016 було зафіксовано падіння в:

- `src/app/mikrotik/backup.py`
- під час виклику `logger.info(..., extra=log_extra)`

Причина:
- `log_extra` (або інший dict, який передається через `extra=`) містить ключ `filename`
- `logging` забороняє перезапис атрибутів LogRecord (`filename`, `module`, `lineno`, `funcName`, etc.)

---

## Вимоги

### 1) Заборонити використання ключа `filename` в extra
У всьому проєкті ключ `filename` **не повинен** зʼявлятись у dict, який передається як `extra=...`.

Необхідно:
- знайти всі місця, де формується `log_extra` (або схожі структури)
- прибрати або перейменувати `filename`

---

### 2) Замінити на безпечний ключ
Використовувати один з безпечних варіантів (обрати один і застосувати послідовно):
- `backup_file`
- `remote_file`
- `local_file`
- `backup_filename`

Рекомендація: `backup_file`.

---

### 3) Оновити конкретний лог (system-backup)
У `src/app/mikrotik/backup.py` (або відповідному файлі) замінити:

```python
logger.info("creating system-backup device=%s filename=%s", device_name, backup_filename, extra=log_extra)
```

на еквівалент без конфлікту:

```python
logger.info("creating system-backup device=%s backup_file=%s", device_name, backup_filename, extra=log_extra)
```

або (кращий структурний варіант):

```python
log_extra2 = dict(log_extra)
log_extra2["backup_file"] = backup_filename
logger.info("creating system-backup", extra=log_extra2)
```

---

### 4) Додати захист від повторення помилки (рекомендовано)
Додати helper-функцію або фільтр, який:
- перевіряє `extra` перед логуванням
- якщо знайдено заборонені ключі (`filename`, `module`, `lineno`, ...), то:
  - перейменовує (наприклад `filename` → `extra_filename`)
  - або видаляє і логує DEBUG-попередження

Мінімально: реалізувати для ключа `filename`.

---

## Логування
Після виправлення:
- логування system-backup не повинно падати
- повідомлення має містити назву backup-файлу (через текст або extra-поле)

---

## Acceptance criteria
- Скрипт `scripts/run.py` проходить backup MikroTik без падіння на логуванні
- В проєкті відсутні випадки `extra={"filename": ...}`
- Повідомлення про system-backup містить назву файлу (через `backup_file=...` або аналог)
- Додано мінімальний захист від повторення конфлікту (щонайменше для `filename`)

---

## Результат
NetConfigBackup стабільно логує події system-backup, не конфліктує зі стандартними атрибутами
`logging.LogRecord` та не падає під час виконання через зарезервовані ключі в `extra`.
