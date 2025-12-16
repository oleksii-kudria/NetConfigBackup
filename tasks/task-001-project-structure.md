# task-001-project-structure.md

## Мета
Створити базову структуру нового репозиторію **NetConfigBackup** для Python-скрипту, який виконує бекап конфігурацій мережевого обладнання Cisco та MikroTik.

Скрипт має запускатися на **Ubuntu** та мати чітку, розширювану структуру.

---

## Загальні вимоги
- Мова: Python 3.10+
- ОС: Ubuntu
- Точка входу: `scripts/run.py`
- Пакетна структура через `src/`
- Репозиторій не повинен містити жодних секретів

---

## Структура репозиторію

```
NetConfigBackup/
├── scripts/
│   └── run.py
├── src/
│   └── app/
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── secrets.py
│       │   ├── logging.py
│       │   ├── models.py
│       │   └── storage.py
│       ├── cisco/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   └── backup.py
│       └── mikrotik/
│           ├── __init__.py
│           ├── client.py
│           └── backup.py
├── config/
│   ├── devices.yml
│   └── secrets.yml.example
├── backups/
├── requirements.txt
├── README.md
├── .gitignore
└── task-001-project-structure.md
```

---

## Вимоги до файлів

### scripts/run.py
- Єдина точка запуску
- Повинен коректно виконуватися:
  `python3 scripts/run.py --help`

---

### config/devices.yml.example
- Лише інвентар пристроїв
- Без паролів
- Валідний YAML
- Без реальних значень
- Реальний devices.yml не комітиться

---

### config/secrets.yml.example
- Приклад структури секретів
- Без реальних значень
- Реальний secrets.yml не комітиться

---

### requirements.txt
Мінімум:
```
PyYAML
```

---

## .gitignore
Обовʼязково виключити:
```
config/devices.yml
config/secrets.yml
backups/
logs/
*.log
.env
.venv/
__pycache__/
```

---

## Критерії приймання
- Вся структура створена
- scripts/run.py запускається без помилок
- Немає секретів у репозиторії
- Структура готова для подальших задач

---

## Результат
Репозиторій NetConfigBackup готовий як фундамент для реалізації бекапів Cisco та MikroTik.
