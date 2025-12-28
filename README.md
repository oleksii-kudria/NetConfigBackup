# NetConfigBackup

## Project overview (UA)
NetConfigBackup — це CLI-інструмент для резервного копіювання конфігурацій Cisco та MikroTik. Запуск виконується через `scripts/run.py`, який надає підкоманду `backup` та опцію `--debug` для деталізованого логування. Для роботи потрібні інвентаризаційні файли у `config/` та каталоги вивантажень для текстових і бінарних резервних копій.

## Реалізований функціонал (UA)
- **Запуск та режими:** CLI `scripts/run.py` з підкомандою `backup`; підтримка `--debug`, що перевизначає рівень логування з `config/local.yml`.
- **Інвентаризація:** читання пристроїв із `config/devices.yml` (логічний поділ за `vendor`, `host`, `port`, `username`, `auth.secret_ref`, `backup.type` тощо); секрети беруться з `config/secrets.yml`.
- **Локальна конфігурація:** опційний `config/local.yml` (не зберігається в git) для налаштування каталогу резервних копій та логів; відсутність або помилки читання не блокують роботу.
- **Логування:** кореневий логер з очищенням секретів, примусовим контекстом `device` та конфігурацією рівня через CLI або `local.yml`; запис у файл і stdout з автоматичним fallback каталогу логів.
- **Визначення BACKUP_DIR:** пріоритет `--backup-dir` CLI → `config/local.yml` → запасний `./backup/`; каталог перевіряється на можливість запису з попереджувальними повідомленнями про відмову.
- **MikroTik:** зняття конфігурації через `/export`, збереження у структуровані каталоги `backup/mikrotik/<device>/`; визначення змін через нормалізований diff та контроль SHA256; збереження diff-файлу при відмінностях; створення бінарного backup через `/system backup save` та завантаження його через SFTP.
- **Розділення копій:** текстовий backup (audit та diff) відокремлений від бінарного backup для disaster recovery.

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

---

## Project overview (EN)
NetConfigBackup is a CLI tool for backing up Cisco and MikroTik configurations. It runs via `scripts/run.py`, exposes the `backup` subcommand, and supports a `--debug` flag to elevate logging. The tool relies on inventory files in `config/` and stores both text and binary backups in structured directories.

## Implemented features (EN)
- **Execution and modes:** CLI `scripts/run.py` with the `backup` subcommand; `--debug` overrides the logging level configured in `config/local.yml`.
- **Inventory:** reads devices from `config/devices.yml` (fields such as `vendor`, `host`, `port`, `username`, `auth.secret_ref`, `backup.type`); secrets are sourced from `config/secrets.yml`.
- **Local configuration:** optional `config/local.yml` (kept out of git) to tune backup and logging directories; missing or unreadable files do not stop execution.
- **Logging:** root logger scrubs secrets, enforces a `device` context, and respects CLI or `local.yml` levels; writes to file and stdout with automatic fallback for the log directory.
- **BACKUP_DIR resolution:** priority `--backup-dir` CLI → `config/local.yml` → fallback `./backup/`; each candidate is probed for writability with warnings when falling back.
- **MikroTik:** captures configuration via `/export`, saves under `backup/mikrotik/<device>/`, detects changes using normalized diffs plus SHA256 hashes, saves diff files when changes occur, and creates binary backups via `/system backup save` with SFTP download.
- **Backup separation:** text backups for audit/diff are kept separate from binary backups for disaster recovery.

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
