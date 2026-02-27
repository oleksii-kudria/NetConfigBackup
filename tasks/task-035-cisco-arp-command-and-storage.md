# task-035-cisco-arp-command-and-storage.md

## Мета
Додати нову CLI-опцію для NetConfigBackup:

- `--cisco-arp`

яка дозволяє збирати ARP-таблицю з Cisco-пристроїв за допомогою команди:

```cisco
show ip arp
```

і зберігати результат у окрему структуру директорій, незалежну від backup-конфігів.

---

## Вимоги

### 1) Нова CLI-опція

Додати до `scripts/run.py` boolean-flag:

- `--cisco-arp`

Вимоги:

- опція має відображатися у `scripts/run.py --help`
- опція може використовуватися:
  - окремо: `scripts/run.py --cisco-arp`
  - у комбінації з іншими опціями (наприклад, `backup`, `--mikrotik-export`, `--cisco-running-config` тощо)

Поведінка:
- якщо задано тільки `--cisco-arp` (без `backup` або інших feature-флагів) – скрипт виконує **лише** збір ARP з Cisco-пристроїв
- якщо `--cisco-arp` вказано разом з іншими опціями – ARP-збір додається до вже обраних задач (vendor-фільтрація: лише Cisco)

---

### 2) Конфіг: директорія для ARP

У `config/local.yml` додати новий блок налаштувань:

```yml
arp:
  directory: ./arp
```

Вимоги:

- якщо `arp.directory` **не задано** в `local.yml`, використовувати значення за замовчуванням `./arp`
- шлях має бути інтерпретований відносно робочої директорії запуску (як і для інших директорій у проєкті)
- директорія створюється автоматично, якщо не існує

---

### 3) Команда на Cisco

Для кожного пристрою з:

```yml
vendor: cisco
```

і при активній опції `--cisco-arp`, виконувати:

```cisco
show ip arp
```

Правила:

- виконувати команду після успішного:
  - SSH-підключення
  - (опційно) enable-mode, якщо це вже реалізовано та потрібно для доступу до `show ip arp`
- читати **повний stdout** до повернення prompt
- не виконувати команду у `--dry-run` режимі (у dry-run тільки перевірка доступності/SSH)

---

### 4) Структура збереження файлів

Використати базову директорію з `local.yml`:

- `arp.directory` (за замовчуванням `./arp`)

Структура збереження:

```
<arp.directory>/cisco/<device.name>/<timestamp>_arp.txt
```

Де:

- `<device.name>` — значення поля `name` з `config/devices.yml` (наприклад `hq-core-sw1`)
- `<timestamp>` — у форматі, який вже використовується у проєкті для інших бекапів (`YYYY-MM-DD_HHMMSS`)

Вимоги:

- директорії `cisco/` та `<device.name>/` створюються автоматично, якщо не існують
- файл не перезаписується (timestamp забезпечує унікальність)

Мінімальний sanity-check:

- файл існує
- size > 0

---

### 5) Логіка виконання / інтеграція з feature flags

- Якщо скрипт запускається **тільки** з `--cisco-arp`, без `backup`:
  - виконати:
    - load config
    - обробити всі `vendor: cisco`
    - підключитись по SSH
    - виконати `show ip arp`
    - зберегти результати
- Якщо `--cisco-arp` використовується разом з іншими флагами (наприклад `backup`, `--mikrotik-export`):
  - ARP-збір додається до набору задач, але:
    - працює **лише для Cisco-пристроїв**
    - не впливає на логіку backup-флагів

У `--dry-run` режимі:

- `show ip arp` **не виконується**
- файли не створюються
- у логах має бути зазначено, що ARP-збір пропущено через `dry_run=true`

---

### 6) Логування

Обовʼязково додати логування:

- INFO на старті:
  - якщо активна опція: `cisco_arp=true`
- Для кожного Cisco-пристрою при виконанні ARP-збору:
  - INFO:
    - `device=<name> collecting cisco arp`
  - INFO після успішного збереження:
    - `device=<name> cisco arp saved path=<path> size=<bytes>`
  - ERROR:
    - `device=<name> cisco arp collection failed` (з коротким описом помилки, без секретів)

Для `--dry-run`:
- INFO:
  - `device=<name> dry_run skipping cisco arp`

---

### 7) Оновлення README.md та help

#### README.md
Додати нову секцію / підсекцію:

- опис опції `--cisco-arp`:
  - що робить
  - де зберігає файли
  - приклади:

```bash
scripts/run.py --cisco-arp
scripts/run.py --cisco-arp --cisco-running-config backup
scripts/run.py --dry-run --cisco-arp
```

#### CLI help
У `scripts/run.py --help`:

- додати опис для `--cisco-arp`
- додати приклад(и) у секції “Examples”:

```text
scripts/run.py --cisco-arp
    Collect ARP tables from Cisco devices (show ip arp)

scripts/run.py --cisco-arp --cisco-running-config backup
    Collect Cisco ARP and running-config in a single run
```

---

## Область змін

- `scripts/run.py`:
  - argparse: додати `--cisco-arp`
  - логіка dispatch для Cisco ARP
- Cisco client/pipeline (наприклад `src/app/cisco/client.py` або окремий модуль):
  - метод на кшталт `fetch_arp_table(...)`
- Обробка `local.yml`:
  - читання блоку `arp.directory` з дефолтом `./arp`
- Оновлення `README.md`
- Оновлення CLI help / examples

---

## Acceptance criteria

- `scripts/run.py --help` показує нову опцію `--cisco-arp` і приклади використання
- `scripts/run.py --cisco-arp`:
  - підключається до всіх Cisco-пристроїв
  - виконує `show ip arp`
  - зберігає файли у `<arp.directory>/cisco/<device.name>/<timestamp>_arp.txt`
- Комбінація з іншими флагами (`--cisco-running-config`, `backup`, MikroTik флаги) працює коректно:
  - ARP збирається тільки для Cisco
  - інші задачі не ламаються
- У `--dry-run` режимі:
  - `show ip arp` не викликається
  - файли не створюються
  - логи відображають пропуск ARP-збору
- README та help актуалізовані.

---

## Результат

NetConfigBackup отримує додаткову діагностичну можливість:
- збір ARP-таблиць з Cisco-пристроїв
- зберігання у структурованому вигляді
- можливість запускати окремо або разом з іншими бекап-задачами.
