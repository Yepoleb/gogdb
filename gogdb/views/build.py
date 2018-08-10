import flask

from gogdb import app, db, model


@app.route("/product/<int:prod_id>/build/<int:build_id>")
def build(prod_id, build_id):
    db_build = db.session.query(model.Build) \
        .filter(model.Build.prod_id == prod_id) \
        .filter(model.Build.build_id == build_id) \
        .one_or_none()

    if db_build is None:
        flask.abort(404)

    if db_build.generation == 1:
        return flask.render_template(
            "build_v1.html", build=db_build, repo=db_build.repo_v1)
    else:
        return flask.render_template(
            "build_v2.html", build=db_build, repo=db_build.repo_v2)
