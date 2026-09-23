# Provider Override Pattern (Per-Task Model Switching)

## Проблема

Subagent наследует provider от родителя (или из `delegation` секции config.yaml). Нельзя указать `model/provider` в `delegate_task()` — нет параметров для per-call override.

Это значит что Skill Improver и Code Surgeon, которые должны делать анализ на сильной модели (claude-sonnet-4.6), а код на быстрой (deepseek-v4-flash), не могут этого сделать сами.

## Решение: Two-Phase Delegation с ручным переключением

### Вариант A: Родитель делает анализ, суб-агент кодирует

Самый надёжный вариант — я (Hermes) делаю анализ на своей модели, а делегирую только реализацию:

```
1. Я: читаю навык, анализирую проблему, составляю план
2. Показываю план пользователю, получаю approval
3. delegate_task → Skill Improver: "Вот план, реализуй"
   (суб-агенту остаётся только применить исправления — минимум рассуждений)
```

### Вариант B: Переключение config.yaml между фазами

Если анализ должен делать суб-агент (свежая голова), можно переключить delegation секцию:

```yaml
# Шаг 1: Временное переключение на claude-sonnet-4.6 для анализа
# ~/.hermes/config.yaml → delegation секция:
delegation:
  model: claude-sonnet-4-20250514
  provider: anthropic
  # api_key из .env

# delegate_task → Skill Improver: "Проанализируй и составь план" 
# (суб-агент идёт через claude)

# Шаг 2: Переключить обратно на deepseek для реализации
delegation:
  model: deepseek/deepseek-v4-flash
  provider: kilocode
  base_url: https://api.kilo.ai/api/gateway
  api_key: ${KILOCODE_API_KEY}

# delegate_task → Skill Improver: "Вот план, реализуй"
# (суб-агент идёт через deepseek)
```

**ВАЖНО:** После каждого переключения — проверять валидность YAML:
```bash
python3 -c "import yaml; yaml.safe_load(open('~/.hermes/config.yaml'))"
```

### Вариант C: Два профиля — два subagent run

Создать два профиля с разными delegation секциями:

```bash
# Профиль для анализа (claude)
hermes profile create analyzer
# → ~/.hermes/profiles/analyzer/config.yaml
# delegation: {model: claude-sonnet-4-20250514, provider: anthropic}

# Профиль для кодирования (deepseek) — наследует default
hermes profile create coder
# → ~/.hermes/profiles/coder/config.yaml
# delegation: {model: deepseek/deepseek-v4-flash, provider: kilocode, base_url: ..., api_key: ...}
```

Запуск через cronjob с profile=analyzer:
```python
cronjob(action='create', prompt="Проанализируй навык X", profile='analyzer')
```

Но для delegate_task это не применимо — subagent не использует профиль.

## Рекомендация

Использовать **Вариант A** для большинства случаев: я делаю анализ/план сам, делегирую только реализацию. Это:
- Не требует переключения конфигов (безопасно)
- Я имею полный контекст сессии
- Суб-агенту остаётся минимум рассуждений (меньше шансов натупить)
- Быстрее — один раунд делегирования вместо двух

Вариант B — для случаев когда нужна **действительно свежая голова** для анализа (я уже в петле и не могу адекватно оценить проблему). Но требует осторожности с конфигом.