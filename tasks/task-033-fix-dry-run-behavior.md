# task-033-fix-dry-run-behavior.md

## Мета
Виправити роботу **dry-run режиму**, щоб під час запуску з опцією `--dry-run`
**жодні backup-команди не виконувались** і **жодні файли не створювались**,
незалежно від обраних feature flags або дефолтної логіки.

---

## Поточна проблема

Наразі dry-run працює некоректно:

### ❌ Некоректна поведінка
1) Команда:
```
scripts/run.py --dry-run backup
```
Фактично виконує:
- MikroTik `/export`
- створює файли

2) Команда:
```
scripts/run.py --mikrotik-export --mikrotik-system-backup --dry-run backup
```
Фактично:
- виконує `/export`
- виконує `/system backup save`
- зберігає **і export, і system-backup файли**

Це **пряме порушення контракту dry-run**.

---

## Очікувана поведінка (правильна)

### Загальне правило
Якщо задано `--dry-run`:

> **ЖОДНА команда, яка створює або зберігає бекап, не повинна виконуватись**

Незалежно від:
- `backup` як команди
- дефолтної логіки
- наявності або відсутності feature flags

---

## Вимоги

### 1) Глобальний dry-run guard
`--dry-run` має бути **глобальним вимикачем backup-операцій**.

У dry-run **ЗАБОРОНЕНО** виконувати:
- MikroTik:
  - `/export`
  - `/system backup save`
- Cisco:
  - `show running-config`
- будь-яке:
  - створення директорій backup
  - запис файлів
  - diff / retention

---

### 2) Що МОЖНА виконувати у dry-run
У dry-run **ДОЗВОЛЕНО**:
- читати `devices.yml`, `secrets.yml`
- виконувати валідацію конфігів
- перевіряти TCP доступність
- виконувати SSH login
- (Cisco) виконати `enable` (якщо потрібно для перевірки доступу)
- логувати, що backup-кроки пропущені

---

### 3) Єдине місце контролю dry-run
Dry-run має контролюватись **в одному місці**, а не через розкидані `if dry_run`:

#### Рекомендований підхід
У `scripts/run.py`:
- якщо `dry_run=true`:
  - **НЕ викликати** функції, що виконують backup
  - викликати лише:
    - connection-check
    - auth-check
    - preflight (за потреби)

Backup-функції (`mikrotik_export`, `mikrotik_system_backup`, `cisco_running_config`)  
**не повинні самі вирішувати**, dry-run чи ні — вони просто **не викликаються**.

---

### 4) Взаємодія з feature flags
Dry-run має працювати коректно у всіх комбінаціях:

- `scripts/run.py --dry-run backup`
- `scripts/run.py --dry-run --mikrotik-export backup`
- `scripts/run.py --dry-run --mikrotik-export --mikrotik-system-backup backup`
- `scripts/run.py --dry-run --cisco-running-config backup`

У ВСІХ випадках:
- backup-команди **не виконуються**
- файли **не створюються**

---

### 5) Логування
Обовʼязково логувати:

- INFO (на старті):
  - `dry_run=true`
- INFO (для кожного пристрою):
  - `device=<name> dry_run skipping backup tasks`
- DEBUG:
  - `dry_run active: backup functions not invoked`

---

### 6) Регресійна перевірка
Після виправлення необхідно вручну перевірити:

```bash
scripts/run.py --dry-run backup
scripts/run.py --dry-run --mikrotik-export backup
scripts/run.py --dry-run --mikrotik-export --mikrotik-system-backup backup
scripts/run.py --dry-run --cisco-running-config backup
```

Очікування:
- відсутні нові файли у backup-директорії
- у логах явно видно, що backup-кроки пропущені

---

## Область змін
- `scripts/run.py` (основна логіка dry-run)
- можливо: маршрутизація feature flags
- README.md (уточнення dry-run поведінки, якщо опис був неточний)

---

## Acceptance criteria
- У dry-run **НЕ створюється жодного backup-файлу**
- `/export`, `/system backup save`, `show running-config` **не виконуються**
- Поведінка dry-run не залежить від feature flags
- Логи чітко показують пропуск backup-кроків
- Звичайний режим (без `--dry-run`) працює без змін

---

## Результат
Dry-run режим відповідає своєму призначенню:
- безпечна перевірка доступу
- без змін на пристроях
- без створення файлів
- передбачувана та стабільна поведінка
