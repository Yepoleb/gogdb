#/bin/sh

export FLASK_APP=gogdb.application
export FLASK_ENV=development
export PYTHONPATH="."
export GOGDB_CONFIG=~/Coden/py/gogdb2/config-development.py

script_name="$1"
shift

case "$script_name" in
flask)
    flask run
    ;;
updater)
    python3 gogdb/updater/updater.py "$@"
    ;;
*)
    echo "Missing script name [flask, updater]"
    ;;
esac
