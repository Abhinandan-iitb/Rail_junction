"""
Railway Visualization Application
Main Flask application for Railway Analysis System
"""

import os
import sys
import logging
from flask import Flask, render_template, redirect, url_for, jsonify, request
from dotenv import load_dotenv

load_dotenv()

# Configure logging
log_level = logging.DEBUG if os.getenv('FLASK_DEBUG', 'False') == 'True' else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Project root: {project_root}")

# ============================================================================
# Flask Application Configuration
# ============================================================================

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

if os.getenv('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
else:
    app.config['DEBUG'] = True

# ============================================================================
# Blueprint Registration
# ============================================================================

# Circuit & Switch Analysis
from modules.circuit_switch_analysis import circuit_switch_analysis_bp
app.register_blueprint(circuit_switch_analysis_bp)
logger.info("✓ Circuit & Switch Analysis blueprint registered")

# Movement Analysis (formerly Phase 2)
try:
    from modules.movement_analysis.routes_movement_analysis import main as movement_analysis_blueprint
    app.register_blueprint(movement_analysis_blueprint, url_prefix='/movement_analysis')
    logger.info("✓ Movement Analysis blueprint registered")
except Exception as e:
    logger.error(f"✗ Error registering Movement Analysis blueprint: {str(e)}")

# Train Movement Analysis
try:
    from modules.train_movement.routes import train_movement_bp
    app.register_blueprint(train_movement_bp, url_prefix='/train-movement')
    logger.info("✓ Train Movement Analysis blueprint registered")
except Exception as e:
    logger.error(f"✗ Error registering Train Movement Analysis blueprint: {str(e)}")

# Railway Data Visuals
try:
    from modules.railway_data_visuals.routes import railway_data_visuals_bp
    app.register_blueprint(railway_data_visuals_bp, url_prefix='/railway-data-visuals')
    logger.info("✓ Railway Data Visuals blueprint registered")
except Exception as e:
    logger.error(f"✗ Error registering Railway Data Visuals blueprint: {str(e)}")

# Shunting Visuals
try:
    from modules.shunting_visuals import shunting_visuals_bp
    app.register_blueprint(shunting_visuals_bp, url_prefix='/shunting-visuals')
    logger.info("✓ Shunting Visuals blueprint registered")
    
    shunting_routes = [str(rule) for rule in app.url_map.iter_rules() if 'shunting' in str(rule)]
    logger.info(f"Shunting routes: {shunting_routes}")
except ImportError as ie:
    logger.error(f"✗ Import error: {str(ie)}")
except Exception as e:
    logger.error(f"✗ Error registering Shunting Visuals blueprint: {str(e)}")

# ============================================================================
# Main Routes
# ============================================================================

@app.route('/')
def home():
    """Main dashboard"""
    return render_template('dashboard.html')

# ============================================================================
# Module Redirects
# ============================================================================

@app.route('/movement_analysis')
@app.route('/movement-analysis')
def movement_analysis():
    """Movement Analysis application"""
    return render_template('movement_analysis.html')

@app.route('/train-movement')
def train_movement():
    """Redirect to Train Movement Analysis"""
    return redirect('/train-movement/')

@app.route('/railway-data-visuals')
def railway_data_visuals():
    """Redirect to Railway Data Visuals"""
    return redirect('/railway-data-visuals/')

# ============================================================================
# Legacy URL Support
# ============================================================================

@app.route('/phase2')
@app.route('/phase2/')
@app.route('/phase2_redirect')
def phase2_legacy_redirect():
    """Legacy redirect for old Phase 2 URLs"""
    return redirect('/movement_analysis/')

@app.route('/download_all_unknown_circuits_csv', methods=['GET'])
def redirect_to_csv_download():
    """Legacy CSV download redirect"""
    return redirect(url_for('circuit_switch_analysis.download_all_unknown_circuits_csv'))

# ============================================================================
# Static File Handling
# ============================================================================

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    try:
        return app.send_static_file(filename)
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {str(e)}")
        return f"Error: Could not serve static file - {str(e)}", 500

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def page_not_found(error):
    """Handle 404 errors"""
    if 'favicon.ico' in request.path:
        return '', 204
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(e)}")
    return render_template('500.html'), 500

# ============================================================================
# Debug Endpoints
# ============================================================================

@app.route('/debug/env')
def debug_env():
    """Display environment and configuration information"""
    env_info = {
        "PYTHONPATH": os.environ.get('PYTHONPATH', 'Not set'),
        "Working Directory": os.getcwd(),
        "Flask App": str(app),
        "Blueprints": list(app.blueprints.keys()),
        "Routes": [str(rule) for rule in app.url_map.iter_rules()]
    }
    return jsonify(env_info)

@app.route('/debug/routes')
def debug_routes():
    """List all registered routes"""
    routes = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda x: str(x)):
        routes.append({
            "url": str(rule),
            "endpoint": rule.endpoint,
            "methods": list(rule.methods)
        })
    return jsonify(routes)

# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    # Display registered routes
    logger.info("\n" + "=" * 60)
    logger.info("REGISTERED ROUTES:")
    logger.info("=" * 60)
    for rule in sorted(app.url_map.iter_rules(), key=lambda x: str(x)):
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        logger.info(f"{str(rule):50} [{methods}]")
    logger.info("=" * 60 + "\n")
    
    # Start application
    logger.info("Starting Railway Visualization Application...")
    port = int(os.getenv('PORT', 5001))
    debug_mode = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)
