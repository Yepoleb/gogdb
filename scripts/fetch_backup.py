#!/usr/bin/python3

import datetime
import pathlib
import requests
import sys

TO_KEEP = 5
now = datetime.datetime.now()

products_url = now.strftime("https://www.gogdb.org/backups_v3/products/%Y-%m/gogdb_%Y-%m-%d.tar.xz")
manifests_url = "https://www.gogdb.org/backups_v3/manifests/manifests_current.tar"
products_name = now.strftime("products_%Y-%m-%d.tar.xz")
manifests_name = now.strftime("manifests_%Y-%m-%d.tar.xz")
backups_dir = pathlib.Path("/var/backups/gogdb")

def download_file(url, dest):
    print(f"Downloading {url}", file=sys.stderr)
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as dest_f:
        for chunk in resp.iter_content(chunk_size=4096):
            dest_f.write(chunk)

download_file(products_url, backups_dir / products_name)
download_file(manifests_url, backups_dir / manifests_name)

def cleanup_old(path, glob_pattern, to_keep):
    matching_files = sorted(path.glob(glob_pattern))
    to_delete = matching_files[:-to_keep]
    for filepath in to_delete:
        filepath.unlink()

cleanup_old(backups_dir, "products_*.tar.xz", TO_KEEP)
cleanup_old(backups_dir, "manifests_*.tar.xz", TO_KEEP)
