#!/bin/bash
# Google Tasks aliases for Hermes
# Add to ~/.bashrc or source directly

exportTasks() {
    export TASKS_API="$HOME/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py"
}

# Quick aliases
alias gtasks-lists='python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py lists'
alias gtasks='python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py tasks MDk3MjUwMTQyNDE4ODkxMjk1ODM6MDow'
alias gtasks-add='python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py add'
alias gtasks-done='python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py complete'
alias gtasks-del='python3 ~/.hermes/skills/productivity/google-workspace/scripts/tasks_api.py delete'