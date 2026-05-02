#!/usr/bin/env python3
"""
Task Manager — демон-планировщик для cron-задач из SQLite

Читает расписание из таблицы cron_jobs в ~/.hermes/tasks/tasks.db и запускает
скрипты по графику. Работает как бесконечный процесс (демон).

Скрипты живут в директориях навыков: ~/.hermes/skills/<skill>/scripts/
Маппинг script → skill задан в SCRIPT_TO_SKILL.
"""

import os
import sys
import time
import sqlite3
import logging
import subprocess
from pathlib import Path
from croniter import croniter
from datetime import datetime, timezone

# Конфигурация
TASKS_DIR = Path.home() / ".hermes" / "tasks"
DB_PATH = TASKS_DIR / "tasks.db"
SKILLS_DIR = Path.home() / ".hermes" / "skills"
SITE_PACKAGES = str(Path.home() / ".local" / "lib" / "python3.12" / "site-packages")

# Маппинг: script name → skill name (для поиска скрипта)
SCRIPT_TO_SKILL = {
    # (skill_category/skill_name) — путь относительно SKILLS_DIR
    "brief": "morning-brief-pipeline",       # productivity/morning-brief-pipeline
    "reminders": "cheap-telegram-reminders", # productivity/cheap-telegram-reminders
    "news_digest": "news-digest",            # productivity/news-digest
    "brief_evening": "evening-diary-brief",  # brief/evening-diary-brief
    "task_migrate": "personal-task-tracker", # productivity/personal-task-tracker
}

# Категория для каждого навыка (путь: skills/{category}/{skill}/scripts/)
SCRIPT_CATEGORY = {
    "brief": "productivity",
    "reminders": "productivity",
    "news_digest": "productivity",
    "brief_evening": "brief",
    "task_migrate": "productivity",
}

# Логирование
log_file = Path.home() / ".hermes" / "logs" / "task_manager.log"
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_script_dir(script_name: str) -> Path:
    """Вернуть директорию, где лежит скрипт (cwd для запуска).
    Путь: ~/.hermes/skills/{category}/{skill}/scripts/"""
    skill = SCRIPT_TO_SKILL.get(script_name)
    category = SCRIPT_CATEGORY.get(script_name)
    if skill and category:
        return SKILLS_DIR / category / skill / "scripts"
    # fallback — может понадобиться для скриптов не в навыках
    return Path.home() / ".hermes" / "scripts"

def get_pythonpath(script_dir: Path) -> str:
    """Собрать PYTHONPATH: директория скрипта + site-packages."""
    return f"{script_dir}:{SITE_PACKAGES}:" + os.environ.get("PYTHONPATH", "")

def get_env_with_path(script_dir: Path) -> dict:
    """Собрать окружение с PYTHONPATH и расширенным PATH."""
    env = os.environ.copy()
    env["PYTHONPATH"] = get_pythonpath(script_dir)
    # Добавляем ~/.local/bin в PATH (там лежат кастомные команды типа t)
    local_bin = str(Path.home() / ".local" / "bin")
    path_parts = env.get("PATH", "").split(":")
    if local_bin not in path_parts:
        env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    return env

# Сопоставление script → команда
SCRIPT_COMMANDS = {
    "brief": [
        "python3", "-c",
        "from brief import generate_brief; generate_brief()"
    ],
    "reminders": [
        "python3", "reminders.py"
    ],
    "news_digest": [
        "python3", "news_digest.py"
    ],
    "brief_evening": [
        "python3", "brief_evening.py"
    ],
    "task_migrate": [
        "python3", "task_migrate.py"
    ],
}

