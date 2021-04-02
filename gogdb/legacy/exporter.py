import sys
import datetime
import copy
import itertools

import sqlalchemy

import gogdb.legacy.model as legacy_model
import gogdb.core.storage
import gogdb.core.model as new_model
from gogdb.core.normalization import normalize_system
import gogdb.core.changelogger as changelogger



def migrate_products(l_session, n_db):
    exported_ids = set()

    l_products = l_session.query(legacy_model.Product)
    for l_prod in l_products:
        exported_ids.add(n_prod.id)

def convert_files(l_files, prod_id):
    return [
        new_model.File(
            id = l_file.slug,
            size = l_file.size,
            downlink = f"https://api.gog.com/products/{ prod_id }/downlink/installer/{ l_file.slug }"
        ) for l_file in l_files if not l_file.deleted
    ]

def convert_bonusdl(l_dl, prod_id):
    return new_model.BonusDownload(
        id = l_dl.slug,
        name = l_dl.name,
        total_size = l_dl.total_size,
        bonus_type = l_dl.bonus_type,
        count = l_dl.count,
        files = convert_files(l_dl.files, prod_id)
    )

def convert_softwaredl(l_dl, prod_id):
    return new_model.SoftwareDownload(
        id = l_dl.slug,
        name = l_dl.name,
        total_size = l_dl.total_size,
        os = normalize_system(l_dl.os),
        language = new_model.Language(
            code=l_dl.language,
            name=l_dl.language
        ),
        version = l_dl.version,
        files = convert_files(l_dl.files, prod_id)
    )

def normalize_system_list(systems):
    if systems is None:
        return []
    else:
        return [normalize_system(s) for s in systems]

def date_to_datetime(d):
    if d is None:
        return None
    return datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc)

def convert_product(l_prod):
    n_prod = new_model.Product()
    n_prod.id = l_prod.id

    def is_add_product_record(changerec):
        return changerec.action == "add" and changerec.type_prim == "product"
    added_record = list(filter(is_add_product_record, l_prod.changes))
    if added_record:
        n_prod.added_on = added_record[0].timestamp.replace(tzinfo=datetime.timezone.utc)
    #n_prod.last_updated

    n_prod.title = l_prod.title
    n_prod.type = l_prod.product_type
    n_prod.slug = l_prod.slug
    n_prod.access = l_prod.access

    #n_prod.features = l_prod.
    #n_prod.localizations = l_prod.
    #n_prod.tags = l_prod.
    n_prod.cs_systems = normalize_system_list(l_prod.cs_systems)
    n_prod.comp_systems = normalize_system_list(l_prod.comp_systems)
    #n_prod.is_using_dosbox = l_prod.

    #n_prod.developers = l_prod.
    #n_prod.publisher = l_prod.
    #n_prod.copyright = l_prod.

    n_prod.global_date = date_to_datetime(l_prod.release_date)
    n_prod.store_date = date_to_datetime(l_prod.store_date)
    n_prod.is_in_development = l_prod.development_active
    n_prod.is_pre_order = l_prod.is_pre_order
    #n_prod.sale_rank = l_prod.

    n_prod.image_logo = l_prod.image_logo
    n_prod.image_background = l_prod.image_background
    n_prod.image_icon = l_prod.image_icon
    #n_prod.image_galaxy_background = l_prod.
    #n_prod.image_boxart = l_prod.
    #n_prod.image_icon_square = l_prod.

    #n_prod.link_forum = l_prod.
    #n_prod.link_store = l_prod.
    #n_prod.link_support = l_prod.

    n_prod.screenshots = [l_scr.image_id for l_scr in l_prod.screenshots]

    n_prod.videos = [
        new_model.Video(
            provider="youtube",
            video_url=f"https://www.youtube.com/embed/{ l_video.video_id }?wmode=opaque&rel=0",
            thumbnail_url=f"https://img.youtube.com/vi/{ l_video.video_id }/hqdefault.jpg"
        ) for l_video in l_prod.videos
    ]

    #n_prod.editions = l_prod.
    #n_prod.includes_games = l_prod.
    #n_prod.is_included_in = l_prod.
    #n_prod.required_by = l_prod.
    if l_prod.base_prod_id:
        n_prod.requires = [l_prod.base_prod_id]
    #n_prod.series = l_prod.
    n_prod.dlcs = [l_dlc.id for l_dlc in l_prod.dlcs]

    n_prod.description = l_prod.description_full
    n_prod.changelog = l_prod.changelog or None

    for l_dl in l_prod.downloads:
        if l_dl.deleted:
            continue
        if l_dl.type == "bonus_content":
            n_prod.dl_bonus.append(convert_bonusdl(l_dl, l_prod.id))
        elif l_dl.type == "installers":
            n_prod.dl_installer.append(convert_softwaredl(l_dl, l_prod.id))
        elif l_dl.type == "language_packs":
            n_prod.dl_langpack.append(convert_softwaredl(l_dl, l_prod.id))
        elif l_dl.type == "patches":
            n_prod.dl_patch.append(convert_softwaredl(l_dl, l_prod.id))

    for l_build in l_prod.builds:
        if l_build.generation == 1:
            manifest_url = "https://cdn.gog.com/content-system/v1/manifests/{}/windows/{}/repository.json".format(
                l_prod.id, l_build.legacy_build_id)
        elif l_build.generation == 2:
            manifest_url = "https://cdn.gog.com/content-system/v2/meta/{}/{}/{}".format(
                l_build.meta_id[0:2], l_build.meta_id[2:4], l_build.meta_id)

        n_prod.builds.append(new_model.Build(
            id = l_build.build_id,
            product_id = l_build.prod_id,
            os = normalize_system(l_build.os),
            branch = None,
            version = l_build.version,
            tags = l_build.tags,
            public = l_build.public,
            date_published = l_build.date_published.astimezone(datetime.timezone.utc),
            generation = l_build.generation,
            legacy_build_id = l_build.legacy_build_id,
            meta_id = l_build.meta_id,
            link = manifest_url,
            listed = True
        ))

    return n_prod


