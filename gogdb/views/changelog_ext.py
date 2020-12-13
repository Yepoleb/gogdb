import itertools
import datetime
import json

import flask

import gogdb.core.model as model
from gogdb.views.pagination import calc_pageinfo
from gogdb.application.datasources import get_indexdb
from gogdb.core.dataclsloader import class_from_json

ITEMS_PER_PAGE = 100


def changelog_ext_page(view):
    page = int(flask.request.args.get("page", "1"))

    cur = get_indexdb().cursor()
    # Get total number of entries
    cur.execute("SELECT COUNT(*) FROM changelog;")
    total_entries = cur.fetchone()[0]

    page_info = calc_pageinfo(page, total_entries, ITEMS_PER_PAGE)

    cur.execute(
        "SELECT * FROM changelog ORDER BY timestamp DESC LIMIT ? OFFSET ?;",
        (ITEMS_PER_PAGE, page_info["from"])
    )

    changes = []
    for change_res in cur:
        record_dict = json.loads(change_res["serialized_record"])
        change = model.IndexChange(
            id = change_res["product_id"],
            title = change_res["product_title"],
            timestamp = datetime.datetime.fromtimestamp(change_res["timestamp"], datetime.timezone.utc),
            action = change_res["action"],
            category = change_res["category"],
            dl_type = change_res["dl_type"],
            bonus_type = change_res["bonus_type"],
            property_name = change_res["property_name"],
            record = class_from_json(model.ChangeRecord, record_dict)
        )
        changes.append(change)

    recordgroups = []
    for groupkey, items in itertools.groupby(
            changes, key=lambda record: (record.timestamp, record.id)):
        recordgroups.append(list(items))

    page_info["prev_link"] = flask.url_for(
        view, page=page_info["page"] - 1)
    page_info["next_link"] = flask.url_for(
        view, page=page_info["page"] + 1)

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

def changelog_atom():
    return changelog_ext_page("changelog_atom")

def changelog_ext():
    return changelog_ext_page("changelog_ext")
