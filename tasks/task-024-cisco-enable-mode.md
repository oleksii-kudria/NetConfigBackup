# task-024-cisco-enable-mode.md

## Мета
Додати підтримку переходу в **privileged EXEC mode** на Cisco (`enable`) для пристроїв,
де це потрібно для виконання команд резервного копіювання (наприклад `show running-config`).

Поведінка має бути **опційною**: якщо `enable_password` відсутній у секретах - працюємо без enable.

---

## Контекст
Після виконання `task-023-cisco-ssh-connection.md` NetConfigBackup має встановлювати SSH-зʼєднання
з Cisco та визначати prompt (`>` або `#`).

Для багатьох моделей/політик доступу:
- `show running-config` може бути недоступним у режимі `>`
- або показує неповний вивід без `enable`

Тому необхідно реалізувати керований перехід у `#`.

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

`enable_password` є опційним.

---

## Вимоги до реалізації

### 1) Умови виконання enable
- Якщо після SSH login prompt вже `#`:
  - enable **не виконувати**
- Якщо prompt `>`:
  - виконувати enable **лише якщо** у секретах є `enable_password`
- Якщо `enable_password` відсутній:
  - залишатись у `>` і продовжити роботу (без падіння)

---

### 2) Логіка виконання enable
Для prompt `>` і наявного `enable_password`:

1) виконати команду:
```cisco
enable
```

2) очікувати `Password:` prompt

3) відправити `enable_password`

4) перевірити, що prompt став `#`

Timeouts:
- кожен крок має мати timeout (конфігурований або дефолт 5–10 сек)

---

### 3) Обробка помилок
Варіанти помилок:
- некоректний `enable_password`
- неочікуваний prompt
- timeout очікування `Password:` або `#`

Поведінка:
- логувати ERROR
- для цього пристрою:
  - або зупинити Cisco-пайплайн (рекомендовано, бо без enable можуть бути неповні дані)
  - або (опційно) продовжити без enable, але з WARNING (якщо це явно дозволено конфігом)

У цій задачі прийняти базовий варіант:
- якщо enable був потрібен (є `enable_password`), але не вдалось - **fail for this device** (пропустити бекап цього пристрою)

---

### 4) Логування
Обовʼязково логувати:

- INFO:
  - `device=<name> enable not required (already privileged)`
- INFO:
  - `device=<name> enable requested`
- INFO:
  - `device=<name> enable ok`
- INFO (коли секрет відсутній):
  - `device=<name> enable skipped (no enable_password)`
- ERROR:
  - `device=<name> enable failed`

⚠️ Паролі не логувати.

---

### 5) Інтеграція
- Реалізація має бути доступна з Cisco client (наприклад `CiscoClient.ensure_enable(...)`)
- Викликати enable перед командами, що вимагають `#` (наприклад перед `terminal length 0`, `show running-config`)

---

### 6) Документація (README.md)
Оновити README.md (UA + EN, якщо використовується двомовність):
- пояснити `enable_password` у `config/secrets.yml`
- пояснити, що enable є опційним
- зазначити, що без enable можуть бути обмеження доступу до конфігу

---

## Область змін
Очікувані файли для змін/додавання:

- `src/app/cisco/client.py`
- Cisco backup pipeline у `scripts/run.py` (або відповідному модулі)
- `config/secrets.yml.example` (додати `enable_password` як optional приклад)
- `README.md`

---

## Acceptance criteria
- Для Cisco-пристрою з prompt `#` - enable не виконується
- Для prompt `>` з наявним `enable_password` - виконуються `enable` + password і отримується `#`
- Для prompt `>` без `enable_password` - enable пропускається, лог INFO присутній
- При помилковому `enable_password` - лог ERROR, backup для пристрою не виконується (пропуск)
- Секрети не потрапляють у логи
- README.md оновлено відповідно до нового параметра

---

## Результат
NetConfigBackup підтримує privileged EXEC mode для Cisco через керований перехід `enable`,
що забезпечує коректне виконання наступних кроків (disable paging, running-config backup).
