import datetime

import flask

import gogdb.core.model as model
from gogdb.views.pagination import calc_pageinfo
from gogdb.application.datasources import get_indexdb

ITEMS_PER_PAGE = 100


def changelog():
    page = int(flask.request.args.get("page", "1"))

    cur = get_indexdb().cursor()
    # Get total number of entries
    cur.execute("SELECT COUNT(*) FROM changelog_summary;")
    total_entries = cur.fetchone()[0]

    page_info = calc_pageinfo(page, total_entries, ITEMS_PER_PAGE)

    cur.execute(
        "SELECT * FROM changelog_summary ORDER BY timestamp DESC LIMIT ? OFFSET ?;",
        (ITEMS_PER_PAGE, page_info["from"])
    )

    changelog_summaries = []
    for summary_res in cur:
        summary = model.IndexChangelogSummary(
            product_id = summary_res["product_id"],
            product_title = summary_res["product_title"],
            timestamp = datetime.datetime.fromtimestamp(summary_res["timestamp"], datetime.timezone.utc),
            categories = summary_res["categories"].split(",")
        )
        changelog_summaries.append(summary)

    page_info["prev_link"] = flask.url_for(
        "changelog", page=page_info["page"] - 1)
    page_info["next_link"] = flask.url_for(
        "changelog", page=page_info["page"] + 1)

    return flask.render_template(
        "changelog.html", changes=changelog_summaries, page_info=page_info)

