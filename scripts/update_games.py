import json
import re
import datetime
import string
import sys
import os.path
import logging
from decimal import Decimal

import sqlalchemy
from sqlalchemy import orm
import arrow

import gog_shared
from gogdb_site import models

IMAGE_RE = re.compile(r".+gog.com/([0-9a-f]+).*")
GOGDATA_RE = re.compile(r"var gogData = (\{.*\})")

CACHEDIR = "cache"



logger = logging.getLogger("UpdateGames")
logging.basicConfig(level=logging.INFO)

def parse_image_url(url):
    if not url:
        return None
    return IMAGE_RE.match(url).group(1)

def parse_release_date(release_date):
    if release_date:
        return arrow.get(release_date).date()
    else:
        return None

def parse_required(required_prods):
    if required_prods:
        return required_prods[0]["id"]
    else:
        return None

def parse_age(rating):
    if rating["age"]["age"] is False:
        return None
    else:
        return rating["age"]["age"]

def parse_company(company_info, companies):
    slug = company_info["slug"]
    if slug not in companies:
        companies[slug] = models.Company(
            slug=slug, name=company_info["name"])
    return companies[slug]

def none_if_false(x):
    if x:
        return x
    else:
        return None

def make_slug(name):
    return "".join(filter(lambda c: c in string.ascii_lowercase, name.lower()))



if len(sys.argv) != 2:
    print("Usage: {} <config.ini>".format(sys.argv[0]))
    exit(1)

config = gog_shared.load_config(sys.argv[1])
engine = sqlalchemy.create_engine(config["sqlalchemy.url"], echo=False)
cachedir = config["scripts.cache"]

Session = orm.sessionmaker(bind=engine)
session = Session()

logger.info("Loading pages")
game_tuples, total_pages = gog_shared.load_pages(config)

games = {}
companies = {}
dependencies = {}
names = {"features": {}, "genres": {}, "languages": {}}

logger.info("Loading stored products")
q = session.query(models.Product).options(
    orm.subqueryload("languages"),
    orm.subqueryload("features"),
    orm.subqueryload("genres"),
    orm.subqueryload("downloads").subqueryload("files"),
    orm.subqueryload("pricehistory"))
for product in q:
    games[product.id] = product

for company in session.query(models.Company):
    companies[company.slug] = company

