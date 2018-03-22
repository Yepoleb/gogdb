import itertools

import flask
from sqlalchemy import orm

from gogdb import app, db, model
from gogdb.views.pagination import calc_pageinfo

ITEMS_PER_PAGE = 100


def changelog_ext_page(view):
    page = int(flask.request.args.get("page", "1"))
    total_entries = db.session.query(model.ChangeRecord.id).count()
    page_info = calc_pageinfo(page, total_entries, ITEMS_PER_PAGE)

    changes = db.session.query(
        model.ChangeRecord
    ).options(
        orm.subqueryload(
            "product"
        ).subqueryload(
            "downloads"
        )
    ).order_by(
        model.ChangeRecord.id.desc()
    ).offset(page_info["from"]).limit(ITEMS_PER_PAGE)

    page_info["prev_link"] = flask.url_for(
        view, page=page_info["page"] - 1)
    page_info["next_link"] = flask.url_for(
        view, page=page_info["page"] + 1)

    recordgroups = []
    for groupkey, items in itertools.groupby(
            changes, key=lambda record: (record.timestamp, record.prod_id)):
        recordgroups.append(list(items))


    if view == "changelog_atom":
        response = flask.make_response(flask.render_template(
            "changelog_ext.xml",
            changes=recordgroups,
            page_info=page_info
        ))
        response.mimetype = "application/atom+xml"
        return response

    else:
        return flask.render_template(
            "changelog_ext.html",
            changes=recordgroups,
            page_info=page_info
        )

@app.route("/changelog_ext.xml")
def changelog_atom():
    return changelog_ext_page("changelog_atom")

@app.route("/changelog_ext")
def changelog_ext():
    return changelog_ext_page("changelog_ext")
