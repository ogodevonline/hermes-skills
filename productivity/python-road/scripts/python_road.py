#!/usr/bin/env python3
"""
Python Road — CLI для системы обучения Python + SE с треккингом прогресса.

Команды:
  prepare --track <track>  — контекст для генерации сессии
  save --track <track> ...  — сохранить сессию
  status                    — показать прогресс по всем трекам
"""

import argparse
import json
import os
import sys
import yaml

# ─── Конфигурация ───────────────────────────────────────────────
VAULT = os.path.expanduser("~/hermes-vault/Python")
TRACKS_DATA = {
    "python-basics": {
        "label": "🐍 Python Basics",
        "slug": "Track-01-python-basics",
        "topics": [
            "variables", "types", "strings", "control-flow", "lists",
            "dicts-sets", "functions", "scope-closures", "comprehensions",
            "classes", "inheritance", "magic-methods", "exceptions",
            "iterators", "generators", "decorators", "context-managers",
            "async-basics", "async-await", "typing"
        ],
    },
    "algorithms": {
        "label": "⚡ Algorithms",
        "slug": "Track-02-algorithms",
        "topics": [
            "two-pointers", "sliding-window", "binary-search",
            "merge-sort", "quick-sort", "dfs", "bfs", "backtracking",
            "dp-basics", "dp-intermediate", "greedy", "intervals",
            "graphs-basics", "topological-sort"
        ],
    },
    "data-structures": {
        "label": "🏗️ Data Structures",
        "slug": "Track-03-data-structures",
        "topics": [
            "arrays", "linked-lists", "stacks", "queues", "hash-tables",
            "hash-sets", "binary-trees", "bst", "heaps", "graphs",
            "tries", "union-find"
        ],
    },
    "databases": {
        "label": "🗄️ Databases",
        "slug": "Track-04-databases",
        "topics": [
            "select-where", "joins", "group-by", "having", "subqueries",
            "window-functions", "cte", "indexes", "normalization",
            "transactions", "explain-analyze"
        ],
    },
    "patterns": {
        "label": "🧩 Patterns",
        "slug": "Track-05-patterns",
        "topics": [
            "strategy", "observer", "factory", "singleton", "decorator",
            "adapter", "facade", "command", "state", "template-method",
            "mvc", "repository"
        ],
    },
    "architecture": {
        "label": "🏛️ Architecture",
        "slug": "Track-06-architecture",
        "topics": [
            "solid", "clean-architecture", "dependency-injection",
            "rest-design", "repository-unitofwork", "event-sourcing",
            "cqs", "microservices", "cqrs"
        ],
    },
    "tooling": {
        "label": "🔧 Tooling",
        "slug": "Track-07-tooling",
        "topics": [
            "git-basics", "git-branching", "pytest-basics",
            "pytest-fixtures", "mocking", "docker-basics",
            "docker-compose", "ruff-flake8", "mypy", "pre-commit",
            "github-actions"
        ],
    },
}

TRACK_IDS = list(TRACKS_DATA.keys())
TRACK_BY_SLUG = {v["slug"]: k for k, v in TRACKS_DATA.items()}


# ─── Пути ────────────────────────────────────────────────────────
def state_path():
    return os.path.join(VAULT, "state.yaml")


def track_dir(track_id):
    return os.path.join(VAULT, TRACKS_DATA[track_id]["slug"])


def track_yaml_path(track_id):
    return os.path.join(track_dir(track_id), "track.yaml")


def session_dir(track_id, session_slug):
    return os.path.join(track_dir(track_id), session_slug)


# ─── Загрузка/сохранение state ──────────────────────────────────
def load_state():
    path = state_path()
    if os.path.exists(path):
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_state(state):
    os.makedirs(VAULT, exist_ok=True)
    with open(state_path(), "w") as f:
        yaml.dump(state, f, default_flow_style=False, allow_unicode=True)


def ensure_state():
    """Создаёт state.yaml если не существует, с дефолтными треками."""
    state = load_state()
    if not state or "tracks" not in state:
        state.setdefault("level", "beginner")
        state.setdefault("active_track", "python-basics")
        state["tracks"] = {}
        for tid in TRACK_IDS:
            state["tracks"][tid] = {
                "label": TRACKS_DATA[tid]["label"],
                "level": "beginner",
                "current_session": None,
                "completed": [],
                "last_topic": None,
                "last_summary": None,
                "last_concepts": [],
            }
        save_state(state)
    return state


