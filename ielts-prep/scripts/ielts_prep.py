#!/usr/bin/env python3
"""
ielts_prep.py — Управление IELTS книгами в Obsidian vault.

Структура:
  IELTS/
  ├── state.yaml
  ├── Book-NNN-slug/
  │   ├── book.yaml
  │   ├── episode-001/
  │   │   ├── reading.md
  │   │   ├── vocabulary.md
  │   │   ├── grammar.md
  │   │   └── writing.md
  │   ├── episode-002/ ...
  │   └── ...
  └── ...

Режимы:
  new-book  — создать новую книгу
  prepare   — подготовить JSON-контекст для генерации эпизода
  save      — сохранить эпизод (reading + vocabulary + grammar + writing)
  status    — текущий статус
  error-add — добавить ошибку в Error Bank
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path.home() / ".hermes" / "skills" / "brief"))
from obsidian_utils import get_vault_path, write_note, commit_all


# ───── константы ─────────────────────────────────────────────────────────────

IELTS_DIR = "IELTS"
PHASES = ["foundation", "building", "pre-exam"]
DEFAULT_PHASE = "foundation"
DEFAULT_BAND = 5.0


# ───── утилиты ───────────────────────────────────────────────────────────────

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
    return s.strip('-').lower()


def _next_book_num(vault: Path) -> int:
    ielts_dir = vault / IELTS_DIR
    if not ielts_dir.exists():
        return 1
    max_num = 0
    for d in ielts_dir.iterdir():
        if d.is_dir() and d.name.startswith("Book-"):
            m = re.match(r'Book-(\d+)', d.name)
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


def _get_ielts_dir(vault: Path) -> Path:
    d = vault / IELTS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_last_episode_summary(vault: Path, book_dir: str, episode: int) -> str:
    """Читает writing.md последнего эпизода — берёт первую строку как summary."""
    if episode == 0:
        return ""
    book_path = vault / IELTS_DIR / book_dir
    writing_path = book_path / f"episode-{episode:03d}" / "writing.md"
    if writing_path.exists():
        text = writing_path.read_text(encoding='utf-8').strip()
        # Берём первые 2 строки как краткое саммари
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        summary = ' '.join(lines[:3])
        return summary[:200]
    return ""


def _get_last_vocab(vault: Path, book_dir: str, episode: int, count: int = 10) -> list:
    """Собрать последние count уникальных слов из vocabulary.md последних 2 эпизодов."""
    words = []
    book_path = vault / IELTS_DIR / book_dir
    start = max(1, episode - 1)
    for e in range(start, episode + 1):
        vocab_path = book_path / f"episode-{e:03d}" / "vocabulary.md"
        if not vocab_path.exists():
            continue
        text = vocab_path.read_text(encoding='utf-8')
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


# ───── команды ───────────────────────────────────────────────────────────────

def cmd_new_book(args):
    """Создать новую книгу (пустую)."""
    vault = get_vault_path()
    ielts = _get_ielts_dir(vault)

    num = _next_book_num(vault)
    num_str = f"{num:03d}"
    slug = _slugify(args.title)
    book_dir_name = f"Book-{num_str}-{slug}"
    book_path = ielts / book_dir_name
    book_path.mkdir(parents=True, exist_ok=True)

    # Разбираем characters если передан YAML
    chars = []
    if args.characters:
        try:
            parsed = yaml.safe_load(args.characters)
            if isinstance(parsed, list):
                chars = parsed
        except Exception:
            pass

    book_data = {
        "title": args.title,
        "genre": args.genre or "investigation",
        "phase": args.phase or DEFAULT_PHASE,
        "setting": args.setting or "",
        "summary": "История только начинается.",
        "characters": chars,
        "themes": [],
        "plot_threads": [
            {"description": "Основная сюжетная линия", "status": "active"}
        ],
    }
    _save_yaml(book_path / "book.yaml", book_data)

    state = {
        "phase": args.phase or DEFAULT_PHASE,
        "target_band": DEFAULT_BAND,
        "current_book": book_dir_name,
        "episode": 0,
        "total_episodes": 0,
        "estimated_bands": {
            "reading": DEFAULT_BAND,
            "writing": DEFAULT_BAND,
            "speaking": DEFAULT_BAND,
            "grammar": DEFAULT_BAND,
            "vocabulary": DEFAULT_BAND,
        },
        "common_errors": [],
    }
    _save_yaml(ielts / "state.yaml", state)

    print(f"✅ Создана IELTS книга: {book_dir_name}")
    print(f"   Путь: {book_path}")
    print(f"   Жанр: {args.genre}, Фаза: {args.phase or DEFAULT_PHASE}")


def cmd_prepare(args):
    """Подготовить JSON-контекст для генерации эпизода."""
    vault = get_vault_path()
    ielts = _get_ielts_dir(vault)
    state_path = ielts / "state.yaml"

    state = _load_yaml(state_path)
    if state is None:
        print("❌ state.yaml не найден. Сначала создайте книгу: new-book", file=sys.stderr)
        sys.exit(1)

    book_name = state.get("current_book")
    episode = state.get("episode", 0)
    phase = state.get("phase", DEFAULT_PHASE)

    book_path = ielts / book_name
    book_yaml = _load_yaml(book_path / "book.yaml") or {}

    result = {
        "phase": phase,
        "book": book_name,
        "book_title": book_yaml.get("title", ""),
        "genre": book_yaml.get("genre", "investigation"),
        "episode": episode,
        "total_episodes": state.get("total_episodes", 0),
        "characters": book_yaml.get("characters", []),
        "setting": book_yaml.get("setting", ""),
        "themes": book_yaml.get("themes", []),
        "plot_threads": book_yaml.get("plot_threads", []),
        "summary": book_yaml.get("summary", ""),
        "last_episode_summary": _get_last_episode_summary(vault, book_name, episode),
        "last_vocab": _get_last_vocab(vault, book_name, episode, count=8),
        "estimated_bands": state.get("estimated_bands", {}),
        "common_errors": state.get("common_errors", [])[-5:],  # последние 5 ошибок
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_save(args):
    """Сохранить эпизод: episode-NNN/{reading.md, vocabulary.md, grammar.md, writing.md}."""
    vault = get_vault_path()
    ielts = _get_ielts_dir(vault)
    state_path = ielts / "state.yaml"

    state = _load_yaml(state_path)
    if state is None:
        print("❌ state.yaml не найден. Сначала создайте книгу: new-book", file=sys.stderr)
        sys.exit(1)

    book_name = state.get("current_book")
    book_path = ielts / book_name
    if not book_path.exists():
        print(f"❌ Директория книги не найдена: {book_path}", file=sys.stderr)
        sys.exit(1)

    # Инкремент эпизода
    episode = state.get("episode", 0) + 1
    state["episode"] = episode
    state["total_episodes"] = state.get("total_episodes", 0) + 1

    # Обновить фазу, если передали
    if args.phase:
        if args.phase in PHASES:
            state["phase"] = args.phase
        else:
            print(f"⚠️  Неизвестная фаза '{args.phase}'. Допустимо: {', '.join(PHASES)}", file=sys.stderr)

    # Обновить estimated bands если переданы
    if args.bands:
        try:
            bands = json.loads(args.bands)
            if isinstance(bands, dict):
                for k, v in bands.items():
                    if k in state.get("estimated_bands", {}):
                        state["estimated_bands"][k] = float(v)
        except json.JSONDecodeError:
            print("⚠️  Не удалось распарсить --bands, пропускаю", file=sys.stderr)

    episode_dir = f"episode-{episode:03d}"

    reading_rel = f"{IELTS_DIR}/{book_name}/{episode_dir}/reading.md"
    vocab_rel = f"{IELTS_DIR}/{book_name}/{episode_dir}/vocabulary.md"
    grammar_rel = f"{IELTS_DIR}/{book_name}/{episode_dir}/grammar.md"
    writing_rel = f"{IELTS_DIR}/{book_name}/{episode_dir}/writing.md"

    if args.reading:
        write_note(reading_rel, args.reading)
    if args.vocab:
        write_note(vocab_rel, args.vocab)
    if args.grammar:
        write_note(grammar_rel, args.grammar)
    if args.writing:
        write_note(writing_rel, args.writing)

    # Обновить book.yaml summary если передан
    if args.summary:
        book_yaml_path = book_path / "book.yaml"
        book_data = _load_yaml(book_yaml_path) or {}
        book_data["summary"] = args.summary
        _save_yaml(book_yaml_path, book_data)

        # Сохраняем через write_note чтобы в Obsidian было
        book_rel = f"{IELTS_DIR}/{book_name}/book.yaml"
        write_note(book_rel, yaml.dump(book_data, default_flow_style=False,
                                       allow_unicode=True, sort_keys=False))

    # Сохранить state.yaml
    state_rel = f"{IELTS_DIR}/state.yaml"
    state_content = yaml.dump(state, default_flow_style=False, allow_unicode=True, sort_keys=False)
    write_note(state_rel, state_content)

    # Git commit
    commit_all(f"ielts: episode {episode:03d} — {book_name}")

    print(f"✅ Сохранён эпизод {episode} книги {book_name}")
    print(f"   Путь: {book_name}/{episode_dir}/")
    print(f"   Фаза: {state.get('phase')}, Всего эпизодов: {state.get('total_episodes')}")


def cmd_status(args):
    """Показать краткий статус."""
    vault = get_vault_path()
    ielts = _get_ielts_dir(vault)
    state_path = ielts / "state.yaml"

    state = _load_yaml(state_path)
    if state is None:
        print("📭 Нет активной IELTS книги. Создайте: new-book")
        return

    book_name = state.get("current_book", "?")
    episode = state.get("episode", 0)
    phase = state.get("phase", "?")
    total = state.get("total_episodes", 0)

    book_path = ielts / book_name
    book_yaml = _load_yaml(book_path / "book.yaml") or {}
    title = book_yaml.get("title", book_name)

    bands = state.get("estimated_bands", {})

    print(f"📚 {title} ({book_name})")
    print(f"📊 Эпизод {episode} | Всего: {total} | Фаза: {phase}")
    print(f"🎯 Target: Band {state.get('target_band', 5.0)}")
    print()
    print(f"  📖 Reading:   {bands.get('reading', '—')}")
    print(f"  ✍️  Writing:   {bands.get('writing', '—')}")
    print(f"  🎤 Speaking:  {bands.get('speaking', '—')}")
    print(f"  🏗️  Grammar:   {bands.get('grammar', '—')}")
    print(f"  📚 Vocab:     {bands.get('vocabulary', '—')}")
    print()
    errors = state.get("common_errors", [])
    if errors:
        print(f"⚠️  Последние ошибки ({len(errors)}):")
        for err in errors[-3:]:
            print(f"   • [{err.get('type', '?')}] {err.get('description', '')[:80]}")
    print()
    print(f"📖 Сюжет: {book_yaml.get('summary', '—')[:150]}...")


def cmd_error_add(args):
    """Добавить ошибку в Error Bank (common_errors в state.yaml)."""
    vault = get_vault_path()
    ielts = _get_ielts_dir(vault)
    state_path = ielts / "state.yaml"

    state = _load_yaml(state_path)
    if state is None:
        print("❌ Нет активной книги.", file=sys.stderr)
        sys.exit(1)

    errors = state.get("common_errors", [])
    error_entry = {
        "type": args.err_type,
        "description": args.description,
        "episode": state.get("episode", 0),
        "count": 1,
    }

    # Проверяем, может такая ошибка уже есть — тогда увеличиваем count
    for err in errors:
        if err.get("type") == args.err_type and err.get("description") == args.description:
            err["count"] = err.get("count", 1) + 1
            err["episode"] = state.get("episode", 0)
            break
    else:
        errors.append(error_entry)

    state["common_errors"] = errors
    state_rel = f"{IELTS_DIR}/state.yaml"
    state_content = yaml.dump(state, default_flow_style=False, allow_unicode=True, sort_keys=False)
    write_note(state_rel, state_content)

    print(f"✅ Добавлена ошибка: [{args.err_type}] {args.description[:60]}")


def cmd_error_list(args):
    """Показать список ошибок."""
    vault = get_vault_path()
    ielts = _get_ielts_dir(vault)
    state_path = ielts / "state.yaml"

    state = _load_yaml(state_path)
    if state is None:
        print("📭 Нет активной книги.")
        return

    errors = state.get("common_errors", [])
    if not errors:
        print("✅ Ошибок нет! Молодец!")
        return

    # Группируем по типу
    by_type = {}
    for err in errors:
        t = err.get("type", "other")
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(err)

    for t, errs in by_type.items():
        print(f"\n[{t}] ({len(errs)} шт.)")
        for err in errs:
            print(f"   ⨯ {err.get('description', '?')[:100]} (×{err.get('count', 1)}, эп. {err.get('episode', '?')})")


# ───── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="IELTS Prep — управление IELTS книгами в Obsidian vault"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # new-book
    p_new = sub.add_parser("new-book", help="Создать новую книгу")
    p_new.add_argument("--title", required=True, help="Название книги")
    p_new.add_argument("--genre", default="investigation", help="Жанр")
    p_new.add_argument("--characters", default="", help="YAML-список персонажей")
    p_new.add_argument("--setting", default="", help="Сеттинг")
    p_new.add_argument("--phase", default=DEFAULT_PHASE,
                       help=f"Фаза: {', '.join(PHASES)}")

    # prepare
    sub.add_parser("prepare", help="Подготовить JSON-контекст для генерации эпизода")

    # save
    p_save = sub.add_parser("save", help="Сохранить эпизод")
    p_save.add_argument("--phase", help="Новая фаза (опционально)")
    p_save.add_argument("--bands", help="JSON с estimated bands (опционально, пример: '{\"reading\": 5.5}')")
    p_save.add_argument("--reading", default="", help="Содержимое reading.md (файл или строка)")
    p_save.add_argument("--vocab", default="", help="Содержимое vocabulary.md")
    p_save.add_argument("--grammar", default="", help="Содержимое grammar.md")
    p_save.add_argument("--writing", default="", help="Содержимое writing.md")
    p_save.add_argument("--summary", default="", help="Новый summary для book.yaml")

    # status
    sub.add_parser("status", help="Краткий статус")

    # error-add
    p_err = sub.add_parser("error-add", help="Добавить ошибку")
    p_err.add_argument("--type", dest="err_type", required=True,
                       help="Тип: grammar/vocab/writing/reading/speaking")
    p_err.add_argument("--description", required=True, help="Описание ошибки")

    # error-list
    sub.add_parser("error-list", help="Показать ошибки")

    args = parser.parse_args()

    if args.command == "new-book":
        cmd_new_book(args)
    elif args.command == "prepare":
        cmd_prepare(args)
    elif args.command == "save":
        # Поддержка: пути к файлам (начинаются с /)
        for field in ("reading", "vocab", "grammar", "writing", "summary"):
            val = getattr(args, field, "")
            if val and val.startswith("/"):
                p = Path(val)
                if p.exists():
                    setattr(args, field, p.read_text(encoding="utf-8"))
        cmd_save(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "error-add":
        cmd_error_add(args)
    elif args.command == "error-list":
        cmd_error_list(args)


if __name__ == "__main__":
    main()
