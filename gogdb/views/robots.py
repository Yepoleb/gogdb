import os

import quart


async def robots():
    static_path = os.path.join(quart.current_app.root_path, "static")
    return await quart.send_from_directory(
        static_path, "robots.txt", mimetype="text/plain")
