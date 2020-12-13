import sqlite3

import flask

import gogdb.core.storage as storage



def get_storagedb():
    if "storagedb" not in flask.g:
        storage_path = flask.current_app.config["STORAGE_PATH"]
        flask.g.storagedb = storage.Storage(storage_path)

    return flask.g.storagedb

def get_indexdb():
    if "indexdb" not in flask.g:
        storagedb = get_storagedb()
        index_path = storagedb.path_indexdb()
        flask.g.indexdb = sqlite3.connect(index_path)
        flask.g.indexdb.row_factory = sqlite3.Row

    return flask.g.indexdb
