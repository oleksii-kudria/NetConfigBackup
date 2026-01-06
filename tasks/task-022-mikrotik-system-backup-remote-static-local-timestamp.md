# task-022-mikrotik-system-backup-remote-static-local-timestamp.md

## Мета
Змінити логіку іменування **бінарного system-backup MikroTik**, розділивши її на два рівні:

- **на маршрутизаторі** - стабільне імʼя файлу без дати  
- **локально** - імʼя з додаванням timestamp

Також необхідно **прибрати видалення файлу з маршрутизатора**, оскільки на пристрої має зберігатися **остання актуальна версія бекапу**.

---

## Контекст
Наразі system-backup створюється з іменем, яке містить timestamp, після чого файл:
- завантажується локально
- перейменовується
- видаляється з маршрутизатора

Такий підхід ускладнює логіку cleanup і не дозволяє мати актуальний бекап безпосередньо на MikroTik.

---

## Нова логіка іменування

### 1) Імʼя файлу на маршрутизаторі
При створенні system-backup через:

```
/system backup save
```

використовувати **тільки імʼя пристрою** з `config/devices.yml`:

```yml
devices:
  - name: main-mikrotik
```

Remote filename:
```
main-mikrotik.backup
```

⚠️ У команді `/system backup save` **НЕ додавати** розширення `.backup`:
```
/system backup save name=main-mikrotik
```

RouterOS додасть `.backup` автоматично.

---

### 2) Імʼя файлу при локальному збереженні
Після завантаження файлу з маршрутизатора в локальну директорію backup,
файл необхідно **перейменувати**, додавши timestamp:

```
main-mikrotik_2025-12-28_121400.backup
```

Формат:
```
<device.name>_<YYYY-MM-DD_HHMMSS>.backup
```

---

## Поведінка щодо файлу на маршрутизаторі

### ❌ Прибрати cleanup
Повністю прибрати логіку:

```
/file remove [find where name="FILENAME"]
```

Після змін:
- файл `main-mikrotik.backup` **залишається на маршрутизаторі**
- кожен новий `/system backup save` **перезаписує попередній файл**

---

## Вимоги до реалізації

### 1) Формування імен
- `device.name` береться **виключно** з `config/devices.yml`
- імʼя не повинно змінюватись (ніяких suffix/prefix)
- використовувати одне джерело істини для імені

---

### 2) Локальне збереження
- файл завантажується з маршрутизатора як `<device.name>.backup`
- після завантаження:
  - перевірити `exists`
  - перевірити `size > 0`
  - виконати перейменування з додаванням timestamp

---

### 3) Логування
Обовʼязково логувати:

- INFO:
  - `creating system-backup device=<name> remote_file=<name>.backup`
- INFO:
  - `system-backup downloaded local_file=<name>_<timestamp>.backup size=<bytes>`
- INFO:
  - `remote system-backup file kept on device file=<name>.backup`

Жодних логів про cleanup бути не повинно.

---

### 4) Область змін
Оновити за потреби:

- `src/app/mikrotik/backup.py`
- `src/app/mikrotik/client.py`
- логіку формування імен файлів
- логіку cleanup (повністю прибрати)

---

### 5) Документація
Оновити `README.md` (UA + EN, якщо використовується двомовність):

- описати нову логіку іменування system-backup
- зазначити, що:
  - на MikroTik зберігається лише останній бекап
  - локально зберігається історія з timestamp

---

## Acceptance criteria
- На маршрутизаторі файл має імʼя `<device.name>.backup`
- Файл **не видаляється** з маршрутизатора
- Локальний файл має імʼя з timestamp
- Cleanup через `/file remove` відсутній у коді
- Логи коректно відображають нову логіку

---

## Результат
NetConfigBackup використовує просту та надійну модель:
- **один актуальний system-backup на MikroTik**
- **версіоновані backup-файли локально**
- мінімальна складність і відсутність помилок cleanup
