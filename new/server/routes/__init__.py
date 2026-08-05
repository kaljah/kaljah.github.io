from flask import Blueprint

auth_bp = Blueprint('auth', __name__)
emissions_bp = Blueprint('emissions', __name__)
facilities_bp = Blueprint('facilities', __name__)
data_bp = Blueprint('data', __name__)
reports_bp = Blueprint('reports', __name__)
custom_factors_bp = Blueprint('custom_factors', __name__)
scope2_bp = Blueprint('scope2', __name__)
scope3_bp = Blueprint('scope3', __name__)
managedata_bp = Blueprint('managedata', __name__)
dashboard_bp = Blueprint('dashboard', __name__)
factors_bp = Blueprint('factors', __name__)  # New: API 2021 emission factors endpoints

from . import auth, emissions, facilities, data, reports, custom_factors, scope2, scope3, managedata, dashboard, emission_factors_routes
