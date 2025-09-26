#!/bin/sh

STORAGE_PATH="/var/lib/gogdb/storage"
BACKUP_PATH="/var/lib/gogdb/backups"

set -e

month=`date '+%Y-%m'`
today=`date '+%Y-%m-%d'`

products_path="$BACKUP_PATH/products"

mkdir -p "$products_path/$month"
cd "$STORAGE_PATH"
echo "Compressing products"
tar --create --xz --file "$products_path/$month/gogdb_$today.tar.xz" "products" "ids.json"
cd "$products_path"
find . -name 'gogdb_*' -printf '%P\n' | sort > "$products_path/filelist.txt"

mkdir -p "$BACKUP_PATH/manifests"
cd "$STORAGE_PATH"
echo "Compressing manifests"
tar --create --file "$BACKUP_PATH/manifests/manifests_current.tar" "manifests_v1" "manifests_v2"

