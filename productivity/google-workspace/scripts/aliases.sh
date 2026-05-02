# Aliases for Google Workspace services
# Source: source ~/.hermes/skills/productivity/google-workspace/scripts/aliases.sh

SCRIPT_DIR="$HOME/.hermes/skills/productivity/google-workspace/scripts"

# Gmail (full google_api.py)
alias gapi="python3 $SCRIPT_DIR/google_api.py"

# Tasks shortcuts
alias gtasks-lists='python3 $SCRIPT_DIR/tasks_api.py lists'
alias gtasks='python3 $SCRIPT_DIR/tasks_api.py tasks MDk3MjUwMTQyNDE4ODkxMjk1ODM6MDow'
alias gtasks-add='python3 $SCRIPT_DIR/tasks_api.py add'
alias gtasks-done='python3 $SCRIPT_DIR/tasks_api.py complete'
alias gtasks-del='python3 $SCRIPT_DIR/tasks_api.py delete'

# Calendar shortcuts (using gapi)
alias gcal='python3 $SCRIPT_DIR/google_api.py calendar'
alias gcal-list='python3 $SCRIPT_DIR/google_api.py calendar list'
alias gcal-create='python3 $SCRIPT_DIR/google_api.py calendar create'

# Setup check
alias gcheck='cd $SCRIPT_DIR && python3 setup.py --check'