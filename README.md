# NetConfigBackup

## Project overview (UA)
NetConfigBackup — це CLI-інструмент для резервного копіювання конфігурацій Cisco та MikroTik. Запуск виконується через `scripts/run.py`, який надає підкоманду `backup` та опцію `--debug` для деталізованого логування. Для роботи потрібні інвентаризаційні файли у `config/` та каталоги вивантажень для текстових і бінарних резервних копій.

## Реалізований функціонал (UA)
- **Запуск та режими:** CLI `scripts/run.py` з підкомандою `backup`; підтримка `--debug`, що перевизначає рівень логування з `config/local.yml`; опційні прапорці `--mikrotik-system-backup` для створення бінарного бекапу та `--dry-run` для перевірки доступності без зняття конфігів.
- **Інвентаризація:** читання пристроїв із `config/devices.yml` з єдиною схемою (`name`, `vendor`, `model`, `ip`, `port`, `username`, `secret_ref`); секрети беруться з `config/secrets.yml`.
- **Локальна конфігурація:** опційний `config/local.yml` (не зберігається в git) для налаштування каталогу резервних копій та логів, а також перемикача `mikrotik.system_backup`; відсутність або помилки читання не блокують роботу.
- **Визначення змін:** MikroTik `/export` і Cisco `running-config` порівнюються з попереднім бекапом по нормалізованому тексту; обчислюється `config_changed=true/false/null`, логується SHA256 нормалізованого вмісту (DEBUG) та формується стислий підсумок `added/removed`; при змінах зберігається `.diff` файл поруч із бекапом.
- **JSON summary:** після кожного запуску формується машиночитний звіт у `<BACKUP_DIR>/summary/run_<YYYY-MM-DD_HHMMSS>.json` із загальними підсумками та деталями по пристроях/задачах (приклад нижче).
- **Логування:** кореневий логер з очищенням секретів, примусовим контекстом `device` та конфігурацією рівня через CLI або `local.yml`; запис у файл і stdout з автоматичним fallback каталогу логів.
- **Визначення BACKUP_DIR:** пріоритет `--backup-dir` CLI → `config/local.yml` → запасний `./backup/`; каталог перевіряється на можливість запису з попереджувальними повідомленнями про відмову.
- **Cisco:** конфігурація знімається з **running-config** командою `show running-config` (startup-config не використовується); перед виконанням вимикається paging через `terminal length 0`, щоб уникнути `--More--`; при обмежених правах можливі WARN про невдале вимкнення paging, але бекап продовжується. Результат зберігається до `<BACKUP_DIR>/cisco/<device>/<YYYY-MM-DD_HHMMSS>_running-config.txt`; після збереження виконується нормалізований diff із попереднім файлом, рахується `added/removed`, створюється `<timestamp>_running-config.diff` при змінах.
- **MikroTik:** зняття конфігурації через `/export`, збереження у структуровані каталоги `backup/mikrotik/<device>/`; визначення змін через нормалізований diff та контроль SHA256 із формуванням `<timestamp>_export.diff` при відмінностях; опційне створення бінарного backup через `/system backup save` та завантаження його через SFTP (прапорець `--mikrotik-system-backup` або `mikrotik.system_backup: true` у `local.yml`). Бінарний system-backup створюється на маршрутизаторі зі стабільним імʼям `<device>.backup`, що перезаписує попередню копію; локально файл зберігається з доданим timestamp `<device>_<YYYY-MM-DD_HHMMSS>.backup` для ведення історії. Remote cleanup вимкнено.
- **Розділення копій:** текстовий backup (audit та diff) відокремлений від бінарного backup для disaster recovery.
- **Feature flags:** CLI-прапорці `--mikrotik-export`, `--mikrotik-system-backup`, `--cisco-running-config` дозволяють запускати окремі кроки для відповідних вендорів.

### Увімкнення MikroTik system-backup (UA)
- CLI: додайте прапорець `--mikrotik-system-backup` до `scripts/run.py backup ...`
- Через локальний конфіг: вкажіть у `config/local.yml`:
  ```yml
  mikrotik:
    system_backup: true
  ```
CLI має пріоритет над `local.yml`. За замовчуванням опція вимкнена, файл бекапу на пристрої не видаляється.

### Запуск окремих кроків (UA)
- Прапорці: `--mikrotik-export`, `--mikrotik-system-backup`, `--cisco-running-config`.
- Без прапорців: виконується стандартний пайплайн (MikroTik `/export` і Cisco `show running-config`), `system_backup` залежить від CLI або `local.yml`.
- Якщо вказано хоча б один прапорець, запускаються **лише** вибрані підзадачі для свого вендора:
  - `scripts/run.py --mikrotik-system-backup backup` → тільки MikroTik system-backup
  - `scripts/run.py --mikrotik-export backup` → тільки MikroTik `/export`
  - `scripts/run.py --mikrotik-system-backup --mikrotik-export backup` → MikroTik system-backup + `/export`
  - `scripts/run.py --mikrotik-system-backup --mikrotik-export --cisco-running-config backup` → MikroTik system-backup + `/export` + Cisco running-config
