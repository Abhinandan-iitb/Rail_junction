"""
Shunting Visuals Routes
Handles routing for shunting data visualization and analysis
"""

from flask import Blueprint, render_template, request, jsonify, session, current_app
import os
import logging
import sys

# Configure logging
logger = logging.getLogger(__name__)
logger.info("Loading routes_shunting_visuals module...")

# Create blueprint first
shunting_visuals_bp = Blueprint('shunting_visuals', __name__)

# Initialize module-level variables
data_loader = None
processor = None
ShuntingDataLoader = None
ShuntingVisualsProcessor = None

# Try to import required modules with detailed error reporting
try:
    logger.info("Attempting to import ShuntingDataLoader...")
    from .load_shunting_visuals_data import ShuntingDataLoader
    logger.info("✓ ShuntingDataLoader imported successfully")
except ImportError as e:
    logger.error(f"✗ Import error for ShuntingDataLoader: {str(e)}", exc_info=True)
except Exception as e:
    logger.error(f"✗ Unexpected error importing ShuntingDataLoader: {str(e)}", exc_info=True)

try:
    logger.info("Attempting to import ShuntingVisualsProcessor...")
    from .shunting_visuals_main import ShuntingVisualsProcessor
    logger.info("✓ ShuntingVisualsProcessor imported successfully")
except ImportError as e:
    logger.error(f"✗ Import error for ShuntingVisualsProcessor: {str(e)}", exc_info=True)
except Exception as e:
    logger.error(f"✗ Unexpected error importing ShuntingVisualsProcessor: {str(e)}", exc_info=True)

# Initialize data loader and processor
if ShuntingDataLoader is not None:
    try:
        logger.info("Attempting to initialize ShuntingDataLoader...")
        data_loader = ShuntingDataLoader()
        logger.info("✓ Data loader initialized successfully")
    except Exception as e:
        logger.error(f"✗ Error initializing data loader: {str(e)}", exc_info=True)
        data_loader = None
else:
    logger.error("✗ ShuntingDataLoader class is None - cannot initialize")

if ShuntingVisualsProcessor is not None:
    try:
        logger.info("Attempting to initialize ShuntingVisualsProcessor...")
        processor = ShuntingVisualsProcessor()
        logger.info("✓ Processor initialized successfully")
    except Exception as e:
        logger.error(f"✗ Error initializing processor: {str(e)}", exc_info=True)
        processor = None
else:
    logger.error("✗ ShuntingVisualsProcessor class is None - cannot initialize")

# Create blueprint
shunting_visuals_bp = Blueprint('shunting_visuals', __name__)

# Initialize data loader and processor
try:
    data_loader = ShuntingDataLoader()
    processor = ShuntingVisualsProcessor()
    logger.info("Data loader and processor initialized successfully")
except Exception as e:
    logger.error(f"Error initializing components: {str(e)}")
    data_loader = None
    processor = None

@shunting_visuals_bp.route('/')
def index():
    """Main shunting visuals dashboard"""
    try:
        return render_template('shunting_visuals.html')
    except Exception as e:
        logger.error(f"Error rendering shunting visuals index: {str(e)}")
        return f"Error loading shunting visuals: {str(e)}", 500

