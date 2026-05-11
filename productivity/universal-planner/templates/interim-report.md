# Template: Interim Research Report

Use this format AFTER each enrich-search-agent or web_search call during Step 2 (Deep Research).

## Weather
```
🌤️ [дата]: [+18°C, солнечно / +12°C, дождь]
```

## Places / Events
```
🔍 Ищу: [запрос]
✅ Нашёл: [N] результатов за ~[N]с

📍 [place] (N):
  - [Название] | [Ключевой факт — часы/цена/адрес]
  - [Название] | [Ключевой факт]

🎪 [event] (N):
  - [Название] | [Дата, цена, место]

📖 [guide] (N):
  - [Обзорная статья] | [О чём]

→ [Моя короткая рефлексия: 1-2 предложения. Что выглядит круто, что проблемно.]
→ [Вопрос пользователю, если нужно уточнение]
```

## Food / Restaurants
```
🔍 Ищу: рестораны [район/метро]
✅ Нашёл: [N] результатов

🍽️ [food] — топ-3:
  🆓 [Название] | [Адрес, средний чек]
  💵 [Название] | [Адрес, средний чек]  
  💰 [Название] | [Адрес, средний чек]

→ [Моя рефлексия: какой вариант лучше подходит под бюджет/ситуацию]
```

## Rules
- After EACH report, ask the user or SAY what the next step is. Don't wait for "продолжаем?"
- If the topic is clear (e.g. weather is fine), move to next step without asking
- Keep reports under 600 chars
- No philosophical reflections — just facts + 1-2 sentences of analysis + next action