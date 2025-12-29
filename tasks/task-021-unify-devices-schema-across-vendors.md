# task-021-unify-devices-schema-across-vendors.md

## Мета
Привести `config/devices.yml.example` (і відповідно очікуваний парсер `config/devices.yml`) до **єдиного плоского формату** для всіх вендорів (MikroTik та Cisco).

Після цього `devices.yml` має використовувати однакові ключі для всіх пристроїв:
- `name`
- `vendor`
- `model` (інформаційне поле, може бути порожнім)
- `ip`
- `port`
- `username`
- `secret_ref`

Також необхідно прибрати зайві та/або передчасні поля (`platform`, `auth.*`, `backup.*`) і оновити документацію.

---

## Контекст / Проблема
Після task-020 Codex додав приклад Cisco у `devices.yml.example`, але формат відрізняється від MikroTik:
- Cisco: `ip`, `ssh_port`, `secrets_ref`, `platform`
- MikroTik: `host`, `port`, вкладені `auth.secret_ref`, `backup.type`

Це ускладнює:
- парсинг
- валідацію
- документацію
- підтримку

Необхідно стандартизувати схему, щоб усі пристрої описувались однаково.

---

## Цільова схема `config/devices.yml`
### Загальний формат
```yml
devices:
  - name: hq-core-sw1
    vendor: cisco
    model: ""
    ip: 192.0.2.10
    port: 22
    username: backup
    secret_ref: hq-core-sw1

  - name: travel-mikrotik
    vendor: mikrotik
    model: hAP ax3
    ip: 198.51.100.5
    port: 22
    username: backup
    secret_ref: travel-mikrotik
```

---

## Вимоги

### 1) Уніфікація полів
Для всіх пристроїв у `devices.yml` використовувати ТІЛЬКИ:
- `name` - назва пристрою
- `vendor` - `mikrotik` або `cisco`
- `model` - інформаційне поле (може бути `""` або відсутнє)
- `ip` - IP пристрою (IPv4/IPv6)
- `port` - порт SSH (default 22)
- `username` - користувач для SSH
- `secret_ref` - посилання на секрети в `config/secrets.yml`

Заборонені/прибрати поля:
- `host` (замінити на `ip`)
- `ssh_port` (замінити на `port`)
- `secrets_ref` (замінити на `secret_ref`)
- `auth.*` (прибрати)
- `backup.*` (прибрати)
- `platform` (прибрати; повернути в майбутньому за потреби)

---

### 2) MikroTik backup settings
- Для MikroTik `backup: type: export` є **зайвими**, оскільки:
  - `/export` виконується за замовчуванням
  - `/system backup save` вмикається окремою CLI-опцією (див. task-019)

Отже, у `devices.yml` не зберігати параметри типу бекапу для MikroTik.

---

### 3) Оновити `config/devices.yml.example`
- Переписати приклади під цільову схему (див. вище)
- Для `model` дозволено:
  - або `model: ""` (щоб показати поле)
  - або пропустити поле повністю (але краще показати як optional)

---

### 4) Оновити парсер/валідацію (якщо потрібно)
Якщо в коді вже є валідація/парсинг:
- додати підтримку нових ключів (`ip`, `port`, `secret_ref`)
- прибрати залежність від старих (`host`, `ssh_port`, `secrets_ref`, `auth.secret_ref`, `backup.type`, `platform`)

Backward compatibility:
- не обовʼязкова
- якщо реалізується - має бути чітко задокументована
- пріоритет: чистота схеми і простота підтримки

---

### 5) Логування
Під час завантаження пристроїв логувати:
- INFO: `device=<name> vendor=<vendor> loaded from devices.yml`
- DEBUG: `ip=<ip> port=<port> username=<username> secret_ref=<secret_ref> model=<model>`

⚠️ Секрети не логувати.

---

### 6) Документація (README.md)
Оновити README.md (UA + EN, якщо використовується двомовність):
- описати єдину схему `devices.yml`
- пояснити поле `model` як інформативне
- пояснити, що:
  - MikroTik `/export` виконується за замовчуванням
  - system backup вмикається окремо (посилання/опис опції)
- прибрати згадки про `platform` (поки не використовується)

---

## Acceptance criteria
- `config/devices.yml.example` використовує єдиний формат і однакові ключі для Cisco та MikroTik
- У прикладах немає `host`, `ssh_port`, `secrets_ref`, `auth.*`, `backup.*`, `platform`
- Код (за потреби) читає нову схему без помилок
- Логи завантаження пристроїв коректні, без витоку секретів
- README.md актуалізовано відповідно до схеми

---

## Результат
NetConfigBackup має уніфіковану та просту схему `devices.yml` для всіх вендорів, що зменшує складність парсингу, валідації та документації, і робить подальший розвиток Cisco-частини передбачуваним.
