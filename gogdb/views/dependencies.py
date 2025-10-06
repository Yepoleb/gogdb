import datetime

import quart

from gogdb.application.datasources import get_storagedb


async def dependencies():
    storagedb = get_storagedb()
    dependencies = await storagedb.user.load("dependencies.json")

    return await quart.render_template("dependencies.html", dependencies=dependencies)
