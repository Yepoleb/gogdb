import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy import Column

from arrow import arrow

from gogdb import db


class PriceRecord(db.Model):
    __tablename__ = "pricerecords"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    prod_id = Column(sql.Integer, sql.ForeignKey("products.id"), nullable=False)
    price_base = Column(sql.Numeric, nullable=True)
    price_final = Column(sql.Numeric, nullable=True)
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
        elif self.price_final is None or self.price_base is None:
            return None
        else:
            price_fract = self.price_final / self.price_base

        discount_rounded = round((1 - price_fract) * 100)
        if (discount_rounded % 10) == 9:
            discount_rounded += 1
        elif (discount_rounded % 10) == 1:
            discount_rounded -= 1
        return discount_rounded

    def same_price(self, other):
        return (
            (self.price_base == other.price_base) and
            (self.price_final == other.price_final)
        )

    def __repr__(self):
        return "<PriceRecord(id={}, prod_id={}, date='{}')>".format(
            self.id, self.prod_id, self.date)
