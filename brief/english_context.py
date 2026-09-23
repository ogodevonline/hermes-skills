#!/usr/bin/env python3
"""
english_context.py — Загрузка контекста последних N сессий для генерации урока.

Использование:
  python3 english_context.py                   # последние 10 сессий
  python3 english_context.py --count 5         # последние 5
  python3 english_context.py --count 10 --text-only  # только текст без заголовков
  python3 english_context.py --json            # JSON-выход
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from obsidian_utils import get_vault_path


def load_yaml(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_context(count: int = 10, as_json: bool = False):
    vault = get_vault_path()
    eng = vault / "Английский"
    state_path = eng / "state.yaml"

    state = load_yaml(state_path)
    if state is None:
        print("❌ state.yaml не найден", file=sys.stderr)
        sys.exit(1)

    book_name = state.get("book")
    session = state.get("session", 0)
    level = state.get("level", "A2")
    total_sessions = state.get("total_sessions", 0)

    book_path = eng / book_name
    book_yaml = load_yaml(book_path / "book.yaml") or {}

    if count < 1:
        count = 1

    start = max(1, session - count + 1)

    sessions = []
    for s in range(start, session + 1):
        text_path = book_path / f"session-{s:03d}" / "text.md"
        grammar_path = book_path / f"session-{s:03d}" / "grammar.md"
        vocab_path = book_path / f"session-{s:03d}" / "vocabulary.md"

        sess = {"number": s}
        if text_path.exists():
            sess["text"] = text_path.read_text(encoding="utf-8")
        if grammar_path.exists():
            sess["grammar"] = grammar_path.read_text(encoding="utf-8")
        if vocab_path.exists():
            sess["vocab"] = vocab_path.read_text(encoding="utf-8")
        sessions.append(sess)

    result = {
        "level": level,
        "book": book_name,
        "book_title": book_yaml.get("title", ""),
        "session": session,
        "total_sessions": total_sessions,
        "characters": book_yaml.get("characters", []),
        "setting": book_yaml.get("setting", ""),
        "themes": book_yaml.get("themes", []),
        "plot_threads": book_yaml.get("plot_threads", []),
        "summary": book_yaml.get("summary", ""),
        "sessions_loaded": len(sessions),
        "sessions": sessions,
    }

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Markdown output
    title = book_yaml.get("title", book_name)
    print(f"# {title} — Контекст (сессии {start}–{session})")
    print(f"Уровень: {level} | Всего сессий: {total_sessions}")
    print()

    # book meta
    print(f"## Основная информация")
    print(f"**Сеттинг:** {book_yaml.get('setting', '—')}")
    print(f"**Сюжет (сводка):** {book_yaml.get('summary', '—')}")
    print()
    print("**Персонажи:**")
    for ch in book_yaml.get("characters", []):
        print(f"- {ch.get('name', '?')} — {ch.get('role', '?')}")
    print()
    print("**Активные сюжетные линии:**")
    for pt in book_yaml.get("plot_threads", []):
        status_icon = "🟢" if pt.get("status") == "active" else "🔴"
        print(f"- {status_icon} {pt.get('description', '?')}")
    print()
    print(f"---")
    print()

    # last vocab
    print("## Последний вокабуляр (последние 3 сессии)")
    if sessions:
        last_vocabs = []
        for s in reversed(sessions[-3:]):
            if "vocab" in s:
                # extract bold words
                import re
                found = re.findall(r'\*\*(.+?)\*\*', s["vocab"])
                last_vocabs.extend(found)
        seen = set()
        unique = []
        for w in last_vocabs:
            wc = w.strip().rstrip(".,;:!?")
            if wc and wc not in seen:
                seen.add(wc)
                unique.append(wc)
        if unique:
            print(", ".join(unique[:15]))
    print()

    # session texts
    for sess in sessions:
        sn = sess["number"]
        text = sess.get("text", "")
        lines = text.strip().split("\n")
        # First line is usually the title
        title_line = lines[0] if lines else f"Session {sn}"
        print(f"## {title_line}")
        print()
        # Full text
        print(text.strip())
        print()
        print("---")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Загрузка контекста последних N сессий"
    )
    parser.add_argument(
        "--count", "-c", type=int, default=10,
        help="Количество сессий для загрузки (default: 10)"
    )
    parser.add_argument(
        "--json", "-j", action="store_true",
        help="Вывод в JSON"
    )
    parser.add_argument(
        "--text-only", "-t", action="store_true",
        help="Только текст сессий, без заголовков"
    )
    args = parser.parse_args()

    load_context(count=args.count, as_json=args.json)


if __name__ == "__main__":
    main()