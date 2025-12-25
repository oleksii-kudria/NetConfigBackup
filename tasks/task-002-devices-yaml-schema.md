# task-002-devices-yaml-schema.md

## Мета
Описати, реалізувати та задокументувати єдину схему конфігураційного файлу `config/devices.yml`, який використовується для зберігання інвентарю мережевого обладнання Cisco та MikroTik.

Файл **НЕ повинен містити паролів або інших секретів**.

---

## Загальні вимоги
- Формат: YAML
- Файл: `config/devices.yml`
- Один файл описує всі пристрої
- Секрети зберігаються окремо та підтягуються через `secret_ref`

---

## Загальна структура devices.yml

```yml
devices:
  - name: <string>
    vendor: <cisco | mikrotik>
    model: <string>
    host: <ip_or_dns>
    port: <int>            # optional, default 22
    username: <string>
    auth:
      secret_ref: <string>
    backup:
      type: <string>
```

---

## Опис полів

### `devices`
Список пристроїв. Кожен елемент описує один мережевий девайс.

### `name` (обовʼязково)
Унікальна назва пристрою, використовується в логах і шляхах бекапів.

### `vendor` (обовʼязково)
Допустимі значення:
- `cisco`
- `mikrotik`

### `model` (обовʼязково)
Модель пристрою (метадані).

### `host` (обовʼязково)
IP-адреса або DNS-імʼя пристрою.

### `port` (опційно)
SSH порт. Якщо не вказано - використовується `22`.

### `username` (обовʼязково)
Користувач для підключення.

### `auth.secret_ref` (обовʼязково)
Посилання на секрет у `config/secrets.yml`.

### `backup.type` (обовʼязково)
- Cisco: `running-config`
- MikroTik: `export`

---

## Повний приклад devices.yml

```yml
devices:
  - name: hq-core-sw1
    vendor: cisco
    model: C9200L
    host: 192.168.10.2
    username: backup
    auth:
      secret_ref: hq-core-sw1
    backup:
      type: running-config

  - name: travel-mikrotik
    vendor: mikrotik
    model: hAP ax3
    host: 192.168.35.1
    port: 22
    username: backup
    auth:
      secret_ref: travel-mikrotik
    backup:
      type: export
```

---

## Реалізація в коді

### Файли
- `src/app/core/config.py`
- `src/app/core/models.py`

### Вимоги до реалізації
- Завантаження YAML
- Валідація обовʼязкових полів
- Перевірка допустимих значень vendor
- Автоматичне застосування дефолтів
- Людяні повідомлення про помилки

---

## Критерії приймання
- devices.yml читається без помилок
- Паролі відсутні
- Дані валідовані
- Помилки інформативні

---

## Результат
`devices.yml` є єдиним, безпечним та розширюваним джерелом інвентарю для NetConfigBackup.
