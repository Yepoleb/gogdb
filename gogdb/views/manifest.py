import io

import flask

from gogdb import app, db, model


FILEFLAGS = ["executable", "hidden", "support"]
FLAGLETTERS = ['X', 'H', 'S']
def fileflags(flags):
    setflags = ['-', '-', '-']
    for i, l in enumerate(FLAGLETTERS):
        if flags[i]:
            setflags[i] = l
    return "".join(setflags)


def get_manifest_v1(manifest_id):
    manifest = db.session.query(model.DepotManifestV1) \
        .filter(model.DepotManifestV1.manifest_id == manifest_id) \
        .one_or_none()

    if manifest is None:
        flask.abort(404)

    return manifest

def get_manifest_v2(manifest_id):
    manifest = db.session.query(model.DepotManifestV2) \
        .filter(model.DepotManifestV2.manifest_id == manifest_id) \
        .one_or_none()

    if manifest is None:
        flask.abort(404)

    return manifest

def get_files_v1(manifest, limit=False):
    count = db.session.query(model.DepotFileV1.id) \
        .filter(model.DepotFileV1.manifest_id == manifest.id) \
        .count()

    file_query = db.session.query(
            model.DepotFileV1.path, model.DepotFileV1.size,
            model.DepotFileV1.checksum, model.DepotFileV1.f_executable,
            model.DepotFileV1.f_hidden, model.DepotFileV1.f_support) \
        .filter(model.DepotFileV1.manifest_id == manifest.id) \
        .order_by(model.DepotFileV1.path)

    if count > 1100 and limit:
        file_query = file_query.limit(1100)

    files = [
        {
            "path": file_res[0],
            "size": file_res[1],
            "checksum": file_res[2] or "",
            "flags": fileflags(file_res[3:6])
        }
        for file_res in file_query
    ]

    return count, files

def get_files_v2(manifest, limit=False):
    count = db.session.query(model.DepotFileV2.id) \
        .filter(model.DepotFileV2.manifest_id == manifest.id) \
        .count()

    file_query = db.session.query(
            model.DepotFileV2.path, model.DepotFileV2.size,
            model.DepotFileV2.checksum, model.DepotFileV2.f_executable,
            model.DepotFileV2.f_hidden, model.DepotFileV2.f_support) \
        .filter(model.DepotFileV2.manifest_id == manifest.id) \
        .order_by(model.DepotFileV2.path)

    if count > 1100 and limit:
        file_query = file_query.limit(1100)

    files = [
        {
            "path": file_res[0],
            "size": file_res[1],
            "checksum": file_res[2] or "",
            "flags": fileflags(file_res[3:6])
        }
        for file_res in file_query
    ]

    return count, files

@app.route("/manifest/<manifest_id>")
def manifest(manifest_id):
    if "-" in manifest_id:
        manifest = get_manifest_v1(manifest_id)
        files_count, files = get_files_v1(manifest, True)

        directory_query = db.session.query(
                model.DepotDirectoryV1.path,
                model.DepotDirectoryV1.f_support) \
            .filter(model.DepotDirectoryV1.manifest_id == manifest.id) \
            .order_by(model.DepotDirectoryV1.path)

        directories = [
            {
                "path": dir_res[0],
                "flags": "--S" if dir_res[1] else "---"
            }
            for dir_res in directory_query
        ]

        link_query = db.session.query(
                model.DepotLinkV1.path, model.DepotLinkV1.target) \
            .filter(model.DepotLinkV1.manifest_id == manifest.id) \
            .order_by(model.DepotLinkV1.path)

        links = [
            {
                "path": link_res[0],
                "target": link_res[1],
            }
            for link_res in link_query
        ]

        builds = db.session.query(model.Build) \
            .join(model.RepositoryV1).join(model.DepotV1) \
            .filter(model.DepotV1.manifest_id == manifest.id) \
            .order_by(model.Build.date_published.desc()) \
            .all()

        return flask.render_template(
            "manifest.html", manifest=manifest, files=files,
            directories=directories, links=links, builds=builds,
            files_count=files_count)

    else:
        manifest = get_manifest_v2(manifest_id)
        files_count, files = get_files_v2(manifest, True)

        directory_query = db.session.query(model.DepotDirectoryV2.path) \
            .filter(model.DepotDirectoryV2.manifest_id == manifest.id) \
            .order_by(model.DepotDirectoryV2.path)

        directories = [
            {
                "path": dir_res[0],
                "flags": "---"
            }
            for dir_res in directory_query
        ]

        link_query = db.session.query(
                model.DepotLinkV2.path, model.DepotLinkV2.target) \
            .filter(model.DepotLinkV2.manifest_id == manifest.id) \
            .order_by(model.DepotLinkV2.path)

        links = [
            {
                "path": link_res[0],
                "target": link_res[1],
            }
            for link_res in link_query
        ]

        builds = db.session.query(model.Build) \
            .join(model.RepositoryV2).join(model.DepotV2) \
            .filter(model.DepotV2.manifest_id == manifest.id) \
            .order_by(model.Build.date_published.desc()) \
            .all()

        return flask.render_template(
            "manifest.html", manifest=manifest, files=files,
            directories=directories, links=links, builds=builds,
            files_count=files_count)



@app.route("/filelist/<manifest_id>")
def filelist(manifest_id):
    if "-" in manifest_id:
        manifest = get_manifest_v1(manifest_id)
        files_count, files = get_files_v1(manifest)
    else:
        manifest = get_manifest_v2(manifest_id)
        files_count, files = get_files_v2(manifest)

    max_path_len = max(len(f["path"]) for f in files)
    max_size = max(f["size"] for f in files)

    path_len = min(100, max_path_len)
    size_len = len(str(max_size))

    liststream = io.StringIO()
    liststream.write(
        "{:^{path_width}} {:^{size_width}} {:^32} {}\n".format(
            "Path", "Size", "Checksum", "Flags",
            path_width=path_len, size_width=size_len))
    for f in files:
        line = "{:<{path_width}} {:{size_width}} {} {}\n".format(
            f["path"], f["size"], f["checksum"], f["flags"],
            path_width=path_len, size_width=size_len)
        liststream.write(line)

    resp = flask.make_response(liststream.getvalue())
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    return resp
