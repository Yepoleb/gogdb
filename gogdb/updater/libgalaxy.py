import asyncio
import logging
import os

DLLNAMES = ("Galaxy.dll", "Galaxy64.dll")

logger = logging.getLogger("UpdateDB.filelist")

class LibGalaxyProcessor:
    wants = {"product"}

    def __init__(self, db):
        self.db = db
        self.gamelist = []

    async def prepare(self):
         pass

    async def process(self, data):
        prod = data.product
        if prod is None:
            return
        is_multiplayer = "multi" not in [feature.id for feature in prod.features]
        win_builds = [
            build for build in prod.builds
            if build.os == "windows" and build.generation == 2
        ]
        win_builds.sort(key=lambda build: build.date_published)
        if win_builds and is_multiplayer:
            latest_build = win_builds[-1]
            repo = await self.db.repository.load(prod.id, latest_build.id)
            if repo is None:
                return
            for depot in repo.get("depots", []):
                manifest = await self.db.manifest_v2.load(depot["manifest"])
                for item in manifest["depot"]["items"]:
                    if item["type"] == "DepotFile":
                        if any(item["path"].endswith(name) for name in DLLNAMES):
                            if len(item["chunks"]) == 1:
                                md5 = item["chunks"][0]["md5"]
                            else:
                                md5 = item["md5"]
                            self.gamelist.append((prod.id, prod.title, md5))
                            return

    async def finish(self):
        await self.db.user.save(self.gamelist, "galaxy_games.json")
