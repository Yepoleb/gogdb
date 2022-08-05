import quart

from gogdb.application.datasources import get_storagedb


async def index():
    startpage_data = await get_storagedb().startpage.load()
    return await quart.render_template("index.html", startpage=startpage_data)
