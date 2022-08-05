import datetime

import quart

import gogdb.core.model as model
from gogdb.views.pagination import calc_pageinfo
from gogdb.application.datasources import get_indexdb_cursor

ITEMS_PER_PAGE = 100


async def changelog():
    page = int(quart.request.args.get("page", "1"))

    cur = await get_indexdb_cursor()
    # Get total number of entries
    await cur.execute("SELECT COUNT(*) FROM changelog_summary;")
    total_entries = (await cur.fetchone())[0]

    page_info = calc_pageinfo(page, total_entries, ITEMS_PER_PAGE)

    await cur.execute(
        "SELECT * FROM changelog_summary ORDER BY timestamp DESC LIMIT ? OFFSET ?;",
        (ITEMS_PER_PAGE, page_info["from"])
    )

    changelog_summaries = []
    async for summary_res in cur:
        summary = model.IndexChangelogSummary(
            product_id = summary_res["product_id"],
            product_title = summary_res["product_title"],
            timestamp = datetime.datetime.fromtimestamp(summary_res["timestamp"], datetime.timezone.utc),
            categories = summary_res["categories"].split(",")
        )
        changelog_summaries.append(summary)
    await cur.close()

    page_info["prev_link"] = quart.url_for(
        "changelog", page=page_info["page"] - 1)
    page_info["next_link"] = quart.url_for(
        "changelog", page=page_info["page"] + 1)

    return await quart.render_template(
        "changelog.html", changes=changelog_summaries, page_info=page_info)

