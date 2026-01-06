# NetConfigBackup

## Project overview (UA)
NetConfigBackup — це CLI-інструмент для резервного копіювання конфігурацій Cisco та MikroTik. Запуск виконується через `scripts/run.py`, який надає підкоманду `backup` та опцію `--debug` для деталізованого логування. Для роботи потрібні інвентаризаційні файли у `config/` та каталоги вивантажень для текстових і бінарних резервних копій.

## Реалізований функціонал (UA)
- **Запуск та режими:** CLI `scripts/run.py` з підкомандою `backup`; підтримка `--debug`, що перевизначає рівень логування з `config/local.yml`; опційний прапорець `--mikrotik-system-backup` для створення бінарного бекапу.
- **Інвентаризація:** читання пристроїв із `config/devices.yml` з єдиною схемою (`name`, `vendor`, `model`, `ip`, `port`, `username`, `secret_ref`); секрети беруться з `config/secrets.yml`.
- **Локальна конфігурація:** опційний `config/local.yml` (не зберігається в git) для налаштування каталогу резервних копій та логів, а також перемикача `mikrotik.system_backup`; відсутність або помилки читання не блокують роботу.
- **Логування:** кореневий логер з очищенням секретів, примусовим контекстом `device` та конфігурацією рівня через CLI або `local.yml`; запис у файл і stdout з автоматичним fallback каталогу логів.
- **Визначення BACKUP_DIR:** пріоритет `--backup-dir` CLI → `config/local.yml` → запасний `./backup/`; каталог перевіряється на можливість запису з попереджувальними повідомленнями про відмову.
- **MikroTik:** зняття конфігурації через `/export`, збереження у структуровані каталоги `backup/mikrotik/<device>/`; визначення змін через нормалізований diff та контроль SHA256; збереження diff-файлу при відмінностях; опційне створення бінарного backup через `/system backup save` та завантаження його через SFTP (прапорець `--mikrotik-system-backup` або `mikrotik.system_backup: true` у `local.yml`). Бінарний system-backup створюється на маршрутизаторі зі стабільним імʼям `<device>.backup`, що перезаписує попередню копію; локально файл зберігається з доданим timestamp `<device>_<YYYY-MM-DD_HHMMSS>.backup` для ведення історії. Remote cleanup вимкнено.
- **Розділення копій:** текстовий backup (audit та diff) відокремлений від бінарного backup для disaster recovery.

### Увімкнення MikroTik system-backup (UA)
- CLI: додайте прапорець `--mikrotik-system-backup` до `scripts/run.py backup ...`
- Через локальний конфіг: вкажіть у `config/local.yml`:
  ```yml
  mikrotik:
    system_backup: true
  ```
CLI має пріоритет над `local.yml`. За замовчуванням опція вимкнена, файл бекапу на пристрої не видаляється.

## MikroTik: користувач і права доступу (UA)
Для збору конфігурацій та системних бекапів потрібен окремий обліковий запис з мінімальними правами. Уникайте використання групи `full` та будь-яких зайвих сервісів (winbox, api, web тощо).

### Приклад створення групи та користувача
```mikrotik
/user group add name=bk_group_01 policy=\
ssh,ftp,read,write,policy,test,sensitive,\
!local,!telnet,!reboot,!winbox,!password,\
!web,!sniff,!api,!romon,!rest-api

/user add name=bk_user_01 group=bk_group_01 password=STRONG_PASSWORD
```

- `ssh` та `ftp` потрібні для виконання команд `/export` і завантаження системного backup через SFTP.
- `read`, `write`, `policy`, `test`, `sensitive` забезпечують доступ до конфігураційних команд без права керування сервісами або локальними користувачами.
- Відмова від `full` знижує ризик несанкціонованих змін та обмежує поверхню атаки.

## Схема devices.yml та secrets.yml (UA)
- **devices.yml** (тільки не-чутливі дані, однакові поля для Cisco та MikroTik)
  ```yml
  devices:
    - name: core-sw-01
      vendor: cisco
      model: ""
      ip: 10.0.0.1
      port: 22          # необовʼязково, за замовчуванням 22
      username: backup
      secret_ref: core-sw-01

    - name: travel-mikrotik
      vendor: mikrotik
      model: hAP ax3    # інформативне поле; можна опустити або залишити ""
      ip: 198.51.100.5
      port: 22
      username: backup
      secret_ref: travel-mikrotik
  ```
- `model` — інформаційне поле; допускається порожній рядок або відсутність.
- `/export` для MikroTik виконується за замовчуванням; system backup вмикається окремо (CLI прапорець `--mikrotik-system-backup` або `mikrotik.system_backup` у `config/local.yml`).
- **secrets.yml** (зберігати локально, не комітити)
  ```yml
  secrets:
    core-sw-01:
      password: "CHANGE_ME"              # обовʼязково
      enable_password: "CHANGE_ME_ENABLE"  # опційно (для входу у privileged EXEC)
    travel-mikrotik:
      password: "CHANGE_ME"
  ```
- `config/secrets.yml` виключений з git (див. `.gitignore`), натомість використовуйте `config/secrets.yml.example` як шаблон.
- `secret_ref` обовʼязковий для кожного пристрою; відсутність файлу або ключа веде до пропуску пристрою з помилкою у логах.
- Паролі або інші секрети **заборонено** додавати в `devices.yml`; валідатор це перевіряє.

