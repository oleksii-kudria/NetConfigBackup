# task-029-config-diff-and-change-summary.md

## Мета
Додати механізм **diff + change summary** для бекапів:

- MikroTik export (`.rsc`)
- Cisco running-config (`.txt`)

Щоб після кожного бекапу можна було надійно визначити:
- чи є зміни (`config_changed=true/false`)
- коротке зведення змін (скільки рядків додано/видалено)
- (опційно) зберегти diff у файл

---

## Контекст
Зараз NetConfigBackup зберігає конфіги (MikroTik export / Cisco running-config). Потрібно додати контроль змін між **двома останніми** бекапами кожного типу для кожного пристрою.

Важливо:
- diff робимо по **нормалізованому** тексту (щоб прибрати шум)
- raw конфіги залишаємо без модифікації
- повний diff у лог не виводимо

---

## Вимоги

### 1) Визначення “попереднього” та “поточного” бекапу
Для кожного пристрою і для кожного типу бекапу:

- знайти **останній** та **передостанній** файли у директорії пристрою
- орієнтир - timestamp у назві файлу (або mtime, якщо timestamp відсутній)

Мінімальна логіка:
- якщо попереднього файла немає - `config_changed=null`, diff не створювати

---

### 2) Нормалізація перед diff
Додати функцію нормалізації текстового конфігу, щоб прибирати динамічні/шумні рядки.

#### MikroTik export
- уніфікувати кінці рядків (`\n`)
- прибрати порожні рядки в кінці

#### Cisco running-config
Прибрати рядки з маркерами на кшталт:
- `! Last configuration change`
- часові мітки / uptime (якщо присутні)
- інші відомі volatile рядки (додати як список regex)

⚠️ Нормалізація має бути консервативною: не видаляти конфіг-команди, лише volatile метадані.

---

### 3) Обчислення “changed”
Після нормалізації:

- обчислити SHA256 для normalized content
- якщо hash однаковий => `config_changed=false`
- якщо різний => `config_changed=true`

---

### 4) Change summary
Якщо `config_changed=true`:

- сформувати коротке summary:
  - `lines_added=<N>`
  - `lines_removed=<M>`

Рекомендація:
- використовувати `difflib.unified_diff`
- рахувати додані/видалені рядки (без заголовків diff)

---

### 5) Diff файл (опційно, але бажано)
Якщо `config_changed=true`, зберігати unified diff у файл поруч з бекапом:

- Для MikroTik export:
  - `<timestamp>_export.diff`
- Для Cisco running-config:
  - `<timestamp>_running-config.diff`

Diff файл:
- текстовий
- не логувати diff у stdout

---

### 6) Логування
Обовʼязково логувати (для кожного пристрою, для кожного типу):

- INFO:
  - `device=<name> diff baseline=<prev_file> current=<cur_file>`
- INFO:
  - `device=<name> config_changed=<true|false|null>`
- INFO (якщо true):
  - `device=<name> change_summary added=<N> removed=<M> diff_file=<path>`
- DEBUG:
  - `device=<name> normalized_hash=<sha256>`

⚠️ Не логувати повний diff і не логувати вміст конфігу.

---

### 7) Взаємодія з feature flags та dry-run
- Якщо `--dry-run` - diff не виконуємо (бо файли не створюються), лише лог `dry_run skipping diff`.
- Якщо запущено тільки частину підзадач (task-027) - diff робимо лише для тих типів, які реально виконувались у цьому запуску.

---

### 8) Документація (README.md)
Оновити README (UA + EN, якщо двомовність вже використовується):
- описати, що NetConfigBackup:
  - визначає `config_changed`
  - формує short summary
  - може зберігати `.diff` файли

---

## Область змін
- модуль для diff/normalize (наприклад `src/app/common/diff.py`, `src/app/common/normalize.py`)
- виклики у Mikrotik pipeline після збереження export
- виклики у Cisco pipeline після збереження running-config
- README.md

---

## Acceptance criteria
- Для MikroTik export і Cisco running-config після збереження файла:
  - визначається `config_changed`
  - формується summary added/removed (якщо changed)
  - створюється `.diff` файл (якщо changed)
- У логах є `config_changed` і summary, без витоку секретів
- В dry-run diff не виконується
- README.md оновлено