- MikroTik прапорці застосовуються лише до `vendor: mikrotik`; Cisco прапорець — лише до `vendor: cisco`.

### Dry-run режим (UA)
- Запускає всі етапи перевірки (читання конфігів, TCP-доступність, SSH-логін, Cisco enable) без виконання команд бекапу та без створення файлів.
- Приклади:
  - `scripts/run.py --dry-run backup`
  - `scripts/run.py --dry-run --cisco-running-config backup`
- Дотримується feature flags: перевіряє тільки ті завдання, які були б виконані в реальному запуску.
- У логах видно: `dry_run=true`, `device=<name> vendor=<vendor> dry_run connection-check start`, `device=<name> ssh connected`, `device=<name> dry_run skipping backup commands`.

### JSON summary (UA)
- Файл автоматично створюється після кожного запуску в `<BACKUP_DIR>/summary/run_<YYYY-MM-DD_HHMMSS>.json`.
- У dry-run поле `dry_run` дорівнює `true`, `saved_path` та `diff_path` залишаються `null`.
- Містить загальні лічильники та деталізацію по пристроях і задачах:
  ```json
  {
    "run_id": "2025-12-28_121400",
    "timestamp": "2025-12-28T12:14:00Z",
    "dry_run": false,
    "selected_features": ["mikrotik_export", "mikrotik_system_backup", "cisco_running_config"],
    "totals": {
      "devices_total": 3,
      "devices_processed": 3,
      "devices_success": 2,
      "devices_failed": 1,
      "backups_created": 3,
      "configs_changed": 1
    },
    "devices": [
      {
        "name": "main-mikrotik",
        "vendor": "mikrotik",
        "status": "success",
        "tasks": {
          "mikrotik_export": {
            "performed": true,
            "saved_path": "backup/mikrotik/main-mikrotik/2025-12-28_121400_export.rsc",
            "size_bytes": 1234,
            "config_changed": true,
            "lines_added": 10,
            "lines_removed": 2,
            "diff_path": "backup/mikrotik/main-mikrotik/2025-12-28_121400_export.diff",
            "error": null
          },
          "mikrotik_system_backup": {
            "performed": true,
            "saved_path": "backup/mikrotik/main-mikrotik/main-mikrotik_2025-12-28_121400.backup",
            "size_bytes": 2048,
            "config_changed": null,
            "lines_added": null,
            "lines_removed": null,
            "diff_path": null,
            "error": null
          }
        }
      }
    ]
  }
  ```
- JSON не містить секретів і підходить для інтеграцій (cron/CI, Telegram/Slack алерти).

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
- **Execution and modes:** CLI `scripts/run.py` with the `backup` subcommand; `--debug` overrides the logging level configured in `config/local.yml`; optional flags `--mikrotik-system-backup` enable binary backups and `--dry-run` validates access without collecting configs.
- **Inventory:** reads devices from `config/devices.yml` using a unified schema (`name`, `vendor`, `model`, `ip`, `port`, `username`, `secret_ref`); secrets are sourced from `config/secrets.yml`.
- **Local configuration:** optional `config/local.yml` (kept out of git) to tune backup and logging directories and the `mikrotik.system_backup` switch; missing or unreadable files do not stop execution.
- **Change detection:** MikroTik `/export` and Cisco `running-config` are compared against the previous backup using normalized text; `config_changed=true/false/null` is determined, the normalized SHA256 hash is logged at DEBUG, and a concise `added/removed` summary is reported; when changes are present a `.diff` file is written next to the backup.
- **JSON summary:** after every run the tool writes a machine-readable report to `<BACKUP_DIR>/summary/run_<YYYY-MM-DD_HHMMSS>.json` with overall totals and per-device/per-task details (see example below).
- **Logging:** root logger scrubs secrets, enforces a `device` context, and respects CLI or `local.yml` levels; writes to file and stdout with automatic fallback for the log directory.
- **BACKUP_DIR resolution:** priority `--backup-dir` CLI → `config/local.yml` → fallback `./backup/`; each candidate is probed for writability with warnings when falling back.
- **Cisco:** configuration is taken from **running-config** via `show running-config` (startup-config is not used); paging is disabled first with `terminal length 0` to prevent `--More--`; if the command is rejected due to permissions, a warning is logged and the backup proceeds. Files are written to `<BACKUP_DIR>/cisco/<device>/<YYYY-MM-DD_HHMMSS>_running-config.txt`; after saving, a normalized diff against the previous backup is produced, `added/removed` counts are logged, and `<timestamp>_running-config.diff` is created when changes exist.
- **MikroTik:** captures configuration via `/export`, saves under `backup/mikrotik/<device>/`, detects changes using normalized diffs plus SHA256 hashes, saves `<timestamp>_export.diff` files when changes occur, and optionally creates binary backups via `/system backup save` with SFTP download (enabled via `--mikrotik-system-backup` or `mikrotik.system_backup: true`). The system-backup is created on the router with a stable `<device>.backup` filename that overwrites the previous copy, while the local copy is renamed with a timestamp `<device>_<YYYY-MM-DD_HHMMSS>.backup` to keep history. Remote cleanup is disabled.
- **Backup separation:** text backups for audit/diff are kept separate from binary backups for disaster recovery.
- **Feature flags:** CLI flags `--mikrotik-export`, `--mikrotik-system-backup`, and `--cisco-running-config` allow running only the selected steps for matching vendors.

