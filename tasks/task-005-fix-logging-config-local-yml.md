# task-010-fix-logging-config-local-yml.md

## Контекст
Задача логування вже була виконана (включно з попередньою версією), але потрібно **виправити реалізацію**, щоб вона відповідала новим вимогам:

- Конфіг логування має бути частиною **локальних змінних**, а не окремим `logging.yml`
- Потрібен файл `config/local.yml`, який **не комітиться**
- Потрібен файл `config/local.yml.example`, який **комітиться**
- `.gitignore` має виключати `config/local.yml`

Ця задача є **fix/correction** до попередньої реалізації логування.

---

## Мета
Переробити реалізацію логування так, щоб вона читала налаштування з `config/local.yml` (секція `logging`) та не вимагала `config/logging.yml`.

---

## Вимоги

### 1) Конфіги
- Видалити/прибрати використання `config/logging.yml` у коді (якщо він існує в репо)
- Додати (або замінити) конфіги:
  - `config/local.yml` (реальний, **не комітиться**)
  - `config/local.yml.example` (приклад, **комітиться**)

#### Формат `config/local.yml(.example)`
```yml
logging:
  directory: /var/log/netconfigbackup
  filename: netconfigbackup.log
  level: INFO
```

> `config/local.yml` має бути розширюваним — у майбутньому можуть зʼявитися інші секції.

---

### 2) .gitignore
Додати/переконатися, що `.gitignore` містить:
```
config/local.yml
logs/
*.log
```

---

### 3) Код: читання local.yml
Оновити `src/app/core/logging.py`:

- За замовчуванням шукати `config/local.yml`
- Якщо файл відсутній — використовувати дефолти:
  - directory: `/var/log/netconfigbackup`
  - filename: `netconfigbackup.log`
  - level: `INFO`
- Якщо директорія недоступна для запису:
  - логувати warning
  - fallback на `./logs/`

Рекомендована функція:
```python
def setup_logging(config_path: str = "config/local.yml") -> logging.Logger:
    ...
```

---

### 4) Інтеграція
Оновити `scripts/run.py`:
- Виклик `setup_logging()` має працювати без `logging.yml`
- В логах має бути чітко видно:
  - час старту
  - час завершення
  - обробку кожного device (коли буде реалізація бекапів)

---

## Перевірка / Acceptance criteria
- Репозиторій не містить `config/local.yml` у git-історії
- `config/local.yml.example` присутній у репо та відповідає формату
- Код не залежить від `config/logging.yml`
- Якщо `config/local.yml` відсутній — логування все одно працює (дефолти)
- Якщо немає доступу до `/var/log/netconfigbackup` — працює fallback `./logs/`
- `python3 scripts/run.py --help` запускається без помилок

---

## Примітки
- Усі повідомлення логів не повинні містити значень секретів/паролів
- Якщо в репо вже є `config/logging.yml`, його:
  - або видалити,
  - або залишити, але **код не повинен його читати/використовувати**
