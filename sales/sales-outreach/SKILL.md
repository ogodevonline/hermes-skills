---
name: sales
description: "Продажи своего продукта малому бизнесу от списка до оплаты, любой канал (Telegram, Instagram, WhatsApp, звонок, визит, email, посевы, реклама). Найти бизнесы и ЛПР, написать первое сообщение как живой человек, вести диалог до оплаты, дожимать, считать воронку. Маршрутизатор к 3 наборам с GitHub (Sales-Skills 122, ai-sales-team 13, hello-boss) и marketingskills. Триггеры: «продать», «найти клиентов», «написать владельцам», «холодные сообщения», «скрипт продаж», «как достучаться до ЛПР», «почему не покупают», «воронка», «посевы», «таргет», «возражения»."
---

# Продажи: от списка до оплаты

Свой короткий порядок работы + готовые модули из открытых наборов. Модули читать
(`Read`) только когда нужен этот шаг, не все сразу.

## 0. Железные правила

1. **Ни слова неправды.** Только то, что реально видно в источнике, и откуда взят контакт. Не писать «видел ваш Instagram», «красивые работы», если не видел. Пойманная ложь = мёртвый диалог.
2. **Не обещать того, чего продукт не делает.** Перед текстом проверить по коду/проду. Не уверен — не пиши.
3. **Первое касание шлёт человек.** Рассылка роботом с личного аккаунта = бан. Агент готовит, владелец отправляет. Автоматизируется всё вокруг.
4. **Сначала разговор, потом продажа.** Первое сообщение = вопрос про их работу. Без цены, ссылки, видео.
5. **Как человек в мессенджере.** До 40 слов, разговорно, на их языке, у каждого свой факт. Прогнать через навык `humanizer`.

## 1. Порядок работы

| Шаг | Что делать | Наш файл | Модули из наборов |
|---|---|---|---|
| 1. Кому продаём | ICP, кто решает, видимый признак боли | [prospecting.md](references/prospecting.md) | `ai-sales-team/skills/sales-icp`, `sales-skills/skills/ideal-customer-profile-matching` |
| 2. Список | карты, реестры, каталоги; скрипт `scripts/ymaps.mjs` | [prospecting.md](references/prospecting.md) | `marketingskills/skills/prospecting` (см. его local-prospecting), `agent-pilot-skills/skills/hello-boss` (реестры, этап 2) |
| 3. ЛПР | реестр юрлиц, Instagram, отзывы, вопрос ресепшену | [prospecting.md](references/prospecting.md) | `sales-skills/skills/decision-maker-identification`, `ai-sales-team/skills/sales-contacts` |
| 4. Первое сообщение | факт → вопрос → (кто я) | ниже | `marketingskills/skills/cold-email` (см. его personalization), `hello-boss` этап 3, `sales-skills/skills/personalization-at-scale`, `response-length-calibration`, `tone-matching` |
| 5. Диалог | лестница маленьких «да» | [dialog.md](references/dialog.md) | `sales-skills/skills/micro-commitment-stacking`, `conversation-branching`, `asking-effective-questions`, `discovery`, `building-rapport` |
| 6. Возражения | ответы под продукт | [dialog.md](references/dialog.md) | `sales-skills/skills/objection-handling`, `pricing-discussion-logic`, `competitor-mention-handling`, `ai-sales-team/skills/sales-objections` |
| 7. Закрытие | одна ссылка, одна сумма, срок | [dialog.md](references/dialog.md) | `sales-skills/skills/closing`, `meeting-conversion` |
| 8. Дожим | день 3 новый угол, день 7 вежливое закрытие | ниже | `sales-skills/skills/ghost-recovery-sequences`, `follow-up-discipline`, `re-engagement-sequencing`, `ai-sales-team/skills/sales-followup` |
| 9. Каналы и автомат | что руками, что само; посевы, таргет | [automation.md](references/automation.md), [channels.md](references/channels.md) | `sales-skills/skills/multi-channel-coordination`, `channel-preference-detection`, `marketingskills/skills/ads`, `ad-creative` |
| 10. Оффер | ценность, гарантия, риск | — | `marketingskills/skills/offers`, `pricing` |

Пути модулей от `~/.agents/vendor/`, файл `SKILL.md` внутри папки.
Модули `sales-skills` написаны как «как построить sales-бота»: брать из них принципы и примеры реплик, а не код.

## 2. Первое сообщение

Формула: **правдивый факт про них → вопрос про их процесс → (кто я одной фразой)**.

> Здравствуйте) у вас на Яндекс картах 4,9 и 79 отзывов, клиентов явно много. А записываются к вам как, в директ или по телефону?

Проверка каждого: факт проверяемый · отвечается одним словом · нет «мы предлагаем / уникальный / хотите узнать» · вслух звучит как человек · не копия соседнего · язык как у них.

## 3. Дожим

День 3: новый угол (проще вопрос / короткий факт), не «напоминаю». День 7: «Не буду надоедать, пишу последний раз. Если понадобится, пишите». Дальше тишина = «нет ответа», вернуться через 2 месяца с новым поводом.

## 4. Что выдаёт агент

1. «Можно обещать / нельзя» по продукту (проверено в коде/на проде).
2. Список с ЛПР, отсортированный (CSV + md с кликабельными контактами).
3. 10–20 персональных первых сообщений с реальными фактами, на их языке.
4. Ответы на шаги 5–8 под продукт.
5. Таблица лога: `дата | бизнес | канал | шаг | ответ | следующее действие + дата`.
6. Через неделю: разбор лога, правка того, что не сработало, цифры в [automation.md](references/automation.md).

Не делать: покупать базы и аккаунты, слать скриптом с личного аккаунта, выдумывать факты и конверсии, обещать несуществующее, писать простыни.
