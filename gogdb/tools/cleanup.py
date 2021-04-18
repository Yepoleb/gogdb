import shutil

import flask

from gogdb.core.storage import Storage

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

def fix_changelog_1(db, prod_id):
    changelog = db.changelog.load(prod_id)
    if changelog is None:
        continue
    changelog = [c for c in changelog if valid_changelog_entry(c)]
    db.changelog.save(changelog, prod_id)

def fix_product_empty(db, prod_id):
    product = db.product.load(prod_id)
    if product.title is None or product.type is None:
        print(prod_id, "is empty")
        product_path = db.path_product(prod_id)
        product_path.rename(product_path.with_name("product_removed.json"))

def main():
    config = flask.Config(".")
    config.from_envvar("GOGDB_CONFIG")
    db = Storage(config["STORAGE_PATH"])
    ids = db.ids.load()
    for prod_id in ids:
        print("Processing", prod_id)
        fix_product_empty(db, prod_id)


main()
