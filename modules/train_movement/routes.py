"""
Train Movement Routes Module

This module defines Flask routes for the train movement visualization system.
"""
import os
import tempfile
from flask import Blueprint, render_template, request, jsonify, current_app, session
from datetime import datetime
from typing import Tuple, Optional

# Import get_train_movement_data function
from .train_movement import get_train_movement_data
from .load_train_movement import load_and_process_data

# Create Blueprint with template folder pointing to the main templates directory
train_movement_bp = Blueprint('train_movement', __name__, template_folder='../../templates')

# Temporary directory for uploaded files
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'railway_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#######################
# MAIN ROUTES         #
#######################

@train_movement_bp.route('/')
def index():
    """Render the train movement visualization page"""
    return render_template('train_status.html')

@train_movement_bp.route('/get_net_group_ids')
def get_net_group_ids():
    """API endpoint to get available Net_Group_ID values for filtering"""
    try:
        # Load data to extract Net_Group_IDs
        _, _, _, circuit_df = load_and_process_data(use_uploaded=False)
        
        if circuit_df is None:
            return jsonify({"net_group_ids": [], "error": "Failed to load data"})
        
        # Extract Net_Group_IDs
        from .filter_features import get_available_net_group_ids
        net_group_ids = get_available_net_group_ids(circuit_df)
        
        return jsonify({"net_group_ids": net_group_ids})
    except Exception as e:
        current_app.logger.error(f"Error getting Net_Group_IDs: {str(e)}")
        return jsonify({"net_group_ids": [], "error": str(e)})

@train_movement_bp.route('/get_track_data')
def get_track_data():
    """API endpoint to get track data for visualization"""
    try:
        # Get query parameters
        use_uploaded = request.args.get('use_uploaded', 'false').lower() == 'true'
        
        # Log the request for debugging
        current_app.logger.info(f"get_track_data called with use_uploaded={use_uploaded}")
        
        # Parse datetime parameters
        start_date, end_date = parse_datetime_parameters()
        
        # Get Net_Group_ID filter parameter
        net_group_id = request.args.get('net_group', '')
        
        # Get data with filters applied
        data = get_train_movement_data(
            use_uploaded=use_uploaded, 
            start_datetime=start_date,
            end_datetime=end_date,
            net_group_id=net_group_id
        )
        
        return jsonify(data)
        
    except Exception as e:
        current_app.logger.error(f"Error in get_track_data: {str(e)}")
        # Return a more detailed error for debugging
        import traceback
        error_details = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        return jsonify(error_details), 500

@train_movement_bp.route('/get_routes')
def get_routes():
    """API endpoint to get available routes for filtering"""
    try:
        # This is a placeholder - in a real app, you would fetch actual routes
        routes = ["101", "102", "103", "104", "105"]
        return jsonify({"routes": routes})
    except Exception as e:
        current_app.logger.error(f"Error getting routes: {str(e)}")
        return jsonify({"routes": [], "error": str(e)})

#######################
# FILE UPLOAD HANDLING #
#######################

@train_movement_bp.route('/upload_files', methods=['POST'])
def upload_files():
    """Handle file uploads for train movement data"""
    try:
        # Validate uploaded files
        validation_result = validate_uploaded_files()
        if not validation_result['success']:
            return jsonify(validation_result)
        
        # Save files
        save_uploaded_files()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Error uploading files: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

def validate_uploaded_files():
    """
    Validate that all required files are present and valid.
    
    Returns:
        Dictionary with validation result
    """
    # Check if required files are present
    if 'nodes_file' not in request.files or \
       'edges_file' not in request.files or \
       'circuit_file' not in request.files:
        return {'success': False, 'error': 'Missing required files'}
    
    nodes_file = request.files['nodes_file']
    edges_file = request.files['edges_file'] 
    circuit_file = request.files['circuit_file']
    
    # Check if files are empty
    if nodes_file.filename == '' or edges_file.filename == '' or circuit_file.filename == '':
        return {'success': False, 'error': 'Empty file(s) provided'}
    
    # Check file extensions
    for file in [nodes_file, edges_file, circuit_file]:
        if not file.filename.lower().endswith('.csv'):
            return {'success': False, 'error': 'All files must be CSV format'}
    
    return {'success': True}

def save_uploaded_files():
    """Save uploaded files and store paths in session"""
    # Get files from request
    nodes_file = request.files['nodes_file']
    edges_file = request.files['edges_file'] 
    circuit_file = request.files['circuit_file']
    
    # Create user-specific upload directory
    user_folder = os.path.join(UPLOAD_FOLDER, str(id(session)))
    os.makedirs(user_folder, exist_ok=True)
    
    # Save files
    nodes_path = os.path.join(user_folder, 'nodes.csv')
    edges_path = os.path.join(user_folder, 'edges.csv')
    circuit_path = os.path.join(user_folder, 'final_circuit_interval_chain_id_net_id_route_id.csv')
    
    nodes_file.save(nodes_path)
    edges_file.save(edges_path)
    circuit_file.save(circuit_path)
    
    # Store the paths in session for later use
    session['uploaded_files'] = {
        'nodes': nodes_path,
        'edges': edges_path,
        'circuit': circuit_path
    }

#######################
# HELPER FUNCTIONS    #
#######################

def parse_datetime_parameters() -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse and validate datetime parameters from request.
    
    Returns:
        Tuple containing start and end datetime objects (if valid)
    """
    # Get datetime filter parameters
    start_datetime = request.args.get('start_datetime', '')
    end_datetime = request.args.get('end_datetime', '')
    
    # Parse datetime strings if provided
    start_date = None
    end_date = None
    
    if start_datetime:
        try:
            # Handle different ISO formats
            if 'Z' in start_datetime:
                start_datetime = start_datetime.replace('Z', '+00:00')
            start_date = datetime.fromisoformat(start_datetime)
        except ValueError as e:
            current_app.logger.error(f"Invalid start datetime format: {start_datetime}, error: {str(e)}")
            raise ValueError(f"Invalid start datetime format: {start_datetime}")
            
    if end_datetime:
        try:
            # Handle different ISO formats
            if 'Z' in end_datetime:
                end_datetime = end_datetime.replace('Z', '+00:00')
            end_date = datetime.fromisoformat(end_datetime)
        except ValueError as e:
            current_app.logger.error(f"Invalid end datetime format: {end_datetime}, error: {str(e)}")
            raise ValueError(f"Invalid end datetime format: {end_datetime}")
    
    return start_date, end_date

@train_movement_bp.route('/test')
def test():
    """Test endpoint to verify blueprint is working"""
    return "Train Movement Blueprint is working!"
