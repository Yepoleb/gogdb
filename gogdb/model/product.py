import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy import Column

from arrow import arrow

from gogdb import db
from gogdb import names


class Product(db.Model):
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
        "Download", back_populates="product", cascade="all, delete-orphan",
        order_by="Download.type, desc(Download.os), Download.slug")
    pricehistory = orm.relationship(
        "PriceRecord", back_populates="product", cascade="all, delete-orphan",
        order_by="PriceRecord.date")
    changes = orm.relationship(
        "ChangeRecord", back_populates="product", cascade="all, delete-orphan",
        order_by="desc(ChangeRecord.id)")

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

    @property
    def valid_downloads(self):
        return [download for download in self.downloads
                if not download.deleted]

    def download_by_slug(self, slug):
        for download in self.downloads:
            if download.slug == slug:
                return download
        return None


    def __repr__(self):
        return "<Product(id={}, slug='{}')>".format(self.id, self.slug)


class Language(db.Model):
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


class Feature(db.Model):
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


class Genre(db.Model):
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


class Company(db.Model):
    __tablename__ = "companies"

    slug = Column(sql.String(120), primary_key=True)
    name = Column(sql.String(120), nullable=False)

    def __repr__(self):
        return "<Company(slug='{}', name='{}')>".format(self.slug, self.name)
