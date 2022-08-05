import quart

from gogdb.application.datasources import get_storagedb
import gogdb.core.buildloader as buildloader


async def build(prod_id, build_id):
    storagedb = get_storagedb()
    product = await storagedb.product.load(prod_id)
    if product is None:
        quart.abort(404)
    repository_raw = await storagedb.repository.load(prod_id, build_id)
    if repository_raw is None:
        quart.abort(404)

    build_data = [b for b in product.builds if b.id == build_id][0]

    if build_data.generation == 1:
        repository = buildloader.load_repository_v1(repository_raw)
        return await quart.render_template(
            "build_v1.html", product=product, build=build_data, repo=repository)
    else:
        repository = buildloader.load_repository_v2(repository_raw)
        return await quart.render_template(
            "build_v2.html", product=product, build=build_data, repo=repository)
