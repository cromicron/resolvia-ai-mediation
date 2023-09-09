from flask import Blueprint

mediation_bp = Blueprint("mediation", __name__)

from . import routes