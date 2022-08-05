import datetime
import gzip
import math
import os

import pygal
from lxml.etree import ElementTree, Element, tostring
import aiofiles

from gogdb.updater.charts_css import CHARTS_CSS


def calculate_y_scale(min_val, max_val, steps_pref):
    """
    Keep trying the step values in step_pref in order to see if they divide without remainder.
    If none of them does, increase max_val by 1 and try again.
    """
    # Rounding to integer values because prices are decimal and rounding makes nicer scales
    min_int = int(math.floor(min_val))
    max_int = int(math.ceil(max_val))
    if max_int == 0:
        max_int = 1
    found_steps = None
    while True:
        diff = max_int - min_int
        for steps in steps_pref:
            if diff % steps == 0:
                found_steps = steps
                break
        if found_steps is not None:
            break
        else:
            max_int += 1
    return list(range(min_int, max_int + 1, diff // found_steps))

def calculate_x_scale(first_day, last_day, max_steps):
    """
    Get a scale using only months with consistent step size.
    Keeps increasing the step size by 1 until the number of months is lower than max_steps
    """
    first_month = first_day.year * 12 + first_day.month - 1  # subtract 1 to make month zero indexed
    last_month = last_day.year * 12 + last_day.month - 1 + 1
    num_months = last_month - first_month
    step_size = 1
    while num_months // step_size > 10:
        step_size += 1
    scale = []
    for month_num in range(first_month, last_month + 1, step_size):
        scale.append(datetime.date(month_num // 12, month_num % 12 + 1, 1))
    return scale

def date_to_timestamp(date):
    return datetime.datetime.combine(date, datetime.time(0, 0, 0), tzinfo=datetime.timezone.utc) \
        .timestamp()

def format_date_timestamp(ts):
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime("%Y-%m-%d")


class ChartsProcessor:
    wants = {"prices"}

    def __init__(self, db):
        self.db = db

    async def prepare(self, num_ids):
        pass

    async def process(self, data):
        if data.prices is None or not data.prices["US"]["USD"]:
            return

        dataseries_x = []
        dataseries_y = []

        for entry in data.prices["US"]["USD"]:
            if dataseries_y:
                dataseries_y.append(dataseries_y[-1])
                dataseries_x.append(entry.date)
            if entry.price_final is None:
                dataseries_y.append(None)
                dataseries_x.append(entry.date)
            else:
                price_final = entry.price_final / 100
                dataseries_y.append(price_final)
                dataseries_x.append(entry.date)

        now_ts = datetime.datetime.now(datetime.timezone.utc).date()
        dataseries_y.append(dataseries_y[-1])
        dataseries_x.append(now_ts)
        dataseries_x_ts = [date_to_timestamp(x) for x in dataseries_x]
        dataseries = list(zip(dataseries_x_ts, dataseries_y))
        max_price = max(filter(lambda x: x is not None, dataseries_y))

        y_scale = calculate_y_scale(0, max_price, steps_pref=[5, 4, 6])
        x_scale = calculate_x_scale(dataseries_x[0], dataseries_x[-1], max_steps=10)
        x_scale_ts = [date_to_timestamp(d) for d in x_scale]

        chart = pygal.XY()
        chart.width = 1000
        chart.height = 300
        chart.show_legend = False
        chart.range = (0, y_scale[-1])
        chart.include_x_axis = True
        chart.value_formatter = lambda p: "${:.2f}".format(p)
        chart.x_value_formatter = format_date_timestamp
        chart.dots_size = 3
        chart.show_x_guides = True
        chart.js = []
        chart.css = []
        chart.y_labels = y_scale
        chart.x_labels = x_scale_ts
        chart.add("Price", dataseries, allow_interruptions=True)

        chart_etree = chart.render_tree()

        # Replace default css with custom version
        defs = chart_etree.find("defs")
        defs.clear()
        style_el = Element("style", {"type": "text/css"})
        style_el.text = CHARTS_CSS
        defs.append(style_el)

        # Remove useless dots description elements
        for dots_el in chart_etree.iterfind(".//g[@class='dots']"):
            for desc_el in dots_el.findall("./desc"):
                if desc_el.attrib["class"] != "value":
                    dots_el.remove(desc_el)

        chart_xml = ElementTree(chart_etree)
        #chart_xml.write("figure.svg", encoding="utf-8", xml_declaration=True, pretty_print=False)
        chart_bytes = tostring(chart_xml, encoding="utf-8", xml_declaration=True, pretty_print=False)
        chart_compressed = gzip.compress(chart_bytes)
        chart_path = self.db.path_chart(data.id)
        try:
            async with aiofiles.open(chart_path, "wb") as fobj:
                await fobj.write(chart_compressed)
        except FileNotFoundError:
            await os.makedirs(chart_path.parent, exist_ok=True)
            async with aiofiles.open(chart_path, "wb") as fobj:
                await fobj.write(chart_compressed)

    async def finish(self):
        pass
