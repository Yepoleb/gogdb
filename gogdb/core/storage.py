import dataclasses
import json
import datetime
import gzip
import os
import pathlib
import itertools
import string

import gogdb.core.model as model
from gogdb.core.dataclsloader import class_from_json


def json_encoder(x):
    if dataclasses.is_dataclass(x):
        return dataclasses.asdict(x)
    elif isinstance(x, datetime.date) or isinstance(x, datetime.datetime):
        assert x.tzinfo is not None
        return x.isoformat()
    else:
        raise TypeError(type(x), repr(x))

def json_dump(obj, f):
    json.dump(obj, f, indent=2, sort_keys=True, ensure_ascii=False, default=json_encoder)

LEGAL_PARAMETER_CHARS = set(string.ascii_letters + string.digits + "-_.")
def params_legal(args, kwargs):
    for param_str in itertools.chain(args, kwargs.values()):
        if isinstance(param_str, int):
            continue
        for c in param_str:
            if c not in LEGAL_PARAMETER_CHARS:
                return False
    return True


class StorageItem:
    def __init__(self, path_function, make_function=None, compressed=False):
        self.path_function = path_function
        self.make_function = make_function
        self.compressed = compressed

    def load(self, *args, **kwargs):
        # Prevent directory traversal and other funny stuff
        if not params_legal(args, kwargs):
            return None
        path = self.path_function(*args, **kwargs)
        try:
            if self.compressed:
                fobj = gzip.open(path, "rt")
            else:
                fobj = open(path, "r")
        except FileNotFoundError:
            return None
        json_data = json.load(fobj)
        fobj.close()
        if self.make_function:
            return self.make_function(json_data)
        else:
            return json_data

    def save(self, instance, *args, **kwargs):
        if not params_legal(args, kwargs):
            return None
        path = self.path_function(*args, **kwargs)
        temp_path = str(path) + ".part"
        try:
            if self.compressed:
                fobj = gzip.open(temp_path, "wt")
            else:
                fobj = open(temp_path, "w")
        except FileNotFoundError:
            path.parent.mkdir(parents=True)
            # Don't want to bother with some fancy recursion, so copy & paste it is
            if self.compressed:
                fobj = gzip.open(temp_path, "wt")
            else:
                fobj = open(temp_path, "w")
        json_dump(instance, fobj)
        fobj.close()
        os.replace(src=temp_path, dst=path)

    def has(self, *args, **kwargs):
        if not params_legal(args, kwargs):
            return None
        path = self.path_function(*args, **kwargs)
        return path.exists()


class Storage:
    def __init__(self, storage_path):
        self.storage_path = pathlib.Path(storage_path)

        self.ids = StorageItem(self.path_ids)
        self.token = StorageItem(self.path_token)
        self.product = StorageItem(self.path_product, self.make_product)
        self.repository = StorageItem(self.path_repository)
        self.prices = StorageItem(self.path_prices, self.make_prices)
        self.prices_old = StorageItem(self.path_prices_old, self.make_prices)
        self.changelog = StorageItem(self.path_changelog, self.make_changelog)
        self.manifest_v1 = StorageItem(self.path_manifest_v1, compressed=True)
        self.manifest_v2 = StorageItem(self.path_manifest_v2, compressed=True)

    def __repr__(self):
        return f"Storage({repr(self.storage_path)})"

    def path_ids(self):
        return self.storage_path / "ids.json"

    def path_token(self):
        return self.storage_path / "secret/token.json"

    def path_product(self, product_id):
        return self.storage_path / f"products/{product_id}/product.json"

    @staticmethod
    def make_product(json_data):
        return class_from_json(model.Product, json_data)

    def path_repository(self, product_id, build_id):
        return self.storage_path / f"products/{product_id}/builds/{build_id}.json"

    def path_prices(self, product_id):
        return self.storage_path / f"products/{product_id}/prices.json"

    def path_prices_old(self, product_id):
        return self.storage_path / f"products/{product_id}/prices_pre2019.json"

    @staticmethod
    def make_prices(json_data):
        result = {}
        for country, country_data in json_data.items():
            result[country] = {}
            for currency, currency_records in country_data.items():
                record_objects = [
                    class_from_json(model.PriceRecord, record_data)
                    for record_data in currency_records
                ]
                result[country][currency] = record_objects
        return result

    def path_changelog(self, product_id):
        return self.storage_path / f"products/{product_id}/changes.json"

    @staticmethod
    def make_changelog(json_data):
        return [class_from_json(model.ChangeRecord, entry) for entry in json_data]

    def path_manifest_v1(self, manifest_id):
        return self.storage_path / f"manifests_v1/{manifest_id[0:2]}/{manifest_id[2:4]}/{manifest_id}.json.gz"

    def path_manifest_v2(self, manifest_id):
        return self.storage_path / f"manifests_v2/{manifest_id[0:2]}/{manifest_id[2:4]}/{manifest_id}.json.gz"

    def path_indexdb(self):
        return self.storage_path / "index.sqlite3"
