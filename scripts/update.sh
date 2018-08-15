#!/bin/sh
export GOGDB_CONFIG=/etc/gogdb/config-production.py
#export DEBUG_UPDATEDB=1

date
python3 /var/www/gogdb/scripts/update_db.py
echo
