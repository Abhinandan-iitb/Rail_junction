from flask import Blueprint

train_movement_bp = Blueprint('train_movement', __name__, template_folder='templates')

from . import routes
from .routes import train_movement_bp

def init_app(app):
    app.register_blueprint(train_movement_bp, url_prefix='/train-movement')
