import sqlalchemy as sql
from sqlalchemy import orm
from sqlalchemy import Column

from legacy.database import Base


class PriceRecord(Base):
    __tablename__ = "pricerecords"

    id = Column(sql.Integer, primary_key=True, autoincrement=True)
    prod_id = Column(sql.Integer, sql.ForeignKey("products.id"), nullable=False)
    price_base = Column(sql.Numeric, nullable=True)
    price_final = Column(sql.Numeric, nullable=True)
    date = Column(sql.DateTime, nullable=False)

    product = orm.relationship("Product", back_populates="pricehistory")

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

    def same_price(self, other):
        return (
            (self.price_base == other.price_base) and
            (self.price_final == other.price_final)
        )

    def __repr__(self):
        return "<PriceRecord(id={}, prod_id={}, date='{}')>".format(
            self.id, self.prod_id, self.date)
