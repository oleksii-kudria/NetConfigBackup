# task-006-backup-dir-rules.md

## Мета
Додати правила визначення директорії для збереження бекапів (**BACKUP_DIR**) у проєкті **NetConfigBackup**.

BACKUP_DIR може задаватися:
1) через параметр запуску `scripts/run.py --backup-dir BACKUP_DIR`
2) через `config/local.yml` (секція `backup.directory`)

Якщо BACKUP_DIR не задано або директорія недоступна для запису - використовувати fallback `./backup/`.

Усі рішення щодо вибору директорії мають бути відображені в логах.

---

## Вимоги

### 1) CLI параметр
Додати в `scripts/run.py` параметр:
- `--backup-dir BACKUP_DIR`

Правило пріоритету:
1. CLI `--backup-dir`
2. `config/local.yml` (`backup.directory`)
3. fallback `./backup/`

---

### 2) config/local.yml
Додати секцію в `config/local.yml` (та у приклад `config/local.yml.example`):

```yml
backup:
  directory: /path/to/backups
```

> `local.yml` не комітиться, `local.yml.example` комітиться.

---

### 3) Fallback директорія
Якщо BACKUP_DIR не задано ні в CLI, ні в `config/local.yml`, то:
- створити директорію `./backup/` (якщо не існує)
- використовувати її як BACKUP_DIR

---

### 4) Перевірка доступності директорії
Перед використанням BACKUP_DIR необхідно перевірити:
- чи існує директорія (якщо ні - спробувати створити)
- чи є права на запис (write permission)
- чи реально можна створити файл в цій директорії (практична перевірка)

Якщо перевірка не пройдена:
- логувати warning/error (без секретів)
- використовувати fallback `./backup/`

---

### 5) Логування
У логах обовʼязково відобразити:
- яке джерело обрано (CLI / local.yml / fallback)
- який шлях встановлено як BACKUP_DIR
- якщо був fallback - причину (немає прав / не вдалося створити / інша помилка)

Приклади повідомлень:
- `INFO | backup_dir source=cli path=/data/backups`
- `INFO | backup_dir source=local_yml path=/data/backups`
- `WARNING | backup_dir fallback=./backup reason="permission denied: /data/backups"`

---

### 6) .gitignore
Додати/переконатися, що у `.gitignore` є:
```
backup/
```

> Саме `./backup/` (директорія для результатів) не повинна комітитися.

---

## Реалізація в коді

### Рекомендовані файли
- (оновити) `scripts/run.py` - додати `--backup-dir` та пріоритет
- (оновити/додати) `src/app/core/storage.py` - функція визначення та перевірки backup_dir
- (оновити) `config/local.yml.example` - додати секцію `backup.directory`

### Рекомендована функція
У `src/app/core/storage.py` реалізувати:
```python
def resolve_backup_dir(cli_backup_dir: str | None, local_cfg: dict | None, logger) -> str:
    ...
```

---

## Критерії приймання
- `--backup-dir` працює та має найвищий пріоритет
- Якщо заданий шлях недоступний - виконується fallback на `./backup/`
- Якщо шлях не задано - створюється та використовується `./backup/`
- Усі рішення логуються
- `backup/` додано до `.gitignore`
- `config/local.yml.example` містить секцію `backup.directory`

---

## Результат
NetConfigBackup завжди має валідну директорію для збереження бекапів, визначену за зрозумілими правилами, з fallback та прозорим логуванням.
