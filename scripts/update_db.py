#!/usr/bin/env python3
import json
import re
import datetime
import string
import os
import logging
import queue
import threading
import sys
import configparser
import random

import requests
import sqlalchemy
from sqlalchemy import orm
import gogapi

import gogdb
from gogdb import db, model
import changelog


IMAGE_RE = re.compile(r".+gog.com/([0-9a-f]+).*")
GALAXY_EXPANDED = [
    "downloads", "description", "screenshots", "videos", "changelog"]
ALLOWED_CHARS = set(string.ascii_lowercase + string.digits)
DL_WORKER_COUNT = 8
DB_QUEUE_LEN = 20
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

def safe_do(func, errormsg, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except (requests.HTTPError, gogapi.GogError) as e:
        if not hasattr(e, "response") or e.response.status_code != 404:
            logger.warning(errormsg, repr(e))
    except gogapi.NotAuthorizedError:
        logger.warning(errormsg, "Not Authorized")
    except Exception as e:
        logger.error(errormsg, repr(e))
        raise

def download_worker(token, dl_queue, db_queue, db_semaphore, existing):
    api = gogapi.GogApi(token)
    api.set_locale(*LOCALE)

    while True:
        db_semaphore.acquire(timeout=600)
        try:
            prod_id, slug = dl_queue.get(block=False)
        except queue.Empty:
            break

        product = api.product(prod_id, slug)

        safe_do(
            lambda prod: prod.update_galaxy(expand=GALAXY_EXPANDED),
            "Failed to load api data for {}: %s".format(product.id),
            product)

        if slug is not None:
            safe_do(
                lambda prod: prod.update_web(),
                "Failed to load gogData for {}: %s".format(product.id),
                product)

        builds = []
        if product.has("content_systems"):
            for system in product.content_systems:
                safe_do(
                    lambda builds, prod, system: \
                        builds.extend(prod.get_builds(system)),
                    "Failed to load builds for {}, {}: %s" \
                        .format(product.id, system),
                    builds, product, system)

        manifests = {1: {}, 2: {}}
        for build in builds:
            if (product.id, build.id) in existing["repo"]:
                continue

            safe_do(
                lambda build: build.update_repo(),
                "Failed to load repository {} for {}: %s" \
                    .format(build.id, product.id),
                build)

            if not build.has("repository"):
                continue

            for depot in build.repository.depots:
                manifests[depot.generation][depot.manifest.manifest_id] \
                    = depot.manifest

        all_manifests = \
            list(manifests[1].values()) + list(manifests[2].values())
        for manifest in all_manifests:
            if manifest.manifest_id in existing["manifest"]:
                continue

            safe_do(
                lambda manifest: manifest.update_manifest(),
                "Failed to load manifest {} for {}: %s" \
                    .format(manifest.manifest_id, product.id),
                manifest)

        dl_result = {
            "prod": product, "builds": builds, "manifests": manifests}
        db_queue.put(dl_result)
        dl_queue.task_done()


# Initialize logging
logging.basicConfig()
logger = logging.getLogger("UpdateDB")
logger.setLevel(logging.INFO)

# Alias session
session_factory = orm.sessionmaker(bind=db.engine)
g_session = session_factory()

# Initialize API

token = gogapi.Token.from_file(gogdb.app.config["TOKEN_PATH"])
g_api = gogapi.GogApi(token)

# Debug

if os.environ.get("DEBUG_CACHE"):
    import requests_cache
    requests_cache.install_cache(backend="redis", allowable_codes=(200, 404))
    print("Request cache enabled")
if os.environ.get("DEBUG_UPDATEDB"):
    logger.setLevel(logging.DEBUG)
if os.environ.get("DEBUG_GOGAPI"):
    logging.getLogger("gogapi").setLevel(logging.DEBUG)
if os.environ.get("DEBUG_SQL"):
    fh = logging.FileHandler(os.environ.get("DEBUG_SQL"))
    engine_logger = logging.getLogger("sqlalchemy.engine")
    engine_logger.addHandler(fh)
    engine_logger.propagate = False
    engine_logger.setLevel(logging.INFO)

# Load products and add them to the queue
logger.info("Loading catalog")
search_products = list(
    g_api.search(mediaType="game", sort="bestselling", limit=50) \
        .iter_products()
)
# Queue for passing search to download workers
dl_queue = queue.Queue()
# Queue for passing downloaded products back to main thread
db_queue = queue.Queue()

db_semaphore = threading.Semaphore(DB_QUEUE_LEN)

slug_map = {row[0]: None for row in g_session.query(model.Product.id)}
for prod in search_products:
    slug_map[prod.id] = prod.slug
del search_products
shuffled_items = list(slug_map.items())
random.shuffle(shuffled_items)
for prod_item in shuffled_items:
    dl_queue.put(prod_item)
products_count = len(slug_map)
logger.info("Found %s products", products_count)

existing = {}
existing["repo"] = set(
    g_session.query(model.Build.prod_id, model.Build.id) \
        .filter(
            (model.Build.legacy_build_id != None) |
            (model.Build.meta_id != None))
)
existing["manifest"] = (
    set(r[0] for r in g_session.query(model.DepotManifestV1.manifest_id)) |
    set(r[0] for r in g_session.query(model.DepotManifestV2.manifest_id))
)

# Start download threads
logger.info("Starting %d download workers", DL_WORKER_COUNT)
dl_threads = []
for i in range(DL_WORKER_COUNT):
    t = threading.Thread(
        target=download_worker,
        args=(token, dl_queue, db_queue, db_semaphore, existing))
    t.start()
    dl_threads.append(t)

dependencies = {}



def insert_downloads(prod, api_prod, cur_time):
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
            changelog.dl_add(download, prod.changes, cur_time)
            prod.downloads.append(download)
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


def flush_manifest(session, depotitems, depotclasses):
    for cls in depotclasses:
        classitems = depotitems[cls.__name__]
        if not classitems:
            continue
        converted_items = [dict(item) for item in classitems]
        converted_items.sort(key=lambda x: x["path"])
        session.bulk_insert_mappings(
            cls, converted_items, return_defaults=False,
            render_nulls=True)
        depotitems[cls.__name__] = []


def insert_manifest_v1(session, manifests_v1):
    manifest_v1_ids = list(manifests_v1.keys())
    db_manifests_v1 = {manifest.manifest_id: manifest
        for manifest in session.query(model.DepotManifestV1) \
        .filter(model.DepotManifestV1.manifest_id.in_(manifest_v1_ids))
    }

    depotclasses = [
        model.DepotFileV1, model.DepotDirectoryV1, model.DepotLinkV1
    ]

    for manifest_id, api_manifest in manifests_v1.items():
        manifest = db_manifests_v1.get(manifest_id)
        depotitems = {cls.__name__: [] for cls in depotclasses}

        if manifest is None:
            manifest = model.DepotManifestV1(manifest_id=manifest_id)
            session.add(manifest)
            session.flush()
            assert manifest.id is not None
            db_manifests_v1[manifest_id] = manifest

        if manifest.loaded or "manifest" not in api_manifest.loaded:
            continue

        manifest.name = api_manifest.name
        manifest.loaded = True

        for api_file in api_manifest.files:
            depotf = model.DepotFileV1(
                manifest_id=manifest.id,
                size=api_file.size,
                path=api_file.path,
                checksum=api_file.checksum,
                url=api_file.url,
                offset=api_file.offset,
                flags=api_file.flags)
            depotitems["DepotFileV1"].append(depotf)
            if (len(depotitems["DepotFileV1"]) > 5000):
                logger.debug("Flushing depot V1 %s", manifest_id)
                flush_manifest(session, depotitems, depotclasses)

        depotitems["DepotDirectoryV1"] += [
            model.DepotDirectoryV1(
                manifest_id=manifest.id,
                path=api_dir.path,
                flags=api_dir.flags
            )
            for api_dir in api_manifest.dirs
        ]

        depotitems["DepotLinkV1"] += [
            model.DepotLinkV1(
                manifest_id=manifest.id,
                path=api_link.path,
                target=api_link.target,
                is_directory=api_link.type == "directory"
            )
            for api_link in api_manifest.links
        ]

        if any(classitems for classitems in depotitems.values()):
            logger.debug("Inserting V1 depot %s", manifest_id)
            flush_manifest(session, depotitems, depotclasses)

    db_manifest_v1_ids = {
        mf.manifest_id: mf.id for mf in db_manifests_v1.values()
        if mf.loaded
    }
    return db_manifest_v1_ids


def insert_manifest_v2(session, manifests_v2):
    manifest_v2_ids = list(manifests_v2.keys())
    db_manifests_v2 = {manifest.manifest_id: manifest
        for manifest in session.query(model.DepotManifestV2) \
        .filter(model.DepotManifestV2.manifest_id.in_(manifest_v2_ids))
    }

    depotclasses = [
        model.DepotFileV2, model.DepotDirectoryV2, model.DepotLinkV2
    ]

    for manifest_id, api_manifest in manifests_v2.items():
        manifest = db_manifests_v2.get(manifest_id)
        depotitems = {cls.__name__: [] for cls in depotclasses}

        if manifest is None:
            manifest = model.DepotManifestV2(manifest_id=manifest_id)
            session.add(manifest)
            session.flush()
            assert manifest.id is not None
            db_manifests_v2[manifest_id] = manifest

        if manifest.loaded or "manifest" not in api_manifest.loaded:
            continue

        manifest.loaded = True

        for api_depotf in api_manifest.files:
            depotf = model.DepotFileV2()
            depotf.manifest_id = manifest.id
            depotf.path = api_depotf.path
            depotf.size = api_depotf.size
            if api_depotf.sfc_ref:
                depotf.sfc_offset = api_depotf.sfc_ref["offset"]
                depotf.sfc_size = api_depotf.sfc_ref["size"]
            else:
                depotf.sfc_offset = None
                depotf.sfc_size = None
            depotf.checksum = api_depotf.checksum
            depotf.flags = api_depotf.flags
            depotitems["DepotFileV2"].append(depotf)
            if (len(depotitems["DepotFileV2"]) > 5000):
                logger.debug("Flushing depot V2 %s", manifest_id)
                flush_manifest(session, depotitems, depotclasses)

        depotitems["DepotDirectoryV2"] += [
            model.DepotDirectoryV2(
                manifest_id = manifest.id,
                path=api_depotdir.path
            )
            for api_depotdir in api_manifest.directories
        ]

        depotitems["DepotLinkV2"] += [
            model.DepotLinkV2(
                manifest_id = manifest.id,
                path=api_link.path,
                target=api_link.target
            )
            for api_link in api_manifest.links
        ]

        if any(classitems for classitems in depotitems.values()):
            logger.debug("Inserting V2 depot %s", manifest_id)
            flush_manifest(session, depotitems, depotclasses)

    db_manifest_v2_ids = {
        mf.manifest_id: mf.id for mf in db_manifests_v2.values()
        if mf.loaded
    }
    return db_manifest_v2_ids


def insert_builds(prod, api_builds, manifest_ids):
    db_builds = {build.build_id: build for build in prod.builds}

    # Mark deleted builds
    api_build_ids = set(build.id for build in api_builds)
    for build in prod.builds:
        if build.build_id in api_build_ids:
            # changelog
            build.deleted = False
        else:
            build.deleted = True

    for api_build in api_builds:
        build = db_builds.get(api_build.id)

        if build is None:
            build = model.Build()
            #changelog.dl_add(download, prod.changes, cur_time)
            prod.builds.append(build)

            build.build_id = api_build.id
            build.prod_id = api_build.product_id
            build.os = api_build.os
            build.version = api_build.version_name
            build.public = api_build.public
            build.date_published = api_build.date_published
            build.generation = api_build.generation
            build.meta_id = api_build.meta_id
            build.legacy_build_id = api_build.legacy_build_id
            build.tags = api_build.tags

        if build.repo is None and api_build.has("repository"):
            if api_build.generation == 1:
                build.repo_v1 = insert_repo_v1(
                    api_build.repository, manifest_ids[1])
            if api_build.generation == 2:
                build.repo_v2 = insert_repo_v2(
                    api_build.repository, manifest_ids[2])


def insert_repo_v1(api_repo, manifest_v1_ids):
    repo = model.RepositoryV1()

    repo.timestamp = api_repo.timestamp
    repo.install_directory = api_repo.install_directory
    repo.base_prod_id = api_repo.root_game_id
    repo.name = api_repo.name

    repo.depots = []
    for api_depot in api_repo.depots:
        depot = model.DepotV1()
        repo.depots.append(depot)

        manifest_id = manifest_v1_ids.get(api_depot.manifest_id)
        if manifest_id is None:
            logger.warning(
                "Manifest %s not available, dropping repository",
                api_depot.manifest_id)
            return None

        depot.size = api_depot.size
        depot.prod_ids = api_depot.game_ids
        depot.os = api_depot.system
        depot.languages = api_depot.languages
        depot.manifest_id = manifest_id

    repo.redists = [
        model.RedistV1(
            redist=api_redist.redist,
            executable=api_redist.executable,
            argument=api_redist.argument,
        )
        for api_redist in api_repo.redists
    ]

    repo.support_commands = []
    for api_cmd in api_repo.support_commands:
        cmd = model.SupportCmdV1()
        repo.support_commands.append(cmd)

        cmd.executable = api_cmd.executable
        cmd.prod_id = api_cmd.product_id
        cmd.os = api_cmd.system
        cmd.lang = api_cmd.language

    repo.products = []
    for api_repoprod in api_repo.game_ids:
        repoprod = model.RepositoryProdV1()
        repo.products.append(repoprod)

        repoprod.prod_id = api_repoprod.product_id
        repoprod.name = api_repoprod.name
        repoprod.dependency = api_repoprod.dependency

    return repo

def insert_repo_v2(api_repo, manifest_v2_ids):
    repo = model.RepositoryV2()

    repo.base_prod_id = api_repo.base_product_id
    repo.client_id = api_repo.client_id
    repo.client_secret = api_repo.client_secret
    repo.install_directory = api_repo.install_directory
    repo.os = api_repo.platform
    repo.tags = api_repo.tags
    repo.dependencies = api_repo.dependencies

    repo.cloudsaves = [
        model.CloudSaveV2(
            location=api_cloudsave.location,
            name=api_cloudsave.name
        )
        for api_cloudsave in api_repo.cloudsaves
    ]

    repo.depot = []
    for api_depot in api_repo.depots:
        depot = model.DepotV2()
        repo.depots.append(depot)

        manifest_id = manifest_v2_ids.get(api_depot.manifest_id)
        if manifest_id is None:
            logger.warning(
                "Manifest %s not available, dropping repository",
                api_depot.manifest_id)
            return None

        depot.size = api_depot.size
        depot.prod_id = api_depot.product_id
        depot.is_gog_depot = api_depot.is_gog_depot
        depot.bitness = api_depot.os_bitness
        depot.is_offline = api_depot.is_offline
        depot.languages = api_depot.languages
        depot.manifest_id = manifest_id

    repo.products = [
        model.RepositoryProdV2(
            name=api_repoprod.name,
            prod_id=api_repoprod.product_id,
            script=api_repoprod.script,
            temp_executable=api_repoprod.temp_executable
        )
        for api_repoprod in api_repo.products
    ]

    return repo


for counter in range(products_count):
    dl_result = db_queue.get(timeout=60)
    db_semaphore.release()
    api_prod = dl_result["prod"]
    prod_session = session_factory()

    logger.debug(
        "Product: %d (%d/%d)", api_prod.id, counter + 1, products_count)

    # Get current timestamp
    cur_time = datetime.datetime.utcnow()

    # Get the old data from the database
    prod = prod_session.query(model.Product) \
        .filter(model.Product.id == api_prod.id).one_or_none()

    if prod is None:
        if api_prod.has("title"):
            logger.info("New Product: %d %s", api_prod.id, api_prod.title)
        else:
            logger.info("New Product: %d", api_prod.id)
        prod = model.Product(id=api_prod.id)
        changelog.prod_add(prod, prod.changes, cur_time)

    # Set access
    if "galaxy" not in api_prod.loaded:
        access = 0
    elif "web" not in api_prod.loaded:
        access = 1
    else:
        access = 2

    if prod.access is not None:
        changelog.prod_access(prod, access, prod.changes, cur_time)
    prod.access = access

    if "galaxy" in api_prod.loaded:

        # Changelog product
        if api_prod.has("systems") and (prod.comp_systems is not None):
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

        prod.cs_systems = api_prod.content_systems

        if api_prod.has("systems"):
            prod.comp_systems = api_prod.systems

        prod.dl_systems = set(dl.os for dl in api_prod.downloads)

        if api_prod.has("is_coming_soon"):
            prod.is_coming_soon = api_prod.is_coming_soon
        else:
            prod.is_coming_soon = False
        prod.is_pre_order = api_prod.is_pre_order
        if api_prod.has("release_date") and api_prod.release_date is not None:
            prod.release_date = api_prod.release_date.date()
        if api_prod.store_date is not None:
            prod.store_date = api_prod.store_date.date()
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

        # Companies

        if api_prod.has("developer", "publisher"):

            companies_query = prod_session.query(model.Company) \
                .filter(model.Company.slug.in_(
                    (api_prod.developer["slug"], api_prod.publisher["slug"]))
                )
            companies = {company.slug: company for company in companies_query}

            prod.developer = parse_company(api_prod.developer, companies)
            prod.publisher = parse_company(api_prod.publisher, companies)

        prod.image_background = parse_image_url(api_prod.image_background)
        prod.image_logo = parse_image_url(api_prod.image_logo)
        prod.image_icon = parse_image_url(api_prod.image_icon)

        prod.description_full = api_prod.description
        prod.description_cool = api_prod.cool_about_it

        if api_prod.has("changelog"):
            prod.changelog = api_prod.changelog

        # Downloads

        insert_downloads(prod, api_prod, cur_time)

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
            prod.languages.append(
                model.Language(isocode=language.isocode))

        # Screenshots

        if api_prod.has("screenshots"):
            prod.screenshots = []
            for image_id in api_prod.screenshots:
                prod.screenshots.append(
                    model.Screenshot(image_id=image_id))

        # Videos

        if api_prod.has("videos"):
            prod.videos = []
            video_ids = set(video.video_id for video in api_prod.videos)
            for video_id in video_ids:
                prod.videos.append(model.Video(video_id=video_id))

        # Dependency

        if api_prod.has("required_product") \
                and api_prod.required_product is not None:
            dependencies[api_prod.id] = api_prod.required_product.id

        # Manifests

        manifest_ids = {
            1: insert_manifest_v1(prod_session, dl_result["manifests"][1]),
            2: insert_manifest_v2(prod_session, dl_result["manifests"][2])
        }

        # Builds

        insert_builds(prod, dl_result["builds"], manifest_ids)


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

    prod_session.add(prod)
    prod_session.commit()
    prod_session.close()
    db_queue.task_done()


# Set dependencies

products = {}
for product in g_session.query(model.Product):
    products[product.id] = product

for prod_id, dep_id in dependencies.items():
    if dep_id not in products:
        logger.warning("Missing dependency: %s for %s", dep_id, prod_id)
        continue

    product = products[prod_id]
    dependency = products[dep_id]
    product.base_product = dependency
    g_session.add(product)

# Apply changes

logger.info("Commiting data")
g_session.commit()
token.save(gogdb.app.config["TOKEN_PATH"])
logger.info("Done")
