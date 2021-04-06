#!/bin/bash

LOG_PATH="/var/log/gogdb/gogdb.log"

date >> "$LOG_PATH"
python3 /usr/local/share/gogdb/gogdb/updater/updater.py all >> "$LOG_PATH" 2>&1
ret_val = $?
echo >> "$LOG_PATH"
if [ $ret_val -ne 0 ]; then
    mail -s "GOG DB Updater failed" "$REPORT_EMAIL" <<< "Failed at `date`"
fi
exit $ret_val
