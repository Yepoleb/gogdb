import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy import Column

from gogdb.legacy.database import Base
from gogdb.legacy.model.common import get_systems_list, set_systems_list



FILEFLAGS = ["executable", "hidden", "support"]

def get_fileflags(self):
    value = []
    for flagname in FILEFLAGS:
        if getattr(self, "f_" + flagname):
            value.append(flagname)
    return value

def set_fileflags(self, value):
    for flagname in FILEFLAGS:
        if flagname in value:
            setattr(self, "f_" + flagname, True)
        else:
            setattr(self, "f_" + flagname, False)


class Build(Base):
    __tablename__ = "build"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    build_id = Column(sql.BigInteger, nullable=False)
    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), nullable=False)
    os = Column(sql.String(20), nullable=False)
    version = Column(sql.String(100), nullable=True)
    public = Column(sql.Boolean, nullable=False)
    date_published = Column(sql.DateTime, nullable=False)
    generation = Column(sql.SmallInteger, nullable=False)
    meta_id = Column(sql.String(32), nullable=True)
    legacy_build_id = Column(sql.Integer, nullable=True)
    deleted = Column(sql.Boolean, default=False, nullable=False)

    product = orm.relationship("Product", back_populates="builds")
    tags_rel = orm.relationship(
        "BuildTag", cascade="all, delete-orphan")
    repo_v1 = orm.relationship(
        "RepositoryV1", uselist=False, back_populates="build",
        cascade="all, delete-orphan")
    repo_v2 = orm.relationship(
        "RepositoryV2", uselist=False, back_populates="build",
        cascade="all, delete-orphan")

    @property
    def repo(self):
        if self.generation == 1:
            return self.repo_v1
        else:
            return self.repo_v2

    @repo.setter
    def repo(self, value):
        if self.generation == 1:
            self.repo_v1 = value
        else:
            self.repo_v2 = value

    @property
    def has_repo(self):
        return (self.meta_id or self.legacy_build_id)

    @property
    def tags(self):
        return [tag.name for tag in self.tags_rel]

    @tags.setter
    def tags(self, value):
        self.tags_rel = [BuildTag(name=name) for name in value]

    def __repr__(self):
        if self.generation == 1:
            return "<Build(id={!r}, prod_id={!r}, legacy_build_id={!r})>" \
                .format(self.id, self.prod_id, self.legacy_build_id)
        else:
            return "<Build(id={!r}, prod_id={!r}, meta_id={!r})>" \
                .format(self.id, self.prod_id, self.meta_id)

class BuildTag(Base):
    __tablename__ = "buildtag"

    build_id = Column(
        sql.Integer, sql.ForeignKey("build.id"), primary_key=True)
    name = Column(sql.String(100), primary_key=True)


### V1

class RepositoryV1(Base):
    __tablename__ = "repository_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    build_id = Column(
        sql.Integer, sql.ForeignKey("build.id"), nullable=False)
    timestamp = Column(sql.Integer, nullable=False)
    install_directory = Column(sql.String(1024), nullable=False)
    base_prod_id = Column(sql.Integer, nullable=False)
    name = Column(sql.String(120), nullable=False)

    depots = orm.relationship("DepotV1", cascade="all, delete-orphan")
    redists = orm.relationship("RedistV1", cascade="all, delete-orphan")
    support_commands = orm.relationship(
        "SupportCmdV1", cascade="all, delete-orphan")
    products = orm.relationship(
        "RepositoryProdV1", cascade="all, delete-orphan")
    build = orm.relationship("Build", back_populates="repo_v1")

class RedistV1(Base):
    __tablename__ = "redist_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v1.id"),
        nullable=False)
    redist = Column(sql.String(120), nullable=False)
    executable = Column(sql.String(1024), nullable=True)
    argument = Column(sql.String(120), nullable=True)

