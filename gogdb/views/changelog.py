import flask
import sqlalchemy

from gogdb import app, db, model
from gogdb.model import ChangeRecord
from gogdb.views.pagination import calc_pageinfo

ITEMS_PER_PAGE = 100


@app.route("/changelog")
def changelog():
    page = int(flask.request.args.get("page", "1"))

    # Get total number of entries
    total_entries = db.session.query(
        ChangeRecord.timestamp # just a placeholder
    ).group_by(
        ChangeRecord.timestamp, ChangeRecord.type_prim, ChangeRecord.prod_id
    ).count()

    page_info = calc_pageinfo(page, total_entries, ITEMS_PER_PAGE)

    changes = db.session.query(
        ChangeRecord.timestamp, ChangeRecord.type_prim, ChangeRecord.prod_id,
        sqlalchemy.sql.functions.max(model.Product.title).label("title")
    ).join(
        model.Product
    ).group_by(
        ChangeRecord.timestamp, ChangeRecord.type_prim, ChangeRecord.prod_id
    ).order_by(
        ChangeRecord.timestamp.desc()
    ).offset(page_info["from"]).limit(ITEMS_PER_PAGE)

    page_info["prev_link"] = flask.url_for(
        "changelog", page=page_info["page"] - 1)
    page_info["next_link"] = flask.url_for(
        "changelog", page=page_info["page"] + 1)

    return flask.render_template(
        "changelog.html", changes=changes, page_info=page_info)

