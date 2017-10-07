from pyramid.view import view_config
from sqlalchemy import orm

from .. import models
from ..models import ChangeRecord
from .pagination import calc_pageinfo

ITEMS_PER_PAGE = 100



@view_config(route_name="changelog_ext", renderer="changelog_ext.html")
def changelog_ext(request):
    page = int(request.params.get("page", "1"))
    total_entries = request.dbsession.query(ChangeRecord.id).count()
    page_info = calc_pageinfo(page, total_entries, ITEMS_PER_PAGE)

    changes = request.dbsession.query(
        models.ChangeRecord
    ).options(
        orm.subqueryload(
            "product"
        ).subqueryload(
            "downloads"
        )
    ).order_by(
        models.ChangeRecord.id.desc()
    ).offset(page_info["from"]).limit(ITEMS_PER_PAGE)

    page_info["prev_link"] = request.route_path("changelog_ext",
        _query={"page": page_info["page"] - 1})
    page_info["next_link"] = request.route_path("changelog_ext",
        _query={"page": page_info["page"] + 1})

    return {"changes": changes, "page_info": page_info}
