import io
import math
import pathlib

import quart

from gogdb.application.datasources import get_storagedb
import gogdb.core.buildloader as buildloader


BINARY_PREFIXES = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
def format_size(num, unit='B'):
    if num == 0:
        return "0{}".format(unit)
    magnitude = int(math.floor(math.log(num, 1000)))
    val = num / math.pow(1000, magnitude)
    if magnitude >= len(BINARY_PREFIXES):
        magnitude = len(BINARY_PREFIXES) - 1
    prefix = BINARY_PREFIXES[magnitude]
    if magnitude == 0:
        return '{:.0f}{}'.format(val, unit)
    if val >= 100:
        return '{:.0f}{}{}'.format(val, prefix, unit)
    elif val >= 10:
        return '{:.0f}{}{}'.format(val, prefix, unit)
    else:
        return '{:.1f}{}{}'.format(val, prefix, unit)

def add_tree_item(tree, item):
    parts = pathlib.PureWindowsPath(item.path).parts
    head = parts[:-1] # Everything leading up to the last item in the path
    tail = parts[-1] # Last item of the path
    cur_level = tree
    # Walk down the tree one path component at a time
    for part in head:
        # Handle malformed manifests where links are inside links
        if getattr(cur_level, "type", None) == "link":
            return
        if part not in cur_level:
            # Directory does not yet exist, create it
            cur_level[part] = {}
        cur_level = cur_level[part]
    # Need to check again for the last element in the loop
    if getattr(cur_level, "type", None) == "link":
        return
    if item.type == "file":
        cur_level[tail] = item
    elif item.type == "dir":
        cur_level[tail] = {}
    else: # link
        cur_level[tail] = item

TREE_CONTINUE = "├── "
TREE_END =      "└── "
TREE_SKIP =     "│   "
TREE_NONE =     "    "
def print_tree(dirtree, cur_indent="", **kwargs):
    for index, item in enumerate(sorted(dirtree.items())):
        name, child = item
        is_last = index == len(dirtree) - 1
        if is_last:
            this_indent = TREE_END
            lower_indent = TREE_NONE
        else:
            this_indent = TREE_CONTINUE
            lower_indent = TREE_SKIP
        if type(child) is dict:
            description = "({} Entries)".format(len(child))
        elif child.type == "file":
            description = "({})".format(format_size(child.size))
        elif child.type == "link":
            description = "-> {}".format(child.target)
        print(cur_indent + this_indent + name, description, **kwargs)
        if type(child) is dict:
            print_tree(child, cur_indent + lower_indent, **kwargs)

async def manifest(manifest_id):
    storagedb = get_storagedb()
    if "-" in manifest_id:
        manifest_data = await storagedb.manifest_v1.load(manifest_id)
        if manifest_data is None:
            quart.abort(404)
        manifest = buildloader.load_manifest_v1(manifest_data)
    else:
        manifest_data = await storagedb.manifest_v2.load(manifest_id)
        if manifest_data is None:
            quart.abort(404)
        manifest = buildloader.load_manifest_v2(manifest_data)

    all_items = manifest.files + manifest.directories + manifest.links
    tree = {}
    for item in all_items:
        add_tree_item(tree, item)

    output = io.StringIO()
    print(".", file=output)
    print_tree(tree, file=output)

    resp = await quart.make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp
