# task-019-mikrotik-system-backup-optional-no-remote-cleanup.md

## Мета
Зробити створення бінарного бекапу MikroTik через `/system backup save` **опційною функцією**, яка вмикається лише за явною опцією запуску (CLI) або налаштуванням у `config/local.yml`.

Також необхідно **прибрати код**, який видаляє (`/file remove ...`) backup-файл з маршрутизатора після завантаження.

---

## Контекст
Наразі system-backup (binary `.backup`) виконується як частина стандартного пайплайну MikroTik і включає cleanup remote file.

Через обмеження різних середовищ (права, нестабільність file-операцій/SSH exec, вимоги до збереження артефактів на пристрої) потрібно:
- робити system-backup **тільки за потреби**
- не виконувати автоматичне видалення файлу з маршрутизатора

---

## Вимоги

### 1) Нова CLI опція
Додати опцію до `scripts/run.py`:

- `--mikrotik-system-backup` (boolean flag)

Правила:
- за замовчуванням `False` (вимкнено)
- якщо прапорець вказаний - system-backup виконується

---

### 2) Налаштування в `config/local.yml`
Додати в `config/local.yml` (та `config/local.yml.example`) параметр:

```yml
mikrotik:
  system_backup: false
```

Правила пріоритету:
- CLI `--mikrotik-system-backup` має **пріоритет** над `local.yml`
- якщо CLI не вказаний - використовувати значення з `local.yml`
- якщо ключ відсутній - трактувати як `false`

---

### 3) Поведінка backup-пайплайна
Для кожного пристрою `vendor: mikrotik`:

- `/export` виконується завжди (як і раніше)
- `/system backup save` виконується **лише** якщо `system_backup=true`

---

### 4) Прибрати remote cleanup
Необхідно видалити/відключити весь код, який:
- виконує `/file remove ...`
- виконує будь-яку перевірку існування файлу на маршрутизаторі виключно для видалення
- логує “remote file removed” або схожі події

Після змін:
- backup-файл **залишається** на маршрутизаторі
- допускається логування інформації:
  - `INFO remote cleanup disabled; file kept on device file=<remote_file>`

---

### 5) Логування
Обовʼязково логувати:

- коли system-backup вимкнено:
  - `INFO mikrotik system-backup disabled (skipping) device=<name>`
- коли system-backup увімкнено:
  - `INFO creating system-backup device=<name> backup_file=<...>`
  - `INFO system-backup saved path=<local_path> size=<bytes>`
- про відсутність cleanup:
  - `INFO remote cleanup disabled; file kept on device file=<remote_file>`

Жодні секрети не логувати.

---

### 6) Оновлення документації
Оновити `README.md` (UA + EN, якщо вже є двомовність):
- описати опцію `--mikrotik-system-backup`
- описати параметр `mikrotik.system_backup` у `local.yml`
- зазначити, що remote cleanup не виконується, і файл залишається на пристрої

---

## Область змін
Перевірити та оновити (за потреби):

- `scripts/run.py` (CLI опція, виклик system-backup)
- `src/app/mikrotik/backup.py` (умовний запуск, видалення cleanup-логіки)
- `src/app/mikrotik/client.py` (видалення функцій/викликів remove remote file)
- `config/local.yml.example`
- `README.md`

---

## Acceptance criteria
- Без опції `--mikrotik-system-backup`:
  - виконується лише `/export`
  - system-backup пропускається з INFO-логом
- З опцією `--mikrotik-system-backup`:
  - виконується `/system backup save`
  - файл завантажується та верифікується локально (exists + size > 0)
- Код remote cleanup відсутній:
  - немає викликів `/file remove`
  - немає логів “remote file removed”
- README.md та `config/local.yml.example` оновлені

---

## Результат
NetConfigBackup підтримує бінарний system-backup MikroTik як опційний режим, що вмикається явним параметром, і більше не виконує автоматичне видалення backup-файлів з маршрутизатора.
