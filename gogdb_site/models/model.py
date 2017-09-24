import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base

from arrow import arrow

from .meta import Base
from . import names

class Language(Base):
    __tablename__ = "languages"

    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), primary_key=True)
    isocode = Column(sql.String(5), primary_key=True)

    product = orm.relationship("Product", back_populates="languages")

    @property
    def name(self):
        # Fall back to isocode if a name isn't defined
        return names.languages.get(self.isocode, self.isocode)

    def __repr__(self):
        return "<Language(prod_id={}, isocode='{}')>".format(
            self.prod_id, self.isocode)

class Feature(Base):
    __tablename__ = "features"

    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), primary_key=True)
    slug = Column(sql.String(30), primary_key=True)

    product = orm.relationship("Product", back_populates="features")

    @property
    def name(self):
        return names.features.get(self.slug, self.slug)

    def __repr__(self):
        return "<Feature(prod_id={}, slug='{}')>".format(
            self.prod_id, self.slug)

class Genre(Base):
    __tablename__ = "genres"

    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), primary_key=True)
    slug = Column(sql.String(30), primary_key=True)

    product = orm.relationship("Product", back_populates="genres")

    @property
    def name(self):
        return names.genres.get(self.slug, self.slug)

    def __repr__(self):
        return "<Genre(prod_id={}, slug='{}')>".format(self.prod_id, self.slug)

class Company(Base):
    __tablename__ = "companies"

    slug = Column(sql.String(120), primary_key=True)
    name = Column(sql.String(120), nullable=False)

    def __repr__(self):
        return "<Company(slug='{}', name='{}')>".format(self.slug, self.name)

class PriceRecord(Base):
    __tablename__ = "pricerecords"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    prod_id = Column(sql.Integer, sql.ForeignKey("products.id"), nullable=True)
    price_base = Column(sql.Numeric, nullable=False)
    price_final = Column(sql.Numeric, nullable=False)
    date = Column(sql.DateTime, nullable=False)

    product = orm.relationship("Product", back_populates="pricehistory")

    @property
    def arrow(self):
        return arrow.Arrow.fromdatetime(self.date)

    @arrow.setter
    def arrow(self, value):
        self.date = value.datetime

    @property
    def discount(self):
        if self.price_base == 0:
            price_fract = 1
        else:
            price_fract = self.price_final / self.price_base

        discount_rounded = round((1 - price_fract) * 100)
        if (discount_rounded % 10) == 9:
            discount_rounded += 1
        elif (discount_rounded % 10) == 1:
            discount_rounded -= 1
        return discount_rounded

    def as_dict(self):
        return {
            "price_base": str(self.price_base),
            "price_final": str(self.price_final),
            "date": self.date.isoformat(),
            "discount": str(self.discount)
        }

    def __repr__(self):
        return "<PriceRecord(id={}, prod_id={}, date='{}')>".format(
            self.id, self.prod_id, self.date)

class DlFile(Base):
    __tablename__ = "files"
    __table_args__ = (sql.UniqueConstraint("download_id", "slug"),)

    download_id = Column(sql.Integer, sql.ForeignKey("downloads.id"),
        primary_key=True, autoincrement=False)
    slug = Column(sql.String(50), primary_key=True)
    size = Column(sql.BigInteger, nullable=False)

    download = orm.relationship("Download", back_populates="files")

    def __repr__(self):
        return "<DlFile(download_id={}, slug='{}', name='{}')>".format(
            self.download_id, self.slug, self.size)

