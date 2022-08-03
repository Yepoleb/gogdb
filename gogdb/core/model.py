import dataclasses
from dataclasses import field
import datetime
from typing import List, Any
import decimal


def get_origin(t):
    """Typing function defined here for compatibility with Python 3.7"""
    return getattr(t, "__origin__", None)

def defaultdataclass(cls):
    for name, anno_type in cls.__annotations__.items():
        if not hasattr(cls, name):
            if get_origin(anno_type) is list:
                fieldvalue = dataclasses.field(default_factory=list)
            else:
                fieldvalue = None
            setattr(cls, name, fieldvalue)
    return dataclasses.dataclass(cls)

def list_field():
    return dataclasses.field(default_factory=list)

@defaultdataclass
class Feature:
    id: str
    name: str

@defaultdataclass
class Localization:
    code: str
    name: str
    text: bool = False
    audio: bool = False

@defaultdataclass
class Video:
    video_url: str
    thumbnail_url: str
    provider: str

@defaultdataclass
class Tag:
    id: int
    level: int
    name: str
    slug: str

@defaultdataclass
class Series:
    id: int
    name: str

@defaultdataclass
class Edition:
    id: int
    name: str
    has_product_card: bool

@defaultdataclass
class Language:
    code: str
    name: str

@defaultdataclass
class File:
    id: str
    size: int
    downlink: str

@defaultdataclass
class Download:
    id: str
    name: str
    total_size: int
    files: List[File]

@defaultdataclass
class BonusDownload(Download):
    bonus_type: str
    count: int

    @property
    def unique_id(self):
        return (self.name, self.bonus_type)

    def is_same(self, other):
        for attr_name in ["name", "total_size", "files", "bonus_type", "count"]:
            if getattr(self, attr_name) != getattr(other, attr_name):
                return False
        return True

@defaultdataclass
class SoftwareDownload(Download):
    os: str
    language: Language
    version: str

    @property
    def unique_id(self):
        return (self.name, self.os, self.language.code)

    def is_same(self, other):
        for attr_name in ["name", "total_size", "files", "os", "version"]:
            if getattr(self, attr_name) != getattr(other, attr_name):
                return False
        # Languages should only be compared on the language codes, the name does not matter
        if self.language.code != other.language.code:
            return False
        return True

@defaultdataclass
class DownloadRecord:
    dl_type: str
    dl_new_bonus: BonusDownload
    dl_old_bonus: BonusDownload
    dl_new_software: SoftwareDownload
    dl_old_software: SoftwareDownload

@defaultdataclass
class PropertyRecord:
    property_name: str
    value_new: Any
    value_old: Any

@defaultdataclass
class ChangeRecord:
    product_id: int
    timestamp: datetime.datetime
    action: str
    category: str
    download_record: DownloadRecord
    property_record: PropertyRecord
    build_id: int

@defaultdataclass
class PriceRecord:
    price_base: int
    price_final: int
    currency: str
    date: datetime.datetime

    @property
    def discount(self):
        if self.price_base == 0:
            # If the product is free the final price is 100% of the base price
            price_fract = 1
        elif self.price_final is None or self.price_base is None:
            # No discounts for products not for sale
            return None
        else:
            price_fract = self.price_final / self.price_base

        discount_rounded = int(round((1 - price_fract) * 100))
        # Round discounts ending with 9 or 1
        if (discount_rounded % 10) == 9:
            discount_rounded += 1
        elif (discount_rounded % 10) == 1:
            discount_rounded -= 1
        return discount_rounded

    @property
    def price_base_decimal(self):
        if self.price_base is None:
            return None
        return decimal.Decimal(self.price_base) / 100

    @price_base_decimal.setter
    def price_base_decimal(self, value):
        if value is None:
            self.price_base = None
        else:
            self.price_base = int(value * 100)

    @property
    def price_final_decimal(self):
        if self.price_final is None:
            return None
        return decimal.Decimal(self.price_final) / 100

    @price_final_decimal.setter
    def price_final_decimal(self, value):
        if value is None:
            self.price_final = None
        else:
            self.price_final = int(value * 100)

    def same_price(self, other):
        return (
            self.price_base == other.price_base and
            self.price_final == other.price_final and
            self.currency == other.currency
        )


@defaultdataclass
class Build:
    id: int
    product_id: int
    os: str
    branch: str
    version: str
    tags: List[str]
    public: bool
    date_published: datetime.datetime
    generation: int
    legacy_build_id: int
    meta_id: str
    link: str
    listed: bool # Shown in builds list