@shunting_visuals_bp.route('/api/data')
def get_shunting_data():
    """API endpoint to get shunting data"""
    try:
        if not data_loader:
            logger.error("Data loader not available")
            return jsonify({
                "status": "error",
                "message": "Data loader not available"
            }), 500
        
        # Load default data
        logger.info("Loading default shunting data...")
        result = data_loader.load_default_data()
        
        if result['status'] == 'success':
            # Process the data and get available Net IDs
            chain_seq_data = result['data']['chain_seq']
            interval_data = result['data']['interval']
            
            logger.info(f"Data loaded: {len(chain_seq_data)} chains, {len(interval_data)} intervals")
            
            # Extract unique Net IDs
            net_ids = list(set([row.get('Net_id') for row in chain_seq_data if row.get('Net_id')]))
            available_net_ids = sorted([int(nid) for nid in net_ids if str(nid).isdigit()])
            
            logger.info(f"Available Net IDs: {available_net_ids}")
            
            # Get data information
            data_info = data_loader.get_data_info(result['data'])
            
            response_data = {
                "status": "success",
                "message": "Default shunting data loaded successfully",
                "data": result['data'],
                "summary": {
                    **result['summary'],
                    **data_info
                },
                "available_net_ids": available_net_ids
            }
            
            logger.info(f"Sending response with summary: {response_data['summary']}")
            return jsonify(response_data)
        else:
            logger.error(f"Failed to load data: {result}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error getting shunting data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@shunting_visuals_bp.route('/analysis')
def analysis():
    """Shunting analysis page"""
    try:
        return render_template('shunting_visuals.html')
    except Exception as e:
        logger.error(f"Error rendering shunting analysis: {str(e)}")
        return f"Error loading shunting analysis: {str(e)}", 500

@shunting_visuals_bp.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file upload for CSV processing"""
    try:
        if not data_loader:
            return jsonify({
                "status": "error",
                "message": "Data loader not available"
            }), 500
            
        # Check if files are present
        if 'chainSeqFile' not in request.files or 'intervalFile' not in request.files:
            return jsonify({
                "status": "error",
                "message": "Both chain sequence and interval files are required"
            }), 400
        
        chain_seq_file = request.files['chainSeqFile']
        interval_file = request.files['intervalFile']
        
        # Check if files have content
        if chain_seq_file.filename == '' or interval_file.filename == '':
            return jsonify({
                "status": "error",
                "message": "Please select both CSV files"
            }), 400
        
        # Parse uploaded files
        result = data_loader.parse_uploaded_files(chain_seq_file, interval_file)
        
        if result['status'] == 'success':
            # Extract unique Net IDs
            chain_seq_data = result['data']['chain_seq']
            net_ids = list(set([row.get('Net_id') for row in chain_seq_data if row.get('Net_id')]))
            available_net_ids = sorted([int(nid) for nid in net_ids if str(nid).isdigit()])
            
            # Get data information
            data_info = data_loader.get_data_info(result['data'])
            
            return jsonify({
                "status": "success",
                "message": "Files uploaded and processed successfully",
                "data": result['data'],
                "summary": {
                    **result['summary'],
                    **data_info
                },
                "available_net_ids": available_net_ids
            })
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@shunting_visuals_bp.route('/api/generate-plot', methods=['POST'])
def generate_plot():
    """Generate plot data for frontend"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Add validation
        net_id = data.get('net_id')
        if not net_id:
            return jsonify({"status": "error", "message": "Net ID is required"}), 400
        
        # Validate spacing
        spacing = data.get('spacing', 20.0)
        if not isinstance(spacing, (int, float)) or spacing <= 0 or spacing > 100:
            return jsonify({"status": "error", "message": "Invalid spacing value"}), 400
        
        # Validate data size
        chain_seq_data = data.get('chain_seq_data', [])
        interval_data = data.get('interval_data', [])
        
        MAX_RECORDS = 10000  # Add limit
        if len(chain_seq_data) > MAX_RECORDS or len(interval_data) > MAX_RECORDS:
            return jsonify({"status": "error", "message": "Data size exceeds limit"}), 400
        
        # Generate plot data
        result = processor.generate_shunting_plot_data(int(net_id), float(spacing), chain_seq_data, interval_data)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error generating plot: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@shunting_visuals_bp.route('/api/load-default', methods=['POST'])
def load_default_data_endpoint():
    """Load default data from CSV files - explicit endpoint"""
    try:
        if not data_loader:
            return jsonify({
                "status": "error",
                "message": "Data loader not available"
            }), 500
            
        result = data_loader.load_default_data()
        
        if result['status'] == 'success':
            # Extract unique Net IDs
            chain_seq_data = result['data']['chain_seq']
            net_ids = list(set([row.get('Net_id') for row in chain_seq_data if row.get('Net_id')]))
            available_net_ids = sorted([int(nid) for nid in net_ids if str(nid).isdigit()])
            
            # Get data information
            data_info = data_loader.get_data_info(result['data'])
            
            return jsonify({
                "status": "success",
                "message": "Default data loaded successfully",
                "data": result['data'],
                "summary": {
                    **result['summary'],
                    **data_info
                },
                "available_net_ids": available_net_ids
            })
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error loading default data: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Health check endpoint for debugging
@shunting_visuals_bp.route('/api/health')
def health_check():
    """Check if components are initialized"""
    import pandas as pd
    
    return jsonify({
        "status": "ok",
        "components": {
            "data_loader": data_loader is not None,
            "processor": processor is not None,
            "ShuntingDataLoader_class": ShuntingDataLoader is not None,
            "ShuntingVisualsProcessor_class": ShuntingVisualsProcessor is not None
        },
        "dependencies": {
            "pandas_version": pd.__version__ if pd else None,
            "python_version": sys.version
        }
    })

logger.info(f"routes_shunting_visuals module loaded. data_loader={'initialized' if data_loader else 'None'}, processor={'initialized' if processor else 'None'}")