class Download(Base):
    __tablename__ = "downloads"
    __table_args__ = (sql.UniqueConstraint("prod_id", "slug"),)

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), nullable=False)
    slug = Column(sql.String(50), nullable=False)
    name = Column(sql.String(120), nullable=False)
    type = Column(sql.String(50), nullable=False)
    bonus_type = Column(sql.String(50), nullable=True)
    count = Column(sql.Integer, nullable=True)
    os = Column(sql.String(20), nullable=True)
    language = Column(sql.String(5), nullable=True)
    version = Column(sql.String(120), nullable=True)

    product = orm.relationship("Product", back_populates="downloads")
    files = orm.relationship(
        "DlFile", back_populates="download", lazy="joined",
        cascade="all, delete-orphan")

    @property
    def type_name(self):
        return names.dl_types.get(self.type, self.type)

    @property
    def language_name(self):
        return names.languages.get(self.language, self.language)

    @property
    def bonus_type_name(self):
        return names.bonus_types.get(self.bonus_type, self.bonus_type)

    def __repr__(self):
        return "<Download(id={}, prod_id={}, slug='{}')>".format(
            self.id, self.prod_id, self.slug)

class Product(Base):
    __tablename__ = "products"

    id = Column(sql.Integer, primary_key=True, autoincrement=False)

    title = Column(sql.String(120), nullable=False)
    slug = Column(sql.String(120), nullable=False)
    title_norm = Column(sql.String(120), nullable=False)
    forum_id = Column(sql.String(120), nullable=False)

    product_type = Column(sql.String(20), nullable=False)
    is_secret = Column(sql.Boolean, nullable=False)
    is_price_visible = Column(sql.Boolean, nullable=False)
    can_be_reviewed = Column(sql.Boolean, nullable=False)
    base_prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), nullable=True)

    cs_windows = Column(sql.Boolean, nullable=False)
    cs_mac = Column(sql.Boolean, nullable=False)
    cs_linux = Column(sql.Boolean, nullable=False)

    os_windows = Column(sql.Boolean, nullable=False)
    os_mac = Column(sql.Boolean, nullable=False)
    os_linux = Column(sql.Boolean, nullable=False)

    is_coming_soon = Column(sql.Boolean, nullable=False)
    is_pre_order = Column(sql.Boolean, nullable=False)
    release_date = Column(sql.Date, nullable=True)
    development_active = Column(sql.Boolean, nullable=False)

    age_esrb = Column(sql.SmallInteger, nullable=True)
    age_pegi = Column(sql.SmallInteger, nullable=True)
    age_usk = Column(sql.SmallInteger, nullable=True)

    rating = Column(sql.SmallInteger, nullable=False)
    votes_count = Column(sql.Integer, nullable=False)
    reviews_count = Column(sql.Integer, nullable=False)

    developer_slug = Column(
        sql.String(120), sql.ForeignKey("companies.slug"), nullable=False)
    publisher_slug = Column(
        sql.String(120), sql.ForeignKey("companies.slug"), nullable=False)

    image_background = Column(sql.String(64), nullable=False)
    image_logo = Column(sql.String(64), nullable=False)
    image_icon = Column(sql.String(64), nullable=True)

    description_full = Column(sql.Text, nullable=True)
    description_cool = Column(sql.Text, nullable=True)

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
    downloads = orm.relationship(
        "Download", back_populates="product", cascade="all, delete-orphan")
    pricehistory = orm.relationship(
        "PriceRecord", back_populates="product", cascade="all, delete-orphan",
        order_by="PriceRecord.date")

    @property
    def product_type_name(self):
        return names.prod_types.get(self.product_type, self.product_type)

    @property
    def cs_systems(self):
        systems = []
        if self.cs_windows:
            systems.append("windows")
        if self.cs_mac:
            systems.append("mac")
        if self.cs_linux:
            systems.append("linux")
        return systems

    @property
    def systems(self):
        systems = []
        if self.os_windows:
            systems.append("windows")
        if self.os_mac:
            systems.append("mac")
        if self.os_linux:
            systems.append("linux")
        return systems

    @property
    def release_arrow(self):
        if self.release_date is not None:
            return arrow.Arrow.fromdate(self.release_date)
        else:
            return None

    def __repr__(self):
        return "<Product(id={}, slug='{}')>".format(self.id, self.slug)
