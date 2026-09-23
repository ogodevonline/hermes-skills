---
name: deep-research-agents
category: research
description: Обзор open source deep research агентов для интеграции с Hermes researcher. Сравнение, установка, конфигурация, питфоллы. Open Deep Research, GPT Researcher, Tavily MCP, Firecrawl MCP.
---

# Deep Research Agents — внешние инструменты для researcher

## Когда загружать этот навык

- Пользователь спрашивает «как улучшить researcher» или «какие есть готовые research агенты»
- Нужно выбрать внешний инструмент для глубокого исследования (multi-source, план→сбор→отчёт)
- Пользователь жалуется на качество/глубину текущего researcher
- Нужно интегрировать новый search API или MCP-сервер для ресерча

## Ландшафт: opensource deep research агенты

### 1. Open Deep Research (LangChain) — `langchain-ai/open_deep_research`

**Рекомендуемый вариант для Hermes** — работает с любым провайдером через OpenRouter.

| Характеристика | Значение |
|----------------|----------|
| GitHub Stars | 11.5k+ |
| Лицензия | MIT |
| Установка | `pip install open-deep-research` или git clone |
| Язык | Python, LangGraph |
| Запуск | LangGraph сервер (порт 2024) или CLI |
| Search API | Tavily (по умолчанию), OpenAI/Anthropic native, MCP |
| Модели | Любые через `init_chat_model()` — 4 роли (summarization, research, compression, report) |
| Structured output | **Обязателен** для всех 4 моделей |
| OpenRouter | Через `OPENAI_BASE_URL` + префикс `openai:` |
| DeepSeek | Через OpenRouter или нативный `ChatDeepSeek` — **надо тестировать structured output** |

**Архитектура:**
- Supervisor + parallel Researcher sub-agents (до 5 параллельно)
- 4 этапа: план → параллельный сбор (search) → компрессия → финальный отчёт
- Max Researcher Iterations (default 3) — сколько раз supervisor задаёт follow-up вопросы
- Max React Tool Calls (default 5) — tool calls на один шаг researcher'а

**Что нужно для работы:**
- Tavily API key (бесплатно 1000 запросов/мес) ИЛИ OpenAI/Anthropic native search
- Модель с structured output для plan/report этапов
- Python 3.11

**Питфоллы:**
- Не все модели поддерживают structured output (qwen/qwq-32b:free — НЕ поддерживает)
- o3-mini, claude-sonnet, gpt-4.1 — поддерживают
- LangGraph сервер нужно держать запущенным
- Для OpenRouter: обязателен `OPENAI_BASE_URL` в .env

---

### 2. GPT Researcher (assafelovic) — `assafelovic/gpt-researcher`

| Характеристика | Значение |
|----------------|----------|
| GitHub Stars | 15k+ |
| Лицензия | MIT |
| Установка | `pip install gpt-researcher` |
| Search API | Tavily (по умолчанию) |
| Модели | **Только OpenAI** (не поддерживает OpenRouter) |
| MCP сервер | Есть — `gptr-mcp` |
| Стоимость | ~$0.40/запрос (o3-mini) |

**Минус для Василия:** требует OpenAI API, не работает с deepseek через KiloCode. Но MCP сервер можно подключить как дополнительный инструмент.

---

### 3. Tavily MCP

Search API, заточенный под AI-агентов. **Есть документация по интеграции с Hermes Agent.**

| Характеристика | Значение |
|----------------|----------|
| Бесплатный tier | 1000 запросов/месяц |
| Что даёт | search + extract + news |
| Интеграция | MCP сервер или как native web backend |
| Качество | Лучше Yandex XML для международных запросов |

Гайд по интеграции: `tavily.com/blog/hermes-agent-web-search-how-to-wire-tavily-into-a-self-improving-agent`

---

### 4. Firecrawl MCP

Веб-скрапинг с JS-рендерингом.

| Характеристика | Значение |
|----------------|----------|
| Бесплатный tier | 1000 credits/мес |
| Интеграция с Hermes | Есть, документирована |
| Зачем | Качественнее текущего `web_extract` (рендерит JS) |

---

## Интеграция с Hermes

### Подход А: MCP сервер (рекомендуется)

```
# Подключаем Tavily/Firecrawl/OpenDeepResearch как MCP
~/.hermes/config.yaml:
  mcp:
    servers:
      tavily:
        transport: http
        url: https://api.tavily.com/mcp
        api_key: ${TAVILY_API_KEY}
      open-deep-research:
        transport: stdio
        command: langgraph
        args: ["dev", "--port", "2024"]
```

После подключения researcher получает доступ к инструментам MCP сервера и может их вызывать как родные тулзы.

### Подход Б: навык для researcher (реализован)

Создан навык `open-deep-research` в `~/.hermes/skills/research/open-deep-research/`, symlink в профиль researcher. Researcher загружает через `skill_view('open-deep-research')`.

Скрипт-обёртка: `~/.hermes/scripts/open_deep_research_runner.py`

Workflow:
```
Запрос → open_deep_research_runner.py --topic "..." --iterations 2-3 → structured report → kanban_complete
```

В SOUL.md researcher добавлен Rule 13 и второй Workflow-путь для Open Deep Research.

### Подход В: delegate_task (самый простой)

Researcher запускает Open Deep Research как sub-agent через terminal:

```
delegate_task(
  goal="Запусти open-deep-research на тему: ...",
  toolsets=["terminal"],
  context="Используй pip install -e ~/open-deep-research или langgraph dev"
)
```

## Выбор модели для structured output

Open Deep Research требует structured output для 4 ролей. Проверенные варианты:

| Модель | Structured output | Доступ через |
|--------|-------------------|--------------|
| deepseek/deepseek-v4-flash | ✅ Проверено: работает (JSON mode + tool calling) | KiloCode (OpenAI-совместимый) |
| o3-mini | ✅ | OpenRouter |
| claude-sonnet-4 | ✅ | OpenRouter / KiloCode |
| gpt-4.1-mini | ✅ | OpenRouter |

**Рекомендация:** deepseek-v4-flash для всех 4 ролей — подтверждено, structured output и tool calling работают через KiloCode. Конфигурация: `openai:deepseek/deepseek-v4-flash` с `OPENAI_BASE_URL=https://api.kilo.ai/api/gateway`.

## Питфоллы

1. **Structured output — узкое место.** Если модель не поддерживает — падает на `generate_report_plan`. Всегда проверяй перед интеграцией.
2. **Tavily API — ещё один ключ.** Нужно получить и хранить в .env
3. **LangGraph сервер жрёт память.** Open Deep Research как LangGraph приложение ~200-500MB RAM
4. **Open Deep Research требует Python 3.11.** Убедись что версия подходит
5. **GPT Researcher не дружит с deepseek.** Только OpenAI — для Василия не вариант
6. **Когда спросили про «лучше #6»** — лидерборд Deep Research Bench состоит из закрытых/платных решений (OpenAI, Perplexity, Google). Open Deep Research — лучший opensource вариант, который можно установить себе.
