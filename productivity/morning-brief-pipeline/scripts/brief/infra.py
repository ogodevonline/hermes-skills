"""Инфраструктура — Docker, диск, RAM, load, Hermes"""
import os
import subprocess

HERMES_HOME = os.path.expanduser("~/.hermes")


def _run_command(cmd, timeout=30):
    """Выполнить shell-команду"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def get_infra_status():
    """Статус инфраструктуры: Docker, диск, RAM, load, Hermes"""
    lines = []

    # Docker
    docker_out, _ = _run_command("docker ps --format '{{.Names}}' 2>/dev/null")
    containers = [c for c in docker_out.splitlines() if c.strip()]
    if containers:
        lines.append(f"🐳 Docker: {len(containers)} контейнеров — {', '.join(containers[:3])}")
    else:
        lines.append("⚠️ Docker: нет работающих контейнеров")

    # Диск
    disk, _ = _run_command("df -h / | tail -1 | awk '{print $5, $4}'")
    if disk:
        parts = disk.split()
        usage = int(parts[0].replace('%', ''))
        free = parts[1] if len(parts) > 1 else "?"
        icon = "🔴" if usage > 90 else ("🟡" if usage > 75 else "💾")
        lines.append(f"{icon} Диск: {usage}% занято, свободно {free}")

    # RAM
    mem, _ = _run_command("free -h | grep Mem | awk '{print $3, $2}'")
    if mem:
        parts = mem.split()
        lines.append(f"🧠 RAM: {parts[0]}/{parts[1]}")

    # Load average
    load, _ = _run_command("cat /proc/loadavg | awk '{print $1}'")
    if load:
        lines.append(f"⚖️ Load: {load}")

    # Hermes
    hermes, _ = _run_command("ps aux | grep -E 'hermes.*gateway' | grep -v grep | wc -l")
    if hermes and int(hermes) > 0:
        lines.append("✅ Hermes: работает")
    else:
        lines.append("⚠️ Hermes: не найден")

    return "\n".join(lines) if lines else "✅ Система в норме"


if __name__ == "__main__":
    print(get_infra_status())