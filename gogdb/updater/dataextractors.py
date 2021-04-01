import dateutil.parser
import collections
import re

import gogdb.core.model as model
from gogdb.core.normalization import normalize_system



def parse_datetime(date_str):
    if date_str is None:
        return None
    else:
        return dateutil.parser.isoparse(date_str)


IMAGE_RE = re.compile(r"\w{64}")
def extract_imageid(image_url):
    if image_url is None:
        return None
    m = IMAGE_RE.search(image_url)
    if m is None:
        return None
    else:
        return m.group(0)

def extract_properties_v0(prod, v0_cont):
    prod.id = v0_cont["id"]
    prod.access = 1

    prod.title = v0_cont["title"]
    prod.type = v0_cont["game_type"]
    prod.slug = v0_cont["slug"]

    prod.cs_systems = []
    for cs_name in ["windows", "osx", "linux"]:
        if v0_cont["content_system_compatibility"][cs_name]:
            prod.cs_systems.append(normalize_system(cs_name))

    prod.store_date = parse_datetime(v0_cont["release_date"])
    prod.is_in_development = v0_cont["in_development"]["active"]
    prod.is_pre_order = v0_cont["is_pre_order"]

    prod.image_logo = extract_imageid(v0_cont["images"]["logo"])
    prod.image_background = extract_imageid(v0_cont["images"]["background"])
    prod.image_icon = extract_imageid(v0_cont["images"]["sidebarIcon"])

    prod.link_forum = v0_cont["links"]["forum"]
    prod.link_store = v0_cont["links"]["product_card"]
    prod.link_support = v0_cont["links"]["support"]

    prod.screenshots = [x["image_id"] for x in v0_cont.get("screenshots", [])]
    prod.videos = [
        model.Video(
            video_url=v["video_url"],
            thumbnail_url=v["thumbnail_url"],
            provider=v["provider"]
        ) for v in v0_cont.get("videos", [])
    ]

    if v0_cont["dlcs"]:
        prod.dlcs = [x["id"] for x in v0_cont["dlcs"]["products"]]

    prod.changelog = v0_cont["changelog"] or None

    def parse_file(file_cont):
        return model.File(
            id = str(file_cont["id"]),
            size = file_cont["size"],
            downlink = file_cont["downlink"]
        )

    def parse_bonusdls(bonus_cont):
        return [
            model.BonusDownload(
                id = str(dl["id"]),
                name = dl["name"],
                total_size = dl["total_size"],
                bonus_type = dl["type"],
                count = dl["count"],
                files = [parse_file(dlfile) for dlfile in dl["files"]]
            ) for dl in bonus_cont
        ]
    prod.dl_bonus = parse_bonusdls(v0_cont["downloads"]["bonus_content"])

    def parse_softwaredls(software_cont):
        return [
            model.SoftwareDownload(
                id = dl["id"],
                name = dl["name"],
                total_size = dl["total_size"],
                os = normalize_system(dl["os"]),
                language = model.Language(dl["language"], dl["language_full"]),
                version = dl["version"],
                files = [parse_file(dlfile) for dlfile in dl["files"]]
            ) for dl in software_cont
        ]
    prod.dl_installer = parse_softwaredls(v0_cont["downloads"]["installers"])
    prod.dl_langpack = parse_softwaredls(v0_cont["downloads"]["language_packs"])
    prod.dl_patch = parse_softwaredls(v0_cont["downloads"]["patches"])


PRODID_RE = re.compile(r"games/(\d+)")
def extract_prodid(apiv2_url):
    m = PRODID_RE.search(apiv2_url)
    return int(m.group(1))

def extract_properties_v2(prod, v2_cont):
    v2_embed = v2_cont["_embedded"]
    v2_links = v2_cont["_links"]

    prod.features = [
        model.Feature(
            id=x["id"],
            name=x["name"]
        ) for x in v2_embed["features"]
    ]
    localizations_map = collections.defaultdict(lambda: model.Localization())
    for loc in v2_embed["localizations"]:
        loc_embed = loc["_embedded"]
        localization = localizations_map[loc_embed["language"]["code"]]
        localization.code = loc_embed["language"]["code"]
        localization.name = loc_embed["language"]["name"]
        if loc_embed["localizationScope"]["type"] == "text":
            localization.text = True
        elif loc_embed["localizationScope"]["type"] == "audio":
            localization.audio = True
    prod.localizations = list(localizations_map.values())
    prod.tags = [
        model.Tag(
            id=x["id"],
            level=x["level"],
            name=x["name"],
            slug=x["slug"]
        ) for x in v2_embed["tags"]
    ]
    prod.comp_systems = [
        normalize_system(support_entry["operatingSystem"]["name"])
        for support_entry in v2_embed["supportedOperatingSystems"]
    ]
    prod.is_using_dosbox = v2_cont["isUsingDosBox"]

    prod.developers = [x["name"] for x in v2_embed["developers"]]
    prod.publisher = v2_embed["publisher"]["name"]
    prod.copyright = v2_cont["copyrights"] or None

    prod.global_date = parse_datetime(v2_embed["product"].get("globalReleaseDate"))
    if "galaxyBackgroundImage" in v2_links:
        prod.image_galaxy_background = extract_imageid(v2_links["galaxyBackgroundImage"]["href"])
    prod.image_boxart = extract_imageid(v2_links["boxArtImage"]["href"])
    prod.image_icon_square = extract_imageid(v2_links["iconSquare"]["href"])

    prod.editions = [
        model.Edition(
            id=ed["id"],
            name=ed["name"],
            has_product_card=ed["hasProductCard"]
        ) for ed in v2_embed["editions"]
    ]
    prod.includes_games = [
        extract_prodid(link["href"])
        for link in v2_links.get("includesGames", [])
    ]
    prod.is_included_in = [
        extract_prodid(link["href"])
        for link in v2_links.get("isIncludedInGames", [])
    ]
    prod.required_by = [
        extract_prodid(link["href"])
        for link in v2_links.get("isRequiredByGames", [])
    ]
    prod.requires = [
        extract_prodid(link["href"])
        for link in v2_links.get("requiresGames", [])
    ]

    if v2_embed["series"]:
        prod.series = model.Series(
            id=v2_embed["series"]["id"],
            name=v2_embed["series"]["name"]
        )

    prod.description = v2_cont["description"]


META_ID_RE = re.compile(r"v2/meta/.{2}/.{2}/(\w+)")
def extract_metaid(meta_url):
    m = META_ID_RE.search(meta_url)
    if m is None:
        return None
    else:
        return m.group(1)

def extract_builds(prod, build_cont, system):
    for build in prod.builds:
        # Mark all builds as unlisted to relist them later
        if build.os == system:
            build.listed = False

    for build_item in build_cont["items"]:
        build_id = int(build_item["build_id"])
        # Find existing build based on id and set `build` to it
        for existing_build in prod.builds:
            if existing_build.id == build_id:
                build = existing_build
                break
        else: # No existing build found
            build = model.Build()
            prod.builds.append(build)
        build.id = build_id
        build.product_id = int(build_item["product_id"])
        build.os = build_item["os"]
        build.branch = build_item["branch"]
        build.version = build_item["version_name"] or None
        build.tags = build_item["tags"]
        build.public = build_item["public"]
        build.date_published = parse_datetime(build_item["date_published"])
        build.generation = build_item["generation"]
        build.legacy_build_id = build_item.get("legacy_build_id")
        build.meta_id = extract_metaid(build_item["link"])
        build.link = build_item["link"]
        build.listed = True

    prod.builds.sort(key=lambda b: b.date_published)
