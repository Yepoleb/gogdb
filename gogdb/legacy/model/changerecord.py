import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy import Column

from legacy.database import Base


class ChangeRecord(Base):
    __tablename__ = "changerecords"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    timestamp = Column(sql.DateTime, nullable=False)
    prod_id = Column(
        sql.Integer, sql.ForeignKey("products.id"), nullable=False)
    action = Column(sql.String(20), nullable=False)
    type_prim = Column(sql.String(40), nullable=False)
    type_sec = Column(sql.String(40), nullable=True)
    resource = Column(sql.String(120), nullable=False)
    old = Column(sql.String(120), nullable=True)
    new = Column(sql.String(120), nullable=True)

    @property
    def type(self):
        if self.type_sec:
            return self.type_prim + "."  + self.type_sec
        else:
            return self.type_prim

    @property
    def old_int(self):
        if self.old is not None:
            return int(self.old)
        else:
            return None

    @property
    def new_int(self):
        if self.new is not None:
            return int(self.new)
        else:
            return None

    @property
    def action_type(self):
        return self.action + " " + self.type

    @property
    def timestamp_arrow(self):
        return arrow.Arrow.fromdatetime(self.timestamp)

    product = orm.relationship("Product", back_populates="changes")
