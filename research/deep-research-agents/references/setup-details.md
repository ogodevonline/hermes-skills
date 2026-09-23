# Setup details for Deep Research Agents

## Open Deep Research (LangChain)

### Установка
```bash
git clone https://github.com/langchain-ai/open_deep_research.git
cd open_deep_research
uv venv
source .venv/bin/activate
uv sync
cp .env.example .env
```

### .env конфигурация для OpenRouter
```
# Для OpenRouter (чтобы работал с deepseek и другими моделями)
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Tavily API (обязателен как search engine)
TAVILY_API_KEY=tvly-...

# Для OpenRouter ключ можно передать как OPENAI_API_KEY
OPENAI_API_KEY=sk-or-v1-...
```

### Запуск
```bash
# LangGraph сервер (рекомендуется)
uvx --refresh --from "langgraph-cli[inmem]" --with-editable . --python 3.11 langgraph dev --allow-blocking
# API: http://127.0.0.1:2024
# Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

### Конфигурация моделей (configuration.py)
```
summarization_model = "openai:gpt-4.1-mini"  # можно заменить на deepseek через OpenRouter
research_model = "openai:gpt-4.1"               # основная модель для research
compression_model = "openai:gpt-4.1-mini"
final_report_model = "openai:gpt-4.1"
```

Для OpenRouter моделей — использовать префикс `openai:` и указать полное имя модели:
```
research_model = "openai:deepseek/deepseek-v4-flash"
```

### Важно: Structured output
Все 4 модели должны поддерживать structured output. 
- deepseek/deepseek-v4-flash — ТРЕБУЕТ ПРОВЕРКИ
- openai:o3-mini — ✅ работает
- anthropic:claude-sonnet-4-20250514 — ✅ работает
- openai:gpt-4.1-mini — ✅ работает по умолчанию

## Tavily MCP

### Бесплатный ключ
Регистрация: https://app.tavily.com
Free tier: 1000 запросов/месяц

### Интеграция с Hermes
```yaml
# ~/.hermes/config.yaml
mcp:
  servers:
    tavily:
      transport: http  
      url: https://api.tavily.com/mcp
      api_key: ${TAVILY_API_KEY}
```

Документация: https://www.tavily.com/blog/hermes-agent-web-search-how-to-wire-tavily-into-a-self-improving-agent

## Firecrawl MCP
Бесплатно: 1000 credits/месяц
Регистрация: https://www.firecrawl.dev/
Документация по Hermes: https://www.firecrawl.dev/blog/hermes-agent

## GPT Researcher MCP (gptr-mcp)
```bash
# Требует OpenAI API ключ
# Установка MCP сервера:
npx @gptr/mcp

# Использование с Claude Desktop:
# ~/.claude/claude_desktop_config.json
{
  "mcpServers": {
    "gptr": {
      "command": "npx",
      "args": ["@gptr/mcp"]
    }
  }
}
```

## Ссылки
- Open Deep Research: https://github.com/langchain-ai/open_deep_research
- GPT Researcher: https://github.com/assafelovic/gpt-researcher
- GPT Researcher MCP: https://github.com/assafelovic/gptr-mcp
- OpenRouter with ODR: https://github.com/langchain-ai/open_deep_research/issues/75
- Tavily Hermes integration: https://www.tavily.com/blog/hermes-agent-web-search-how-to-wire-tavily-into-a-self-improving-agent
- Firecrawl Hermes: https://www.firecrawl.dev/blog/hermes-agent
- Deep Research Bench leaderboard: https://huggingface.co/spaces/muset-ai/DeepResearch-Bench-Leaderboard
- LangChain init_chat_model: https://python.langchain.com/docs/how_to/chat_models_universal_init/