@new_model.defaultdataclass
class MetaDownload:
    type: str
    deleted: bool
    download: None

@new_model.defaultdataclass
class DummyProduct:
    id: int
    title: str
    comp_systems: list
    access: int
    downloads: list

    @property
    def dl_bonus(self):
        return [dl.download for dl in self.downloads if dl.type == "bonus_content" and not dl.deleted]

    @property
    def dl_installer(self):
        return [dl.download for dl in self.downloads if dl.type == "installers" and not dl.deleted]

    @property
    def dl_langpack(self):
        return [dl.download for dl in self.downloads if dl.type == "language_packs" and not dl.deleted]

    @property
    def dl_patch(self):
        return [dl.download for dl in self.downloads if dl.type == "patches" and not dl.deleted]

    def download_by_id(self, dl_id):
        for dl in self.downloads:
            if dl.download.id == dl_id:
                return dl
        else:
            breakpoint()
            raise Exception("Download not found: " + dl_id)


def convert_changelog(l_prod):
    l_changes = l_prod.changes
    if not l_changes:
        return []

    # Group changes by date
    l_changes_groups = []
    last_date = l_changes[0].timestamp
    l_cur_group = []
    for l_changerec in l_changes:
        if l_changerec.timestamp == last_date:
            l_cur_group.append(l_changerec)
        else:
            l_changes_groups.append(l_cur_group)
            l_cur_group = [l_changerec]
        last_date = l_changerec.timestamp
    l_changes_groups.append(l_cur_group)

    dummy_prod = DummyProduct()
    dummy_prod.id = l_prod.id
    dummy_prod.title = l_prod.title
    dummy_prod.comp_systems = normalize_system_list(l_prod.comp_systems)
    dummy_prod.access = l_prod.access

    dummy_prod.downloads = []
    for l_dl in l_prod.downloads:
        if l_dl.type == "bonus_content":
            dummy_prod.downloads.append(
                MetaDownload(
                    type = l_dl.type,
                    deleted = l_dl.deleted,
                    download = convert_bonusdl(l_dl, l_prod.id)
                )
            )
        else:
            dummy_prod.downloads.append(
                MetaDownload(
                    type = l_dl.type,
                    deleted = l_dl.deleted,
                    download = convert_softwaredl(l_dl, l_prod.id)
                )
            )

    # Moving in time backwards, so the previous state is actually in the future
    future_productstate = dummy_prod
    changelog = []

    for l_ch_group in l_changes_groups:
        cur_productstate = copy.deepcopy(future_productstate)
        cur_date = l_ch_group[0].timestamp.replace(tzinfo=datetime.timezone.utc)
        prod_changelogger = changelogger.Changelogger(future_productstate, cur_productstate, cur_date)
        for l_change in l_ch_group:
            action_type = l_change.action_type
            if action_type == "add product":
                prod_changelogger.prod_added()
            elif action_type == "change product.access":
                cur_productstate.access = int(l_change.old)
            elif action_type == "change product.cs":
                pass
            elif action_type == "change product.os":
                cur_productstate.comp_systems = [normalize_system(s) for s in l_change.old.split(",")]
            elif action_type == "change product.title":
                cur_productstate.title = l_change.old
            elif action_type == "change product.forum_slug":
                pass
            elif action_type == "add download":
                cur_productstate.download_by_id(l_change.resource).deleted = True
            elif action_type == "del download":
                cur_productstate.download_by_id(l_change.resource).deleted = False
            elif action_type == "change download.version":
                cur_productstate.download_by_id(l_change.resource).download.version = l_change.old
            elif action_type == "change download.name":
                cur_productstate.download_by_id(l_change.resource).download.name = l_change.old
            elif action_type == "change download.total_size":
                cur_productstate.download_by_id(l_change.resource).download.total_size = int(l_change.old)
            else:
                raise RuntimeError("Unknown change type " + l_change.action_type)

        prod_changelogger.property("title")
        prod_changelogger.property("comp_systems")
        prod_changelogger.property("access")
        prod_changelogger.downloads("bonus")
        prod_changelogger.downloads("installer")
        prod_changelogger.downloads("langpack")
        prod_changelogger.downloads("patch")
        changelog += prod_changelogger.entries
        future_productstate = cur_productstate

    changelog.reverse() # reverse so entries are sorted oldest to most recent
    return changelog

