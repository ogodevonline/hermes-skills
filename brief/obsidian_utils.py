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