class SupportCmdV1(Base):
    __tablename__ = "supportcmd_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v1.id"),
        nullable=False)
    executable = Column(sql.String(1024), nullable=False)
    prod_id = Column(sql.Integer, nullable=False)
    os = Column(sql.String(20), nullable=False)
    lang = Column(sql.String(20), primary_key=True)

class DepotV1(Base):
    __tablename__ = "depot_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v1.id"),
        nullable=False)
    manifest_id = Column(
        sql.Integer, sql.ForeignKey("depotmanifest_v1.id"),
        nullable=False)
    size = Column(sql.BigInteger, nullable=True)
    os = Column(sql.String(20), nullable=False)

    languages_rel = orm.relationship(
        "DepotLangV1", cascade="all, delete-orphan")
    prod_ids_rel = orm.relationship(
        "DepotProdV1", cascade="all, delete-orphan")
    manifest = orm.relationship("DepotManifestV1", cascade="all")

    @property
    def languages(self):
        return [lang.lang for lang in self.languages_rel]

    @languages.setter
    def languages(self, value):
        self.languages_rel = [DepotLangV1(lang=lang) for lang in value]

    @property
    def prod_ids(self):
        return [prod_id.prod_id for prod_id in self.prod_ids_rel]

    @prod_ids.setter
    def prod_ids(self, value):
        self.prod_ids_rel = [DepotProdV1(prod_id=prod_id) for prod_id in value]

class DepotLangV1(Base):
    __tablename__ = "depotlang_v1"

    depot_id = Column(
        sql.Integer, sql.ForeignKey("depot_v1.id"), primary_key=True)
    lang = Column(sql.String(20), primary_key=True)

class DepotManifestV1(Base):
    __tablename__ = "depotmanifest_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    manifest_id = Column(sql.String(40), unique=True, nullable=False)
    name = Column(sql.String(120), nullable=True)
    loaded = Column(sql.Boolean, default=False, nullable=False)

    files = orm.relationship(
        "DepotFileV1", order_by="DepotFileV1.path",
        cascade="all, delete-orphan")
    dirs = orm.relationship(
        "DepotDirectoryV1", order_by="DepotDirectoryV1.path",
        cascade="all, delete-orphan")
    links = orm.relationship(
        "DepotLinkV1", order_by="DepotLinkV1.path",
        cascade="all, delete-orphan")

class DepotProdV1(Base):
    __tablename__ = "depotprod_v1"

    depot_id = Column(
        sql.Integer, sql.ForeignKey("depot_v1.id"), primary_key=True)
    prod_id = Column(sql.Integer, primary_key=True)

class DepotFileV1(Base):
    __tablename__ = "depotfile_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    manifest_id = Column(
        sql.Integer, sql.ForeignKey("depotmanifest_v1.id"),
        index=True, nullable=False)
    path = Column(sql.String(1024), nullable=False)
    size = Column(sql.BigInteger, nullable=False)
    checksum = Column(sql.String(40), nullable=True)
    url = Column(sql.String(1024), nullable=True)
    offset = Column(sql.BigInteger, nullable=True)
    f_executable = Column(sql.Boolean, nullable=False)
    f_hidden = Column(sql.Boolean, nullable=False)
    f_support = Column(sql.Boolean, nullable=False)

    flags = property(get_fileflags, set_fileflags)

    def __iter__(self):
        fields = [
            "manifest_id", "path", "size", "checksum", "url", "offset",
            "f_executable", "f_hidden", "f_support"]
        for fieldname in fields:
            yield (fieldname, getattr(self, fieldname))

class DepotDirectoryV1(Base):
    __tablename__ = "depotdir_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    manifest_id = Column(
        sql.Integer, sql.ForeignKey("depotmanifest_v1.id"),
        nullable=False)
    path = Column(sql.String(1024), nullable=False)
    f_support = Column(sql.Boolean, nullable=False)

    @property
    def flags(self):
        if self.f_support:
            return ["support"]
        else:
            return []

    @flags.setter
    def flags(self, value):
        self.f_support = "support" in value

    def __iter__(self):
        for fieldname in ["manifest_id", "path", "f_support"]:
            yield (fieldname, getattr(self, fieldname))

