# task-030-json-run-summary.md

## Мета
Додати генерацію **JSON summary** після кожного запуску `scripts/run.py`, щоб мати машиночитний підсумок.

JSON summary потрібен для:
- інтеграції з cron/CI
- подальших алертів (Telegram/Slack)
- швидкого аналізу, що було збережено/змінено/впало

---

## Вимоги

### 1) Вихідний файл summary
Після завершення команди (наприклад `backup`) створювати файл:

- за замовчуванням: у `<BACKUP_DIR>/summary/` (або інша логічна директорія, але однакова для всіх run)
- формат імені: `run_<YYYY-MM-DD_HHMMSS>.json`

У dry-run:
- summary створювати можна, але має мати `dry_run=true`.

---

### 2) Структура JSON
Мінімальна структура:

```json
{
  "run_id": "2025-12-28_121400",
  "timestamp": "2025-12-28T12:14:00Z",
  "dry_run": false,
  "selected_features": ["mikrotik_export", "mikrotik_system_backup", "cisco_running_config"],
  "totals": {
    "devices_total": 0,
    "devices_processed": 0,
    "devices_success": 0,
    "devices_failed": 0,
    "backups_created": 0,
    "configs_changed": 0
  },
  "devices": [
    {
      "name": "main-mikrotik",
      "vendor": "mikrotik",
      "status": "success",
      "tasks": {
        "mikrotik_export": {
          "performed": true,
          "saved_path": "…",
          "size_bytes": 1234,
          "config_changed": true,
          "lines_added": 10,
          "lines_removed": 2,
          "diff_path": "…"
        }
      }
    }
  ]
}
```

Політика полів:
- `saved_path`, `diff_path` можуть бути `null`, якщо не створювались
- `config_changed` може бути `null`, якщо немає baseline
- `status`: `success|failed|skipped`

⚠️ Секрети не записувати у JSON.

---

### 3) Формування підсумку
Під час виконання pipeline збирати метрики:
- per-device статус
- per-task статус
- чи створено файл
- чи були зміни (з task-029)

Якщо девайс unreachable/auth failed:
- `status=failed`
- записати короткий `error` (без секретів)

---

### 4) Логування
- INFO: `run_summary_json_saved path=<path>`

---

### 5) Документація (README.md)
Оновити README (UA + EN):
- де створюється summary
- приклад структури
- як використати для інтеграцій

---

## Область змін
- `scripts/run.py` (збір даних, запис json)
- допоміжний модуль (наприклад `src/app/common/run_summary.py`)
- README.md

---

## Acceptance criteria
- Після кожного запуску створюється JSON summary файл
- JSON містить totals + список devices з деталями задач
- У dry-run JSON має `dry_run=true` і немає `saved_path` для бекапів
- Секрети не потрапляють у JSON
- README.md оновлено
