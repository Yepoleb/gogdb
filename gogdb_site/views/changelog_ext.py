import itertools

from pyramid.view import view_config
from pyramid.renderers import render_to_response
from sqlalchemy import orm

from .. import models
from ..models import ChangeRecord
from .pagination import calc_pageinfo

ITEMS_PER_PAGE = 100



@view_config(route_name="changelog_atom", renderer="changelog_ext.xml")
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

    recordgroups = []
    for groupkey, items in itertools.groupby(
            changes, key=lambda record: (record.timestamp, record.prod_id)):
        recordgroups.append(list(items))


    if request.matched_route.name == "changelog_atom":
        response = render_to_response(
            "changelog_ext.xml",
            {"changes": recordgroups, "page_info": page_info},
            request=request
        )
        response.content_type = "application/atom+xml"
        return response

    else:
        return render_to_response(
            "changelog_ext.html",
            {"changes": recordgroups, "page_info": page_info},
            request=request
        )
