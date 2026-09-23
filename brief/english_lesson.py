#!/usr/bin/env python3
"""
english_lesson.py — Управление изучением английского в Obsidian vault.

Новая структура (сессии, а не главы):
  Learning/English/
  ├── state.yaml
  └── Книга-NNN-slug/
      ├── book.yaml
      ├── session-001/
      │   ├── grammar.md
      │   ├── text.md
      │   └── vocabulary.md
      ├── session-002/ ...
      └── ...

Режимы:
  new-book  — создать новую книгу
  prepare   — подготовить JSON-контекст для генерации сессии
  save      — сохранить сессию (grammar.md + text.md + vocabulary.md)
  status    — текущий статус
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path.home() / ".hermes" / "scripts"))
from obsidian_utils import get_vault_path, write_note, commit_all


# ───── утилиты ─────────────────────────────────────────────────────────────

def _translit(text: str) -> str:
    mapping = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'E', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch',
        'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    }
    result = []
    for ch in text:
        result.append(mapping.get(ch, ch))
    return ''.join(result)


def _slugify(text: str) -> str:
    s = _translit(text)
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[-\s]+', '-', s)
    return s.strip('-').title().replace('-', '-')


def _next_book_num(vault: Path) -> int:
    eng_dir = vault / "Learning" / "English"
    if not eng_dir.exists():
        return 1
    max_num = 0
    for d in eng_dir.iterdir():
        if d.is_dir() and d.name.startswith("Книга-"):
            m = re.match(r'Книга-(\d+)', d.name)
            if m:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
    return max_num + 1


def _load_yaml(path: Path):
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _save_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _get_english_dir(vault: Path) -> Path:
    d = vault / "Learning" / "English"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_last_vocab(vault: Path, book_dir: str, session: int, count: int = 10) -> list:
    """Собрать последние count уникальных слов из vocabulary.md последних 3 сессий."""
    words = []
    book_path = vault / "Learning" / "English" / book_dir
    start = max(1, session - 2)
    for s in range(start, session + 1):
        vocab_path = book_path / f"session-{s:03d}" / "vocabulary.md"
        if not vocab_path.exists():
            continue
        text = vocab_path.read_text(encoding='utf-8')
        # Ищем строки вида **word** или ### word
        found = re.findall(r'\*\*(.+?)\*\*', text)
        words.extend(found)
        found_h3 = re.findall(r'^###\s+(.+)$', text, re.MULTILINE)
        words.extend(found_h3)
    seen = set()
    unique = []
    for w in words:
        w_clean = w.strip().rstrip('.,;:!?')
        if w_clean and w_clean not in seen:
            seen.add(w_clean)
            unique.append(w_clean)
    return unique[:count]


def _get_last_session_text(vault: Path, book_dir: str, session: int) -> str:
    """Прочитать text.md последней сессии."""
    if session == 0:
        return ""
    book_path = vault / "Learning" / "English" / book_dir
    text_path = book_path / f"session-{session:03d}" / "text.md"
    if text_path.exists():
        return text_path.read_text(encoding='utf-8')
    return ""


# ───── режимы ──────────────────────────────────────────────────────────────

def cmd_new_book(args):
    """Создать новую книгу."""
    vault = get_vault_path()
    eng = _get_english_dir(vault)

    num = _next_book_num(vault)
    num_str = f"{num:03d}"
    slug = _slugify(args.title)
    book_dir_name = f"Книга-{num_str}-{slug}"
    book_path = eng / book_dir_name
    book_path.mkdir(parents=True, exist_ok=True)

    book_data = {
        "title": args.title,
        "level": args.level or "A2",
        "setting": args.setting or "",
        "summary": "История только начинается.",
        "characters": [],
        "themes": [],
        "plot_threads": [],
    }
    if args.characters:
        try:
            chars = yaml.safe_load(args.characters)
            if isinstance(chars, list):
                book_data["characters"] = chars
        except Exception:
            pass

    _save_yaml(book_path / "book.yaml", book_data)

    state = {
        "level": args.level or "A2",
        "book": book_dir_name,
        "session": 0,
        "total_sessions": 0,
        "last_session_date": None,
    }
    _save_yaml(eng / "state.yaml", state)

    print(f"✅ Создана книга: {book_dir_name}")
    print(f"   Путь: {book_path}")


def cmd_prepare(args):
    """Подготовить JSON-контекст для генерации сессии."""
    vault = get_vault_path()
    eng = _get_english_dir(vault)
    state_path = eng / "state.yaml"

    state = _load_yaml(state_path)
    if state is None:
        print("❌ state.yaml не найден. Сначала создайте книгу: new-book", file=sys.stderr)
        sys.exit(1)

    book_name = state.get("book")
    session = state.get("session", 0)
    level = state.get("level", "A2")
    total_sessions = state.get("total_sessions", 0)

    book_path = eng / book_name
    book_yaml = _load_yaml(book_path / "book.yaml") or {}

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
        "last_session_text": _get_last_session_text(vault, book_name, session),
        "last_vocab": _get_last_vocab(vault, book_name, session, count=10),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_save(args):
    """Сохранить сессию: session-NNN/{grammar.md, text.md, vocabulary.md}."""
    vault = get_vault_path()
    eng = _get_english_dir(vault)
    state_path = eng / "state.yaml"

    state = _load_yaml(state_path)
    if state is None:
        print("❌ state.yaml не найден. Сначала создайте книгу: new-book", file=sys.stderr)
        sys.exit(1)

    book_name = state.get("book")
    book_path = eng / book_name
    if not book_path.exists():
        print(f"❌ Директория книги не найдена: {book_path}", file=sys.stderr)
        sys.exit(1)

    # Инкремент сессии
    session = state.get("session", 0) + 1
    state["session"] = session

    if args.level:
        state["level"] = args.level

    # sessions
    state["total_sessions"] = state.get("total_sessions", 0) + 1

    today = str(date.today())
    if state.get("last_session_date") != today:
        state["sessions_today"] = 0
    state["sessions_today"] = state.get("sessions_today", 0) + 1
    state["last_session_date"] = today

    session_dir = f"session-{session:03d}"

    # text.md
    if args.text:
        text_rel = f"Learning/English/{book_name}/{session_dir}/text.md"
        write_note(text_rel, args.text)

    # grammar.md
    if args.grammar:
        grammar_rel = f"Learning/English/{book_name}/{session_dir}/grammar.md"
        write_note(grammar_rel, args.grammar)

    # vocabulary.md
    if args.vocab:
        vocab_rel = f"Learning/English/{book_name}/{session_dir}/vocabulary.md"
        write_note(vocab_rel, args.vocab)

    # Загрузить book.yaml (нужен для summary, chars, threads)
    book_path_yaml = book_path / "book.yaml"
    book_data = _load_yaml(book_path_yaml) or {}

    # Обновить book.yaml — summary
    if args.summary:
        book_data["summary"] = args.summary

    # Обновить book.yaml — character_sheets (JSON-строка → merge)
    if args.chars:
        try:
            new_chars = json.loads(args.chars)
            existing = book_data.get("character_sheets", {})
            existing.update(new_chars)
            book_data["character_sheets"] = existing
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка парсинга --chars: {e}", file=sys.stderr)

    # Обновить book.yaml — plot_threads (JSON-строка → replace)
    if args.threads:
        try:
            new_threads = json.loads(args.threads)
            book_data["plot_threads"] = new_threads
        except json.JSONDecodeError as e:
            print(f"⚠️ Ошибка парсинга --threads: {e}", file=sys.stderr)

    # Сохранить book.yaml, если были изменения
    _save_yaml(book_path_yaml, book_data)
    book_rel = f"Learning/English/{book_name}/book.yaml"
    write_note(book_rel, yaml.dump(book_data, default_flow_style=False,
                                   allow_unicode=True, sort_keys=False))

    # Сохранить state.yaml
    state_rel = "Learning/English/state.yaml"
    state_content = yaml.dump(state, default_flow_style=False, allow_unicode=True, sort_keys=False)
    write_note(state_rel, state_content)

    # Один коммит на всю сессию
    commit_all(f"english: session {session:03d} — {book_name}")

    print(f"✅ Сохранена сессия {session} книги {book_name}")
    print(f"   Путь: {book_name}/{session_dir}/")
    print(f"   level={state.get('level')}, total_sessions={state.get('total_sessions')}")

    # Отправка в Telegram
    if getattr(args, "send", False):
        from subprocess import run
        book_title = ""
        if book_data:
            book_title = book_data.get("title", "")
        header = f"📖 **English — {book_title}, Сессия {session:03d}**" if book_title else f"📖 **English — Сессия {session:03d}**"
        run([
            "python3",
            str(Path.home() / ".hermes" / "scripts" / "telegram_send_lesson.py"),
            "--header", header,
            "--text", args.text,
            "--vocab", args.vocab if args.vocab else "",
            "--grammar", args.grammar,
        ], timeout=30)


def cmd_status(args):
    """Показать краткий статус."""
    vault = get_vault_path()
    eng = _get_english_dir(vault)
    state_path = eng / "state.yaml"

    state = _load_yaml(state_path)
    if state is None:
        print("📭 Нет активной книги. Создайте: new-book")
        return

    book_name = state.get("book", "?")
    session = state.get("session", 0)
    level = state.get("level", "?")
    total_sessions = state.get("total_sessions", 0)

    book_path = eng / book_name
    book_yaml = _load_yaml(book_path / "book.yaml") or {}
    title = book_yaml.get("title", book_name)

    last_vocab = _get_last_vocab(vault, book_name, session, count=5)
    vocab_str = ", ".join(last_vocab) if last_vocab else "—"

    print(f"📚 {title} ({book_name})")
    print(f"📊 Сессия {session} | Всего: {total_sessions} | Уровень: {level}")
    print(f"📝 Последние слова: {vocab_str}")
    print(f"📖 Сюжет: {book_yaml.get('summary', '—')[:120]}...")


# ───── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Управление изучением английского в Obsidian vault"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # new-book
    p_new = sub.add_parser("new-book", help="Создать новую книгу")
    p_new.add_argument("--title", required=True, help="Название книги")
    p_new.add_argument("--characters", default="", help="YAML-список персонажей")
    p_new.add_argument("--setting", default="", help="Сеттинг книги")
    p_new.add_argument("--level", default="A2", help="Уровень (A2, B1, ...)")

    # prepare
    p_prep = sub.add_parser("prepare", help="Подготовить JSON-контекст для генерации сессии")

    # save
    p_save = sub.add_parser("save", help="Сохранить сессию")
    p_save.add_argument("--level", help="Новый уровень (опционально)")
    p_save.add_argument("--text", required=True, help="Содержимое text.md (файл или строка)")
    p_save.add_argument("--grammar", required=True, help="Содержимое grammar.md (файл или строка)")
    p_save.add_argument("--vocab", default="", help="Содержимое vocabulary.md (файл или строка)")
    p_save.add_argument("--summary", default="", help="Новый summary для book.yaml (опционально)")
    p_save.add_argument("--chars", default="", help="JSON: character_sheets для book.yaml (обновление/добавление)")
    p_save.add_argument("--threads", default="", help="JSON: plot_threads для book.yaml (полная замена)")
    p_save.add_argument("--send", action="store_true", help="Отправить урок в Telegram после сохранения")

    # status
    sub.add_parser("status", help="Краткий статус")

    args = parser.parse_args()

    if args.command == "new-book":
        cmd_new_book(args)
    elif args.command == "prepare":
        cmd_prepare(args)
    elif args.command == "save":
        # Поддержка: аргументы могут быть путями к файлам (начинаются с /)
        for field in ("text", "grammar", "vocab", "summary"):
            val = getattr(args, field, "")
            if val and val.startswith("/"):
                p = Path(val)
                if p.exists():
                    setattr(args, field, p.read_text(encoding="utf-8"))
        cmd_save(args)
    elif args.command == "status":
        cmd_status(args)


if __name__ == "__main__":
    main()
