# task-008-debug-mode.md

## Мета
Додати **DEBUG-режим** у проєкт **NetConfigBackup**, який дозволяє під час запуску скрипту бачити детальний хід виконання: що саме відбувається, у якій послідовності та з якими параметрами (без розкриття секретів).

DEBUG-режим має впливати **лише на рівень логування**, а не на бізнес-логіку роботи скрипту.

---

## Загальні вимоги
- DEBUG-режим вмикається **явно**
- DEBUG керує verbosity логів
- DEBUG не змінює логіку виконання
- DEBUG не розкриває паролі або секрети
- Реалізація базується на стандартному модулі `logging`

---

## 1) CLI параметр

У `scripts/run.py` додати параметр запуску:

```bash
--debug
```

Поведінка:
- якщо `--debug` вказано - рівень логування встановлюється в `DEBUG`
- якщо не вказано - використовується рівень з `config/local.yml` або дефолтний `INFO`

---

## 2) Пріоритети рівня логування

Рівень логування визначається за наступним порядком:
1. CLI параметр `--debug`
2. `config/local.yml` → `logging.level`
3. Дефолтне значення `INFO`

CLI завжди має найвищий пріоритет.

---

## 3) Поведінка DEBUG-режиму

У DEBUG-режимі мають логуватись:

- завантаження конфігів (`devices.yml`, `local.yml`)
- кількість знайдених пристроїв
- кількість пристроїв за вендорами
- вибір BACKUP_DIR та джерело (CLI / local.yml / fallback)
- кроки підключення до пристроїв
- виконувані команди (без секретів)
- обʼєм отриманих даних (bytes)
- шлях збереження бекапів
- рішення про fallback або skip

---

## 4) Заборонено в DEBUG-режимі

Навіть у DEBUG **ЗАБОРОНЕНО** логувати:
- паролі
- значення секретів
- відповідності `secret_ref → password`
- raw SSH session dumps

---

## 5) Приклади DEBUG-логів

```
DEBUG | loading devices from config/devices.yml
DEBUG | total devices loaded=5
DEBUG | mikrotik devices selected=2
DEBUG | backup_dir source=cli path=./backup
DEBUG | connecting to device=main-mikrotik host=10.0.0.1 port=22
DEBUG | ssh connection established device=main-mikrotik
DEBUG | executing command='/export show-sensitive=false'
DEBUG | export received bytes=48231
DEBUG | saving backup to ./backup/mikrotik/main-mikrotik/2025-01-03_221530_export.rsc
```

---

## 6) Реалізація в коді

### Оновлення файлів
- `scripts/run.py`
  - додати парсинг `--debug`
  - передати інформацію в logging setup
- `src/app/core/logging.py`
  - підтримати встановлення рівня логування з CLI
  - не змінювати формат логів

---

## 7) Інтеграція з local.yml

Файл `config/local.yml` (та `local.yml.example`) може містити:

```yml
logging:
  level: INFO
```

Якщо вказано `--debug`, значення з `local.yml` ігнорується.

---

## Acceptance criteria
- `--debug` вмикає детальне логування
- Без `--debug` працює стандартний режим
- DEBUG не змінює логіку виконання
- DEBUG не розкриває секрети
- DEBUG працює для:
  - завантаження конфігів
  - вибору BACKUP_DIR
  - backup MikroTik
  - обробки помилок

---

## Результат
NetConfigBackup підтримує керований DEBUG-режим, який спрощує налагодження, аналіз помилок та контроль виконання без ризику витоку чутливих даних.
