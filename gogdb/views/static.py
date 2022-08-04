import re
import os.path

import flask


cache_token_re = re.compile(r"_[0-9a-f]{8}")

def static(filename):
    static_folder = os.path.join(flask.current_app.root_path, "static")
    filename_notoken = cache_token_re.sub("", filename)
    return flask.send_from_directory(static_folder, filename_notoken)