class DepotLinkV1(Base):
    __tablename__ = "depotlink_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    manifest_id = Column(
        sql.Integer, sql.ForeignKey("depotmanifest_v1.id"),
        nullable=False)
    path = Column(sql.String(1024), nullable=False)
    target = Column(sql.String(1024), nullable=False)
    is_directory = Column(sql.Boolean, nullable=False)

    def __iter__(self):
        for fieldname in ["manifest_id", "path", "target", "is_directory"]:
            yield (fieldname, getattr(self, fieldname))

class RepositoryProdV1(Base):
    __tablename__ = "repositoryprod_v1"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v1.id"),
        nullable=False)
    dependency = Column(sql.Integer, nullable=True)
    name = Column(sql.String(120), nullable=False)
    prod_id = Column(sql.Integer, nullable=False)


### V2

class RepositoryV2(Base):
    __tablename__ = "repository_v2"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    build_id = Column(
        sql.Integer, sql.ForeignKey("build.id"), nullable=False)
    base_prod_id = Column(sql.Integer, nullable=False)
    client_id = Column(sql.String(20), nullable=True)
    client_secret = Column(sql.String(64), nullable=True)
    install_directory = Column(sql.String(1024), nullable=False)
    os = Column(sql.String(20), nullable=False)

    cloudsaves = orm.relationship(
        "CloudSaveV2", cascade="all, delete-orphan")
    dependencies_rel = orm.relationship(
        "DependencyV2", cascade="all, delete-orphan")
    depots = orm.relationship(
        "DepotV2", cascade="all, delete-orphan")
    products = orm.relationship(
        "RepositoryProdV2", cascade="all, delete-orphan")
    tags_rel = orm.relationship(
        "RepositoryTagV2", cascade="all, delete-orphan")
    build = orm.relationship("Build", back_populates="repo_v2")

    @property
    def tags(self):
        return [tag.name for tag in self.tags_rel]

    @tags.setter
    def tags(self, value):
        self.tags_rel = [RepositoryTagV2(name=name) for name in value]

    @property
    def dependencies(self):
        return [dep.name for dep in self.dependencies_rel]

    @dependencies.setter
    def dependencies(self, value):
        self.dependencies_rel = [DependencyV2(name=name) for name in value]

    @property
    def scripted_prods(self):
        return [
            repoprod for repoprod in self.products
            if repoprod.script or repoprod.temp_executable]

class CloudSaveV2(Base):
    __tablename__ = "cloudsave_v2"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v2.id"),
        nullable=False)
    location = Column(sql.String(1024), nullable=False)
    name = Column(sql.String(1024), nullable=False)

class DependencyV2(Base):
    __tablename__ = "dependency_v2"

    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v2.id"),
        primary_key=True)
    name = Column(sql.String(100), primary_key=True)

class RepositoryProdV2(Base):
    __tablename__ = "repositoryprod_v2"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v2.id"),
        nullable=False)
    name = Column(sql.String(120), nullable=False)
    prod_id = Column(sql.Integer, nullable=False)
    script = Column(sql.String(100), nullable=True)
    temp_executable = Column(sql.String(1024), nullable=False)

class RepositoryTagV2(Base):
    __tablename__ = "repositorytag_v2"

    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v2.id"),
        primary_key=True)
    name = Column(sql.String(100), primary_key=True)

