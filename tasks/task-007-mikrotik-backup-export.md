# task-007-mikrotik-backup-export.md

## Мета
Реалізувати отримання конфігурації з маршрутизаторів **MikroTik**, які перелічені у `config/devices.yml` (де `vendor: mikrotik`), з перевіркою доступності, аутентифікацією по SSH, отриманням конфігу та збереженням результату в директорію бекапів (**BACKUP_DIR**).

Усі дії та помилки мають логуватись.

---

## Вхідні дані
- `config/devices.yml` (фільтр: `vendor: mikrotik`)
- пароль/секрет через `auth.secret_ref` (див. task-003)
- директорія бекапів визначається правилами task-006 (CLI `--backup-dir` / `config/local.yml` / fallback `./backup/`)

---

## Вимоги

### 1) Відбір пристроїв
Обробляти **лише** ті пристрої, у яких:
- `vendor: mikrotik`

Використовувати значення:
- `name`
- `host`
- `port` (default 22)
- `username`
- `auth.secret_ref`
- `model` (як метадані)

---

### 2) Перевірка доступності
Перед SSH-підключенням виконати перевірку доступності:
- TCP check до `host:port` (рекомендовано, наприклад socket connect з timeout)

Правила:
- Якщо порт недоступний (timeout/refused) - логувати помилку та перейти до наступного пристрою.
- Таймаут має бути розумним (наприклад 3-5 секунд) і не блокувати виконання надовго.

---

### 3) SSH аутентифікація
Підключення по SSH з використанням:
- `username` з devices.yml
- `password` з secrets (за `secret_ref`)

Вимоги:
- Обробити типові помилки: auth failed, timeout, host key issue
- Пароль/секрет **не логувати**

---

### 4) Отримання конфігурації
Для MikroTik отримувати конфіг як текстовий export.

Команда:
- Базово: `/export`
- Якщо можливо і підтримується: `/export show-sensitive=false`

Вимоги:
- Повернути текст конфігу (stdout)
- При порожній відповіді - трактувати як помилку та логувати

---

### 5) Збереження результату (BACKUP_DIR)
Збереження має відбуватися в директорії:

```
<BACKUP_DIR>/mikrotik/<device_name>/
```

Приклади:
- `./backup/mikrotik/main-mikrotik/`
- `./backup/mikrotik/work-mikrotik/`

Файл з конфігом:
- імʼя файлу повинно містити дату/час (щоб не перезаписувати попередні бекапи)
- рекомендований формат:
  - `YYYY-mm-dd_HHMMSS_export.rsc`

Також додати метадані в header (на початку файлу) або поруч окремим `meta.yml`:
- device name, vendor, model, host
- час бекапу (UTC або local - але консистентно)

---

### 6) Логування
Логувати (мінімум):
- старт задачі / загальний старт бекапу mikrotik-пристроїв
- для кожного девайсу:
  - `start backup device=<name> host=<host>`
  - результат доступності `tcp_check ok/fail`
  - результат auth `ssh ok/fail`
  - `config fetched bytes=<N>`
  - `saved path=<...>`
- усі помилки з traceback (де доречно), без секретів

---

## Реалізація в коді

### Файли (орієнтовно)
- `src/app/mikrotik/client.py`:
  - SSH connect
  - execute command
- `src/app/mikrotik/backup.py`:
  - `fetch_export(device, password, logger) -> str`
- `src/app/core/storage.py`:
  - `save_backup_text(backup_dir, vendor, device_name, filename, content, logger) -> str`
- `scripts/run.py`:
  - виклик mikrotik backup для всіх `vendor=mikrotik`
  - використання BACKUP_DIR (task-006)

### Залежності
Додати у `requirements.txt` (якщо ще немає):
- `paramiko`
- `PyYAML` (вже має бути)

---

## Acceptance criteria
- Скрипт обробляє всі `vendor: mikrotik` з `devices.yml`
- Для кожного пристрою:
  - виконується TCP check
  - виконується SSH auth
  - отримується конфіг `/export`
  - конфіг зберігається у:
    - `<BACKUP_DIR>/mikrotik/<name>/YYYY-mm-dd_HHMMSS_export.rsc`
- При недоступності або auth fail:
  - пристрій пропускається
  - у логах є причина
- У логах видно повний шлях до збереженого файлу
- Секрети/паролі не потрапляють у лог

---

## Результат
NetConfigBackup може автоматично зчитувати та зберігати конфігурації з MikroTik-пристроїв, керуючись інвентарем `devices.yml`, з перевірками доступності та детальним логуванням.
