# Отчет по тестовым прогонам Trace2Flow

Состояние на: 2026-04-25

Этот файл собирает в одном месте, где хранится история прогонов, какие статистики уже посчитаны, какие сценарии мы пробовали, и что из этого получилось.

## Краткий вывод

Информация о тестовых прогонах уже хорошо сохранена и восстановима:

- `data/workflow_memory.sqlite` хранит структурированные записи о прогонах, памяти и графе страниц.
- `results/` хранит агрегированные JSON-сводки и текстовые логи экспериментов.
- `artifacts/runs/` хранит трассы каждого конкретного запуска.
- `docs/findings.md` содержит подробную интерпретацию результатов.
- `.planning/` хранит историю проекта, решения и состояние фаз.

Текущее покрытие уже достаточное для анализа, демо и рефлексии:

- 68 записей в таблице `runs`
- 14 записей в таблице `memories`
- 33 записи в таблице `site_pages`
- 58 успешных прогонов, 7 `failed_verification`, 3 `failed_execution`
- 39 baseline-прогонов и 29 memory-прогонов

## Где что лежит

| Путь | Что там хранится | Для чего смотреть |
|---|---|---|
| [data/workflow_memory.sqlite](/Users/a/MAI/sem2/trace2flow/data/workflow_memory.sqlite) | `runs`, `memories`, `site_pages` | Источник структурной правды по всем прогонам |
| [results/](/Users/a/MAI/sem2/trace2flow/results) | `eval_*.json`, `eval_*_log.txt` | Читабельные сводки по пакетам кейсов |
| [artifacts/runs/](/Users/a/MAI/sem2/trace2flow/artifacts/runs) | `trace.json`, `result.json`, `normalized.json` по каждому `run_id` | Разбор конкретного прогона шаг за шагом |
| [docs/findings.md](/Users/a/MAI/sem2/trace2flow/docs/findings.md) | Итоговая аналитика по эксперименту | Быстро понять, что сработало и где регрессии |
| [.planning/PROJECT.md](/Users/a/MAI/sem2/trace2flow/.planning/PROJECT.md) | Цель, требования, ограничения | Контекст проекта и рамки гипотезы |
| [.planning/ROADMAP.md](/Users/a/MAI/sem2/trace2flow/.planning/ROADMAP.md) | Фазы и планы | Где находимся в lifecycle работ |
| [.planning/STATE.md](/Users/a/MAI/sem2/trace2flow/.planning/STATE.md) | Текущее состояние и continuity | Что было последним активным состоянием |

## Структура данных

В SQLite сейчас есть три основных таблицы:

- `runs` - каждый baseline или memory-run с метриками и путями к артефактам
- `memories` - admitted hint-packages после оптимизации
- `site_pages` - нормализованный граф страниц по сайтам

Снимок базы на этот момент:

- `runs`: 68
- `memories`: 14
- `site_pages`: 33

По `runs`:

- baseline: 39
- memory: 29
- status `succeeded`: 58
- status `failed_verification`: 7
- status `failed_execution`: 3

По `memories`:

- `helpful`: 5
- `neutral`: 1
- `harmful`: 1
- `unknown`: 7

По `site_pages`:

- `books.toscrape.com`: 10 страниц
- `kinostar86.ru`: 6 страниц
- `mai.ru`: 9 страниц
- `quotes.toscrape.com`: 8 страниц

## Что мы пробовали

Основной набор экспериментов сейчас лежит в:

- [results/eval_20_combined.json](/Users/a/MAI/sem2/trace2flow/results/eval_20_combined.json)
- [results/eval_kinostar.json](/Users/a/MAI/sem2/trace2flow/results/eval_kinostar.json)

### MAI

`mai` - самый сильный и наиболее демонстративный сценарий.

- 8 кейсов
- baseline success: 88%
- memory success: 88%
- среднее улучшение: 31.6%
- лучший кейс: `mai-s05`
- лучший результат: `20 -> 3` действий

Смысл этого сценария в том, что memory-run действительно убирает лишнюю навигацию и заметно сокращает путь к расписанию.

### books.toscrape.com

Стабильный, но менее наглядный сценарий.

- 6 кейсов
- baseline success: 100%
- memory success: 100%
- среднее улучшение: 27.2%

Этот набор полезен как проверка, но для live demo он хуже MAI: улучшение есть, но оно не так эффектно визуально.

### quotes.toscrape.com

Сценарий с отрицательным эффектом памяти.

- 6 кейсов
- baseline success: 100%
- memory success: 83%
- среднее изменение: -19.4%

Здесь память иногда вводит агента в заблуждение: `direct_url` и путь навигации не всегда соответствуют реальному intent задачи, особенно для авторов и тегов.

### kinostar86.ru

Частичный прогон, полезный как дополнительный stress-case.

- 9 кейсов в файле
- прогон завершился до `kino-10`
- 5 кейсов имели memory-run
- среднее улучшение: 9.8%

По этому набору видно, что сценарий более хрупкий: есть и полезные ускорения, и регрессия, и случаи с `cross-origin iframe`, где baseline и memory упираются в ограничения верификации.

## Сводка по итогам экспериментов

Сейчас в репозитории уже есть подробная статистика по тому, что мы пробовали:

| Сценарий | Кейсы | Успех baseline | Успех memory | Среднее изменение |
|---|---:|---:|---:|---:|
| MAI | 8 | 88% | 88% | +31.6% |
| books | 6 | 100% | 100% | +27.2% |
| quotes | 6 | 100% | 83% | -19.4% |
| kinostar | 9 | частичный прогон | частичный прогон | +9.8% |

Ключевой вывод:

- память помогает там, где есть предсказуемый путь и хорошая точка входа
- память вредна, если `direct_url` не соответствует реальному intent задачи
- MAI сейчас лучший пример для демонстрации, потому что там выигрыш подтвержден и визуально очевиден

## Где смотреть конкретику

Если нужен один конкретный `run_id`, смотри:

- `artifacts/runs/<run_id>/trace.json`
- `artifacts/runs/<run_id>/result.json`
- `artifacts/runs/<run_id>/normalized.json`

Если нужен обзор по пакету кейсов:

- `results/eval_20_combined.json`
- `results/eval_kinostar.json`
- `docs/findings.md`

Если нужен текущий проектный контекст и почему выбран именно этот набор сценариев:

- `.planning/STATE.md`
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`

## Что уже можно считать подтвержденным

1. Система действительно хранит историю прогонов и памяти в структурированном виде.
2. Есть достаточная статистика по baseline vs memory-run.
3. Есть не только успешные, но и неудачные сценарии, поэтому анализ не выглядит натянутым.
4. Для демонстрации лучше всего использовать MAI-сценарий `mai-s05`.

## Что остается полезно добавлять дальше

- еще один полный MAI-прогон после любых изменений в промпте или retrieval
- отдельную сводку по качеству `memories`
- более строгую сводку по `site_pages` с примерами `url_pattern`
- короткий changelog для новых evaluation batch

## Быстрая проверка

Чтобы быстро восстановить статистику без ручного поиска, достаточно:

```bash
sqlite3 data/workflow_memory.sqlite "select run_mode, count(*) from runs group by run_mode;"
sqlite3 data/workflow_memory.sqlite "select status, count(*) from runs group by status;"
sqlite3 data/workflow_memory.sqlite "select site, count(*) from memories group by site;"
sqlite3 data/workflow_memory.sqlite "select site, count(*) from site_pages group by site;"
```

