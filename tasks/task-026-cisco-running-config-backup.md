# task-026-cisco-running-config-backup.md

## Мета
Реалізувати **отримання та збереження running-config** з Cisco-комутаторів та маршрутизаторів
через SSH з використанням CLI-команди `show running-config`.

Ця задача є ключовою для Cisco-пайплайну та використовує результати попередніх задач:
SSH-зʼєднання, enable-mode (за потреби) та вимкнення paging.

---

## Контекст
Після виконання:
- `task-023-cisco-ssh-connection.md`
- `task-024-cisco-enable-mode.md` (опційно)
- `task-025-cisco-disable-paging.md`

NetConfigBackup має активну SSH-сесію до Cisco-пристрою, готову до виконання команд,
що повертають великий обʼєм тексту.

---

## Вхідні дані

### `config/devices.yml`
```yml
devices:
  - name: hq-core-sw1
    vendor: cisco
    model: ""
    ip: 192.0.2.10
    port: 22
    username: backup
    secret_ref: hq-core-sw1
```

### `config/secrets.yml`
```yml
secrets:
  hq-core-sw1:
    password: "CHANGE_ME"
    enable_password: "CHANGE_ME_ENABLE"
```

---

## Вимоги до реалізації

### 1) Виконання команди
Для кожного `vendor: cisco` необхідно виконати команду:

```cisco
show running-config
```

Правила:
- виконувати **після**:
  - успішного SSH login
  - enable-mode (якщо застосовується)
  - вимкнення paging
- читати **повний stdout** до повернення prompt
- не допускати обрізання виводу

---

### 2) Обробка виводу
Отриманий текст конфігурації:

- зберігати як **raw output**
- не логувати повний вміст
- не модифікувати на цьому етапі (нормалізація - окрема задача)

Мінімальні sanity-checkʼи:
- output не порожній
- output містить ключові маркери (наприклад `version`, `hostname` або `!`)

У разі провалу sanity-check:
- логувати ERROR
- вважати backup для пристрою невдалим
- перейти до наступного пристрою

---

### 3) Збереження файлу
Зберігати running-config у файлову систему з такою структурою:

```
<BACKUP_DIR>/cisco/<device.name>/
```

Імʼя файлу:
```
<YYYY-MM-DD_HHMMSS>_running-config.txt
```

Вимоги:
- директорія створюється автоматично, якщо не існує
- файл перезаписувати не дозволяється (timestamp унікальний)
- перевірити:
  - файл існує
  - size > 0

---

### 4) Логування
Обовʼязково логувати:

- INFO:
  - `device=<name> fetching running-config`
- INFO:
  - `device=<name> running-config retrieved`
- INFO:
  - `device=<name> running-config saved path=<path> size=<bytes>`
- ERROR:
  - `device=<name> running-config retrieval failed`
  - `device=<name> running-config sanity-check failed`

⚠️ Конфігурація та секрети не логуються.

---

### 5) Інтеграція з pipeline
Реалізація має бути інкапсульована, наприклад:
- `CiscoClient.fetch_running_config(...)`

Викликати метод у Cisco-пайплайні після:
- SSH connect
- enable (за потреби)
- disable paging

---

### 6) Документація (README.md)
Оновити README.md (UA + EN, якщо використовується двомовність):
- описати, що Cisco backup базується на `show running-config`
- зазначити, що знімається **running-config**, а не startup-config
- описати структуру збереження файлів

---

## Область змін
Очікувані файли для змін/додавання:

- `src/app/cisco/client.py`
- Cisco pipeline у `scripts/run.py` (або відповідному модулі)
- логіка збереження файлів
- `README.md` (за потреби)

---

## Acceptance criteria
- Для кожного Cisco-пристрою:
  - виконується `show running-config`
  - отримується повний output без `--More--`
  - файл збережено у правильну директорію
- Файл проходить sanity-check (exists + size > 0)
- Помилка з одним пристроєм не зупиняє обробку інших
- Логи коректно відображають статус backup
- README.md актуалізовано

---

## Результат
NetConfigBackup підтримує коректне отримання та збереження running-config з Cisco-пристроїв,
що є основою для подальшої нормалізації, diff та аудиту змін.
