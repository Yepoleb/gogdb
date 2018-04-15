#!/usr/bin/env python3
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
import gogapi

import gogdb
from gogdb import db, model
import changelog


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
        companies[slug] = model.Company(
            slug=slug, name=company_info["name"])
    return companies[slug]


def normalize_title(title):
    return "".join(c for c in title.lower() if c in ALLOWED_CHARS)



# API download worker

def download_worker(api, dl_queue, db_queue):
    while True:
        try:
            prod_id, slug = dl_queue.get(block=False)
        except queue.Empty:
            break

        product = api.product(prod_id, slug)
        try:
            product.update_galaxy(expand=GALAXY_EXPANDED)
        except (requests.HTTPError, gogapi.GogError) as e:
            logger.warning("Failed to load api data for %s: %s", product.id, e)

        if slug is not None:
            try:
                product.update_web()
            except (requests.HTTPError, gogapi.GogError) as e:
                logger.warning("Failed to load gogdata for %s: %s", product.id, e)

        db_queue.put(product)
        dl_queue.task_done()


# Initialize logging
logging.basicConfig()
logger = logging.getLogger("UpdateDB")
logger.setLevel(logging.INFO)

# Alias session
session = db.session

# Initialize API

api = gogapi.GogApi()
api.set_locale(*LOCALE)

# Debug

#import requests_cache
#requests_cache.install_cache(backend="redis", allowable_codes=(200, 404))
#logger.setLevel(logging.DEBUG)
#logging.getLogger("gogapi").setLevel(logging.DEBUG)

# Load products and add them to the queue
logger.info("Loading catalog")
search_products = list(
    api.search(mediaType="game", sort="bestselling", limit=50).iter_products()
)
# Queue for passing search to download workers
dl_queue = queue.Queue()
# Queue for passing downloaded products back to main thread
db_queue = queue.Queue()

slug_map = {row[0]: None for row in session.query(model.Product.id)}
for prod in search_products:
    slug_map[prod.id] = prod.slug
del search_products
for prod_item in slug_map.items():
    dl_queue.put(prod_item)
products_count = len(slug_map)
logger.info("Found %s products", products_count)


# Start download threads
logger.info("Starting %d download workers", DL_WORKER_COUNT)
dl_threads = []
for i in range(DL_WORKER_COUNT):
    t = threading.Thread(
        target=download_worker, args=(api, dl_queue, db_queue))
    t.start()
    dl_threads.append(t)

dependencies = {}
companies = {}

for company in session.query(model.Company):
    companies[company.slug] = company

