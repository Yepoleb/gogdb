from pyramid.view import view_config
import sqlalchemy

from .. import models
from ..models import ChangeRecord
from .pagination import calc_pageinfo

ITEMS_PER_PAGE = 100



@view_config(route_name="changelog", renderer="changelog.html")
def changelog(request):
    page = int(request.params.get("page", "1"))

    # Get total number of entries
    total_entries = request.dbsession.query(
        ChangeRecord.timestamp # just a placeholder
    ).group_by(
        ChangeRecord.timestamp, ChangeRecord.type_prim, ChangeRecord.prod_id
    ).count()

    page_info = calc_pageinfo(page, total_entries, ITEMS_PER_PAGE)

    changes = request.dbsession.query(
        ChangeRecord.timestamp, ChangeRecord.type_prim, ChangeRecord.prod_id,
        sqlalchemy.sql.functions.max(models.Product.title).label("title")
    ).join(
        models.Product
    ).group_by(
        ChangeRecord.timestamp, ChangeRecord.type_prim, ChangeRecord.prod_id
    ).order_by(
        ChangeRecord.timestamp.desc()
    ).offset(page_info["from"]).limit(ITEMS_PER_PAGE)

    page_info["prev_link"] = request.route_path("changelog",
        _query={"page": page_info["page"] - 1})
    page_info["next_link"] = request.route_path("changelog",
        _query={"page": page_info["page"] + 1})

    return {"changes": changes, "page_info": page_info}

