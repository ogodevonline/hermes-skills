# Curated Agent Skills Inventory (сентябрь 2026)

Проверено 02.09.2026 через web-tools + extract README. Звёзды/версии — на дату проверки.

## Заработок / бизнес

| Скилл | Что делает | Статус |
|---|---|---|
| iamzifei/show-me-the-money | 25 скиллов «ОС для бизнеса»: от идеи до revenue. Валидация спроса, продукт, маркетинг, реклама, контент (Topic Gate, короткие видео). Автор: соло-фаундер 6 SaaS, $1M+ выручки. v2.8.0, 849★. Бесплатно для личного использования; коммерческая перепродажа — OEM-лицензия | ✅ README проверен |
| Snyk «Top 8 Claude Skills for Entrepreneurs» (snyk.io/articles/top-8-claude-skills-entrepreneurs-startup-founders-solopreneurs/) | Маркетинг, копирайтинг, финмодели, запуск, лидоген для соло-фаундеров | ✅ статья проверена |
| Anthropic «Claude for Small Business» (anthropic.com/news/claude-for-small-business) | 15 готовых агентских воркфлоу: финансы, операции. Официально | по анонсу |
| Cowork Plugin for Business Coaches (coworkstack.ai/persona-packs/cowork-plugin-for-business-coaches/) | 20 capability для коучей: соглашения, подготовка сессий, ценообразование | сниппет |
| Business Growth Coach (mcpmarket.com/tools/skills/business-growth-coach) | Стиль Лилы Хормози: ROI, системы, масштабирование, «no-BS» | сниппет, extract 429 |
| Money Restore (mcpmarket.com/tools/skills/money-restore) | Continuity-скилл: подхват бизнес-разработки с места остановки | сниппет, extract 429 |
| Mindstudio Small Business Plugin Packs (mindstudio.ai) | Пак «getting paid»: инвойсы, учёт, follow-up | сниппет |

## Интервью → узнать пользователя → перепрошить мышление

| Скилл | Что делает | Статус |
|---|---|---|
| gidsi/claude-interview-skill (lobehub.com/skills/gidsi-claude-interview-skill-interview) | 3 фазы: (1) тихий анализ среды/инструментов/гит-паттернов, (2) интерактивное интервью по находкам, (3) USER_PROFILE_QUICK.md (300-500 токенов) + USER_PROFILE.md (2000-3000) + авто-подключение в CLAUDE.md. ⚠️ только последовательные батчи 3-5 tool calls (параллель ломает состояние) | ✅ lobehub проверен |
| Forlives/21-day-self-interview (github.com/Forlives/21-day-self-interview, 134★) | Экзистенциальный психолог: 3 вопроса каждый вечер × 21 день, помнит и отражает твои слова. Bilingual zh/en. «A Hermes Agent skill» — ставится и в Hermes | ✅ skillsllm + security PASSED |
| koreyba/Claude-Skill-Developmental-Coach (18★) | Интегральный коуч: Spiral Dynamics, стадии эго Кук-Гройтер, мета-рефлексия, рефрейминг. Память сессий — Notion MCP (обязателен) | ✅ README проверен |
| wealth-mindset (skills.rest/skill/wealth-mindset, repo cdeistopened/ask-sam) | Денежная психология, уровни мышления богатства, Wealth Staircase, «Perfect Tuesday Exercise». Старт: «What's your relationship with money right now?» | ✅ skills.rest проверен |
| Life Assessment Coach (mcpmarket.com/tools/skills/life-assessment-coach) | Аудит жизни: 10 сфер, приоритеты, планы роста | сниппет, extract 429 |
| Rich Guide (mcpmarket.com/tools/skills/rich-guide) | Персональный финансовый архитектор: структурированные финансовые интервью | сниппет, extract 429 |

## НЕ путать: job-interview коучинг (про устройство на работу)

- noamseg/interview-coach-skill — JD-анализ, резюме, mock-интервью (FAANG)
- raphaotten/claude-interview-coach — «Learns your story», CV + коучинг собеседований
- agentic-job-search-vault (awesomeskill.ai) — prep-interview
- Career-Ops (habr.com/ru/articles/1019990/) — 14 режимов, отклик на вакансии за тебя

Василий под «интервью, чтобы узнать меня» имеет в виду ЛИЧНЫЙ коучинг, а не собеседования. Если сниппет говорит «job search / FAANG / resume» — это не тот класс.

## Полезные агрегаторы / маркетплейсы

- github.com/anthropics/skills — официальные Agent Skills (PowerPoint/Excel/Word/PDF)
- platform.claude.com/docs — Agent Skills overview
- awesome-claude-skills (BehiSecc), VoltAgent/awesome-agent-skills (1000+), travisvn/awesome-claude-skills
- alirezarezvani/claude-skills (380+), rohitg00/awesome-claude-code-toolkit (135 agents/176+ plugins)
- tons-of-skills (tonsofskills.com, 471 plugins/3069 skills/347 agents, ccpi CLI)
- pluginmarketplace.ai/best-claude-plugins — по установкам (Frontend Design 1.1M, Superpowers 1.0M, Code Review 438k, Context7 417k)
- claudedirectory.org, mcpmarket.com, skills.rest, skillsllm.com, gradually.ai (47 маркетплейсов), awesomeskill.ai
- buildwithclaude.com/marketplaces — каталог маркетплейсов

## Безопасность

Snyk ToxicSkills (блог snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/):
- 36% просканированных скиллов содержали prompt injection
- 1467 вредоносных payload-ов в экосистеме
- 534 скилла (13.4%) — минимум одна критическая уязвимость

Правило: смотреть SKILL.md и скрипты ДО установки. skillsllm.com показывает security-скан (PASSED/issues) — использовать для быстрой проверки.

## Установка

- Пользовательский уровень: `~/.claude/skills/<name>/` (везде)
- Проектный уровень: `<project>/.claude/skills/<name>/` (в git)
- Через плагин: `/plugin marketplace add owner/repo`
- В Hermes: скопировать папку в `~/.hermes/skills/` — тот же формат SKILL.md

## Формат SKILL.md

- YAML frontmatter: name, description (критично для активации!), argument-hint → slash-command
- Прогрессивная загрузка: старт = name+description (~100 токенов/скилл), полный SKILL.md при совпадении, файлы по запросу
- Может исполнять скрипты: scripts/, `!command` синтаксис
- Спецификация: agentskills.io/specification