class DepotV2(Base):
    __tablename__ = "depot_v2"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        sql.Integer, sql.ForeignKey("repository_v2.id"),
        nullable=False)
    manifest_id = Column(
        sql.Integer, sql.ForeignKey("depotmanifest_v2.id"),
        nullable=False)
    size = Column(sql.BigInteger, nullable=False)
    prod_id = Column(sql.Integer, nullable=False)
    is_gog_depot = Column(sql.Boolean, nullable=False)
    #bitness = Column(sql.String(50), nullable=True)
    bitness_32 = Column(sql.Boolean, nullable=True)
    bitness_64 = Column(sql.Boolean, nullable=True)
    is_offline = Column(sql.Boolean, nullable=False)

    languages_rel = orm.relationship(
        "DepotLangV2", cascade="all, delete-orphan")
    manifest = orm.relationship("DepotManifestV2", cascade="all")

    @property
    def languages(self):
        return [lang.lang for lang in self.languages_rel]

    @languages.setter
    def languages(self, value):
        self.languages_rel = [DepotLangV2(lang=lang) for lang in value]

    @property
    def bitness(self):
        values = []
        if self.bitness_32 is True: values.append("32")
        if self.bitness_32 is False: values.append("!32")
        if self.bitness_64 is True: values.append("64")
        if self.bitness_64 is False: values.append("!64")
        return values

    @bitness.setter
    def bitness(self, values):
        self.bitness_32 = None
        self.bitness_64 = None
        if values is None:
            return

        if "32" in values: self.bitness_32 = True
        elif "!32" in values: self.bitness_32 = False
        if "64" in values: self.bitness_64 = True
        if "!64" in values: self.bitness_64 = False

class DepotLangV2(Base):
    __tablename__ = "depotlang_v2"

    depot_id = Column(
        sql.Integer, sql.ForeignKey("depot_v2.id"), primary_key=True)
    lang = Column(sql.String(20), primary_key=True)

class DepotManifestV2(Base):
    __tablename__ = "depotmanifest_v2"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    manifest_id = Column(sql.String(32), unique=True, nullable=False)
    loaded = Column(sql.Boolean, default=False, nullable=False)

    files = orm.relationship(
        "DepotFileV2", cascade="all, delete-orphan")
    dirs = orm.relationship(
        "DepotDirectoryV2", cascade="all, delete-orphan")
    links = orm.relationship(
        "DepotLinkV2", cascade="all, delete-orphan")

class DepotFileV2(Base):
    __tablename__ = "depotfile_v2"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    manifest_id = Column(
        sql.Integer, sql.ForeignKey("depotmanifest_v2.id"),
        index=True, nullable=False)
    path = Column(sql.String(1024), nullable=False)
    size = Column(sql.BigInteger, nullable=False)
    sfc_offset = Column(sql.BigInteger, nullable=True)
    sfc_size = Column(sql.Integer, nullable=True)
    checksum = Column(sql.String(32), nullable=True)
    f_executable = Column(sql.Boolean, nullable=False)
    f_hidden = Column(sql.Boolean, nullable=False)
    f_support = Column(sql.Boolean, nullable=False)

    flags = property(get_fileflags, set_fileflags)

    def __iter__(self):
        fields = [
            "manifest_id", "path", "size", "sfc_offset", "sfc_size",
            "checksum", "f_executable", "f_hidden", "f_support"]
        for fieldname in fields:
            yield (fieldname, getattr(self, fieldname))

class DepotDirectoryV2(Base):
    __tablename__ = "depotdir_v2"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    manifest_id = Column(
        sql.Integer, sql.ForeignKey("depotmanifest_v2.id"),
        nullable=False)
    path = Column(sql.String(1024), nullable=False)

    def __iter__(self):
        for fieldname in ["manifest_id", "path"]:
            yield (fieldname, getattr(self, fieldname))

class DepotLinkV2(Base):
    __tablename__ = "depotlink_v2"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    manifest_id = Column(
        sql.Integer, sql.ForeignKey("depotmanifest_v2.id"),
        nullable=False)
    path = Column(sql.String(1024), nullable=False)
    target = Column(sql.String(1024), nullable=False)

    def __iter__(self):
        for fieldname in ["manifest_id", "path", "target"]:
            yield (fieldname, getattr(self, fieldname))