def load_track_yaml(track_id):
    path = track_yaml_path(track_id)
    if os.path.exists(path):
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_track_yaml(track_id, data):
    d = track_dir(track_id)
    os.makedirs(d, exist_ok=True)
    with open(track_yaml_path(track_id), "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def ensure_track_yaml(track_id):
    """Создаёт track.yaml для трека если не существует."""
    data = load_track_yaml(track_id)
    td = TRACKS_DATA[track_id]
    if not data:
        data = {
            "track": track_id,
            "label": td["label"],
            "level": "beginner",
            "description": None,
            "topics": td["topics"],
            "current_topic_index": 0,
            "completed_topics": [],
        }
        save_track_yaml(track_id, data)
    return data


def next_topic(track_id):
    """Возвращает следующую неосвоенную тему из последовательности."""
    td = TRACKS_DATA[track_id]
    state = ensure_state()
    track_state = state["tracks"][track_id]
    completed = track_state.get("completed", [])
    last_topic = track_state.get("last_topic")

    # Сначала идём после last_topic
    if last_topic and last_topic in td["topics"]:
        idx = td["topics"].index(last_topic)
        for t in td["topics"][idx + 1:]:
            # Проверяем, не была ли тема уже пройдена
            topic_slug = f"session-{td['topics'].index(t)+1:03d}-{t}"
            if topic_slug not in completed:
                return t

    # Если ничего не нашли — берём первую непройденную
    for t in td["topics"]:
        topic_slug = f"session-{td['topics'].index(t)+1:03d}-{t}"
        if topic_slug not in completed:
            return t

    return None  # Все темы пройдены


def session_slug(track_id, topic):
    td = TRACKS_DATA[track_id]
    idx = td["topics"].index(topic) if topic in td["topics"] else len(td["topics"])
    return f"session-{idx+1:03d}-{topic}"


def load_session_yaml(track_id, slug):
    path = os.path.join(session_dir(track_id, slug), "session.yaml")
    if os.path.exists(path):
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


# ─── Команда: prepare ────────────────────────────────────────────
def cmd_prepare(args):
    state = ensure_state()
    track_id = args.track

    if track_id not in TRACKS_DATA:
        print(json.dumps({"error": f"Unknown track: {track_id}. Available: {', '.join(TRACK_IDS)}"}))
        sys.exit(1)

    ensure_track_yaml(track_id)
    track_state = state["tracks"][track_id]
    topic = next_topic(track_id)

    # Ищем последнюю завершённую сессию для контекста
    completed = track_state.get("completed", [])
    last_summary = track_state.get("last_summary")
    last_concepts = track_state.get("last_concepts", [])

    # Собираем компактный контекст
    result = {
        "track": track_id,
        "label": TRACKS_DATA[track_id]["label"],
        "level": track_state.get("level", "beginner"),
        "next_topic": topic,
        "current_session": track_state.get("current_session"),
        "completed_sessions": completed,
        "completed_count": len(completed),
        "total_topics": len(TRACKS_DATA[track_id]["topics"]),
        "last_summary": last_summary,
        "last_concepts": last_concepts,
        "all_progress": {},
    }

    # Краткий прогресс по всем трекам
    for tid in TRACK_IDS:
        ts = state["tracks"].get(tid, {})
        completed_count = len(ts.get("completed", []))
        total = len(TRACKS_DATA[tid]["topics"])
        result["all_progress"][tid] = {
            "label": ts.get("label", tid),
            "completed": completed_count,
            "total": total,
            "last_topic": ts.get("last_topic"),
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


# ─── Команда: save ───────────────────────────────────────────────
def cmd_save(args):
    state = ensure_state()
    track_id = args.track

    if track_id not in TRACKS_DATA:
        print(json.dumps({"error": f"Unknown track: {track_id}"}))
        sys.exit(1)

    track_data = TRACKS_DATA[track_id]
    topic = args.topic
    if not topic:
        print(json.dumps({"error": "Missing --topic"}))
        sys.exit(1)

    # Определяем slug сессии
    slug = session_slug(track_id, topic)
    sdir = session_dir(track_id, slug)
    os.makedirs(sdir, exist_ok=True)

    def read_content(value_or_path):
        """Если строка начинается с / — это путь к файлу, читаем его."""
        if value_or_path and value_or_path.startswith("/"):
            path = os.path.expanduser(value_or_path)
            if os.path.exists(path):
                with open(path) as f:
                    return f.read()
            return f"<file not found: {path}>"
        return value_or_path or ""

    # Сохраняем файлы сессии
    if args.notes:
        with open(os.path.join(sdir, "notes.md"), "w") as f:
            f.write(read_content(args.notes))

    if args.practice:
        with open(os.path.join(sdir, "practice.md"), "w") as f:
            f.write(read_content(args.practice))

    if args.review:
        with open(os.path.join(sdir, "review.md"), "w") as f:
            f.write(read_content(args.review))

    # session.yaml
    session_data = {
        "topic": topic,
        "summary": args.summary or "",
        "concepts": [c.strip() for c in (args.concepts or "").split(",") if c.strip()],
        "leetcode_solved": [int(x) for x in (args.leetcode or "").split(",") if x.strip().isdigit()],
    }
    with open(os.path.join(sdir, "session.yaml"), "w") as f:
        yaml.dump(session_data, f, default_flow_style=False, allow_unicode=True)

    # Обновляем state.yaml
    track_state = state["tracks"][track_id]
    track_state["current_session"] = slug
    track_state["last_topic"] = topic
    track_state["last_summary"] = args.summary
    track_state["last_concepts"] = [c.strip() for c in (args.concepts or "").split(",") if c.strip()]

    completed_list = track_state.get("completed", [])
    if slug not in completed_list:
        completed_list.append(slug)
    track_state["completed"] = completed_list

    save_state(state)

    print(json.dumps({"status": "saved", "track": track_id, "session": slug}, ensure_ascii=False, indent=2))


# ─── Команда: status ─────────────────────────────────────────────
def cmd_status(args):
    state = ensure_state()

    lines = []
    lines.append("📚 **Python Roadmap**")
    lines.append("")

    for tid in TRACK_IDS:
        ts = state["tracks"].get(tid, {})
        label = ts.get("label", TRACKS_DATA[tid]["label"])
        completed = len(ts.get("completed", []))
        total = len(TRACKS_DATA[tid]["topics"])
        pct = int(completed / total * 100) if total > 0 else 0
        filled = pct // 10
        bar = "█" * filled + "░" * (10 - filled)
        level = ts.get("level", "beginner")
        last_topic = ts.get("last_topic") or "—"
        lines.append(f"  {label}  {bar}  {pct:>2}%  [{level}]  _{last_topic}_")

    lines.append("")
    lines.append(f"Активный трек: **{state.get('active_track', '—')}**")
    lines.append(f"Общий уровень: **{state.get('level', 'beginner')}**")

    print("\n".join(lines))


# ─── Main ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Python Road — CLI для системы обучения Python + SE")
    subparsers = parser.add_subparsers(dest="command")

    # prepare
    p_prepare = subparsers.add_parser("prepare", help="Получить контекст для генерации сессии")
    p_prepare.add_argument("--track", required=True, choices=TRACK_IDS, help="Код трека")

    # save
    p_save = subparsers.add_parser("save", help="Сохранить сессию")
    p_save.add_argument("--track", required=True, choices=TRACK_IDS, help="Код трека")
    p_save.add_argument("--topic", required=True, help="Название темы")
    p_save.add_argument("--summary", help="Краткое саммари (1-2 предложения)")
    p_save.add_argument("--concepts", help="Ключевые понятия через запятую")
    p_save.add_argument("--leetcode", help="ID решённых задач через запятую")
    p_save.add_argument("--notes", help="Содержимое notes.md или путь к файлу")
    p_save.add_argument("--practice", help="Содержимое practice.md или путь к файлу")
    p_save.add_argument("--review", help="Содержимое review.md или путь к файлу")

    # status
    subparsers.add_parser("status", help="Показать прогресс по всем трекам")

    args = parser.parse_args()

    if args.command == "prepare":
        cmd_prepare(args)
    elif args.command == "save":
        cmd_save(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
