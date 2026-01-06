# task-023-cisco-ssh-connection.md

## Мета
Реалізувати **стабільне SSH-підключення до пристроїв Cisco** для подальшого виконання
read-only команд з отримання конфігурації.

SSH-зʼєднання є базою для всіх наступних Cisco-задач (enable-mode, backup, diff),
тому має бути максимально надійним та коректно логованим.

---

## Контекст
NetConfigBackup вже має реалізовану SSH-логіку для MikroTik.
Для Cisco необхідно:

- використовувати уніфіковану схему `devices.yml`
- брати паролі з `config/secrets.yml`
- коректно обробляти помилки доступності та автентифікації
- забезпечити чисте завершення сесій

---

## Вхідні дані

### `config/devices.yml`
```yml
devices:
  - name: hq-core-sw1
    vendor: cisco
    model: ""
    ip: 192.0.2.10
    port: 22
    username: backup
    secret_ref: hq-core-sw1
```

### `config/secrets.yml`
```yml
secrets:
  hq-core-sw1:
    password: "CHANGE_ME"
```

---

## Вимоги до реалізації

### 1) Перевірка доступності
Перед спробою SSH:
- перевірити TCP-доступність `ip:port`
- timeout: конфігурований (за замовчуванням 5–10 секунд)

Логування:
- INFO: `device=<name> checking ssh connectivity`
- ERROR: `device=<name> ssh port unreachable ip=<ip> port=<port>`

---

### 2) SSH-підключення
Реалізувати SSH login з використанням:
- `username` з `devices.yml`
- `password` з `secrets.yml`

Вимоги:
- використовувати Paramiko (або вже існуючий SSH-клієнт у проєкті)
- коректно обробляти:
  - неправильний пароль
  - timeout
  - key exchange error
- після підключення зберігати SSH-сесію для подальших команд

Логування:
- INFO: `device=<name> ssh connected`
- ERROR: `device=<name> ssh authentication failed`
- ERROR: `device=<name> ssh connection error`

⚠️ Паролі не логувати.

---

### 3) Ідентифікація prompt
Після успішного login:
- зчитати первинний prompt
- визначити тип:
  - `>` (user EXEC)
  - `#` (privileged EXEC)

Результат зберегти в контексті сесії для наступних задач.

Логування:
- DEBUG: `device=<name> initial prompt detected prompt=<...>`

---

### 4) Завершення сесії
SSH-зʼєднання має:
- коректно закриватись після завершення роботи з пристроєм
- закриватись у випадку помилки на будь-якому етапі

Логування:
- DEBUG: `device=<name> ssh session closed`

---

## Область змін
Очікувані файли для змін/додавання:

- `src/app/cisco/client.py` (новий або розширення)
- спільний SSH-helper (якщо вже існує)
- використання у `scripts/run.py` для `vendor: cisco`

---

## Взаємодія з наступними задачами
Ця задача є основою для:

- `task-024-cisco-enable-mode.md`
- `task-025-cisco-disable-paging.md`
- `task-026-cisco-running-config-backup.md`

Без виконання цієї задачі наступні Cisco-задачі реалізувати неможливо.

---

## Acceptance criteria
- Для кожного `vendor: cisco`:
  - перевіряється доступність `ip:port`
  - встановлюється SSH-зʼєднання
  - логуються успішні та неуспішні підключення
- Паролі та секрети не зʼявляються в логах
- SSH-сесія коректно закривається
- Помилка з одним Cisco-пристроєм не зупиняє обробку інших

---

## Результат
NetConfigBackup має надійний механізм SSH-підключення до Cisco-пристроїв, який
використовується як фундамент для отримання конфігураційних бекапів.
