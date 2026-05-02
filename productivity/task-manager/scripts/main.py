#!/usr/bin/env python3
"""
Task Manager — демон-планировщик для cronjobs.yml

Читает расписание из ~/.hermes/tasks/cronjobs.yml и запускает
скрипты по графику. Работает как бесконечный процесс (демон).

Архитектура:
- cronjobs.yml: список cron-задач (name, script, schedule, description)
- script: имя скрипта ("brief", "reminders") → сопоставляется с командой
- schedule: cron-выражение (UTC)
"""

import os
import sys
import time
import yaml
import logging
import subprocess
from pathlib import Path
from croniter import croniter
from datetime import datetime, timezone

# Конфигурация
TASKS_DIR = Path.home() / ".hermes" / "tasks"
CRONJOBS_FILE = TASKS_DIR / "cronjobs.yml"
SCRIPTS_DIR = Path.home() / ".hermes" / "scripts"

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
}

def load_cronjobs():
    """Загрузить список cron-задач из YAML."""
    if not CRONJOBS_FILE.exists():
        logger.error(f"Файл {CRONJOBS_FILE} не найден")
        return []
    with open(CRONJOBS_FILE, "r") as f:
        data = yaml.safe_load(f)
    jobs = data.get("cronjobs", [])
    # Инициализируем _next_run для каждой задачи
    now = datetime.now(timezone.utc)
    grace_period = 120  # секунд: если задача должна была запуститься в течение последних 2 минут — запускаем сейчас
    for job in jobs:
        schedule = job.get("schedule")
        if schedule:
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
                logger.debug(f"Задача '{job.get('name')}': prev={prev_run_dt.isoformat()}, next={next_run_dt.isoformat()}, now={now.isoformat()}")
            except Exception as e:
                logger.error(f"Ошибка парсинга cron '{schedule}' для задачи '{job.get('name')}': {e}")
                job["_next_run"] = None
    return jobs

def run_script(script_name: str, job_name: str):
    """Запустить скрипт по имени."""
    if script_name not in SCRIPT_COMMANDS:
        logger.error(f"Неизвестный скрипт: {script_name}")
        return False

    cmd = SCRIPT_COMMANDS[script_name]
    env = os.environ.copy()
    # Устанавливаем PYTHONPATH: SCRIPTS_DIR (для импорта brief как модуля) + site-packages
    site_packages = str(Path.home() / ".local" / "lib" / "python3.12" / "site-packages")
    env["PYTHONPATH"] = f"{SCRIPTS_DIR}:{site_packages}:" + env.get("PYTHONPATH", "")

    try:
        logger.info(f"▶ Запуск: {job_name} ({script_name})")
        result = subprocess.run(
            cmd,
            cwd=SCRIPTS_DIR,
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
    cronjobs = load_cronjobs()
    if not cronjobs:
        logger.warning("Нет cronjobs для выполнения. Проверьте ~/.hermes/tasks/cronjobs.yml")
        time.sleep(60)
        return

    logger.info(f"Загружено {len(cronjobs)} cronjobs")
    for job in cronjobs:
        logger.info(f"  '{job.get('name')}': _next_run={job.get('_next_run')}")

    # Отслеживание модификации cronjobs.yml для авто-перезагрузки
    cronjobs_mtime = CRONJOBS_FILE.stat().st_mtime if CRONJOBS_FILE.exists() else 0

    while True:
        # Проверяем, изменился ли cronjobs.yml
        try:
            if CRONJOBS_FILE.exists():
                current_mtime = CRONJOBS_FILE.stat().st_mtime
                if current_mtime != cronjobs_mtime:
                    logger.info("🔄 Обнаружено изменение в cronjobs.yml, перезагружаем...")
                    cronjobs = load_cronjobs()
                    cronjobs_mtime = current_mtime
                    logger.info(f"Загружено {len(cronjobs)} cronjobs")
        except Exception as e:
            logger.error(f"Ошибка при проверке mtime cronjobs.yml: {e}")

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
                if success:
                    # Пересчитываем следующий запуск
                    try:
                        iter = croniter(schedule, now_dt)
                        next_run = iter.get_next(datetime)
                        job["_next_run"] = next_run.timestamp()
                        logger.debug(f"Следующий запуск '{name}': {next_run.isoformat()}")
                    except Exception as e:
                        logger.error(f"Ошибка пересчёта расписания для '{name}': {e}")
                else:
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
