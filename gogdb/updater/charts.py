import datetime
import gzip
import math

import pygal
from lxml.etree import ElementTree, Element, tostring
import aiofiles

from gogdb.updater.charts_css import CHARTS_CSS


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
        dataseries = list(zip(dataseries_x, dataseries_y))
        max_price = max(filter(lambda x: x is not None, dataseries_y))
        range_top = int(math.ceil(max_price / 10) * 10)

        chart = pygal.DateLine()
        chart.width = 1000
        chart.height = 300
        chart.show_legend = False
        chart.range = (0, range_top)  # Round to nearest multiple of 10
        chart.max_scale = 6
        chart.include_x_axis = True
        chart.value_formatter = lambda p: "${:.2f}".format(p)
        chart.dots_size = 3
        chart.show_x_guides = True
        chart.js = []
        chart.css = []
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
            await aiofiles.os.makedirs(chart_path.parent, exist_ok=True)
            async with aiofiles.open(chart_path, "wb") as fobj:
                await fobj.write(chart_compressed)

    async def finish(self):
        pass