def convert_prices(l_prod):
    price_log = {"US": {"USD": []}}

    for l_pricerec in l_prod.pricehistory:
        n_record = new_model.PriceRecord(
            date = l_pricerec.date.replace(tzinfo=datetime.timezone.utc),
            currency = "USD"
        )
        if l_pricerec.price_base is not None:
            n_record.price_base = int(l_pricerec.price_base * 100)
        if l_pricerec.price_final is not None:
            n_record.price_final = int(l_pricerec.price_final * 100)
        price_log["US"]["USD"].append(n_record)
    return price_log

def main():
    if len(sys.argv) < 3:
        print("Usage: exporter postgresql://<sqlalchemy_conn> <storage_path>")
        return 1

    engine = sqlalchemy.create_engine(sys.argv[1])
    Sessionmaker = sqlalchemy.orm.sessionmaker(bind=engine)
    l_session = Sessionmaker()

    n_db = gogdb.core.storage.Storage(sys.argv[2])

    exported_ids = set()

    l_products = l_session.query(legacy_model.Product)
    for l_prod in l_products:
        print("Converting", l_prod.id)
        n_prod = convert_product(l_prod)
        n_prices = convert_prices(l_prod)
        n_changes = convert_changelog(l_prod)
        exported_ids.add(n_prod.id)
        n_db.product.save(n_prod, n_prod.id)
        n_db.prices.save(n_prices, n_prod.id)
        n_db.changelog.save(n_changes, n_prod.id)

    n_db.ids.save(list(exported_ids))

main()
