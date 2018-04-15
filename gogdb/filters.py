import jinja2

from gogdb import app


OS_ICON_ELEMENTS = {
    "windows": '<i class="fa fa-windows" aria-hidden="true"></i>',
    "mac": '<i class="fa fa-apple" aria-hidden="true"></i>',
    "linux": '<i class="fa fa-linux" aria-hidden="true"></i>'
}

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
    icons = []
    for system in systems:
        icons.append(OS_ICON_ELEMENTS[system])
    return jinja2.Markup(" ".join(icons))


def iter_attr(attr_name, objects):
    for obj in objects:
        yield getattr(obj, attr_name)

@app.template_filter("comma_attr")
def comma_attr(objects, attr_name):
    return ", ".join(sorted(iter_attr(attr_name, objects)))
