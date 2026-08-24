# Loop Calendar

Минимальный командный календарь для Loop.

Источник истины — SQLite. Markdown-файлы являются производным представлением и
перегенерируются после изменения событий.

## Команды

```text
/cal today
/cal week
/cal mine

/cal remote today
/cal remote tomorrow
/cal remote 24.08
/cal remote 24.08..26.08

/cal vacation 01.09..14.09
/cal off 28.08

/cal meeting 25.08 14:00-15:00 "Редакционная планерка"

/cal delete 42
/cal help
```

Поддерживаются и русские алиасы: `удаленка`, `удалёнка`, `отпуск`, `отгул`,
`встреча`, `сегодня`, `неделя`, `мои`, `удалить`, `помощь`.

## Установка

```bash
uv sync
cp .env.example .env
```

Укажите токен slash-команды Loop в `.env`:

```dotenv
LOOP_SLASH_TOKEN=...
```

Запуск:

```bash
uv run uvicorn loop_calendar.main:app --host 0.0.0.0 --port 8000
```

Проверка:

```bash
curl http://localhost:8000/health
```

## Настройка Loop

Создайте пользовательскую slash-команду с trigger `cal` и POST endpoint:

```text
https://your-host.example/loop/command
```

Loop отправляет `application/x-www-form-urlencoded`. Приложение проверяет и
form-поле `token`, и заголовок `Authorization: Token <token>`.

## Markdown

После изменения календаря создаются:

```text
data/markdown/current.md
data/markdown/YYYY-MM.md
```

`current.md` — календарь текущей недели. Месячные файлы содержат список событий
по дням.

Эти файлы по умолчанию исключены из Git, потому что являются генерируемыми
runtime-данными. Если вы хотите хранить историю Markdown в Git, удалите строку
`data/markdown/*.md` из `.gitignore`.

## Тесты

```bash
uv run pytest
```

Проверка Ruff:

```bash
uv run ruff check .
```
