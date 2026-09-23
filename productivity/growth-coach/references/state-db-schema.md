# state.db — схема сессий

Файл: `~/.hermes/state.db` (SQLite)

## Таблица sessions
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | TEXT | UUID сессии (напр. `20260526_215901_f130ee`) |
| source | TEXT | `cli`, `telegram`, `cron` и т.д. |
| title | TEXT | Название сессии |
| started_at | REAL | Unix timestamp начала |
| ended_at | REAL | Unix timestamp конца |
| message_count | INTEGER | Кол-во сообщений |
| tool_call_count | INTEGER | Кол-во вызовов инструментов |
| input_tokens | INTEGER | Токенов на вход |
| output_tokens | INTEGER | Токенов на выход |

## Таблица messages
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | INTEGER | PK |
| session_id | TEXT | FK → sessions.id |
| role | TEXT | `user`, `assistant`, `tool` |
| content | TEXT | Текст сообщения |
| timestamp | REAL | Unix timestamp |
| tool_name | TEXT | Имя вызванного инструмента |

## FTS5
- `messages_fts` — полнотекстовый поиск
- Используется `session_search` tool
