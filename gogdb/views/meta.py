import aiohttp
import zlib
import json

import quart


async def meta(meta_id):
    url = "https://cdn.gog.com/content-system/v2/meta/{}/{}/{}".format(
        meta_id[0:2], meta_id[2:4], meta_id)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            json_text = zlib.decompress(await resp.read(), 15).decode("utf-8")
    return quart.jsonify(json.loads(json_text))
