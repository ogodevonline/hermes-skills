# Open Deep Research — Setup & Configuration

## Установка

```bash
cd ~/.hermes/profiles/researcher
python3 -m venv venv-odr
source venv-odr/bin/activate
pip install open-deep-research
```

OK: установлено в `~/.hermes/profiles/researcher/venv-odr`

## Переменные окружения (.env)

В `~/.hermes/profiles/researcher/.env`:

```
TAVILY_API_KEY=tvly-dev-...
```

При запуске runner скрипт сам читает KiloCode ключ из `~/.hermes/.env` и Tavily ключ из `~/.hermes/profiles/researcher/.env`.

## Модели

Все 4 роли используют `openai:deepseek/deepseek-v4-flash` через KiloCode:

| Роль | Модель | Max tokens | 
|------|--------|-----------|
| Summarization | `openai:deepseek/deepseek-v4-flash` | 4096 |
| Research | `openai:deepseek/deepseek-v4-flash` | 10000 |
| Compression | `openai:deepseek/deepseek-v4-flash` | 4096 |
| Final Report | `openai:deepseek/deepseek-v4-flash` | 10000 |

LangChain `init_chat_model()` с префиксом `openai:` использует `ChatOpenAI`, который читает:
- `OPENAI_API_KEY` → KiloCode API key
- `OPENAI_BASE_URL` → `https://api.kilo.ai/api/gateway`

## Проверено: deepseek/deepseek-v4-flash через KiloCode

- ✅ **JSON mode (structured output)**: `{"capital": "Paris"}` — работает
- ✅ **Tool calling**: `get_weather("Paris")` — работает

Обе критичные функции поддерживаются.

## Скрипт-обёртка

Путь: `~/.hermes/scripts/open_deep_research_runner.py`

Запуск:
```bash
cd ~/.hermes/profiles/researcher
source venv-odr/bin/activate
python3 ~/.hermes/scripts/open_deep_research_runner.py --topic "..." --iterations 2 --output ~/report.md
```

Параметры:
- `--topic` — тема исследования (обязательно)
- `--iterations` — глубина (1-5, дефолт 2)
- `--output` — файл для сохранения отчёта

## Архитектура графа

```
User message → clarify_with_user → write_research_brief → 
  research_supervisor (supervisor + parallel researchers) → 
  final_report_generation → final_report
```

Supervisor суб-граф:
```
supervisor → supervisor_tools(parallel researcher_subgraphs) → supervisor (loop)
```

Researcher суб-граф:
```
researcher → researcher_tools(Tavily search) → researcher(loop) or compress_research
```

## Производительность

- Первый запуск: ~10-15с (LangChain/LangGraph инициализация)
- Последующие: зависит от iterations
  - iterations=1, react_tool_calls=3: ~20-30с
  - iterations=3, react_tool_calls=5: ~60-90с
- Tavily search: ~2-3с на запрос

## Ограничения

1. Tavily хуже ищет по RU/UZ — для локальных тем лучше search.py
2. Если Tavily возвращает пустые результаты — отчёт будет общим, без конкретных цифр
3. LangGraph тянет много зависимостей (~200MB в venv)
