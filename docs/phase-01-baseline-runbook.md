# Руководство по запуску Phase 1 Baseline

Операторное руководство для запуска базового стенда Phase 1. Предполагается, что планы 01-01 и 01-02 выполнены, а `.venv/` заполнен через `pip install -e .`.

## Подготовка

1. Установите Chromium один раз (отдельно от Python-пакета):
   ```
   .venv/bin/playwright install chromium
   ```
2. Заполните `.env` на основе `.env.example`. Минимум — укажите `OPENAI_API_KEY`. Публичная страница расписания MAI, используемая в Phase 1, **не требует** `MAI_USERNAME` / `MAI_PASSWORD`.
3. Проверьте загрузку конфига:
   ```
   .venv/bin/python -c "from workflow_memory.config import load_config; from pathlib import Path; print(load_config(Path('config/project.yaml')))"
   ```

## Запуск одной задачи

Короткая форма (для копирования):
```
.venv/bin/workflow-memory baseline --site mai_schedule --task-family schedule_lookup --input '{"group":"М3О-210Б-23","date":"2026-04-27"}' --config config/project.yaml
```

Многострочная форма для читаемости:
```
.venv/bin/workflow-memory baseline \
    --site mai_schedule \
    --task-family schedule_lookup \
    --input '{"group":"М3О-210Б-23","date":"2026-04-27"}' \
    --config config/project.yaml
```

Команда выводит `run_id`, `status`, `action_count`, `elapsed_seconds`.
Артефакты сохраняются в `artifacts/runs/<run_id>/`, строка добавляется в `data/workflow_memory.sqlite` (путь задаётся в `config/project.yaml`).

## Запуск полного набора задач

Короткая форма:
```
.venv/bin/workflow-memory baseline-suite --suite tasks/mai_schedule.yaml --config config/project.yaml
```

Многострочная форма:
```
.venv/bin/workflow-memory baseline-suite \
    --suite tasks/mai_schedule.yaml \
    --config config/project.yaml
```

Или через вспомогательный скрипт:

```
.venv/bin/python scripts/run_baseline_suite.py tasks/mai_schedule.yaml
```

Каждый элемент набора порождает один прогон. Команда выводит строку по каждому прогону и итоговую строку `Suite complete: total=N succeeded=X failed=Y`.

## Просмотр артефактов

Каждая директория прогона (`artifacts/runs/<run_id>/`) содержит три файла:

- `trace.json` — полный вывод `AgentHistoryList.model_dump()` от browser-use. Содержит пошаговые действия, снимки состояния браузера, сообщения LLM. Большой файл.
- `normalized.json` — компактная сводка в формате проекта. **Стабильная схема**, которую потребляют Phase 2 и Phase 3. Ключи:

  | Ключ | Тип | Описание |
  |------|-----|----------|
  | `run_id` | str | UUIDv7-строка — уникальный идентификатор прогона |
  | `site` | str | например `"mai_schedule"` |
  | `task_family` | str | например `"schedule_lookup"` |
  | `task_input` | dict | То, что передано через `--input` |
  | `run_mode` | str | `"baseline"` в Phase 1 |
  | `status` | str | `"succeeded"` / `"failed_verification"` / `"failed_execution"` |
  | `elapsed_seconds` | float | Реальное время выполнения `agent.run_sync` |
  | `action_count` | int | Количество шагов агента |
  | `action_names` | list[str] | Упорядоченные названия действий из истории агента |
  | `final_result` | str \| null | `history.final_result()` из browser-use |
  | `agent_success` | bool \| null | `history.is_successful()` из browser-use |
  | `is_done` | bool | `history.is_done()` из browser-use |
  | `errors` | list[str] | Ненулевые строки ошибок по шагам |
  | `urls_visited` | list[str \| null] | `history.urls()` — посещённые страницы |

- `result.json` — читаемая человеком сводка (`run_id`, `status`, `final_result`, `agent_success`, `elapsed_seconds`, `action_count`, опционально `error`).

Просмотр конкретного прогона:
```
cat artifacts/runs/<run_id>/result.json
jq . artifacts/runs/<run_id>/normalized.json
```

Список прогонов через SQLite:
```
sqlite3 data/workflow_memory.sqlite \
    "SELECT run_id, site, task_family, status, json_extract(metrics_json,'$.elapsed_seconds') FROM runs ORDER BY rowid DESC LIMIT 20;"
```

## Проверка воспроизводимости

Запустите одну и ту же задачу дважды и убедитесь:

1. Получены два разных `run_id`.
2. Созданы две отдельные директории артефактов.
3. Обе прошли валидацию схемы:
   ```
   .venv/bin/python scripts/check_artifact_schema.py artifacts
   ```
   Ожидается: каждый прогон выведен с `OK`, код завершения 0.
4. `status` равен `"succeeded"` хотя бы для одного прогона (страница расписания MAI зависит от доступности сайта и удачи навигации агента; одна повторная попытка допустима в рамках исследовательского прототипа Phase 1).

Если `status` равен `"failed_execution"` при каждой попытке, изучите `trace.json`:
```
jq '.history[-1]' artifacts/runs/<run_id>/trace.json
```
Частые причины:
- Chromium не установлен — выполните `playwright install chromium`.
- `OPENAI_API_KEY` не задан или недействителен — проверьте `.env`.
- Сайт MAI временно недоступен — повторите позже.
- `max_steps=25` слишком мало для этой группы/даты — попробуйте `--max-steps 35`.

## Известные ограничения Phase 1

- Верификатор — на основе правил (длина > 50 символов + наличие паттерна `\d{1,2}:\d{2}`). Может давать ложноположительные на страницах, случайно содержащих время, и ложноотрицательные на компактных выводах расписания. Доработка отложена до Phase 3.
- Нет автоматического повтора при сбое. Если агент исчерпывает `max_steps`, прогон записывается как `failed_execution`, оператор решает — повторять или нет.
- Стоимость одного прогона не ограничена стендом — ограничивается косвенно через `max_steps` и паттерн LLM-вызовов browser-use. При запуске полного набора следите за потреблением OpenAI.
