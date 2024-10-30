import collections

class DependenciesProcessor:
    wants = {"product"}

    def __init__(self, db):
        self.db = db
        self.dependency_map = collections.defaultdict(list)

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
        if win_builds:
            latest_build = win_builds[-1]
            repo = await self.db.repository.load(prod.id, latest_build.id)
            if repo is None:
                return
            for dependency in repo.get("dependencies", []):
                self.dependency_map[dependency].append({"id": prod.id, "title": prod.title})

    async def finish(self):
        for game_list in self.dependency_map.values():
            game_list.sort(key=lambda x: x["id"])
        await self.db.user.save(self.dependency_map, "dependencies.json")
