#!/bin/bash
# dk.sh — выполняет docker-команду в группе docker (обход неактивной группы в долгоживущей сессии Hermes)
#
# Когда: пользователь добавил hermes в группу docker (usermod -aG docker), но сессия
# Hermes запущена ДО этого — группа не применится без перелогина, docker даёт
# permission denied. `newgrp docker -c "..."` возвращает ПУСТО (не работает),
# а heredoc-форма работает.
#
# Использование:
#   ~/.hermes/scripts/dk.sh docker ps
#   ~/.hermes/scripts/dk.sh docker compose -f ~/projects/lead-platform/docker-compose.yml logs app --tail 50
#
# ⚠️ КВОТИНГ: команды с вложенными кавычками (exec -T app sh -c '...') ломаются —
# $* снимает кавычки, и команда тихо выполняется НА ХОСТЕ (traceback покажет
# хост-пути /home/hermes/... вместо /app/...). Надёжный паттерн: записать команду
# в скрипт-файл (write_file /tmp/x.sh) и вызвать `dk.sh bash /tmp/x.sh`.
cmd=$(printf '%q ' "$@")
cat > /tmp/dk_cmd.sh <<CMD
#!/bin/bash
bash -c "$cmd"
CMD
chmod +x /tmp/dk_cmd.sh
newgrp docker <<'EOF'
bash /tmp/dk_cmd.sh
EOF
