import asyncio
import logging
import os

import aiofiles

logger = logging.getLogger("UpdateDB.filelist")

class FilelistProcessor:
    wants = {"product"}

    def __init__(self, db):
        self.db = db
        self.lock = asyncio.Lock()

    async def prepare(self):
        self.path_txt = self.db.path_user("filelist_win.txt")
        self.path_gz = self.db.path_user("filelist_win.txt.gz")
        self.path_temp = self.db.path_user("filelist_win.txt.gz.part")
        self.filelist = await aiofiles.open(self.path_txt, "w")

    async def write_files(self, game_files):
        product_lines = [
            f"{product_name} {version} {path}\n" for path, version, product_name in game_files
        ]
        await self.lock.acquire()
        await self.filelist.writelines(product_lines)
        self.lock.release()

    async def process(self, data):
        prod = data.product
        if prod is None:
            return
        win_builds = [
            build for build in prod.builds
            if build.os == "windows" and build.generation == 2
        ]
        game_files = []
        for build in win_builds:
            repo = await self.db.repository.load(prod.id, build.id)
            if repo is None:
                return
            for depot in repo.get("depots", []):
                manifest = await self.db.manifest_v2.load(depot["manifest"])
                for item in manifest["depot"]["items"]:
                    if item["type"] == "DepotFile":
                        game_files.append((item["path"], build.version, prod.title))

        await self.write_files(game_files)

    async def finish(self):
        await self.filelist.close()
        logger.info("Compressing filelist.txt")
        self.path_temp.unlink(missing_ok=True)
        compress_process = await asyncio.create_subprocess_exec(
            "/usr/bin/gzip", "--suffix=.gz.part", str(self.path_txt)
        )
        await compress_process.wait()
        os.replace(src=self.path_temp, dst=self.path_gz)
