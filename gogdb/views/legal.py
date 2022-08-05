import quart


async def legal():
    return await quart.render_template("legal.html")
