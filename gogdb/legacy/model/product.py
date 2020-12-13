import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy import Column

from legacy.database import Base
from legacy.model.common import get_systems_list, set_systems_list


class Product(Base):
    __tablename__ = "products"

    id = Column(sql.Integer, primary_key=True, autoincrement=False)

    title = Column(sql.String(120), nullable=True)
    slug = Column(sql.String(120), nullable=True)
    title_norm = Column(sql.String(120), default="", nullable=False)
    forum_id = Column(sql.String(120), nullable=True)

    product_type = Column(sql.String(20), nullable=True)
    is_secret = Column(sql.Boolean, nullable=True)
    is_price_visible = Column(sql.Boolean, nullable=True)
    can_be_reviewed = Column(sql.Boolean, nullable=True)
    base_prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), nullable=True)

    cs_windows = Column(sql.Boolean, nullable=True)
    cs_mac = Column(sql.Boolean, nullable=True)
    cs_linux = Column(sql.Boolean, nullable=True)

    os_windows = Column(sql.Boolean, nullable=True)
    os_mac = Column(sql.Boolean, nullable=True)
    os_linux = Column(sql.Boolean, nullable=True)

    dl_windows = Column(sql.Boolean, nullable=True)
    dl_mac = Column(sql.Boolean, nullable=True)
    dl_linux = Column(sql.Boolean, nullable=True)

    is_coming_soon = Column(sql.Boolean, nullable=True)
    is_pre_order = Column(sql.Boolean, nullable=True)
    release_date = Column(sql.Date, nullable=True)
    store_date = Column(sql.Date, nullable=True)
    development_active = Column(sql.Boolean, nullable=True)
    access = Column(sql.SmallInteger, nullable=True)

    age_esrb = Column(sql.SmallInteger, nullable=True)
    age_pegi = Column(sql.SmallInteger, nullable=True)
    age_usk = Column(sql.SmallInteger, nullable=True)

    rating = Column(sql.SmallInteger, nullable=True)
    votes_count = Column(sql.Integer, nullable=True)
    reviews_count = Column(sql.Integer, nullable=True)

    developer_slug = Column(
        sql.String(120), sql.ForeignKey("companies.slug"), nullable=True)
    publisher_slug = Column(
        sql.String(120), sql.ForeignKey("companies.slug"), nullable=True)

    image_background = Column(sql.String(64), nullable=True)
    image_logo = Column(sql.String(64), nullable=True)
    image_icon = Column(sql.String(64), nullable=True)

    description_full = Column(sql.Text, nullable=True)
    description_cool = Column(sql.Text, nullable=True)
    changelog = Column(sql.Text, nullable=True)

    developer = orm.relationship("Company", foreign_keys=[developer_slug])
    publisher = orm.relationship("Company", foreign_keys=[publisher_slug])

    dlcs = orm.relationship(
        "Product", backref=orm.backref("base_product", remote_side=[id]))
    languages = orm.relationship(
        "Language", back_populates="product", cascade="all, delete-orphan")
    features = orm.relationship(
        "Feature", back_populates="product", cascade="all, delete-orphan")
    genres = orm.relationship(
        "Genre", back_populates="product", cascade="all, delete-orphan")
    screenshots = orm.relationship(
        "Screenshot", back_populates="product", cascade="all, delete-orphan")
    videos = orm.relationship(
        "Video", back_populates="product", cascade="all, delete-orphan")
    downloads = orm.relationship(
        "Download", back_populates="product", cascade="all, delete-orphan",
        order_by="Download.type, desc(Download.os), Download.slug")
    builds = orm.relationship(
        "Build", back_populates="product", cascade="all, delete-orphan",
        order_by="desc(Build.date_published)")
    pricehistory = orm.relationship(
        "PriceRecord", back_populates="product", cascade="all, delete-orphan",
        order_by="PriceRecord.date")
    changes = orm.relationship(
        "ChangeRecord", back_populates="product", cascade="all, delete-orphan",
        order_by="desc(ChangeRecord.id)")

    cs_systems = property(
        lambda self: get_systems_list(self, "cs_"),
        lambda self, v: set_systems_list(self, "cs_", v)
    )

    comp_systems = property(
        lambda self: get_systems_list(self, "os_"),
        lambda self, v: set_systems_list(self, "os_", v)
    )

    dl_systems = property(
        lambda self: get_systems_list(self, "dl_"),
        lambda self, v: set_systems_list(self, "dl_", v)
    )

    @property
    def systems(self):
        if self.access >= 2:
            return self.comp_systems
        else:
            return self.dl_systems

    @property
    def release_arrow(self):
        if self.release_date is not None:
            return arrow.Arrow.fromdate(self.release_date)
        else:
            return None

    @property
    def valid_downloads(self):
        return [download for download in self.downloads
            if not download.deleted]

    @property
    def valid_installers(self):
        return [download for download in self.downloads
            if not download.deleted and download.type != "bonus_content"
        ]

    @property
    def valid_bonus(self):
        return [download for download in self.downloads
            if not download.deleted and download.type == "bonus_content"
        ]

    def download_by_slug(self, slug):
        for download in self.downloads:
            if download.slug == slug:
                return download
        return None

    def build_by_id(self, build_id):
        for build in self.builds:
            if build.id == build_id:
                return build
        return None

    def __repr__(self):
        return "<Product(id={}, slug='{}')>".format(self.id, self.slug)


class Language(Base):
    __tablename__ = "languages"

    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), primary_key=True)
    isocode = Column(sql.String(20), primary_key=True)

    product = orm.relationship("Product", back_populates="languages")

    def __repr__(self):
        return "<Language(prod_id={}, isocode='{}')>".format(
            self.prod_id, self.isocode)


class Feature(Base):
    __tablename__ = "features"

    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), primary_key=True)
    slug = Column(sql.String(30), primary_key=True)

    product = orm.relationship("Product", back_populates="features")

    def __repr__(self):
        return "<Feature(prod_id={}, slug='{}')>".format(
            self.prod_id, self.slug)


class Genre(Base):
    __tablename__ = "genres"

    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), primary_key=True)
    slug = Column(sql.String(30), primary_key=True)

    product = orm.relationship("Product", back_populates="genres")

    def __repr__(self):
        return "<Genre(prod_id={}, slug='{}')>".format(
            self.prod_id, self.slug)


class Screenshot(Base):
    __tablename__ = "screenshots"

    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), primary_key=True)
    image_id = Column(sql.String(255), primary_key=True)

    product = orm.relationship("Product", back_populates="screenshots")

    def __repr__(self):
        return "<Screenshot(prod_id={}, image_id='{}')>".format(
            self.prod_id, self.image_id)


class Video(Base):
    __tablename__ = "videos"

    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), primary_key=True)
    video_id = Column(sql.String(20), primary_key=True)

    product = orm.relationship("Product", back_populates="videos")

    def __repr__(self):
        return "<Video(prod_id={}, video_id='{}')>".format(
            self.prod_id, self.video_id)


class Company(Base):
    __tablename__ = "companies"

    slug = Column(sql.String(120), primary_key=True)
    name = Column(sql.String(120), nullable=False)

    def __repr__(self):
        return "<Company(slug='{}', name='{}')>".format(self.slug, self.name)