for counter in range(products_count):
    api_prod = db_queue.get(timeout=60)
    logger.debug(
        "Product: %d (%d/%d)", api_prod.id, counter + 1, products_count)

    # Get current timestamp
    cur_time = datetime.datetime.utcnow()

    # Get the old data from the database
    prod = session.query(model.Product) \
        .filter(model.Product.id == api_prod.id).one_or_none()

    if prod is None:
        if api_prod.has("title"):
            logger.info("New Product: %d %s", api_prod.id, api_prod.title)
        else:
            logger.info("New Product: %d", api_prod.id)
        prod = model.Product(id=api_prod.id)
        changelog.prod_add(prod, prod.changes, cur_time)

    # Set availability
    if "galaxy" not in api_prod.loaded:
        availability = 0
    elif "web" not in api_prod.loaded:
        availability = 1
    else:
        availability = 2

    if prod.availability is not None:
        changelog.prod_avail(
            prod, availability, prod.changes, cur_time)
    prod.availability = availability

    if "galaxy" in api_prod.loaded:

        # Changelog product
        if api_prod.has("systems") and (prod.os_windows is not None):
            changelog.prod_os(
                prod, api_prod.systems, prod.changes, cur_time)
        if prod.title is not None:
            changelog.prod_title(
                prod, api_prod.title_galaxy, prod.changes, cur_time)
        if prod.forum_id is not None:
            changelog.prod_forum(
                prod, api_prod.forum_slug, prod.changes, cur_time)

        # Basic properties

        prod.product_type = api_prod.type
        prod.is_secret = api_prod.is_secret
        if api_prod.has("is_price_visible", "reviewable"):
            prod.is_price_visible = api_prod.is_price_visible
            prod.can_be_reviewed = api_prod.reviewable
        else:
            prod.is_price_visible = False
            prod.can_be_reviewed = False

        prod.cs_windows = "windows" in api_prod.content_systems
        prod.cs_mac = "mac" in api_prod.content_systems
        prod.cs_linux = "linux" in api_prod.content_systems

        if api_prod.has("systems"):
            prod.os_windows = "windows" in api_prod.systems
            prod.os_mac = "mac" in api_prod.systems
            prod.os_linux = "linux" in api_prod.systems

        if api_prod.has("is_coming_soon"):
            prod.is_coming_soon = api_prod.is_coming_soon
        else:
            prod.is_coming_soon = False
        prod.is_pre_order = api_prod.is_pre_order
        if api_prod.has("release_date"):
            prod.release_date = api_prod.release_date
        prod.store_date = api_prod.store_date
        prod.development_active = api_prod.in_development

        if api_prod.has("brand_ratings"):
            prod.age_esrb = parse_age(api_prod.brand_ratings["esrb"])
            prod.age_pegi = parse_age(api_prod.brand_ratings["pegi"])
            prod.age_usk = parse_age(api_prod.brand_ratings["usk"])

        if api_prod.has("rating"):
            prod.rating = api_prod.rating
            prod.votes_count = api_prod.votes_count
            prod.reviews_count = api_prod.reviews.total_results

        prod.title = api_prod.title_galaxy
        prod.slug = api_prod.slug
        prod.title_norm = normalize_title(api_prod.title)
        prod.forum_id = api_prod.forum_slug

        if api_prod.has("developer", "publisher"):
            prod.developer = parse_company(api_prod.developer, companies)
            prod.publisher = parse_company(api_prod.publisher, companies)

        prod.image_background = parse_image_url(api_prod.image_background)
        prod.image_logo = parse_image_url(api_prod.image_logo)
        prod.image_icon = parse_image_url(api_prod.image_icon)

        prod.description_full = api_prod.description
        prod.description_cool = api_prod.cool_about_it

        # Downloads

        db_download_slugs = set(dl.slug for dl in prod.downloads if not dl.deleted)
        api_download_slugs = set(dl.id for dl in api_prod.downloads)

        # Mark deleted downloads
        for del_slug in db_download_slugs - api_download_slugs:
            download = prod.download_by_slug(del_slug)
            changelog.dl_del(download, prod.changes, cur_time)
            download.deleted = True

        for api_download in api_prod.downloads:
            download = prod.download_by_slug(api_download.id)

            # Add new downloads
            if download is None:
                download = model.Download(slug=api_download.id)
                prod.downloads.append(download)
                changelog.dl_add(download, prod.changes, cur_time)
            elif download.deleted:
                download.deleted = False
                changelog.dl_add(download, prod.changes, cur_time)
            else:
                changelog.dl_name(
                    download, api_download.name, prod.changes, cur_time)
                changelog.dl_version(
                    download, api_download.version, prod.changes, cur_time)
                changelog.dl_total_size(
                    download, api_download.total_size, prod.changes, cur_time)

            download.name = api_download.name
            download.type = api_download.category
            download.bonus_type = api_download.bonus_type
            download.count = api_download.count
            download.os = api_download.os
            download.language = api_download.language
            download.version = api_download.version

            # Files

            db_file_ids = set(f.slug for f in download.files if not f.deleted)
            api_file_ids = set(f.id for f in api_download.files)

            # Remove old files
            for del_id in db_file_ids - api_file_ids:
                download.file_by_slug(del_id).deleted = True

            for api_file in api_download.files:
                dlfile = download.file_by_slug(api_file.id)

                # Add new files
                if dlfile is None:
                    dlfile = model.DlFile(slug=api_file.id)
                    download.files.append(dlfile)

                dlfile.deleted = False
                dlfile.size = api_file.size


        # Features

        if api_prod.has("features"):
            prod.features = []
            for feature in api_prod.features:
                prod.features.append(model.Feature(slug=feature.slug))

        # Genres

        if api_prod.has("genres"):
            prod.genres = []
            for genre in api_prod.genres:
                prod.genres.append(model.Genre(slug=genre.slug))

        # Languages

        prod.languages = []
        for language in api_prod.languages:
            prod.languages.append(model.Language(isocode=language.isocode))

        # Dependency

        if api_prod.has("required_product") and api_prod.required_product is not None:
            dependencies[api_prod.id] = api_prod.required_product.id

    # Price entry

    if prod.pricehistory:
        last_record = prod.pricehistory[-1]
    else:
        last_record = model.PriceRecord(
            price_base = None,
            price_final = None)

    if api_prod.has("price") and api_prod.is_price_visible:
        current_record = model.PriceRecord(
            price_base = api_prod.price.base,
            price_final = api_prod.price.final)
    else:
        current_record = model.PriceRecord(
            price_base = None,
            price_final = None)

    current_record.date = datetime.datetime.utcnow()
    if (not current_record.same_price(last_record)):
        prod.pricehistory.append(current_record)

    # Add to session and clean up

    session.add(prod)
    session.flush()
    session.expunge(prod)
    db_queue.task_done()


# Set dependencies

products = {}
for product in session.query(model.Product):
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
logger.info("Done")
