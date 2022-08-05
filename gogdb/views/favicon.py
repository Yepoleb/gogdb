import os

import quart


async def favicon():
    static_path = os.path.join(quart.current_app.root_path, "static")
    return await quart.send_from_directory(
        static_path, "img/favicon.ico", mimetype="image/vnd.microsoft.icon")
