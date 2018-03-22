from flask import Flask


app = Flask("gogdb")

import gogdb.config
from gogdb.database import db
import gogdb.assets
import gogdb.model
import gogdb.filters
import gogdb.views
