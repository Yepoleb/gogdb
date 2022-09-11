import datetime

import quart

from gogdb.application.datasources import get_storagedb


async def version_mismatch():
    storagedb = get_storagedb()
    versions_data = await storagedb.versions.load()
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    return await quart.render_template("version_mismatch.html", versions=versions_data, now=now)