@defaultdataclass
class Product:
    id: int
    added_on: datetime.datetime
    last_updated: datetime.datetime

    title: str
    type: str
    slug: str
    access: int

    features: List[Feature]
    localizations: List[Localization]
    tags: List[Tag]
    cs_systems: List[str]
    comp_systems: List[str]
    #dl_systems: List[str]  # never used in V2
    is_using_dosbox: bool

    developers: List[str]
    publisher: str
    copyright: str

    global_date: datetime.datetime
    store_date: datetime.datetime
    is_in_development: bool
    #is_pre_order: bool  # deprecated in favor of store_state
    age_rating: int

    user_rating: int
    store_state: str
    rank_bestselling: int
    rank_trending: int
    #sale_rank: int = 0  # deprecated

    image_logo: str
    image_background: str
    image_icon: str
    image_galaxy_background: str
    image_boxart: str
    image_icon_square: str

    link_forum: str
    link_store: str
    link_support: str

    screenshots: List[str]
    videos: List[Video]

    editions: List[Edition]
    includes_games: List[int]
    is_included_in: List[int]
    required_by: List[int]
    requires: List[int]
    series: Series
    dlcs: List[int]

    description: str
    changelog: str

    dl_bonus: List[BonusDownload]
    dl_installer: List[SoftwareDownload]
    dl_langpack: List[SoftwareDownload]
    dl_patch: List[SoftwareDownload]
    builds: List[Build]

    def has_content(self):
         # If the product has its id set that means at least v0 content is available
        return bool(self.id)


# Index classes

@defaultdataclass
class IndexProduct:
    id: int
    title: str
    image_logo: str
    type: str
    comp_systems: List[str]
    sale_rank: int
    search_title: str

@defaultdataclass
class IndexChange:
    id: int
    title: str
    timestamp: datetime.datetime
    action: str
    category: str

    dl_type: str
    bonus_type: str
    property_name: str
    record: ChangeRecord

@defaultdataclass
class IndexChangelogSummary:
    product_id: int
    product_title: str
    timestamp: datetime.datetime
    categories: List[str]

@defaultdataclass
class StartpageProduct:
    id: int
    title: str
    image_logo: str
    discount: int

@defaultdataclass
class StartpageLists:
    added: List[StartpageProduct]
    trending: List[StartpageProduct]
    builds: List[StartpageProduct]
    sale: List[StartpageProduct]


########################################
# Generation 1
########################################

@defaultdataclass
class DepotV1:
    languages: List[str]
    size: int
    game_ids: List[int]
    system: str
    manifest: str

    @property
    def manifest_id(self):
        return self.manifest[:-len(".json")]

@defaultdataclass
class RedistV1:
    """Either target_dir or executable and argument are set"""
    redist: str
    executable: str
    argument: str
    target_dir: str

@defaultdataclass
class SupportCommandV1:
    language: str
    executable: str
    product_id: int
    system: str

@defaultdataclass
class RepositoryProductV1:
    dependency: int
    product_id: int
    name: str
    standalone: bool

@defaultdataclass
class RepositoryV1:
    timestamp: int # Seconds since 2014-02-28 23:00:00
    depots: List[DepotV1]
    redists: List[RedistV1]
    support_commands: List[SupportCommandV1]
    install_directory: str
    root_game_id: int
    products: List[RepositoryProductV1]
    name: str


@defaultdataclass
class DepotFileV1:
    type = "file"
    path: str
    size: int
    checksum: str
    url: str
    offset: int
    flags: List[str]

@defaultdataclass
class DepotDirectoryV1:
    type = "dir"
    path: str
    flags: List[str]

@defaultdataclass
class DepotLinkV1:
    type = "link"
    path: str
    target: str
    link_type: str

@defaultdataclass
class DepotManifestV1:
    name: str
    files: List[DepotFileV1]
    directories: List[DepotDirectoryV1]
    links: List[DepotLinkV1]

    @property
    def manifest_id(self):
        assert self.url.endswith(".json")
        return self.url[self.url.rfind("/") + 1:-len(".json")]


########################################
# Generation 2
########################################

@defaultdataclass
class CloudSaveV2:
    location: str
    name: str

@defaultdataclass
class DepotV2:
    compressed_size: int
    size: int
    languages: List[str]
    manifest_id: str
    product_id: int
    is_gog_depot: bool
    os_bitness: str # "32" or "64"

@defaultdataclass
class RepositoryProductV2:
    name: str
    product_id: int
    script: str
    temp_arguments: str
    temp_executable: str

@defaultdataclass
class RepositoryV2:
    base_product_id: int
    client_id: str
    client_secret: str
    cloudsaves: CloudSaveV2
    dependencies: List[str] # Names of redistributables
    depots: List[DepotV2]
    install_directory: str
    offline_depot: DepotV2
    platform: str
    products: List[RepositoryProductV2]
    script_interpreter: bool
    tags: List[str]



@defaultdataclass
class DepotChunkV2:
    compressed_md5: str
    compressed_size: int
    md5: str
    size: int

@defaultdataclass
class DepotFileV2:
    type = "file"
    chunks: List[DepotChunkV2]
    sfc_offset: int
    sfc_size: int
    flags: List[str]
    path: str
    md5: str
    sha256: str

    @property
    def size(self):
        return sum(chunk.size for chunk in self.chunks)

@defaultdataclass
class DepotDirectoryV2:
    type = "dir"
    path: str

@defaultdataclass
class DepotLinkV2:
    type = "link"
    path: str
    target: str

@defaultdataclass
class DepotManifestV2:
    files: List[DepotFileV2]
    directories: List[DepotDirectoryV2]
    links: List[DepotLinkV2]
    small_files_container: DepotFileV2
