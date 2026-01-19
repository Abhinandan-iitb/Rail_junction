"""
Circuit & Switch Analysis Module
Provides railway circuit and switch state analysis with visualization capabilities.
"""

from flask import Blueprint

# Initialize blueprint
circuit_switch_analysis_bp = Blueprint(
    'circuit_switch_analysis',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/circuit-switch-analysis'
)

# Import routes
from . import routes_circuit_switch_analysis
