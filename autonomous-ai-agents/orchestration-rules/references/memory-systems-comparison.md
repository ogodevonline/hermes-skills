# Сравнение систем памяти для AI-агентов

Исследование от 2026-05-25. Сравнено 7 систем с Hermes Agent.

## Ключевой вывод

Hermes Agent **не нужно догонять** Mem0 или Zep — у него принципиально другая архитектура (frozen snapshot + prefix caching + кураторство агентом = 0ms latency). Но есть улучшения, которые стоит внедрить.

## Сравнительная таблица

| Система | Лицензия | ⭐ | Тип памяти | Ключевая фича |
|---------|----------|----|-----------|--------------|
| **Mem0** | Apache 2.0 | 56.6K | Key-value + vector | Подключаемый memory layer, SOTA бенчмарки (94.8% LongMemEval) |
| **Letta/MemGPT** | Apache 2.0 | 21K | 3-tier (core/recall/archival) | ОС-подобная память, self-editing |
| **CrewAI Memory** | MIT | — | 4 типа: short/long/entity/task | memory=True одной строкой, автопаспинг фактов |
| **LangGraph Memory** | MIT | — | Checkpoints + Store | Time travel, production-grade persistence |
| **Zep/Graphiti** | Apache 2.0 (Graphiti) | — | Темпоральный граф знаний | Би-темпоральность, provenance |
| **VectorMemory** | Apache 2.0 | — | Векторная (ChromaDB/Qdrant) | Просто, но без отношений и темпоральности |

## Чем Hermes Agent лучше

| Аспект | Преимущество |
|--------|-------------|
| **Latency = 0** | Память всегда в контексте — нет retrieval latency, нет round-trip к внешней БД |
| **Простота** | Два файла, один memory tool. Не нужно ставить Neo4j, настраивать эмбеддинги |
| **Кураторство** | Агент сам решает, что важно. Не garbage-in-garbage-out как у пассивных extraction pipeline |
| **Frozen Snapshot** | Prefix caching — огромная экономия токенов на каждом шаге сессии |
| **Session Search** | Быстрый FTS5 по истории — альтернатива долгосрочной памяти без оверхеда |
| **Skills = процедурная память** | Отдельная система для инструкций/workflow — не засоряет фактуальную память |

## План улучшений для Hermes Agent (по приоритетам)

### Priority 1 (1-2 дня)
- **Векторный поиск по памяти** — ChromaDB с local embedding моделью (all-MiniLM-L6-v2). Даст semantic search вместо FTS5 keyword match.
- **Auto-extract фактов** — после каждого диалога дешёвый LLM вызов для извлечения ключевых фактов в memory. Экономит ручную работу агента.

### Priority 2 (3-5 дней)
- **Auto-prefetch session_search** — перед ответом автоматически искать релевантные прошлые сессии.
- **Conflict detection** — если новая инфа противоречит старой памяти — подсвечивать.

### Priority 3 (1-2 недели)
- **MCP-сервер Hermes Memory** — чтобы другие агенты (через MCP) могли читать/писать в память.
- **Versioning истории изменений** — кто и когда менял память.

## Примечание по нагрузке

- FTS5 / session_search — бесплатно (SQLite, миллисекунды)
- Auto-extract — 1 LLM вызов (DeepSeek V4 Flash) после диалога, ~500-1000 токенов
- Векторный поиск — самая тяжёлая часть. Local embedding ≈ +80-100 MB RAM, CPU нагрузка. Если нет дешёвого embedding API — отложить.