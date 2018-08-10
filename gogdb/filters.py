import jinja2
import flask

from gogdb import app


OS_ICON_ELEMENTS = {
    "windows": '<i class="fa fa-windows" aria-hidden="true"></i>' \
        '<span class="nocss">W</span>',
    "mac": '<i class="fa fa-apple" aria-hidden="true"></i>' \
        '<span class="nocss">M</span>',
    "linux": '<i class="fa fa-linux" aria-hidden="true"></i>' \
        '<span class="nocss">L</span>'
}

YESNO_ICON_ELEMENTS = [
    jinja2.Markup(
        '<i class="fa fa-times" aria-hidden="true">'
        '</i><span class="nocss">No</span>'),
    jinja2.Markup(
        '<i class="fa fa-check" aria-hidden="true">'
        '</i><span class="nocss">Yes</span>')
]

NUM_IMAGE_HOSTS = 4


@app.template_filter("yes_no")
def format_yes_no(value):
    if isinstance(value, jinja2.Undefined):
        return value
    else:
        return YESNO_ICON_ELEMENTS[bool(value)]

@app.template_filter("os_icon")
def os_icon(system):
    return jinja2.Markup(OS_ICON_ELEMENTS[system])

@app.template_filter("os_icons")
def os_icons(systems):
    if systems is None:
        return "N/A"
    icons = []
    for system in systems:
        icons.append(OS_ICON_ELEMENTS[system])
    if icons:
        return jinja2.Markup(" ".join(icons))
    else:
        return "N/A"


def iter_attr(attr_name, objects):
    for obj in objects:
        yield getattr(obj, attr_name)

@app.template_filter("comma_attr")
def comma_attr(objects, attr_name):
    return ", ".join(sorted(iter_attr(attr_name, objects)))


@app.template_filter("gog_image")
def gog_image(image_id, extension):
    host_num = hash(image_id) % NUM_IMAGE_HOSTS + 1
    return "https://images-{}.gog.com/{}{}".format(
        host_num, image_id, extension)


@app.template_filter("gog_meta")
def gog_meta(meta_id):
    return "https://cdn.gog.com/content-system/v2/meta/{}/{}/{}".format(
        meta_id[0:2], meta_id[2:4], meta_id)

@app.template_filter("prod_url")
def prod_url(prod_id):
    url = flask.url_for("product_info", prod_id=prod_id)
    return jinja2.Markup('<a class="hoveronly" href="{}">{}</a>'.format(
        jinja2.escape(url), prod_id))

@app.template_filter("prod_urls")
def prod_urls(prod_ids):
    return jinja2.Markup(
        ", ".join(prod_url(prod_id) for prod_id in prod_ids))


FILEFLAGS = ["executable", "hidden", "support"]
FLAGLETTERS = ['X', 'H', 'S']
@app.template_filter("fileflags")
def fileflags(flags):
    setflags = ['-', '-', '-']
    for i, flagname in enumerate(FILEFLAGS):
        if flagname in flags:
            setflags[i] = FLAGLETTERS[i]
    return "".join(setflags)
