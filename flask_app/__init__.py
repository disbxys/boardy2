from flask import Flask

from flask_app.config import Config
from flask_app.models import db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    from flask_app.models import db
    db.create_all()


import flask_app.routes