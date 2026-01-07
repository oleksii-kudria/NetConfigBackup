# task-034-fix-mikrotik-diff-false-negative-and-device-path-mismatch.md

## Мета
Виправити проблему, коли для MikroTik `/export` **є реальні зміни у файлах**, але NetConfigBackup
помилково визначає `config_changed=false`, через що **не створюється diff файл**.

Додатково: виправити/захиститись від ситуації, коли в логах/шляхах змішується `device` (наприклад `device=petrov-mikrotik`, але шлях містить `.../main-mikrotik/...`), що може призводити до порівняння “не тих” файлів.

---

## Симптоми (приклад)
Є зміни у конфігу (наприклад зʼявились рядки):

```
/system ntp client
set enabled=yes
```

Але в логах:
- `diff baseline=... current=...`
- `config_changed=false`
- diff файл не створюється

Також спостерігається невідповідність device в логах і device у шляху збереження.

---

## Підозрювані причини (що треба перевірити та закрити)
1) Diff/Hash рахується не з реальних файлів (помилка з шляхами: відкривається не той файл або один і той самий файл).
2) Нормалізація MikroTik export випадково прибирає/ігнорує рядки, що мають залишатись.
3) Базовий/поточний файл обирається з неправильного device-dir через змішування `device.name` або `log_extra`.

---

## Вимоги до виправлення

### 1) Diff повинен працювати по абсолютних/повних шляхах
У модулі diff (або у виклику diff з pipeline):
- передавати `Path` до baseline/current як **повні шляхи**
- при відкритті файлів використовувати тільки ці `Path`, без reliance на cwd

У логах замінити:
- `baseline=<filename> current=<filename>`
на
- `baseline_path=<full_path> current_path=<full_path>`

---

### 2) Логування контрольних метрик для debug
Додати DEBUG (або INFO у debug-mode) перед визначенням `config_changed`:
- `baseline_size_bytes=<int>`
- `current_size_bytes=<int>`
- `baseline_sha256=<hash>`
- `current_sha256=<hash>`
- `baseline_lines=<int>`
- `current_lines=<int>`

⚠️ Вміст конфігів і diff у логи не виводити.

---

### 3) Виправити / спростити нормалізацію MikroTik export
Переконатись, що для MikroTik export нормалізація **не видаляє** конфіг-команди.
Допустимі операції нормалізації (лише ці, або чітко обґрунтований мінімум):
- уніфікація кінців рядків `\r\n` -> `\n`
- rstrip() для кожного рядка (опційно)
- видалення порожніх рядків у кінці файла

Заборонено (для MikroTik export) без окремої узгодженої задачі:
- regex фільтрація блоків `/system ...`
- видалення рядків з `ntp`, `time`, `clock` тощо

---

### 4) Виправити “device mismatch” (log_extra / шлях збереження)
Забезпечити, що `device.name` для поточного циклу обробки пристрою використовується послідовно:
- у формуванні `backup_dir`
- у baseline/current пошуку
- у `log_extra` (`device=<device.name>`)

Додати guard:
- якщо `device.name` не співпадає з директорією пристрою, логувати ERROR і fail цей device (щоб не псувати дані).

---

### 5) Поведінка при реальних змінах
Якщо hash різний:
- `config_changed=true`
- створити diff файл (як у task-029)
- логувати change summary (added/removed)
- diff файл створювати в тій же директорії, що і current backup

---

### 6) Регресійні тести / перевірка
Мінімум - додати unit-тест (якщо тестовий каркас є) або простий інтеграційний сценарій:
- два штучні `.rsc` файли, де другий містить додаткові рядки (наприклад NTP)
- очікування:
  - `config_changed=true`
  - `diff` файл створений
  - hashes різні

Також перевірити кейс “без змін”:
- `config_changed=false`
- diff файл не створюється

---

## Область змін
Очікувані файли:
- модуль diff/normalize (наприклад `src/app/common/diff.py`, `src/app/common/normalize.py`)
- Mikrotik pipeline після збереження export
- логіка формування шляхів device backup dir
- (опційно) тести

---

## Acceptance criteria
- Якщо в `.rsc` файлах є різниця (наприклад додані `/system ntp client` рядки):
  - `config_changed=true`
  - diff файл створюється
  - логи містять `baseline_path`/`current_path` та sha256/size
- Якщо різниці немає:
  - `config_changed=false`
  - diff файл не створюється
- Немає ситуацій, коли один device зберігає/порівнює файли в директорії іншого device
- Нормалізація MikroTik не видаляє значимі рядки конфігів

---

## Результат
Diff для MikroTik `/export` стає надійним:
- без false negative
- без плутанини device/шляхів
- з достатнім діагностичним логуванням для швидкого пошуку подібних проблем.
