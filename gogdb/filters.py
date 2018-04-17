import jinja2

from gogdb import app


OS_ICON_ELEMENTS = {
    "windows": '<i class="fa fa-windows" aria-hidden="true"></i>' \
        '<span class="nocss">W</span>',
    "mac": '<i class="fa fa-apple" aria-hidden="true"></i>' \
        '<span class="nocss">M</span>',
    "linux": '<i class="fa fa-linux" aria-hidden="true"></i>' \
        '<span class="nocss">L</span>'
}

NUM_IMAGE_HOSTS = 4


@app.template_filter("yes_no")
def format_yes_no(value):
    if isinstance(value, jinja2.Undefined):
        return value
    else:
        return ["No", "Yes"][bool(value)]

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
