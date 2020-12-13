#!/bin/bash

SIZES="16 32 48 64 128 180 256"
FILENAMES="gogdb"

for size in $SIZES; do
    output_path="gogdb/static/img/sizes/gogdb_${size}x${size}.png"
    input_path="gogdb/static/img/gogdb.svg"
    if [[ ! -f $output_path ]]; then
        inkscape --export-png "$output_path" -w $size -h $size "$input_path"
    fi
done

FAVICON_SRC="gogdb/static/img/sizes/gogdb_16x16.png"
FAVICON_DST="gogdb/static/img/favicon.ico"

if [[ ! -f $FAVICON_DST ]]; then
    convert "$FAVICON_SRC" "$FAVICON_DST"
fi

optipng gogdb/static/img/sizes/*

