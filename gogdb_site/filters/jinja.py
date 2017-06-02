import jinja2

def format_yes_no(value):
    return "Yes" if value else "No"

def names_for(ids, names):
    return list(names[x] for x in ids)

def iter_attr(attr_name, objects):
    for obj in objects:
        yield getattr(obj, attr_name)

def comma_attr(attr_name, objects):
    return ", ".join(sorted(iter_attr(attr_name, objects)))

OS_ICON_ELEMENTS = {
    "windows": '<i class="fa fa-windows" aria-hidden="true"></i>',
    "mac": '<i class="fa fa-apple" aria-hidden="true"></i>',
    "linux": '<i class="fa fa-linux" aria-hidden="true"></i>'
}

def os_icon(system):
    return jinja2.Markup(OS_ICON_ELEMENTS[system])

def os_icons(systems):
    icons = []
    for system in systems:
        icons.append(OS_ICON_ELEMENTS[system])
    return jinja2.Markup(" ".join(icons))
