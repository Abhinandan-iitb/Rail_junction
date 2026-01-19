from flask import Blueprint, render_template, jsonify, request, session, current_app, flash, redirect, url_for
import logging
import os
import pandas as pd
import json
from .data_visuals import Net, dataframe_to_html, NumpyEncoder
from .load_visual_data import (
    handle_file_upload, UPLOAD_FOLDER, ALLOWED_EXTENSIONS,
    DEFAULT_MAIN_DATASET, DEFAULT_SECOND_DATASET, DEFAULT_THIRD_DATASET,
    DEFAULT_START_END_DATASET, DATA_FOLDER, check_default_data_available
)
from .sample_inputs import get_all_samples

# Configure logging
logger = logging.getLogger(__name__)

# Create the blueprint
railway_data_visuals_bp = Blueprint('railway_data_visuals', __name__, 
                                  template_folder='templates')

@railway_data_visuals_bp.route('/')
def index():
    """Render the Railway Data Visuals main page"""
    logger.info("Rendering Railway Data Visuals main page")
    # Get sample data for display
    sample_data = get_all_samples()
    return render_template('Railway_data_visuals.html', sample_data=sample_data)

@railway_data_visuals_bp.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads for the three data sources"""
    if request.method != 'POST':
        return jsonify({"status": "error", "message": "Only POST method is supported"})

    # Create upload folder if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Initialize response data
    response_data = {"status": "success", "files": {}}
    all_success = True
    
    try:
        # Process main dataset file
        if 'main_file' in request.files:
            main_file = request.files['main_file']
            success, message, filepath = handle_file_upload(main_file, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, 'main_file')
            response_data["files"]["main_file"] = {"success": success, "message": message}
            if success:
                session['main_file_path'] = filepath
            else:
                all_success = False
        
        # Process JSON dataset file
        if 'json_file' in request.files:
            json_file = request.files['json_file']
            success, message, filepath = handle_file_upload(json_file, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, 'json_file')
            response_data["files"]["json_file"] = {"success": success, "message": message}
            if success:
                session['json_file_path'] = filepath
            else:
                all_success = False
                
        # Process start-end file if provided
        if 'start_end_file' in request.files and request.files['start_end_file'].filename:
            start_end_file = request.files['start_end_file']
            success, message, filepath = handle_file_upload(start_end_file, UPLOAD_FOLDER, ALLOWED_EXTENSIONS, 'start_end_file')
            response_data["files"]["start_end_file"] = {"success": success, "message": message}
            if success:
                session['start_end_file_path'] = filepath
        
        # If all files were uploaded successfully, initialize Net and store summary
        if all_success and 'main_file_path' in session and 'json_file_path' in session:
            try:
                net = Net(session['main_file_path'], None, session['json_file_path'])
                
                # Load start-end file if provided
                if 'start_end_file_path' in session:
                    net.load_start_end_dataset(session['start_end_file_path'])
                    
                # Handle potential non-JSON serializable objects in the data summary
                summary = net.data_summary()
                # Convert sets to lists for JSON serialization
                if "main_dataset" in summary and "unique_net_ids" in summary["main_dataset"]:
                    summary["main_dataset"]["unique_net_ids"] = list(summary["main_dataset"]["unique_net_ids"])
                if "main_dataset" in summary and "unique_chain_ids" in summary["main_dataset"]:
                    summary["main_dataset"]["unique_chain_ids"] = list(summary["main_dataset"]["unique_chain_ids"])
                if "json_dataset" in summary and "unique_net_ids" in summary["json_dataset"]:
                    summary["json_dataset"]["unique_net_ids"] = list(summary["json_dataset"]["unique_net_ids"])
                
                response_data["data_summary"] = summary
            except Exception as e:
                logger.error(f"Error initializing Net: {str(e)}")
                response_data["status"] = "error"
                response_data["message"] = f"Error processing uploaded files: {str(e)}"
        
        # Return JSON response
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error during file upload: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error during file upload: {str(e)}"
        })

@railway_data_visuals_bp.route('/api/net-analysis', methods=['GET', 'POST'])
def net_analysis():
    """API endpoint to perform analysis on Net data"""
    if request.method == 'POST':
        data = request.get_json()
    else:
        data = request.args.to_dict()
    
    # Check if files have been uploaded
    if not all(key in session for key in ['main_file_path', 'json_file_path']):
        return jsonify({
            "status": "error",
            "message": "All required files must be uploaded first"
        })
    
    # Initialize Net with the uploaded files
    try:
        net = Net(session['main_file_path'], None, session['json_file_path'])
    except Exception as e:
        logger.error(f"Error initializing Net: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error initializing analysis with uploaded files: {str(e)}"
        })
    
    # Determine which analysis to perform
    analysis_type = data.get('analysis_type')
    result_df = pd.DataFrame()
    analysis_title = "Analysis Results"
    
    try:
        # Validate analysis_type is one of the supported methods
        supported_methods = [
            "get_records_by_netid", "get_unique_chains_by_netid", 
            "get_unique_circuits_by_netid", 
            "get_chains_by_netid", "show_start_end_chain",
            "get_chain_sequence_length", "get_chain_circuit_sequence",
            "get_chain_interval_by_chainid", "get_all_chain_intervals"
        ]
        
        if analysis_type not in supported_methods:
            return jsonify({
                "status": "error",
                "message": f"Unsupported analysis type: {analysis_type}"
            })
            
        if analysis_type in ["get_records_by_netid", "get_unique_chains_by_netid", 
                           "get_unique_circuits_by_netid", 
                           "get_chains_by_netid"]:
            # These methods require net_id
            net_id = int(data.get('net_id', 0))
            
            if net_id <= 0:
                return jsonify({
                    "status": "error",
                    "message": "Valid Net ID is required"
                })
                
            if analysis_type == "get_records_by_netid":
                result_df = net.get_records_by_netid(net_id)
                analysis_title = f"Records for Net ID: {net_id}"
            elif analysis_type == "get_unique_chains_by_netid":
                result_df = net.get_unique_chains_by_netid(net_id)
                analysis_title = f"Unique Chain IDs for Net ID: {net_id}"
            elif analysis_type == "get_unique_circuits_by_netid":
                result_df = net.get_unique_circuits_by_netid(net_id)
                analysis_title = f"Unique Circuit Names for Net ID: {net_id}"
            elif analysis_type == "get_chains_by_netid":
                result_df = net.get_chains_by_netid(net_id)
                analysis_title = f"Chains & Sub-Chains for Net ID: {net_id}"
                
        elif analysis_type in ["show_start_end_chain", "get_chain_sequence_length", "get_chain_circuit_sequence", "get_chain_interval_by_chainid"]:
            # These methods require chain_id
            chain_id = int(data.get('chain_id', 0))
            
            if analysis_type == "show_start_end_chain":
                result_df = net.show_start_end_chain(chain_id)
                analysis_title = f"Start-End of Chain ID: {chain_id}"
            elif analysis_type == "get_chain_sequence_length":
                result_df = net.get_chain_sequence_length(chain_id)
                analysis_title = f"Chain Sequence Length for Chain ID: {chain_id}"
            elif analysis_type == "get_chain_circuit_sequence":
                result_df = net.get_chain_circuit_sequence(chain_id)
                analysis_title = f"Circuit Sequence for Chain ID: {chain_id}"
            elif analysis_type == "get_chain_interval_by_chainid":
                result_df = net.get_chain_interval_by_chainid(chain_id)
                analysis_title = f"Chain Interval for Chain ID: {chain_id}"
                
        elif analysis_type == "get_all_chain_intervals":
            # This method doesn't require any parameters
            result_df = net.get_all_chain_intervals()
            analysis_title = "All Chain Intervals"
        
        # Convert result to HTML
        if result_df.empty:
            result_html = '<div class="alert alert-warning">No records found for the specified criteria.</div>'
        else:
            result_html = dataframe_to_html(result_df)
            
        return jsonify({
            "status": "success", 
            "title": analysis_title,
            "result_html": result_html,
            "row_count": len(result_df)
        })
            
    except Exception as e:
        logger.error(f"Error performing analysis: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error performing analysis: {str(e)}"
        })

@railway_data_visuals_bp.route('/api/data-summary', methods=['GET'])
def get_data_summary():
    """Get a summary of the loaded data"""
    # Check if files have been uploaded
    if not all(key in session for key in ['main_file_path', 'json_file_path']):
        return jsonify({
            "status": "error",
            "message": "All required files must be uploaded first"
        })
    
    try:
        net = Net(session['main_file_path'], None, session['json_file_path'])
        summary = net.data_summary()
        
        # Convert set objects to lists for JSON serialization
        if "main_dataset" in summary and "unique_net_ids" in summary["main_dataset"]:
            summary["main_dataset"]["unique_net_ids"] = list(summary["main_dataset"]["unique_net_ids"])
        if "main_dataset" in summary and "unique_chain_ids" in summary["main_dataset"]:
            summary["main_dataset"]["unique_chain_ids"] = list(summary["main_dataset"]["unique_chain_ids"])
        if "json_dataset" in summary and "unique_net_ids" in summary["json_dataset"]:
            summary["json_dataset"]["unique_net_ids"] = list(summary["json_dataset"]["unique_net_ids"])
            
        return jsonify({
            "status": "success",
            "summary": summary
        })
    except Exception as e:
        logger.error(f"Error getting data summary: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error retrieving data summary: {str(e)}"
        })

@railway_data_visuals_bp.route('/api/use-default-data', methods=['POST'])
def use_default_data():
    """API endpoint to load default data instead of uploading files"""
    try:
        logger.info("Use default data API called")
        
        # Check if default data files are available
        default_data_status = check_default_data_available()
        
        if not default_data_status["all_available"]:
            # Only get the missing required files
            required_files = ["main_file", "json_file", "start_end_file"]
            missing = [file for file in required_files if not default_data_status[file]]
            error_message = f"Required default files not found: {', '.join(missing)}"
            logger.error(error_message)
            logger.info(f"Data folder path: {DATA_FOLDER}")
            return jsonify({
                "status": "error",
                "message": error_message + f". Data folder: {DATA_FOLDER}"
            }), 404
        
        # Set session variables to default file paths
        session['main_file_path'] = DEFAULT_MAIN_DATASET
        session['json_file_path'] = DEFAULT_THIRD_DATASET
        session['start_end_file_path'] = DEFAULT_START_END_DATASET
        
        logger.info(f"Default files set in session: {DEFAULT_MAIN_DATASET}, {DEFAULT_THIRD_DATASET}, {DEFAULT_START_END_DATASET}")
        
        # Initialize Net with the default files
        try:
            # Using the updated Net class constructor parameters
            net = Net(
                main_data_source=DEFAULT_MAIN_DATASET, 
                second_data_source=None, 
                third_data_source=DEFAULT_THIRD_DATASET
            )
            
            # Load the start-end dataset
            net.load_start_end_dataset(DEFAULT_START_END_DATASET)
            
            # Get data summary
            summary = net.data_summary()
            
            # Store in session that we're using default data
            session['using_default_data'] = True
            
            logger.info("Default data loaded successfully")
            
            # Use custom encoder to handle NumPy types
            return json.dumps({
                "status": "success",
                "message": "Default datasets loaded successfully",
                "data_summary": summary,
                "using_default": True
            }, cls=NumpyEncoder), 200, {'Content-Type': 'application/json'}
            
        except Exception as net_error:
            logger.error(f"Error initializing Net with default files: {str(net_error)}")
            return json.dumps({
                "status": "error",
                "message": f"Error processing default datasets: {str(net_error)}"
            }, cls=NumpyEncoder), 500, {'Content-Type': 'application/json'}
            
    except Exception as e:
        logger.error(f"Error loading default data: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Error loading default data: {str(e)}"
        }, cls=NumpyEncoder), 500, {'Content-Type': 'application/json'}

# The upload-start-end route is no longer needed as start-end file
# upload is now handled in the main upload route

@railway_data_visuals_bp.route('/api/check-default-data', methods=['GET'])
def check_default_data():
    """API endpoint to check if default data files are available"""
    try:
        # Check if default data files are available
        default_data_status = check_default_data_available()
        
        # Prepare response
        missing_files = []
        if not default_data_status["all_available"]:
            for file_type, exists in default_data_status.items():
                if not exists and file_type != "all_available":
                    missing_files.append(file_type)
        
        return json.dumps({
            "status": "success",
            "all_available": default_data_status["all_available"],
            "missing": missing_files,
            "data_folder": DATA_FOLDER
        }, cls=NumpyEncoder), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"Error checking default data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error checking default data: {str(e)}"
        }), 500

@railway_data_visuals_bp.route('/api/feature-start-end', methods=['GET', 'POST'])
def feature_start_end_api():
    """API endpoint to get start-end data for a specific Net ID"""
    if request.method == 'POST':
        data = request.get_json()
    else:
        data = request.args.to_dict()
    
    # Check if files have been uploaded
    if not ('main_file_path' in session and 'start_end_file_path' in session):
        return jsonify({
            "status": "error",
            "message": "Required files must be uploaded first"
        })
    
    try:
        # Get Net ID from request
        net_id = data.get('net_id')
        
        # Initialize Net with the uploaded files
        net = Net(session['main_file_path'], None, session.get('json_file_path'))
        
        # Load start-end dataset
        if 'start_end_file_path' in session:
            net.load_start_end_dataset(session['start_end_file_path'])
        
        # Get start-end data for the Net ID
        result_df = net.feature_start_end(net_id)
        
        # Set title
        if net_id:
            analysis_title = f"Start-End Data for Net ID: {net_id}"
        else:
            analysis_title = "All Start-End Data"
        
        # Convert result to HTML
        if result_df.empty:
            result_html = '<div class="alert alert-warning">No records found for the specified criteria.</div>'
        else:
            result_html = dataframe_to_html(result_df)
            
        return jsonify({
            "status": "success", 
            "title": analysis_title,
            "result_html": result_html,
            "row_count": len(result_df)
        })
            
    except Exception as e:
        logger.error(f"Error in feature_start_end: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Error processing start-end data: {str(e)}"
        })