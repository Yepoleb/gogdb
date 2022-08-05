import re
import os.path

import quart


cache_token_re = re.compile(r"_[0-9a-f]{8}")

async def static(filename):
    static_folder = os.path.join(quart.current_app.root_path, "static")
    filename_notoken = cache_token_re.sub("", filename)
    return await quart.send_from_directory(static_folder, filename_notoken)
