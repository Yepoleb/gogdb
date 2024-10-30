import collections

class BackrefProcessor:
    wants = {"product"}

    def __init__(self, db):
        self.db = db
        self.manifest_map = {}

    async def prepare(self):
        pass

    async def process(self, data):
        prod = data.product
        if prod is None:
            return
        win_builds = [
            build for build in prod.builds
            if build.os == "windows" and build.generation == 2
        ]
        for build in win_builds:
            repo = await self.db.repository.load(prod.id, build.id)
            if repo is None:
                return
            for depot in repo.get("depots", []):
                self.manifest_map[depot["manifest"]] = {"title": prod.title, "prod_id": prod.id, "build_id": build.id}

    async def finish(self):
        await self.db.user.save(self.manifest_map, "manifest_backref.json")
