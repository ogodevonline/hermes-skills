import json
import os
from datetime import datetime, timedelta
from pathlib import Path

def generate_plan():
    plan_config = {
        "current_project": {
            "name": "Доработки OSINT проекта (30bit.ru)",
            "fixed_days": 15,
            "status": "неизвестно_после",
            "dependency": "продажа_идеи_клиентам"
        },
        "today_date": datetime.now().strftime("%Y-%m-%d"),
    }

    output = []
    output.append("=" * 60)
    output.append("📊 СКРИПТ ПЛАНИРОВАНИЯ — АДАПТИВНАЯ СИСТЕМА")
    output.append(f"Дата запуска: {plan_config['today_date']}")
    output.append("=" * 60)
    output.append("")

    # Уровень 1: Стратегия
    output.append("🎯 УРОВЕНЬ 1: СТРАТЕГИЯ (на 3 месяца)")
    output.append("-" * 40)
    output.append("Цель: сфокусироваться на том, что ВНУТРИ вашего контроля")
    output.append("")

    strategy = {
        "Карьера/Навыки": [
            "• Завершить текущий проект (15 дней) — показать результат",
            "• Обновить резюме и LinkedIn (делать по 30 мин/день)",
            "• Сделать pet-проект или case-study из текущей работы",
            "• Пройти 1-2 подходящих курса/челленджа (Python/JS)"
        ],
        "Здоровье": [
            "• 3-4 фиксированные тренировки в неделю (записать в календарь)",
            "• Сон 7-8 часов (неприкосновенно)",
            "• Прогулки/движение в те дни, когда нет спорта"
        ],
        "Отношения": [
            "• 1 фиксированный вечер в неделю — только вы (без работы)",
            "• 1 выходной в месяц — активити (готовить, музей, прогулка)",
            "• Честно обсуждать планы: 'давай смотреть, как закроем проект'"
        ],
        "Финансы": [
            "• Собрать резерв на 3-6 месяцев (если возможно)",
            "• Записать все траты 2 недели — понять, где оптимизировать",
            "• Рассчитать минимальный бюджет (на случай паузы)"
        ],
        "Проект": [
            "• Фокус на следующие 15 дней — всё для закрытия",
            "• Параллельно: готовить 'план Б' (поиск, пет-проекты)",
            "• Собрать портфолио: ключи, что сделано, результаты"
        ]
    }

    for area, tasks in strategy.items():
        output.append(f"\n{area}:")
        for t in tasks:
            output.append(t)

    output.append("")
    output.append("⚠️ ВАЖНО: Не обещай то, что зависит от работы")
    output.append("   Вместо: 'поедем в отпуск в августе'")
    output.append("   Скажи: 'давай выберем 3 варианта, а решим когда закроем проект'")
    output.append("")

    # Уровень 2: Тактика
    output.append("📅 УРОВЕНЬ 2: ТАКТИКА (планирование по воскресеньям)")
    output.append("-" * 40)
    output.append("Метод: Agile-подход — планировать только ближайшие 7 дней")
    output.append("")

    tactics = {
        "Must (обязательно)": [
            "• Задачи из текущего проекта (15 дней фикс)",
            "• Тренировки (записаны в календарь)",
            "• Вечер с девушкой (фикс)"
        ],
        "Should (важно)": [
            "• Подготовка к смене работы (30-60 мин/день)",
            "• Решения, уменьшающие неопределенность",
            "• Доработка навыков (Python/JS/React)"
        ],
        "Could (хочу)": [
            "• Личные проекты, хобби",
            "• Чтение, обучение",
            "• Долгие прогулки"
        ]
    }

    for category, items in tactics.items():
        output.append(f"{category}:")
        for i in items:
            output.append(i)
        output.append("")

    output.append("Ритуал воскресенья (20:00):")
    output.append("  1. Смотрю, что сделано за неделю")
    output.append("  2. Отмечаю завершенные задачи (✅)")
    output.append("  3. Планирую следующие 7 дней")
    output.append("  4. Корректирую Must/Should/Could")
    output.append("  5. Обновляю задачи в tasks.yml")
    output.append("")

    # Уровень 3: Оперативка
    output.append("⚡ УРОВЕНЬ 3: ОПЕРАТИВКА (ежедневно)")
    output.append("-" * 40)
    output.append("Правило 1-3-5: 1 главная, 3 средние, 5 мелких задач максимум")
    output.append("")
    output.append("Утро (утренний бриф):")
    output.append("  • Читаю tasks.yml")
    output.append("  • Выбираю 1-3 MUST-задачи на сегодня")
    output.append("  • Блокирую время в календаре (фокус-чанки)")
    output.append("")
    output.append("День (исполнение):")
    output.append("  • Deep Work (2-3 часа утра)")
    output.append("  • Разделять: работа / поиск / обучение")
    output.append("  • Если не закрыл задачу — перенести на завтра (пересмотреть)")
    output.append("")
    output.append("Вечер (дневник):")
    output.append("  • Выполнить evening-diary-brief")
    output.append("  • Проверить прогресс по проекту")
    output.append("  • Настроить задачи на завтра")
    output.append("")

    # Конкретный план
    output.append("=" * 60)
    output.append("📌 КОНКРЕТНЫЙ ПЛАН: БЛИЖАЙШИЕ 15 ДНЕЙ")
    output.append("=" * 60)
    output.append("")

    project_days = []
    for i in range(15):
        date = datetime.now() + timedelta(days=i+1)
        day_type = "Работа" if i < 10 else "Буфер/Переключение"
        if i == 0:
            task = "Старт: четкий план доработок на 15 дней"
        elif i == 14:
            task = "Финиш: завершение, сбор результатов"
        elif i == 7:
            task = "Чек-пойнт: середина, корректировка"
        elif i < 10:
            task = "Доработки проекта + параллельно: 30 мин подготовка к будущему"
        else:
            task = "Завершение + оценка ситуации (ясно что делать дальше)"

        project_days.append({
            "day": i+1,
            "date": date.strftime("%Y-%m-%d (%a)"),
            "type": day_type,
            "task": task
        })

    for d in project_days:
        marker = "🎯" if d["day"] in [1, 7, 10, 14, 15] else "📍"
        output.append(f"{marker} День {d['day']:2d} | {d['date']} | {d['type']}")
        output.append(f"     {d['task']}")
        output.append("")

    output.append("🔄 ПАРАЛЛЕЛЬНЫЕ ЗАДАЧИ (30-60 мин/день, всегда):")
    output.append("-" * 40)
    output.append("• Обновление резюме и LinkedIn (делать понемногу)")
    output.append("• Сбор ключей из текущего проекта")
    output.append("• Поиск похожих вакансий (понимание рынка)")
    output.append("• Тренировки (по расписанию)")
    output.append("• Вечер с девушкой (строго по плану)")
    output.append("")

    # Сценарии
    output.append("=" * 60)
    output.append("🔮 СЦЕНАРИИ (что делаем в зависимости от результата)")
    output.append("=" * 60)
    output.append("")

    scenarios = {
        "✅ Сценарий А: Проект продали, всё ок": [
            "• Отлично! Делаем 3-5 дней паузы",
            "• Создаем pet-проект из того, что понравилось",
            "• Активно ищем новые интересные задачи",
            "• Увереннее чувствуем себя на рынке"
        ],
        "⚠️ Сценарий Б: Проект закрыли, ищем новую работу": [
            "• Уже есть готовое портфолио (из этих 15 дней)",
            "• Резюме обновлено — сразу шлем",
            "• Знаем рынок, смотрели похожие места",
            "• Финансовый буфер позволяет искать спокойно (1-2 мес)"
        ],
        "🔄 Сценарий В: Проект продолжается, но неопределенность": [
            "• Продолжаем доработки",
            "• Параллельно создаем бэкап (поиск/пет-проекты)",
            "• Каждую неделю — чек-пойнт",
            "• Если через месяц не уверены — активируем поиск 100%"
        ]
    }

    for scenario, actions in scenarios.items():
        output.append(scenario)
        for a in actions:
            output.append(a)
        output.append("")

    output.append("=" * 60)
    output.append("🚀 КАК ЗАПУСТИТЬ")
    output.append("=" * 60)
    output.append("")
    output.append("1. Сохранить как ~/.hermes/scripts/planning.py")
    output.append("2. Запускать когда нужен план: python ~/.hermes/scripts/planning.py")
    output.append("3. Или добавить в cron/task-manager:")
    output.append("   - В воскресенье 20:00 — ревью недели")
    output.append("   - Конец месяца — план на следующий")
    output.append("")
    output.append("Альтернатива: встроить в свой evening-diary-brief")
    output.append("как раздел 'Планирование на неделю'")
    output.append("")

    return "\n".join(output)

if __name__ == "__main__":
    print(generate_plan())
