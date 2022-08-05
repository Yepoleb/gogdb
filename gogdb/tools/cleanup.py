import shutil
import datetime
import asyncio

import quart

from gogdb.core.storage import Storage
import gogdb.core.dataclsloader

"""
Removes invalid database entries
"""



def valid_changelog_entry(entry):
    if entry.category == "property" and entry.property_record.property_name == "changelog":
        return False
    elif entry.category == "property" and entry.property_record.property_name == "access":
        return False
    elif entry.action == "change" and entry.category == "download":
        if entry.download_record.dl_type != "bonus":
            if entry.download_record.dl_old_software.is_same(entry.download_record.dl_new_software):
                return False

    return True

async def fix_changelog_1(db, prod_id):
    changelog = await db.changelog.load(prod_id)
    if changelog is None:
        return
    changelog = [c for c in changelog if valid_changelog_entry(c)]
    await db.changelog.save(changelog, prod_id)

async def fix_product_empty(db, prod_id):
    product = await db.product.load(prod_id)
    if product is None:
        return
    if product.title is None or product.type is None:
        print(prod_id, "is empty")
        product_path = db.path_product(prod_id)
        product_path.rename(product_path.with_name("product_removed.json"))

async def fix_price_jitter(price_log, prod_id):
    if price_log is None:
        return
    currency_log = price_log["US"]["USD"]
    i = 0
    while i < len(currency_log):
        if i >= 1:
            is_gap = (
                currency_log[i].price_base is not None
                and currency_log[i-1].price_base is None
                and (currency_log[i].date - currency_log[i-1].date) < datetime.timedelta(hours=48)
            )
            if is_gap:
                print("Deleting gap for", prod_id)
                #print(currency_log)
                del currency_log[i-1]
                i -= 1
            if currency_log[i].same_price(currency_log[i-1]):
                print("Duplicate entry for", prod_id, "at", i)
                del currency_log[i]
                i -= 1
        i += 1
    if len(currency_log) == 1 and currency_log[0].price_base is None:
        print("None log", prod_id)
    while currency_log and currency_log[0].price_base is None:
        print("Deleting none start", prod_id)
        del currency_log[0]

async def remove_extra_fields(db, prod_id):
    print("Processing", prod_id)
    gogdb.core.dataclsloader.ignore_extra_fields = True
    product = await db.product.load(prod_id)
    if product is None:
        return
    await db.product.save(product, prod_id)

async def price_placeholders(price_log, prod_id):
    if price_log is None:
        return
    currency_log = price_log["US"]["USD"]
    if currency_log:
        num_9999 = len([c for c in currency_log if c.price_base == 9999])
        if 0 < num_9999 < 5:
            i = 0
            while i < len(currency_log):
                if currency_log[i].price_base == 9999:
                    del currency_log[i]
                    print("9999", prod_id, num_9999)
                    i -= 1
                i += 1

async def cleanup_worker(db, ids, worker_num):
    while ids:
        prod_id = ids.pop()
        price_log = await db.prices.load(prod_id)
        #await price_placeholders(price_log, prod_id)
        #await fix_price_jitter(price_log, prod_id)
        #await db.prices.save(price_log, prod_id)
        await remove_extra_fields(db, prod_id)


async def main():
    config = quart.Config(".")
    config.from_envvar("GOGDB_CONFIG")
    db = Storage(config["STORAGE_PATH"])
    ids = await db.ids.load()
    worker_tasks = [
        asyncio.create_task(cleanup_worker(db, ids, worker_num))
        for worker_num in range(8)
    ]
    await asyncio.gather(*worker_tasks, return_exceptions=False)

asyncio.run(main())
