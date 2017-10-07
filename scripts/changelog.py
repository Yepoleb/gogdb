from gogdb_site.models import ChangeRecord



SYSTEMS_ORDER = ["windows", "mac", "linux"]

def make_systems_str(systems):
    if systems is None:
        return None
    systems_list = list(systems)
    systems_list.sort(key=lambda x: SYSTEMS_ORDER.index(x))
    return ",".join(systems_list)



def prod_add(product, changes, cur_time):
    record = ChangeRecord(
        timestamp=cur_time,
        action="add",
        type_prim="product",
        type_sec=None,
        resource=str(product.id),
        old=None,
        new=None
    )
    changes.append(record)

def prod_cs(product, value, changes, cur_time):
    if set(product.cs_systems) == set(value):
        return

    record = ChangeRecord(
        timestamp=cur_time,
        action="change",
        type_prim="product",
        type_sec="cs",
        resource=str(product.id),
        old=make_systems_str(product.cs_systems),
        new=make_systems_str(value)
    )
    changes.append(record)

def prod_os(product, value, changes, cur_time):
    if set(product.systems) == set(value):
        return

    record = ChangeRecord(
        timestamp=cur_time,
        action="change",
        type_prim="product",
        type_sec="os",
        resource=str(product.id),
        old=make_systems_str(product.systems),
        new=make_systems_str(value)
    )
    changes.append(record)

def prod_title(product, value, changes, cur_time):
    if product.title == value:
        return

    record = ChangeRecord(
        timestamp=cur_time,
        action="change",
        type_prim="product",
        type_sec="title",
        resource=str(product.id),
        old=product.title,
        new=value
    )
    changes.append(record)

def prod_forum(product, value, changes, cur_time):
    if product.forum_id == value:
        return

    record = ChangeRecord(
        timestamp=cur_time,
        action="change",
        type_prim="product",
        type_sec="forum_slug",
        resource=str(product.id),
        old=product.forum_id,
        new=value
    )
    changes.append(record)

def dl_add(download, changes, cur_time):
    record = ChangeRecord(
        timestamp=cur_time,
        action="add",
        type_prim="download",
        type_sec=None,
        resource=download.slug,
        old=None,
        new=None
    )
    changes.append(record)

def dl_del(download, changes, cur_time):
    record = ChangeRecord(
        timestamp=cur_time,
        action="del",
        type_prim="download",
        type_sec=None,
        resource=download.slug,
        old=None,
        new=None
    )
    changes.append(record)

def dl_version(download, value, changes, cur_time):
    if download.version == value:
        return

    record = ChangeRecord(
        timestamp=cur_time,
        action="change",
        type_prim="download",
        type_sec="version",
        resource=download.slug,
        old=download.version,
        new=value
    )
    changes.append(record)

def dl_name(download, value, changes, cur_time):
    if download.name == value:
        return

    record = ChangeRecord(
        timestamp=cur_time,
        action="change",
        type_prim="download",
        type_sec="name",
        resource=download.slug,
        old=download.name,
        new=value
    )
    changes.append(record)

def dl_total_size(download, value, changes, cur_time):
    if download.total_size == value:
        return

    record = ChangeRecord(
        timestamp=cur_time,
        action="change",
        type_prim="download",
        type_sec="total_size",
        resource=download.slug,
        old=download.total_size,
        new=value
    )
    changes.append(record)
