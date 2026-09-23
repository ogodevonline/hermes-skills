---
name: open-deep-research
category: research
description: "Post-mortem Open Deep Research (LangChain): что это, почему НЕ подходит. Справочный материал. Для продакшна используй research-report-templates + SOUL.md researcher."
---

# Open Deep Research — Post-Mortem

> ⚠️ НЕ ИСПОЛЬЗОВАТЬ. Оставлен как справочный материал. Установлен в `venv-odr` профиля researcher, может быть удалён.

## Что это

Open Deep Research (LangChain) — LangGraph-приложение для deep research. Пайплайн:
```
clarify → write_brief → research_supervisor → researcher_subgraph (search + compress) → final_report
```

Использует 4 модели: summarization, research, compression, final report. Все через `init_chat_model()`.

## Почему НЕ подходит

| Проблема | Подробности |
|----------|-------------|
| **Search API жёстко зашит** | Поддерживает только Tavily / OpenAI / Anthropic native search. Никакого Yandex XML или кастомных поисковиков без переписывания кода пакета. |
| **Tavily слаб для RU/UZ** | Для международных технологических запросов — норм. Для локальных (цены в РФ, OLX, Узбекистан) — пустые результаты. |
| **Мониторинг-патч ломает ссылки** | LangGraph компилирует граф со ссылками на функции. `utils.tavily_search` заменяется, но внутренние вызовы в `get_all_tools` уже захвачены. Патч `get_search_tool` тоже не спасает — граф использует `get_all_tools`, который внутри вызывает оригинальный поиск. |
| **Гибрид (собрал данные → передал в ODR)** | ODR игнорирует injected данные. Supervisor всё равно пытается искать. Без search_api пайплайн завершается пустым. |
| **Тяжёлый** | LangGraph + LangChain + supabase + google-cloud-aiplatform + 200+ зависимостей. Импорт ~15с. |
| **Brave Search API — платный** | $5/1000 запросов, кредитка. Не альтернатива. |

## Что проверено

1. **deepseek-v4-flash через KiloCode** — JSON mode ✅, tool calling ✅. Модель работает для всех 4 ролей.
2. **Tavily API** — бесплатный ключ есть, но для RU/UZ запросов результаты пустые.
3. **Yandex XML (search.py)** — отлично работает standalone, но не интегрируется в ODR.
4. **Monkey-patch подход** — не работает из-за того что LangGraph компилирует граф со статическими ссылками.

## Альтернативный подход

Вместо ODR использовать **прямой пайплайн** через SOUL.md researcher'а:

```
search.py / aviasales-api → верификация → structured report → kanban_complete
```

Шаблоны отчётов, self-check и workflow — в навыке `research-report-templates`.

## Ключевой урок

Не пытайся интегрировать внешние deep research фреймворки (ODR, GPT Researcher) в эту архитектуру.
Search API жёстко зашит (Tavily/OpenAI/Anthropic), monkey-patch не работает (LangGraph компилирует граф со статическими ссылками), гибридный подход (собрал данные → передал фреймворку) — фреймворк игнорирует injected данные.

**Рабочий подход:** search.py / aviasales-api / crawl4ai → анализ через deepseek → structured report по шаблону. Всё в одной Kanban-сессии.

См. навык `research-report-templates`.

## Технические детали (если пересматривать)

- Установка: `pip install open-deep-research` в `venv-odr`
- Граф: `from open_deep_research.deep_researcher import deep_researcher`
- API ключи в `researcher/.env`: `TAVILY_API_KEY=...`
- Модели: `openai:deepseek/deepseek-v4-flash` через `OPENAI_BASE_URL=https://api.kilo.ai/api/gateway`
- Конфигурация через `RunnableConfig(configurable={...})`

См. `references/pipeline-architecture.md` — полная схема графа ODR и точки интеграции.
