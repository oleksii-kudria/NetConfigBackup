# task-013-mikrotik-binary-backup-verification-and-cleanup.md

## Мета
Додати обовʼязкову **перевірку (verification) бінарного backup-файлу** MikroTik після його завантаження на локальну систему та реалізувати **очищення файлу з роутера** після успішного завершення.

Ця задача стосується **binary backup**, створеного через `/system backup save`.

---

## Контекст
У task-011 було додано створення та завантаження бінарного backup-файлу (`*.backup`) з MikroTik.

Для коректного та безпечного використання необхідно:
- переконатись, що файл **дійсно завантажився**
- не залишати чутливі backup-файли у файловій системі маршрутизатора

---

## Вимоги

### 1) Перевірка після завантаження (sanity-check)
Після завершення завантаження binary backup на локальну систему необхідно виконати мінімальну перевірку:

- файл **існує** на локальній файловій системі
- розмір файлу **більше 0 байт**

Ці перевірки є **обовʼязковими**.

---

### 2) Успішний сценарій
Якщо sanity-check пройдено успішно:

- вважати binary backup **валідним**
- виконати очищення файлу з MikroTik:
```mikrotik
/file remove <filename>
```

- логувати:
  - успішну верифікацію
  - успішне видалення файлу з пристрою

---

### 3) Неуспішний сценарій
Якщо sanity-check **не пройдено**:

- файл **НЕ видаляти** з маршрутизатора
- логувати помилку
- binary backup вважається **failed**
- текстовий `/export` backup при цьому **не вважається зламаним**

---

## Логування

### Обовʼязкові лог-повідомлення
- `INFO binary-backup downloaded path=<path>`
- `INFO binary-backup verification passed size=<bytes>`
- `INFO binary-backup remote file removed file=<filename>`

### При помилках
- `ERROR binary-backup verification failed reason=<missing|zero-size>`
- `WARNING binary-backup remote file kept for manual recovery`

Жодні чутливі дані **не логуються**.

---

## Реалізація в коді

### Орієнтовні файли
- (оновити) `src/app/mikrotik/backup.py`
- (оновити) `src/app/mikrotik/client.py`
- (опційно) `src/app/core/storage.py`

### Рекомендовані функції
```python
def verify_binary_backup(path: str) -> bool:
    ...

def cleanup_remote_backup(filename: str) -> None:
    ...
```

---

## Acceptance criteria
- Після завантаження binary backup:
  - файл існує
  - size > 0
- При успішній перевірці:
  - файл видаляється з MikroTik
  - подія зафіксована в логах
- При неуспішній перевірці:
  - файл **не видаляється**
  - лог містить причину
- Backup-процес не завершується аварійно через cleanup

---

## Результат
NetConfigBackup гарантує, що бінарні backup-файли MikroTik:
- коректно завантажені
- перевірені на базову цілісність
- не залишаються у файловій системі маршрутизатора після успішного бекапу.