### Enabling MikroTik system-backup (EN)
- CLI: add the `--mikrotik-system-backup` flag when running `scripts/run.py backup ...`
- Local config: set in `config/local.yml`:
  ```yml
  mikrotik:
    system_backup: true
  ```
The CLI flag overrides `local.yml`. By default the feature is disabled and the backup file stays on the device (no remote cleanup).

### Running selective steps (EN)
- Flags: `--mikrotik-export`, `--mikrotik-system-backup`, `--cisco-running-config`.
- With no flags: the default pipeline runs (MikroTik `/export` and Cisco `show running-config`), and `system_backup` follows CLI/local configuration.
- With at least one flag: **only** the selected sub-tasks run for the corresponding vendor:
  - `scripts/run.py --mikrotik-system-backup backup` → MikroTik system-backup only
  - `scripts/run.py --mikrotik-export backup` → MikroTik `/export` only
  - `scripts/run.py --mikrotik-system-backup --mikrotik-export backup` → MikroTik system-backup + `/export`
  - `scripts/run.py --mikrotik-system-backup --mikrotik-export --cisco-running-config backup` → MikroTik system-backup + `/export` + Cisco running-config
- MikroTik flags apply only to `vendor: mikrotik`; the Cisco flag applies only to `vendor: cisco`.

### Dry-run mode (EN)
- Runs validation steps (config loading, TCP reachability, SSH login, Cisco enable) without issuing backup commands or creating files.
- Examples:
  - `scripts/run.py --dry-run backup`
  - `scripts/run.py --dry-run --cisco-running-config backup`
- Respects feature flags: only the tasks that would run in a real backup are checked.
- Logs show: `dry_run=true`, `device=<name> vendor=<vendor> dry_run connection-check start`, `device=<name> ssh connected`, `device=<name> dry_run skipping backup commands`.

### JSON summary (EN)
- The tool writes a report to `<BACKUP_DIR>/summary/run_<YYYY-MM-DD_HHMMSS>.json` after every execution.
- In dry-run the `dry_run` field is `true`, and `saved_path`/`diff_path` remain `null`.
- The file contains overall totals plus per-device and per-task details:
  ```json
  {
    "run_id": "2025-12-28_121400",
    "timestamp": "2025-12-28T12:14:00Z",
    "dry_run": false,
    "selected_features": ["mikrotik_export", "mikrotik_system_backup", "cisco_running_config"],
    "totals": {
      "devices_total": 3,
      "devices_processed": 3,
      "devices_success": 2,
      "devices_failed": 1,
      "backups_created": 3,
      "configs_changed": 1
    },
    "devices": [
      {
        "name": "main-mikrotik",
        "vendor": "mikrotik",
        "status": "success",
        "tasks": {
          "mikrotik_export": {
            "performed": true,
            "saved_path": "backup/mikrotik/main-mikrotik/2025-12-28_121400_export.rsc",
            "size_bytes": 1234,
            "config_changed": true,
            "lines_added": 10,
            "lines_removed": 2,
            "diff_path": "backup/mikrotik/main-mikrotik/2025-12-28_121400_export.diff",
            "error": null
          },
          "mikrotik_system_backup": {
            "performed": true,
            "saved_path": "backup/mikrotik/main-mikrotik/main-mikrotik_2025-12-28_121400.backup",
            "size_bytes": 2048,
            "config_changed": null,
            "lines_added": null,
            "lines_removed": null,
            "diff_path": null,
            "error": null
          }
        }
      }
    ]
  }
  ```
- No secrets are written to the JSON, making it suitable for cron/CI integrations or outbound alerts (Telegram/Slack, etc.).

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
