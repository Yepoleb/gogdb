#/bin/sh

export FLASK_APP=gogdb.application
export FLASK_ENV=development
export PYTHONPATH="."
GOGDB_CONFIG=`realpath "${GOGDB_CONFIG:-config-development.py}"`
export GOGDB_CONFIG

script_name="$1"
shift

case "$script_name" in
flask)
    flask run "$@"
    ;;
assets)
    flask assets build "$@"
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
    echo "Missing script name [flask, assets, updater, token, exporter]"
    ;;
esac