### Cisco: privileged EXEC / enable (UA)
- Якщо після логіну prompt завершується на `#`, перехід у privileged EXEC не виконується.
- Для prompt `>`:
  - якщо в `secrets.yml` заданий `enable_password`, виконується `enable`, очікування `Password:` та prompt `#`;
  - якщо `enable_password` відсутній, крок пропускається з INFO логом `enable skipped (no enable_password)`.
- При неправильному паролі або таймауті лог пише `enable failed`, і бекап пристрою пропускається.
- Без enable команди на кшталт `show running-config` можуть бути недоступні або повертати неповний вивід.

---

## Project overview (EN)
NetConfigBackup is a CLI tool for backing up Cisco and MikroTik configurations. It runs via `scripts/run.py`, exposes the `backup` subcommand, and supports a `--debug` flag to elevate logging. The tool relies on inventory files in `config/` and stores both text and binary backups in structured directories.

## Implemented features (EN)
- **Execution and modes:** CLI `scripts/run.py` with the `backup` subcommand; `--debug` overrides the logging level configured in `config/local.yml`; optional `--mikrotik-system-backup` flag enables binary backups.
- **Inventory:** reads devices from `config/devices.yml` using a unified schema (`name`, `vendor`, `model`, `ip`, `port`, `username`, `secret_ref`); secrets are sourced from `config/secrets.yml`.
- **Local configuration:** optional `config/local.yml` (kept out of git) to tune backup and logging directories and the `mikrotik.system_backup` switch; missing or unreadable files do not stop execution.
- **Logging:** root logger scrubs secrets, enforces a `device` context, and respects CLI or `local.yml` levels; writes to file and stdout with automatic fallback for the log directory.
- **BACKUP_DIR resolution:** priority `--backup-dir` CLI → `config/local.yml` → fallback `./backup/`; each candidate is probed for writability with warnings when falling back.
- **MikroTik:** captures configuration via `/export`, saves under `backup/mikrotik/<device>/`, detects changes using normalized diffs plus SHA256 hashes, saves diff files when changes occur, and optionally creates binary backups via `/system backup save` with SFTP download (enabled via `--mikrotik-system-backup` or `mikrotik.system_backup: true`). The system-backup is created on the router with a stable `<device>.backup` filename that overwrites the previous copy, while the local copy is renamed with a timestamp `<device>_<YYYY-MM-DD_HHMMSS>.backup` to keep history. Remote cleanup is disabled.
- **Backup separation:** text backups for audit/diff are kept separate from binary backups for disaster recovery.

### Enabling MikroTik system-backup (EN)
- CLI: add the `--mikrotik-system-backup` flag when running `scripts/run.py backup ...`
- Local config: set in `config/local.yml`:
  ```yml
  mikrotik:
    system_backup: true
  ```
The CLI flag overrides `local.yml`. By default the feature is disabled and the backup file stays on the device (no remote cleanup).

## MikroTik: user and permissions (EN)
Use a dedicated account with minimal privileges for collecting exports and system backups. Avoid the `full` group and disable unnecessary services (winbox, api, web, etc.).

### Example: create group and user
```mikrotik
/user group add name=bk_group_01 policy=\
ssh,ftp,read,write,policy,test,sensitive,\
!local,!telnet,!reboot,!winbox,!password,\
!web,!sniff,!api,!romon,!rest-api

/user add name=bk_user_01 group=bk_group_01 password=STRONG_PASSWORD
```

- `ssh` and `ftp` are required to run `/export` and retrieve the system backup via SFTP.
- `read`, `write`, `policy`, `test`, and `sensitive` enable configuration export while blocking service management and local user administration.
- Avoiding `full` reduces the blast radius of the account and limits the attack surface.

## devices.yml and secrets.yml schema (EN)
- **devices.yml** (non-sensitive data only, shared fields for Cisco and MikroTik)
  ```yml
  devices:
    - name: core-sw-01
      vendor: cisco
      model: ""
      ip: 10.0.0.1
      port: 22          # optional, defaults to 22
      username: backup
      secret_ref: core-sw-01

    - name: travel-mikrotik
      vendor: mikrotik
      model: hAP ax3    # informational; can be omitted or set to ""
      ip: 198.51.100.5
      port: 22
      username: backup
      secret_ref: travel-mikrotik
  ```
- `model` is informational only; it may be left empty or omitted.
- MikroTik uses `/export` by default; the binary system backup is enabled separately (CLI flag `--mikrotik-system-backup` or `mikrotik.system_backup` in `config/local.yml`).
- **secrets.yml** (keep locally, do not commit)
  ```yml
  secrets:
    core-sw-01:
      password: "CHANGE_ME"              # required
      enable_password: "CHANGE_ME_ENABLE"  # optional (for privileged EXEC)
    travel-mikrotik:
      password: "CHANGE_ME"
  ```
- `config/secrets.yml` is ignored by git (see `.gitignore`). Use `config/secrets.yml.example` as a template without real secrets.
- `secret_ref` is mandatory for each device; when the file or key is missing the device is skipped and an error is logged.
- Passwords or other secrets **must not** appear in `devices.yml`; validation enforces this.

### Cisco: privileged EXEC / enable (EN)
- If the login prompt already ends with `#`, the tool does not attempt an enable step.
- For a `>` prompt:
  - when `enable_password` is provided in `secrets.yml`, `enable` is executed, `Password:` is awaited, and the `#` prompt is expected;
  - when `enable_password` is missing, the step is skipped with an INFO log `enable skipped (no enable_password)`.
- On wrong passwords or timeouts the log records `enable failed` and the device backup is skipped.
- Without enable, commands such as `show running-config` may be unavailable or return incomplete output.
