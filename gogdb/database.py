import sqlalchemy
import flask_sqlalchemy

from gogdb import app


NAMING_CONVENTION = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = sqlalchemy.MetaData(naming_convention=NAMING_CONVENTION)
db = flask_sqlalchemy.SQLAlchemy(app, metadata=metadata)
