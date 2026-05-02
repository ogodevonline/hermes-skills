#!/usr/bin/env python3
"""Перенос просроченных задач на завтра (00:01 МСК)."""
import subprocess, os, sys

# systemd не видит ~/.local/bin, используем полный путь
t_path = os.path.expanduser("~/.local/bin/t")
if not os.path.exists(t_path):
    # fallback: ищем через which
    import shutil
    t_path = shutil.which("t")
    if not t_path:
        print("❌ t не найден ни в ~/.local/bin/t, ни в PATH", file=sys.stderr)
        sys.exit(1)

result = subprocess.run([t_path, "migrate"], capture_output=True, text=True, timeout=30)
out = (result.stdout or "").strip()
err = (result.stderr or "").strip()
print(out or err)
sys.exit(result.returncode)
