import json
import re
import datetime
import string
import os.path
import logging
import queue
import threading
import sys
import configparser

import requests
import sqlalchemy
from sqlalchemy import orm
from gogapi import GogApi

from gogdb_site import models



CONFIG_SECTION = "app:main"
IMAGE_RE = re.compile(r".+gog.com/([0-9a-f]+).*")
GALAXY_EXPANDED = ["downloads", "description"]
ALLOWED_CHARS = set(string.ascii_lowercase + string.digits)
DL_WORKER_COUNT = 8
LOCALE = ("US", "USD", "en-US")


# Parsing functions

def parse_image_url(url):
    if not url:
        return None
    return IMAGE_RE.match(url).group(1)

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

def normalize_title(title):
    return "".join(c for c in title.lower() if c in ALLOWED_CHARS)



# API download worker

def download_worker(dl_queue, db_queue):
    while True:
        try:
            product = dl_queue.get(block=False)
        except queue.Empty:
            break

        try:
            product.update_galaxy(expand=GALAXY_EXPANDED)
        except requests.HTTPError as e:
            logger.warning("Failed to load api data for %s: %s", product.id, e)

        try:
            product.update_web()
        except requests.HTTPError as e:
            logger.warning("Failed to load gogdata for %s: %s", product.id, e)

        db_queue.put(product)
        dl_queue.task_done()


# Initialize logging
logging.basicConfig()
logger = logging.getLogger("UpdateGames")
logger.setLevel(logging.DEBUG)

# Load config
config = configparser.ConfigParser()
with open(sys.argv[1], "r") as configfile:
    config.read_file(configfile)
mainconfig = config[CONFIG_SECTION]
engine = sqlalchemy.create_engine(mainconfig["sqlalchemy.url"])
cachedir = mainconfig["scripts.cache"]

# Create ORM session
Session = orm.sessionmaker(bind=engine)
session = Session()

# Initialize API

api = GogApi()
api.set_locale(*LOCALE)

# Load products and add them to the queue
logger.info("Loading catalog")
search_res = api.search(mediaType="game", sort="bestselling", limit=10000)
products_count = search_res.count
# Queue for passing search to download workers
dl_queue = queue.Queue()
# Queue for passing downloaded products back to main thread
db_queue = queue.Queue()

for prod in search_res.products: dl_queue.put(prod)
del search_res
logger.info("Found %s products", products_count)


# Start download threads
logger.info("Starting %d download workers", DL_WORKER_COUNT)
dl_threads = []
for i in range(DL_WORKER_COUNT):
    t = threading.Thread(target=download_worker, args=(dl_queue, db_queue))
    t.start()
    dl_threads.append(t)

dependencies = {}
names = {"features": {}, "genres": {}, "languages": {}}
companies = {}

for company in session.query(models.Company):
    companies[company.slug] = company

