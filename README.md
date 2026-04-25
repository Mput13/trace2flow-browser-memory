Track: C+D

# Browser Workflow Memory

Исследовательский прототип: слой памяти поверх [browser-use](https://github.com/browser-use/browser-use). Повторяющиеся браузерные задачи на том же сайте выполняются быстрее после первого успешного прогона — агент запоминает путь навигации и переиспользует его.

**Основное утверждение:** повторяющиеся браузерные задачи на том же сайте должны требовать меньше действий после одного успешного прогона.

Результаты экспериментов — в [docs/findings.md](docs/findings.md).

## Быстрый старт

```bash
# 1. Установка зависимостей (требуется Python 3.11–3.12)
pip install uv
uv sync
.venv/bin/playwright install chromium

# 2. Укажите LLM-ключ (рекомендуется OpenRouter; обычный OpenAI тоже работает)
export OPENROUTER_API_KEY=sk-or-...
# или: export OPENAI_API_KEY=sk-...

# 3. Запустите задачу
workflow-memory run \
  --task "Зайди на http://books.toscrape.com и найди все книги категории Mystery"
```

Вывод:

```
run_id: <uuid>
status: succeeded
action_count: 8
elapsed_seconds: 47.3
```

## Цикл памяти

```
run        →  optimize  →  memory-run
(baseline)    (LLM извлекает    (агент получает
               знания о сайте)   подсказки навигации)
```

1. **`run`** — агент решает задачу с нуля, артефакты сохраняются
2. **`optimize`** — LLM анализирует прогон, извлекает hint-пакет и граф страниц сайта, сохраняет в SQLite
3. **`memory-run`** — та же задача снова, агент получает подсказки: прямой URL, карту сайта, признаки успеха

## Команды

| Команда | Описание |
|---|---|
| `run --task "..."` | Базовый прогон без памяти |
| `run --task "..." --site <тег>` | Базовый прогон с явной группировкой по сайту |
| `optimize --run-id <id>` | Анализ завершённого прогона, сохранение памяти |
| `memory-run --task "..."` | Прогон с подсказками из памяти (если есть) |
| `eval-batch --suite <file.yaml>` | Полное сравнение: baseline → optimize → memory для каждого кейса |
| `eval-batch --suite <file.yaml> --output` | То же, вывод в JSON |

## Интерфейс для агентов (Claude / Codex / OpenClaw)

CLI — основной интерфейс для агентов. Любой оркестратор может вызывать команды через subprocess:

```bash
# Запустить задачу, получить JSON
workflow-memory run \
  --task "Найди расписание группы М8О-105БВ-25 на https://mai.ru/education/studies/schedule/groups.php" \
  --output-json
```

JSON-ответ:

```json
{
  "run_id": "069ec105-...",
  "status": "succeeded",
  "final_result": "...",
  "action_count": 16,
  "elapsed_seconds": 235.2
}
```

После успешного прогона — извлечь и сохранить память:

```bash
workflow-memory optimize --run-id 069ec105-...
```

Следующие прогоны на том же сайте автоматически используют сохранённую память:

```bash
workflow-memory memory-run \
  --task "Найди расписание группы М8О-106БВ-25 на https://mai.ru/education/studies/schedule/groups.php"
```

## Формат набора задач

Создайте YAML-файл для пакетного запуска нескольких задач:

```yaml
site: books.toscrape.com
task_family: book_search
cases:
  - case_id: books-01
    task: "Зайди на http://books.toscrape.com и найди все книги Mystery"
  - case_id: books-02
    task: "Зайди на http://books.toscrape.com и найди все книги Science Fiction"
```

Запуск полного сравнения baseline vs memory:

```bash
workflow-memory eval-batch --suite tasks/books_toscrape_eval.yaml --output
```

## Конфигурация

`config/project.yaml`:

```yaml
llm_provider: openrouter
llm_base_url: https://openrouter.ai/api/v1
llm_api_key_env: OPENROUTER_API_KEY
judge_model: google/gemini-3-flash-preview
optimize_model: qwen/qwen3.6-plus
sqlite_path: data/workflow_memory.sqlite
artifacts_root: artifacts
admission:
  min_relative_improvement: 0.10
retrieval:
  fuzzy_threshold: 0.75
```

`OPENROUTER_API_KEY` задаётся в переменных окружения или в `.env`.

## Граф страниц сайта

Система памяти строит граф страниц по каждому сайту на основе наблюдаемых прогонов. Каждый узел хранит:
- URL-паттерн (с плейсхолдерами `{param}`)
- Что делает страница и когда её использовать
- Query-параметры и их смысл
- Уровень уверенности (затухает за 90 дней, сбрасывается при подтверждённом визите)

Это позволяет агенту переходить напрямую к нужным страницам при повторных визитах, даже для задач с другими параметрами (например, другая группа на том же сайте расписания университета).

## Структура проекта

```
src/workflow_memory/
  cli.py              # CLI-точка входа (Typer)
  pipeline/
    baseline.py       # Базовый прогон
    optimize.py       # Шаг оптимизации + сохранение памяти
    memory_run.py     # Прогон с памятью
  eval/
    batch.py          # Запуск набора задач
    reporting.py      # Агрегация метрик
  storage/
    repository.py     # SQLite CRUD (runs, memories, site_pages)
  optimization/
    optimizer.py      # LLM-извлечение подсказок
  retrieval/
    scoring.py        # Нечёткое сопоставление задач
tasks/                # YAML-файлы наборов задач
results/              # JSON с результатами eval
docs/
  findings.md         # Результаты экспериментов
```

## Запуск тестов

```bash
python -m pytest tests/ -q
```

145 тестов, внешние зависимости не требуются.
