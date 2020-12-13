#/bin/sh

export FLASK_APP=gogdb.application
export FLASK_ENV=development
export PYTHONPATH="."
export GOGDB_CONFIG=~/Coden/py/gogdb2/config-development.py

case $1 in
flask)
    flask run
    ;;
gen_index)
    python3 gogdb/scripts/gen_index.py
    ;;
update_db)
    python3 gogdb/scripts/update_db.py
    ;;
*)
    echo "Missing script name [flask, gen_index, update_db]"
    ;;
esac
