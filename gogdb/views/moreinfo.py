import quart


async def moreinfo():
    return await quart.render_template("moreinfo.html")
