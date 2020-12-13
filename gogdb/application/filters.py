import jinja2
import flask

import gogdb.core.names as names



def yes_no(value):
    if isinstance(value, jinja2.Undefined):
        return value
    if value:
        return jinja2.Markup(
            '<i class="fa fa-check" aria-hidden="true"></i>'
            '<span class="nocss">Yes</span>')
    else:
        return jinja2.Markup(
            '<i class="fa fa-times" aria-hidden="true"></i>'
            '<span class="nocss">No</span>')

OS_ICON_ELEMENTS = {
    "windows": '<i class="fa fa-windows" aria-hidden="true"></i>' \
        '<span class="nocss">W</span>',
    "osx": '<i class="fa fa-apple" aria-hidden="true"></i>' \
        '<span class="nocss">M</span>',
    "linux": '<i class="fa fa-linux" aria-hidden="true"></i>' \
        '<span class="nocss">L</span>'
}

def os_icon(system):
    return jinja2.Markup(OS_ICON_ELEMENTS[system])

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

def os_name(system):
    return {"windows": "Windows", "osx": "Mac", "linux": "Linux"}[system]

def os_names(systems):
    return ", ".join(os_name(s) for s in systems)

def comma_attr(objects, attr_name):
    return ", ".join(sorted(
        getattr(obj, attr_name) for obj in objects
    ))

def gog_image(image_id, extension):
    if not image_id:
        return None
    return "https://images.gog.com/{}{}".format(image_id, extension)


def gog_meta(meta_id):
    return "https://cdn.gog.com/content-system/v2/meta/{}/{}/{}".format(
        meta_id[0:2], meta_id[2:4], meta_id)

def prod_url(prod_id):
    return "{}/product/{}".format(flask.request.script_root, prod_id)

def prod_anchor(prod_id):
    url = prod_url(prod_id=prod_id)
    return jinja2.Markup('<a class="hoveronly" href="{}">{}</a>'.format(
        jinja2.escape(url), prod_id))

def prod_type(type_slug):
    return names.PROD_TYPES[type_slug]

def bonus_type(type_slug):
    return names.BONUS_TYPES[type_slug]

def download_type(type_slug):
    return names.DL_TYPES[type_slug]

def property_name(name):
    return {
        "title": "Title",
        "comp_systems": "Systems",
        "is_pre_order": "Is Preorder",
        "changelog": "Changelog",
        "access": "Access"
    }[name]

def datetime_day(dt):
    """Format datetime to day accuracy"""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d")

def datetime_minute(dt):
    """Format datetime to minute accuracy"""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M")

def makeanchor(url):
    if not url:
        return None
    return flask.Markup('<a href="{0}">{0}</a>'.format(flask.escape(url)))

def nodata(value):
    """Replace a value of None or empty string with 'No data'"""
    if value is None or value == "":
        return "No data"
    else:
        return value

def videoid(video):
    if video.provider == "youtube":
        return video.thumbnail_url.split("/")[4]

def add_filters(app):
    app.add_template_filter(yes_no)
    app.add_template_filter(os_icon)
    app.add_template_filter(os_icons)
    app.add_template_filter(os_name)
    app.add_template_filter(os_names)
    app.add_template_filter(comma_attr)
    app.add_template_filter(gog_image)
    app.add_template_filter(gog_meta)
    app.add_template_global(prod_url)
    app.add_template_filter(prod_anchor)
    app.add_template_filter(prod_type)
    app.add_template_filter(bonus_type)
    app.add_template_filter(download_type)
    app.add_template_filter(property_name)
    app.add_template_filter(datetime_day)
    app.add_template_filter(datetime_minute)
    app.add_template_filter(makeanchor)
    app.add_template_filter(nodata)
    app.add_template_filter(videoid)
