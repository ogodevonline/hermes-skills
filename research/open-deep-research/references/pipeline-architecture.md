# ODR Pipeline Architecture

Граф ODR (open_deep_research/deep_researcher.py):

```
START → clarify_with_user ──→ write_research_brief ──→ research_supervisor(subgraph) ──→ final_report_generation → END
                                         │                      │
                                         └── если clarify надо  │
                                                                 └── supervisor → supervisor_tools → [researcher_subgraph × N] → supervisor
                                                                                                    │
                                                                                                    └── researcher → researcher_tools → compress_research → END
```

## Ключевые модули

| Файл | Назначение |
|------|-----------|
| `deep_researcher.py` | Граф, 369 строк. Все node-функции. |
| `configuration.py` | Pydantic модель Configuration с 16 полями. Читается из env или configurable dict. |
| `utils.py` | Tavily search tool, MCP loading, token limit utils. |
| `state.py` | Pydantic модели состояний (AgentState, SupervisorState, ResearcherState). |
| `prompts.py` | Системные промпты для каждой роли. |

## Как работает поиск

1. `researcher()` node вызывает `get_all_tools(config)` из utils.py
2. `get_all_tools()` вызывает `get_search_tool(search_api)` — возвращает список инструментов
3. Если search_api=TAVILY — возвращает `tavily_search` (декорированная @tool функция)
4. Researcher model (deepseek) получает инструменты и решает когда вызывать `web_search`
5. `researcher_tools()` node выполняет вызовы инструментов параллельно через `asyncio.gather`
6. `compress_research()` node сжимает результаты через compression model

## Почему monkey-patch не работает

LangGraph компилирует граф через `StateGraph.compile()`. На момент компиляции:
- `researcher_subgraph` и `supervisor_subgraph` создаются с захваченными ссылками
- `configurable_model = init_chat_model(configurable_fields=...)` создаётся один раз на уровне модуля
- `get_all_tools` импортирован как `from open_deep_research.utils import get_all_tools`

Даже если заменить `utils.tavily_search = new_func` и `utils.get_search_tool = new_func`, ссылки внутри скомпилированного графа уже указывают на старые объекты. LangGraph не перечитывает модуль при каждом вызове.

Единственный рабочий способ: модифицировать исходники пакета перед импортом.
