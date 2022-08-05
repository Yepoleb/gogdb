#/bin/sh

export QUART_APP=gogdb.application
export QUART_ENV=development
export PYTHONPATH="."
GOGDB_CONFIG=`realpath "${GOGDB_CONFIG:-config-development.py}"`
export GOGDB_CONFIG

script_name="$1"
shift

case "$script_name" in
web)
    quart run "$@"
    ;;
updater)
    python3 gogdb/updater/updater.py "$@"
    ;;
token)
    python3 gogdb/updater/gogtoken.py "$@"
    ;;
exporter)
    python3 gogdb/legacy/exporter.py "$@"
    ;;
cleanup)
    python3 gogdb/tools/cleanup.py "$@"
    ;;
*)
    echo "Missing script name [web, updater, token, exporter, cleanup]"
    ;;
esac
