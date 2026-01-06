# task-032-cli-help-and-readme-examples.md

## Мета
Доповнити **CLI help (`scripts/run.py --help`)** та **README.md** повним переліком прикладів використання
всіх доступних опцій запуску NetConfigBackup.

Користувач має з `--help` одразу розуміти:
- які опції існують
- як їх комбінувати
- що саме буде виконано у кожному сценарії

README.md має містити ті самі приклади у розширеному вигляді.

---

## Контекст
Станом на зараз у проєкті вже є низка CLI-опцій:
- feature flags для бекапів (MikroTik / Cisco)
- `--dry-run`
- `--backup-dir`
- інші базові аргументи

Але:
- не всі комбінації відображені в `--help`
- приклади частково або повністю відсутні в README.md

Це ускладнює використання інструменту без читання коду.

---

## Вимоги

### 1) Оновлення CLI help (`scripts/run.py --help`)
У help необхідно **додати секцію “Examples”** або розширити опис опцій так,
щоб були явно показані приклади запуску.

Мінімальний набір прикладів (обовʼязково):

```text
Examples:
  scripts/run.py backup
      Run default backup pipeline

  scripts/run.py --dry-run backup
      Validate connectivity and authentication without creating backups

  scripts/run.py --mikrotik-export backup
      Run only MikroTik export backups

  scripts/run.py --mikrotik-system-backup backup
      Run only MikroTik system backup

  scripts/run.py --mikrotik-export --mikrotik-system-backup backup
      Run MikroTik export and system backup

  scripts/run.py --cisco-running-config backup
      Run only Cisco running-config backups

  scripts/run.py --mikrotik-export --cisco-running-config backup
      Run MikroTik export and Cisco running-config backups

  scripts/run.py --mikrotik-export --mikrotik-system-backup --cisco-running-config backup
      Run all supported backup types

  scripts/run.py --dry-run --cisco-running-config backup
      Dry-run Cisco backup pipeline

  scripts/run.py --backup-dir /data/backups backup
      Store backups in custom directory
```

Формат прикладів може бути адаптований під argparse, але зміст має бути збережений.

---

### 2) README.md – розділ “Usage examples”
У README.md необхідно:

- додати окремий розділ **Usage / Приклади використання**
- продублювати всі приклади з CLI help
- для кожного прикладу коротко пояснити:
  - що запускається
  - що НЕ запускається
  - чи створюються файли

README.md має бути:
- українською та англійською (якщо проєкт уже двомовний)
- з однаковою логікою прикладів у обох мовах

---

### 3) Актуальність прикладів
Приклади мають відповідати реальному функціоналу після задач:
- task-027 (feature flags)
- task-028 (dry-run)
- task-031 (exit codes)

Застарілі або неіснуючі опції:
- не згадувати
- або явно видалити з README/help

---

### 4) Логування (необовʼязково, але бажано)
Після парсингу аргументів логувати:
- INFO: `cli_examples_available=true`

(не критично, але корисно для дебагу)

---

## Область змін
- `scripts/run.py` (argparse help / epilog / examples)
- `README.md`

---

## Acceptance criteria
- `scripts/run.py --help` містить секцію з прикладами
- У help присутні всі ключові сценарії запуску
- README.md містить ті самі приклади з поясненнями
- Приклади відповідають реальному функціоналу
- Немає згадок про неіснуючі або застарілі опції

---

## Результат
NetConfigBackup має самодокументований CLI:
- `--help` дає повне уявлення про використання
- README.md слугує розширеною інструкцією
- користувач може коректно запустити потрібний сценарій без читання коду
