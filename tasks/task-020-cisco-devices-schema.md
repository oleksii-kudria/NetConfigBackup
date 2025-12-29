# task-020-cisco-devices-schema.md

## Мета
Описати та впровадити **схему опису Cisco-пристроїв** у файлі `config/devices.yml`, яка буде
використовуватись NetConfigBackup для підключення та зняття конфігураційних бекапів.

Критична вимога: **жодні паролі/секрети не зберігаються в `devices.yml`**.
Усі секрети мають бути винесені в окремий файл `config/secrets.yml` (який не комітиться).

Схема має бути розширюваною та узгодженою з уже існуючою моделлю для MikroTik.

---

## Контекст
NetConfigBackup вже підтримує опис пристроїв у `config/devices.yml` та окреме зберігання секретів.
Для Cisco необхідно формалізувати:

- які поля знаходяться в `devices.yml` (тільки не-чутливі)
- як виконувати привʼязку секретів з `secrets.yml`
- як це відображається в логах та README

---

## 1) Схема Cisco в `config/devices.yml` (без секретів)

### Базовий приклад
```yml
devices:
  - vendor: cisco
    name: core-sw-01
    ip: 10.0.0.1
    ssh_port: 22
    username: backup
    secrets_ref: core-sw-01
```

---

## 2) Секрети Cisco в `config/secrets.yml`

### Базовий приклад
```yml
secrets:
  core-sw-01:
    password: "CHANGE_ME"
    enable_password: "CHANGE_ME_ENABLE"
```

Правила:
- ключ під `secrets:` є **ідентифікатором секретів**
- `devices.yml` посилається на секрети через `secrets_ref`
- `enable_password` є опційним

---

## Опис полів `devices.yml`

### Обовʼязкові
- `vendor`
  - значення: `cisco`
- `name`
  - унікальне логічне імʼя пристрою
  - використовується:
    - у логах
    - у назвах директорій
    - у назвах файлів
- `ip`
  - IPv4 або IPv6 адреса пристрою
- `username`
  - користувач для SSH-підключення
- `secrets_ref`
  - ключ для пошуку секретів у `config/secrets.yml`

---

### Опційні
- `ssh_port`
  - порт SSH
  - за замовуванням: `22`
- `platform`
  - тип Cisco OS (на майбутнє)
  - можливі значення:
    - `ios`
    - `iosxe`
    - `nxos`

---

## Опис полів `secrets.yml`

### Обовʼязкові
- `password`
  - пароль користувача для SSH

### Опційні
- `enable_password`
  - пароль для переходу в privileged mode (`enable`)

---

## Вимоги до реалізації

### 1) Парсинг `devices.yml`
- Cisco-пристрої визначаються за `vendor: cisco`
- Валідувати:
  - наявність обовʼязкових полів у `devices.yml`
  - унікальність `name`
  - наявність `secrets_ref`
- У разі помилки:
  - логувати `ERROR`
  - пропускати некоректний пристрій
  - не зупиняти виконання для інших пристроїв

---

### 2) Завантаження та привʼязка секретів
- зчитати `config/secrets.yml` (якщо файл існує)
- знайти `secrets[<secrets_ref>]`
- валідувати:
  - наявність `password`
  - `enable_password` опційний
- якщо секретів немає:
  - логувати `ERROR device=<name> missing secrets for secrets_ref=<...>`
  - пропустити пристрій (Cisco backup неможливий)

⚠️ Секрети не логувати і не виводити у stdout.

---

### 3) Логування
Обовʼязково логувати:

- INFO:
  - `device=<name> vendor=cisco loaded from devices.yml`
- INFO:
  - `device=<name> secrets_ref=<ref> secrets_loaded=true`
- ERROR:
  - відсутні обовʼязкові поля
  - відсутній `secrets_ref`
  - відсутній `secrets.yml` або відповідний ключ
- DEBUG:
  - повний набір не-чутливих параметрів (ip, port, username, platform)

---

### 4) `.gitignore`
- переконатися, що `config/secrets.yml` вже виключений у `.gitignore`
- додати `config/secrets.yml.example` (без реальних секретів)

---

### 5) Документація
Оновити `README.md` (UA + EN, якщо вже є двомовність):
- описати формат Cisco-пристрою в `devices.yml`
- описати формат `secrets.yml` для Cisco
- навести приклади
- підкреслити, що секрети не комітяться і зберігаються локально

---

## Acceptance criteria
- В `devices.yml` відсутні паролі/секрети (парсер/валідація це контролює)
- Cisco-пристрої коректно описуються через `secrets_ref`
- `secrets.yml` підтримує `password` та опційний `enable_password`
- Некоректні записи логуються та пропускаються
- README.md і `config/secrets.yml.example` оновлені/додані

---

## Результат
NetConfigBackup має формалізовану, задокументовану та безпечну схему опису Cisco-пристроїв:
- **не-чутливі дані** у `devices.yml`
- **усі секрети** у `secrets.yml`
- коректна валідація та логування для подальших Cisco-задач.
