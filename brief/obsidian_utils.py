"""Общие утилиты для работы с Obsidian vault: запись заметок и git."""

import os
import subprocess
from pathlib import Path

VAULT_PATH = os.path.expanduser("~/hermes-vault")


def get_vault_path() -> Path:
    """Вернуть Path к Obsidian vault."""
    return Path(VAULT_PATH)


def write_note(subpath: str, content: str) -> str:
    """Записать файл в vault (без git-коммита)."""
    full_path = os.path.join(VAULT_PATH, subpath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    return full_path


def _parse_sections(text: str) -> list[dict]:
    """Разбить markdown на секции по заголовкам 2-го уровня (##).
    Возвращает [{'header': '## Утренний ритуал', 'body': '...', 'start': N, 'end': N}, ...]"""
    import re
    sections = []
    # Ищем заголовки ##
    pattern = re.compile(r'^(#{1,})\s+(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        return [{'header': '', 'body': text, 'start': 0, 'end': len(text)}]

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        sections.append({
            'header': m.group(0).rstrip(),
            'body': text[start:end],
            'start': start,
            'end': end,
        })
    return sections


def write_section(subpath: str, section_header: str, content: str) -> str:
    """Записать (или обновить) секцию в markdown-файле.
    Если секция с таким заголовком уже есть — заменяет её содержимое.
    Если нет — дописывает в конец.
    """
    full_path = os.path.join(VAULT_PATH, subpath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    existing = ""
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            existing = f.read()

    if not existing.strip():
        # Файла нет или пустой — пишем с нуля
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return full_path

    sections = _parse_sections(existing)
    header_match = section_header.rstrip()

    for sec in sections:
        if sec['header'] == header_match:
            # Замена секции
            new_text = existing[:sec['start']] + content + existing[sec['end']:]
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_text)
            return full_path

    # Секции нет — дописываем в конец
    with open(full_path, "a", encoding="utf-8") as f:
        f.write("\n\n" + content)
    return full_path


def commit_all(msg: str) -> None:
    """Один git add -A && git commit -m 'msg'. Post-commit hook делает push."""
    os.chdir(VAULT_PATH)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", msg], check=False)  # not check — может нечего коммитить


def save_note(subpath: str, content: str) -> str:
    """Устаревшая — только для обратной совместимости. Используй write_note + commit_all."""
    path = write_note(subpath, content)
    commit_all(f"update {subpath}")
    return path