def load_cronjobs_from_db():
    """Загрузить список cron-задач из SQLite (таблица cron_jobs)."""
    if not DB_PATH.exists():
        logger.error(f"База данных {DB_PATH} не найдена")
        return []
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        cur.execute(
            "SELECT name, script, schedule, description, enabled FROM cron_jobs ORDER BY id"
        )
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка чтения из БД: {e}")
        return []

    jobs = []
    now = datetime.now(timezone.utc)
    grace_period = 120  # секунд: если задача должна была запуститься в течение последних 2 минут — запускаем сейчас

    for row in rows:
        name, script, schedule, description, enabled = row
        job = {
            "name": name,
            "script": script,
            "schedule": schedule,
            "description": description or "",
            "enabled": bool(enabled),
        }
        # Инициализируем _next_run
        try:
            iter = croniter(schedule, now)
            next_run_dt = iter.get_next(datetime)
            prev_run_dt = iter.get_prev(datetime)
            # Если предыдущий запуск был в последние grace_period секунд,
            # то считаем что задача не была обработана (демон был offline) и ставим _next_run = prev_run
            if (now - prev_run_dt).total_seconds() < grace_period:
                job["_next_run"] = prev_run_dt.timestamp()
            else:
                job["_next_run"] = next_run_dt.timestamp()
            logger.debug(f"Задача '{name}': prev={prev_run_dt.isoformat()}, next={next_run_dt.isoformat()}, now={now.isoformat()}")
        except Exception as e:
            logger.error(f"Ошибка парсинга cron '{schedule}' для задачи '{name}': {e}")
            job["_next_run"] = None

        jobs.append(job)

    return jobs

def run_script(script_name: str, job_name: str):
    """Запустить скрипт по имени."""
    if script_name not in SCRIPT_COMMANDS:
        logger.error(f"Неизвестный скрипт: {script_name}")
        return False

    cmd = SCRIPT_COMMANDS[script_name]
    script_dir = get_script_dir(script_name)
    env = get_env_with_path(script_dir)

    try:
        logger.info(f"▶ Запуск: {job_name} ({script_name})")
        result = subprocess.run(
            cmd,
            cwd=script_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 минут максимум
        )
        if result.returncode == 0:
            logger.info(f"✅ Успешно: {job_name}")
            if result.stdout:
                logger.debug(f"stdout: {result.stdout[:200]}")
        else:
            logger.error(f"❌ Ошибка {result.returncode}: {job_name}")
            if result.stderr:
                logger.error(f"stderr: {result.stderr[:500]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Timeout: {job_name}")
        return False
    except Exception as e:
        logger.error(f"💥 Исключение при запуске {job_name}: {e}")
        return False

def main():
    logger.info("🚀 Task Manager демон запущен")

    # Загружаем cronjobs с вычисленными next_run
    cronjobs = load_cronjobs_from_db()
    if not cronjobs:
        logger.warning("Нет cronjobs для выполнения. Проверьте таблицу cron_jobs в tasks.db")
        time.sleep(60)
        return

    logger.info(f"Загружено {len(cronjobs)} cronjobs")
    for job in cronjobs:
        logger.info(f"  '{job.get('name')}': _next_run={job.get('_next_run')}")

    # Отслеживание количества записей в БД для авто-перезагрузки
    prev_count = len(cronjobs)

    while True:
        # Проверяем, изменилось ли количество записей в БД
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM cron_jobs")
            current_count = cur.fetchone()[0]
            conn.close()
            if current_count != prev_count:
                logger.info("🔄 Обнаружено изменение в cron_jobs, перезагружаем...")
                cronjobs = load_cronjobs_from_db()
                prev_count = current_count
                logger.info(f"Загружено {len(cronjobs)} cronjobs")
        except Exception as e:
            logger.error(f"Ошибка при проверке cron_jobs: {e}")

        now_ts = time.time()
        now_dt = datetime.now(timezone.utc)

        for job in cronjobs:
            name = job.get("name", "Unnamed")
            script = job.get("script")
            schedule = job.get("schedule")
            enabled = job.get("enabled", True)
            next_run_ts = job.get("_next_run")

            if not enabled or not script or not schedule or next_run_ts is None:
                continue

            # Если пора запускать (текущее время >= next_run)
            if now_ts >= next_run_ts:
                success = run_script(script, name)
                # Пересчитываем следующий запуск в любом случае (успех или ошибка)
                try:
                    iter = croniter(schedule, now_dt)
                    next_run = iter.get_next(datetime)
                    job["_next_run"] = next_run.timestamp()
                    logger.debug(f"Следующий запуск '{name}': {next_run.isoformat()}")
                except Exception as e:
                    logger.error(f"Ошибка пересчёта расписания для '{name}': {e}")
                if not success:
                    logger.warning(f"Задача '{name}' завершилась с ошибкой, следующий запуск по расписанию")

        # Сон 60 секунд (проверяем каждую минуту)
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Task Manager остановлен пользователем")
    except Exception as e:
        logger.exception(f"💀 Критическая ошибка: {e}")
        sys.exit(1)
