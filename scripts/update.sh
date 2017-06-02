SCRIPT_DIR=.
PYTHON_BIN="${SCRIPT_DIR}/../env/bin/python3"
CONFIG_FILE="${SCRIPT_DIR}/config.ini"

$PYTHON_BIN "${SCRIPT_DIR}/refresh_cache.py" "$CONFIG_FILE"
$PYTHON_BIN "${SCRIPT_DIR}/update_games.py" "$CONFIG_FILE"
$PYTHON_BIN "${SCRIPT_DIR}/update_search.py" "$CONFIG_FILE"