for counter in range(products_count):
    api_prod = db_queue.get()

    # Check if product actually got loaded
    if not ("galaxy" in api_prod.loaded and "web" in api_prod.loaded):
        continue

    logger.debug(
        "Product: %d (%d/%d)", api_prod.id, counter + 1, products_count)

    # Get the old data from the database

    prod = session.query(models.Product).filter(
        models.Product.id == api_prod.id).one_or_none()
    if prod is None:
        prod = models.Product()

    # Basic properties

    prod.id = api_prod.id

    prod.product_type = api_prod.type
    prod.is_secret = api_prod.is_secret
    prod.is_price_visible = api_prod.is_price_visible
    prod.can_be_reviewed = api_prod.reviewable

    prod.cs_windows = "windows" in api_prod.content_systems
    prod.cs_mac = "mac" in api_prod.content_systems
    prod.cs_linux = "linux" in api_prod.content_systems

    prod.os_windows = "windows" in api_prod.systems
    prod.os_mac = "mac" in api_prod.systems
    prod.os_linux = "linux" in api_prod.systems

    prod.is_coming_soon = api_prod.is_coming_soon
    prod.is_pre_order = api_prod.is_pre_order
    prod.release_date = api_prod.release_date
    prod.development_active = api_prod.in_development

    prod.age_esrb = parse_age(api_prod.brand_ratings["esrb"])
    prod.age_pegi = parse_age(api_prod.brand_ratings["pegi"])
    prod.age_usk = parse_age(api_prod.brand_ratings["usk"])

    prod.rating = api_prod.rating
    prod.votes_count = api_prod.votes_count
    prod.reviews_count = api_prod.reviews.total_results

    prod.title = api_prod.title
    prod.slug = api_prod.slug
    prod.title_norm = normalize_title(api_prod.title)
    prod.forum_id = api_prod.link_forum.rsplit('/', 1)[1]

    prod.developer = parse_company(api_prod.developer, companies)
    prod.publisher = parse_company(api_prod.publisher, companies)

    prod.image_background = parse_image_url(api_prod.image_background)
    prod.image_logo = parse_image_url(api_prod.image_logo)
    prod.image_icon = parse_image_url(api_prod.image_icon)

    prod.description_full = api_prod.description
    prod.description_cool = api_prod.cool_about_it

    # Downloads

    downloads = {}
    for download in prod.downloads:
        downloads[download.slug] = download
    for api_download in api_prod.downloads:
        if api_download.id not in downloads:
            download = models.Download()
            prod.downloads.append(download)
        else:
            download = downloads[api_download.id]

        download.slug = api_download.id
        download.name = api_download.name
        download.type = api_download.category
        download.bonus_type = api_download.bonus_type
        download.count = api_download.count
        download.os = api_download.os
        download.language = api_download.language
        download.version = api_download.version

        files = {}
        public_slugs = []
        for dlfile in download.files:
            files[dlfile.slug] = dlfile
        for api_file in api_download.files:
            if api_file.id not in files:
                dlfile = models.DlFile()
                download.files.append(dlfile)
            else:
                dlfile = files[api_file.id]

            dlfile.slug = api_file.id
            dlfile.size = api_file.size
            public_slugs.append(api_file.id)

        # Clear out old files
        to_remove = []
        for dlfile in download.files:
            if dlfile.slug not in public_slugs:
                logger.info("Old file: %s - %s", api_prod.title, dlfile.slug)
                to_remove.append(dlfile)

        for dlfile in to_remove:
            download.files.remove(dlfile)

    # Features

    prod.features = []
    for feature in api_prod.features:
        prod.features.append(models.Feature(slug=feature.slug))
        names["features"][feature.slug] = feature.name

    # Genres

    prod.genres = []
    for genre in api_prod.genres:
        prod.genres.append(models.Genre(slug=genre.slug))
        names["genres"][genre.slug] = genre.name

    # Languages

    prod.languages = []
    for language in api_prod.languages:
        prod.languages.append(models.Language(isocode=language.isocode))
        names["languages"][language.isocode] = language.name

    # Price entry

    if prod.pricehistory:
        last_record = prod.pricehistory[-1]
    else:
        last_record = models.PriceRecord()

    current_record = models.PriceRecord(
        price_base = api_prod.price.base,
        price_final = api_prod.price.final,
        date = datetime.datetime.utcnow()
    )
    if ((current_record.price_final != last_record.price_final) or
            (current_record.price_base != last_record.price_base)):
        prod.pricehistory.append(current_record)

    # Dependency

    if api_prod.required_product is not None:
        dependencies[api_prod.id] = api_prod.required_product.id

    # Add to session and clean up

    session.add(prod)
    session.flush()
    session.expunge(prod)
    db_queue.task_done()


# Set dependencies

products = {}
for product in session.query(models.Product):
    products[product.id] = product

for prod_id, dep_id in dependencies.items():
    if dep_id not in products:
        logger.warning("Missing dependency: %s for %s", dep_id, prod_id)
        continue

    product = products[prod_id]
    dependency = products[dep_id]
    product.base_product = dependency
    session.add(product)

# Apply changes

logger.info("Commiting data")
session.commit()

# Dump names

with open(os.path.join(cachedir, "names.json"), "w") as namefile:
    json.dump(names, namefile, indent=2, sort_keys=True)

logger.info("Done")