logger.info("Parsing products")
for _, prod_id in game_tuples:
    logger.debug("Product: %s", prod_id)

    filepath = os.path.join(cachedir, "api/{}.json").format(prod_id)
    try:
        with open(filepath) as apifile:
            apidata = json.load(apifile)
    except Exception:
        logger.warning("Failed to load api data for %s", prod_id)
        continue

    filepath = os.path.join(cachedir, "game/{}").format(apidata["slug"])
    try:
        with open(filepath) as gamefile:
            gamesite = gamefile.read()
            gogdata_str = GOGDATA_RE.search(gamesite).group(1)
            gogdata = json.loads(gogdata_str)
    except Exception:
        logger.warning("Failed to load gogdata for %s", prod_id)
        continue

    productdata = gogdata["gameProductData"]

    dependencies[prod_id] = parse_required(productdata["requiredProducts"])

    # Basic properties

    game = games.get(prod_id, models.Product())
    game.id = apidata["id"]

    game.product_type = apidata["game_type"]
    game.is_secret = apidata["is_secret"]
    game.is_price_visible = productdata["isPriceVisible"]
    game.can_be_reviewed = productdata["canBeReviewed"]

    game.cs_windows = apidata["content_system_compatibility"]["windows"]
    game.cs_mac = apidata["content_system_compatibility"]["osx"]
    game.cs_linux = apidata["content_system_compatibility"]["linux"]

    game.os_windows = productdata["worksOn"]["Windows"]
    game.os_mac = productdata["worksOn"]["Mac"]
    game.os_linux = productdata["worksOn"]["Linux"]

    game.is_coming_soon = productdata["isComingSoon"]
    game.is_pre_order = apidata["is_pre_order"]
    game.release_date = parse_release_date(apidata["release_date"])
    game.development_active = apidata["in_development"]["active"]

    game.age_esrb = parse_age(productdata["brandRatings"]["esrb"])
    game.age_pegi = parse_age(productdata["brandRatings"]["pegi"])
    game.age_usk = parse_age(productdata["brandRatings"]["usk"])

    game.rating = productdata["rating"]
    game.votes_count = productdata["votesCount"]
    game.reviews_count = int(productdata["reviews"]["totalResults"])

    game.title = apidata["title"]
    game.slug = apidata["slug"]
    game.forum_id = apidata["links"]["forum"].rsplit('/', 1)[1]

    game.developer = parse_company(productdata["developer"], companies)
    game.publisher = parse_company(productdata["publisher"], companies)

    game.image_background = parse_image_url(apidata["images"]["background"])
    game.image_logo = parse_image_url(apidata["images"]["logo"])
    game.image_icon = parse_image_url(apidata["images"].get("icon"))

    game.description_full = none_if_false(apidata["description"]["full"])
    game.description_cool = none_if_false(apidata["description"]["whats_cool_about_it"])

    # Downloads

    downloads = {}
    for download in game.downloads:
        downloads[download.slug] = download
    for dlcategory, dlitems in apidata["downloads"].items():
        for dldata in dlitems:
            dlslug = str(dldata["id"])
            if dlslug not in downloads:
                download = models.Download()
                game.downloads.append(download)
            else:
                download = downloads[dlslug]

            download.slug = dlslug
            download.name = dldata["name"]
            download.type = dlcategory
            download.bonus_type = dldata.get("type")
            download.count = dldata.get("count")
            download.os = dldata.get("os")
            download.language = dldata.get("language")
            download.version = none_if_false(dldata.get("version"))

            files = {}
            public_slugs = []
            for dlfile in download.files:
                files[dlfile.slug] = dlfile
            for filedata in dldata["files"]:
                fileslug = str(filedata["id"])
                if fileslug not in files:
                    dlfile = models.DlFile()
                    download.files.append(dlfile)
                else:
                    dlfile = files[fileslug]

                dlfile.slug = fileslug
                dlfile.size = filedata["size"]
                public_slugs.append(fileslug)

            # Clear out old files
            to_remove = []
            for dlfile in download.files:
                if dlfile.slug not in public_slugs:
                    logger.info("Old file: %s - %s", game.title, dlfile.slug)
                    to_remove.append(dlfile)

            for dlfile in to_remove:
                download.files.remove(dlfile)

    # Features

    game.features = []
    added_features = set()
    for feature in productdata["features"]:
        if not feature["title"]:
            continue
        elif not feature["slug"]:
            feature["slug"] = make_slug(feature["title"])
        if feature["slug"] in added_features: # Ignore duplicates
            continue
        else:
            added_features.add(feature["slug"])
        game.features.append(models.Feature(slug=feature["slug"]))
        names["features"][feature["slug"]] = feature["title"]

    # Genres

    game.genres = []
    added_genres = set()
    for genre in productdata["genres"]:
        if not genre["name"]:
            continue
        if not genre["slug"]:
            genre["slug"] = make_slug(genre["name"])
        if genre["slug"] in added_genres: # Ignore duplicates
            continue
        else:
            added_genres.add(genre["slug"])
        game.genres.append(models.Genre(slug=genre["slug"]))
        names["genres"][genre["slug"]] = genre["name"]

    # Languages

    game.languages = []
    added_languages = set()
    for lang, name in apidata["languages"].items():
        if lang in added_languages:
            continue
        else:
            added_languages.add(lang)
        game.languages.append(models.Language(isocode=lang))
        names["languages"][lang] = name

    # Price entry

    if game.pricehistory:
        last_record = game.pricehistory[-1]
    else:
        last_record = models.PriceRecord()
    current_record = models.PriceRecord(
        prod_id = productdata["id"],
        price_base = Decimal(productdata["price"]["baseAmount"]),
        price_final = Decimal(productdata["price"]["finalAmount"]),
        date = datetime.datetime.utcnow()
    )
    if ((current_record.price_final != last_record.price_final) or
            (current_record.price_base != last_record.price_base)):
        game.pricehistory.append(current_record)

    games[game.id] = game


for prod, dep in dependencies.items():
    if dep is not None:
        try:
            games[prod].base_product = games[dep]
        except KeyError:
            logger.warning("Missing dependency: %s for %s", dep, prod)

logger.info("Inserting data")
session.add_all(games.values())
session.commit()

with open(os.path.join(cachedir, "names.json"), "w") as namefile:
    json.dump(names, namefile, indent=2, sort_keys=True)

logger.info("Done")
