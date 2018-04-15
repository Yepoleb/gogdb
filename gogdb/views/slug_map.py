import flask

from gogdb import app, db, model


@app.route("/slug-map.json")
def slug_map():
    slug_map = dict(
        db.session.query(model.Product.slug, model.Product.id) \
            .filter(model.Product.availability == 2) \
            .order_by(model.Product.slug))

    return flask.jsonify(slug_map)
