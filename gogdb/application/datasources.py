import quart
import aiosqlite

import gogdb.core.storage as storage



def get_storagedb():
    if "storagedb" not in quart.g:
        storage_path = quart.current_app.config["STORAGE_PATH"]
        quart.g.storagedb = storage.Storage(storage_path)

    return quart.g.storagedb

async def get_indexdb():
    if "indexdb" not in quart.g:
        storagedb = get_storagedb()
        index_path = storagedb.path_indexdb()
        quart.g.indexdb = await aiosqlite.connect(index_path)
        quart.g.indexdb.row_factory = aiosqlite.Row

    return quart.g.indexdb

async def get_indexdb_cursor():
    return await (await get_indexdb()).cursor()
