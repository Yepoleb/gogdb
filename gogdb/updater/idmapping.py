import logging

logger = logging.getLogger("UpdateDB.idmapping")

class IdMappingProcessor:
    wants = {"product"}

    def __init__(self, db):
        self.db = db
        self.store_to_id = {}
        self.id_to_store = {}

    async def prepare(self):
        pass

    async def process(self, data):
        product = data.product
        if product is None:
            return
        if product.store_state:
            if product.link_store.split("/")[-1] != product.slug:
                logger.error(f"Mismatched slug and store link: {product.slug} {product.link_store}")
            self.store_to_id[product.slug] = product.id
            self.id_to_store[product.id] = product.slug

    async def finish(self):
        await self.db.user.save(self.store_to_id, "store_to_id.json")
        await self.db.user.save(self.id_to_store, "id_to_store.json")
