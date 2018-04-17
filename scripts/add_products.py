#!/usr/bin/env python3
import json
import datetime
import sys

import gogdb
from gogdb import db, model
import changelog


if len(sys.argv) < 2:
    print("Usage: {} <games.json>".format(sys.argv[0]))

json_path = sys.argv[1]
with open(json_path) as json_f:
    owned_ids = set(json.load(json_f)["owned"])

registered_ids_q = db.session.query(model.Product.id) \
    .filter(model.Product.id.in_(owned_ids))
registered_ids = set(row[0] for row in registered_ids_q)
new_ids = owned_ids - registered_ids
print("New IDs:", new_ids)

for new_id in new_ids:
    prod = model.Product(id=new_id)
    changelog.prod_add(prod, prod.changes, datetime.datetime.utcnow())
    db.session.add(prod)

db.session.commit()
