import quart
import bleach

from gogdb.application.datasources import get_storagedb


ALLOWED_TAGS = [
    "a", "abbr", "acronym", "b", "blockquote", "br", "code", "del", "em",
    "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "li", "ol", "p", "pre", "strong", "ul"
]

ALLOWED_ATTRIBUTES = ["href", "alt", "title", "src", "start"]

async def releasenotes(prod_id):
    storagedb = get_storagedb()
    product = await storagedb.product.load(prod_id)

    if product is None or not product.changelog:
        quart.abort(404)

    sanitized_html = quart.Markup(bleach.clean(
        product.changelog, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip_comments=False
    ))

    return await quart.render_template("releasenotes.html", product=product, sanitized_html=sanitized_html)
