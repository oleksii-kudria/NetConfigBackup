# task-027-backup-feature-flags-mikrotik-export-cisco-running-config.md

## Мета
Додати керування виконанням бекапів через **feature flags (CLI опції)** за аналогією з існуючим `--mikrotik-system-backup`:

- `--mikrotik-export` - запускати тільки MikroTik `/export` (text backup)
- `--cisco-running-config` - запускати тільки Cisco `show running-config` (text backup)

Також змінити логіку вибору задач так, щоб при наявності одного чи кількох прапорців запускались **лише** відповідні підзадачі.

---

## Контекст
Зараз NetConfigBackup має (або буде мати) окремі кроки бекапу:
- MikroTik export (`/export`) - виконується за замовчуванням
- MikroTik system backup (`/system backup save`) - опційно
- Cisco running-config (`show running-config`) - базовий Cisco backup

Користувачеві потрібно мати можливість запускати окремі частини або їх комбінацію, не виконуючи інші кроки.

---

## Вимоги

### 1) Нові CLI опції
Додати до `scripts/run.py`:

- `--mikrotik-export` (boolean flag)
- `--cisco-running-config` (boolean flag)

Прапорці мають відображатись у `--help`.

---

### 2) Логіка виконання залежно від прапорців

#### 2.1 Якщо **жоден** з feature-флагів не вказаний
Поведінка (default mode):
- виконувати стандартний пайплайн як зараз (поточна дефолтна логіка проєкту)
  - для MikroTik: export виконується за замовчуванням
  - для Cisco: running-config виконується за замовчуванням (якщо Cisco уже підтримано)
  - system-backup залежить від поточної дефолтної логіки (може бути вимкнено)

⚠️ Важливо: ця задача НЕ змінює дефолтний режим, якщо прапорці не вказані.

#### 2.2 Якщо вказано **хоча б один** feature-флаг
Тоді виконувати **лише** ті підзадачі, для яких передані прапорці.

Приклади (обовʼязково реалізувати саме так):

- `scripts/run.py --mikrotik-system-backup backup`  
  => запускає **тільки** MikroTik system backup

- `scripts/run.py --mikrotik-export backup`  
  => запускає **тільки** MikroTik export

- `scripts/run.py --mikrotik-system-backup --mikrotik-export backup`  
  => запускає **тільки** MikroTik system backup + MikroTik export

- `scripts/run.py --mikrotik-system-backup --mikrotik-export --cisco-running-config backup`  
  => запускає **тільки** MikroTik system backup + MikroTik export + Cisco running-config

---

### 3) Вендор-фільтрація
Під час виконання кожного feature:
- `--mikrotik-export` і `--mikrotik-system-backup` застосовуються **лише** до `vendor: mikrotik`
- `--cisco-running-config` застосовується **лише** до `vendor: cisco`

---

### 4) Логування
Обовʼязково логувати на старті:

- INFO:
  - `selected_features=mikrotik_export,mikrotik_system_backup,cisco_running_config`
  - або `selected_features=default` якщо прапорці не вказані

Для кожного пристрою логувати:
- INFO: `device=<name> vendor=<vendor> selected_tasks=<...>`

---

### 5) Документація (README.md)
Оновити README.md (UA + EN, якщо використовується двомовність):
- описати нові опції:
  - `--mikrotik-export`
  - `--cisco-running-config`
- навести приклади команд (як у секції 2.2)
- пояснити правило:
  - якщо вказаний хоча б один feature-flag, запускаються тільки вибрані підзадачі

---

## Область змін
- `scripts/run.py` (argparse: додати опції, змінити маршрутизацію виконання)
- модулі, які викликають mikrotik/cisco backup підзадачі (за потреби)
- `README.md`

---

## Acceptance criteria
- `scripts/run.py --help` показує нові опції
- При вказанні одного флага запускається лише відповідний backup-крок
- Комбінації флагів працюють як у прикладах
- Без флагів поведінка не змінюється (default mode)
- У логах відображається, які feature flags активні
- README.md містить опис і приклади

---

## Результат
NetConfigBackup дозволяє гнучко запускати окремі частини backup-пайплайну (MikroTik export/system-backup і Cisco running-config) за допомогою CLI feature flags, що спрощує експлуатацію та дебаг.
