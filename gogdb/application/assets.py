import os.path
import hashlib

import quart


hash_cache = {}

def asset_url(filepath):
    """
    Insert 8 characters of the SHA256 hash into the file path before the extension.
    Hashes are cached until application reload.
    """
    app = quart.current_app
    file_hash = hash_cache.get(filepath)
    if file_hash is None:
        filepath_abs = os.path.join(app.root_path, "static", filepath)
        hasher = hashlib.sha256()
        hasher.update(open(filepath_abs, "rb").read())
        file_hash = hasher.hexdigest()
        hash_cache[filepath] = file_hash
    path_split_ext = filepath.rsplit(".", 1)
    if len(path_split_ext) == 2:
        path_base, path_ext = path_split_ext
        hashed_path = f"{path_base}_{file_hash[:8]}.{path_ext}"
    else:
        hashed_path = f"{filepath}_{file_hash[:8]}"
    return f"/static/{hashed_path}"
