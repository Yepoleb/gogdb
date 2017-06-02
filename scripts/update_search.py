import string
import sys
import logging

import sqlalchemy

import gog_shared
from gogdb_site import models

ALLOWED_CHARS = set(string.ascii_lowercase + string.digits)



logger = logging.getLogger("UpdateSearch")
logging.basicConfig(level=logging.INFO)

def normalize_title(title):
        return "".join(filter(lambda c: c in ALLOWED_CHARS, title.lower()))

def build_searchindex(engine):
    conn = engine.connect()

    logger.info("Loading product titles")
    s = sqlalchemy.sql.select([models.Product.id, models.Product.title])
    res = conn.execute(s)

    logger.info("Generating search values")
    data = []
    for product_id, title in res:
        title_norm = normalize_title(title)
        logger.debug("%s %s %s", product_id, title, title_norm)
        data.append({"prod_id": product_id, "title_norm": title_norm})

    logger.info("Inserting data")
    conn.execute(models.SearchIndex.__table__.delete())
    conn.execute(models.SearchIndex.__table__.insert(), data)



if len(sys.argv) != 2:
    print("Usage: {} <config.ini>".format(sys.argv[0]))
    exit(1)

config = gog_shared.load_config(sys.argv[1])
engine = sqlalchemy.create_engine(config["sqlalchemy"]["url"], echo=False)
build_searchindex(engine)

logger.info("Done")
