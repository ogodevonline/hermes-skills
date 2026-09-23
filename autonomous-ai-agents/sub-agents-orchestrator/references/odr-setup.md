# Open Deep Research (ODR) — Setup & Usage

Open Deep Research (LangChain) — opensource deep research агент. Планирует → ищет (до 5 агентов параллельно) → сжимает → пишет отчёт.

## Installation

```bash
# Отдельное venv в профиле researcher
cd ~/.hermes/profiles/researcher
python3 -m venv venv-odr
source venv-odr/bin/activate
pip install open-deep-research
```

## Configuration

### API Keys (в ~/.hermes/profiles/researcher/.env)
```
TAVILY_API_KEY=tvly-...      # Search engine (бесплатно 1000 запросов/мес)
```

### Переменные окружения (при запуске)
```bash
export OPENAI_API_KEY="<kilocode_key>"     # KiloCode API key
export OPENAI_BASE_URL="https://api.kilo.ai/api/gateway"
export TAVILY_API_KEY="<tavily_key>"
```

### Модели (через RunnableConfig)

Все 4 роли — deepseek/deepseek-v4-flash через KiloCode:
- `summarization_model`: `openai:deepseek/deepseek-v4-flash`
- `research_model`: `openai:deepseek/deepseek-v4-flash`
- `compression_model`: `openai:deepseek/deepseek-v4-flash`
- `final_report_model`: `openai:deepseek/deepseek-v4-flash`

**Проверено:** JSON mode (structured output) ✅, tool calling ✅ — работают.

### Tavily (search API)
Ограничения бесплатного tier:
- 1000 запросов/месяц
- Rate limit: ~5 запросов/сек
- Хорош для международных запросов
- ⚠️ Слаб на RU/UZ-специфичных запросах (цены в России, OLX, Яндекс)

## Usage via Kanban

Создать задачу на researcher:
```bash
hermes kanban create "deep research: [тема]" --assignee researcher \
  --body "Запусти Open Deep Research для темы: [тема].
  Скрипт: cd ~/.hermes/profiles/researcher && source venv-odr/bin/activate
  && export OPENAI_API_KEY=\$(grep KILOCODE_API_KEY ~/.hermes/.env | cut -d= -f2) \
  && export OPENAI_BASE_URL='https://api.kilo.ai/api/gateway' \
  && export TAVILY_API_KEY=... \
  && python3 run_deep_research.py --topic \"[тема]\"

  После завершения — сохрани отчёт в report-[topic].md.
  kanban_complete с summary отчёта."
```

## Python invocation (from script)

```python
import os, asyncio
from langchain_core.runnables import RunnableConfig
from open_deep_research.deep_researcher import deep_researcher

async def research(topic: str) -> str:
    config = RunnableConfig(configurable={
        "search_api": "tavily",
        "summarization_model": "openai:deepseek/deepseek-v4-flash",
        "research_model": "openai:deepseek/deepseek-v4-flash",
        "compression_model": "openai:deepseek/deepseek-v4-flash",
        "final_report_model": "openai:deepseek/deepseek-v4-flash",
        "allow_clarification": False,
        "max_researcher_iterations": 1,
        "max_react_tool_calls": 3,
        "max_concurrent_research_units": 2,
    })
    result = await deep_researcher.ainvoke(
        {"messages": [("user", topic)]},
        config
    )
    return result.get("final_report", "No report generated")

result = asyncio.run(research("Your research topic here"))
```

## Two-tier research approach

| Тип запроса | Что использовать |
|-------------|-----------------|
| **Быстрый факт** (погода, курс, 1 цена) | `web_search` / `search.py` |
| **RU/UZ поиск** (Яндекс, OLX, местные цены) | `web-search-scraper` (Yandex XML) |
| **Глубокий анализ** (multi-source, международный, structured report) | **Open Deep Research** |
| **Авиабилеты** | `aviasales-api` (Travelpayouts) |

## Pitfalls

1. **Tavily слаб на RU/UZ** — для российских/узбекских запросов даёт пустые или неточные результаты. Использовать Yandex XML для региона.
2. **Первый запуск медленный** — импорт LangChain грузится 10-30 секунд. Нормально.
3. **Structured output** — deepseek-v4-flash поддерживает, но может быть нестабилен на сложных схемах. Если `generate_report_plan` падает — попробуй `max_structured_output_retries: 3`.
4. **Tokenizer limits** — у deepseek-v4-flash нет записи в MODEL_TOKEN_LIMITS (utils.py). Если токены превышены — просто уменьши max_tokens.
5. **Не использовать для single-fact запросов** — ODR делает полный цикл (plan → search → verify → report), что занимает 30-60 сек. Для одного факта это оверхед.
