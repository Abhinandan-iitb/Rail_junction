"""
Route controllers for Movement Analysis Railway Visualization application.
Defines API endpoints and page routes.
"""
from flask import Blueprint, jsonify, request, render_template
import pandas as pd
import logging
import os
from werkzeug.utils import secure_filename
from modules.movement_analysis.data_load_movement_analysis import load_routes, get_best_file_of_type, identify_file_type
from modules.movement_analysis.data_load_movement_analysis import get_available_csv_files, has_required_uploads
from modules.movement_analysis.data_filter_movement_analysis import get_circuit_data, get_route_details, calculate_movement_times
from modules.movement_analysis.plot_movement_analysis import generate_plot
from .helper_movement_analysis import validate_route_chart_csv, validate_circuit_data_csv
from .helper_movement_analysis import generate_route_chart_template, generate_Movement_data_template

logger = logging.getLogger(__name__)

# Create Blueprint
main = Blueprint("main", __name__, 
                template_folder='../templates', 
                static_folder=None,
                url_prefix='/movement_analysis')

# Create an uploads directory to store uploaded CSV files
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper Functions
def _extract_routes_from_request(data):
    """Extract and normalize routes from request data"""
    routes = data.get("routes", [])
    if isinstance(routes, str):
        routes = [routes]
    
    if not routes:
        route = data.get("route")
        if route:
            routes = [route]
    
    return routes

def _parse_time_range(data):
    """Parse time range from request and determine if chunked processing is needed"""
    from_time = None
    to_time = None
    chunked_processing = False
    
    if data.get("from_time") and data.get("to_time"):
        from_time = pd.to_datetime(data.get("from_time"))
        to_time = pd.to_datetime(data.get("to_time"))
        
        time_span_days = (to_time - from_time).total_seconds() / (24 * 3600)
        if time_span_days > 7:
            chunked_processing = True
            logger.info(f"Using chunked processing for {time_span_days:.1f} day span")
    
    return from_time, to_time, chunked_processing

def _collect_route_data(routes, from_time, to_time, chunked_processing):
    """Collect circuit data for all selected routes"""
    combined_df = pd.DataFrame()
    movement_counts = {}
    movement_id_field = "Movement_id"
    
    if chunked_processing:
        chunk_size = pd.Timedelta(days=3)
        current_start = from_time
        
        while current_start < to_time:
            current_end = min(current_start + chunk_size, to_time)
            logger.info(f"Processing chunk: {current_start} to {current_end}")
            
            for route_name in routes:
                chunk_df = get_circuit_data(route_name, current_start, current_end)
                if not chunk_df.empty:
                    combined_df = pd.concat([combined_df, chunk_df])
            
            current_start = current_end
    else:
        for route_name in routes:
            df = get_circuit_data(route_name, from_time, to_time)
            if not df.empty:
                if movement_id_field in df.columns:
                    movement_counts[route_name] = df[movement_id_field].nunique()
                combined_df = pd.concat([combined_df, df])
    
    # Calculate movement counts if not populated during standard processing
    if not movement_counts and movement_id_field in combined_df.columns:
        for route_name in routes:
            route_data = combined_df[combined_df["Route_id"] == route_name]
            if not route_data.empty:
                movement_counts[route_name] = route_data[movement_id_field].nunique()
    
    return combined_df, movement_counts

@main.route("/", methods=["GET"])
def index():
    """Renders the Movement Analysis dashboard page"""
    return render_template("movement_analysis.html")

@main.route("/routes", methods=["GET"])
def get_routes():
    """API endpoint to get available routes"""
    try:
        # Clear cache to ensure fresh data is loaded
        from modules.movement_analysis.data_load_movement_analysis import clear_cache
        clear_cache()
        logger.info("Cache cleared before loading routes")
        
        # Check if required uploads exist
        has_required, error_msg = has_required_uploads()
        if not has_required:
            return jsonify({"error": error_msg, "routes": []}), 400
        
        # Log environment info for debugging
        current_dir = os.getcwd()
        logger.info(f"Current working directory: {current_dir}")
        
        # Check upload folder and list available files
        if os.path.exists(UPLOAD_FOLDER):
            files = os.listdir(UPLOAD_FOLDER)
            logger.info(f"Files in upload folder: {files}")
            
            # Check file types for better debugging
            for file_path in get_available_csv_files():
                try:
                    file_type = identify_file_type(file_path)
                    file_name = os.path.basename(file_path)
                    logger.info(f"Found uploaded file: {file_name} (type: {file_type})")
                    
                    # Show a preview of the file content
                    with open(file_path, 'r') as f:
                        head = [next(f) for x in range(3) if x < 3]
                        logger.info(f"First 3 lines of {file_name}: {head}")
                except Exception as e:
                    logger.warning(f"Could not analyze file {file_path}: {str(e)}")
        
        # Load routes
        routes = load_routes()
        
        if routes:
            logger.info(f"Found {len(routes)} routes: {routes}")
        else:
            logger.warning("No routes found")
            
        return jsonify({"routes": routes})
    except Exception as e:
        logger.error(f"Error in get_routes: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@main.route("/route/<route_name>", methods=["GET"])
def route_details(route_name):
    """API endpoint to get details about a specific route"""
    try:
        logger.info(f"Fetching details for route: {route_name}")
        details = get_route_details(route_name)
        
        if details:
            return jsonify({"route": details})
        else:
            return jsonify({"error": "Route not found"}), 404
    except Exception as e:
        logger.error(f"Error fetching route details: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route("/plot", methods=["POST"])
def plot():
    """API endpoint to generate plot data based on selected routes and time range"""
    try:
        has_required, error_msg = has_required_uploads()
        if not has_required:
            return jsonify({
                "plot": f"<div class='alert alert-warning'><i class='fas fa-exclamation-triangle'></i> {error_msg}</div>",
                "stats": {"dataPoints": 0, "avgSpeed": 0, "movements": 0},
                "movementCounts": {},
                "selectedRoutes": []
            }), 400
        
        data = request.json
        routes = _extract_routes_from_request(data)
        
        if not routes:
            return jsonify({
                "plot": "<div class='alert alert-warning'><i class='fas fa-exclamation-triangle'></i> No routes selected.</div>",
            }), 400
        
        from_time, to_time, chunked_processing = _parse_time_range(data)
        
        logger.info(f"Generating timeline plot for {len(routes)} routes: {routes}")
        if from_time and to_time:
            logger.info(f"Time range: {from_time} to {to_time}")
        
        combined_df, movement_counts = _collect_route_data(routes, from_time, to_time, chunked_processing)
        
        if combined_df.empty:
            logger.warning("No data found for selected routes")
            return jsonify({
                "plot": "<div class='alert alert-warning'><i class='fas fa-exclamation-triangle'></i> No data found for the selected routes and time range.</div>",
                "stats": {"dataPoints": 0, "avgSpeed": 0, "movements": 0},
                "movementCounts": {},
                "selectedRoutes": routes
            })
        
        plot_html = generate_plot(combined_df)
        
        movement_id_field = "Movement_id"
        stats = {
            "dataPoints": len(combined_df),
            "avgSpeed": round(combined_df["avg_speed"].mean(), 1) if "avg_speed" in combined_df.columns and not combined_df.empty else 0,
            "movements": combined_df[movement_id_field].nunique() if movement_id_field in combined_df.columns else 1,
            "routes": len(routes)
        }
        
        logger.info(f"Generated timeline plot: {len(combined_df)} points, {stats['movements']} movements, {stats['routes']} routes")
        
        return jsonify({
            "plot": plot_html, 
            "stats": stats,
            "movementCounts": movement_counts,
            "selectedRoutes": routes
        })
    
    except Exception as e:
        logger.error(f"Error in plot endpoint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@main.route("/plot_overview", methods=["POST"])
def plot_overview():
    """Generates a low-detail overview plot for quick initial display"""
    try:
        data = request.json
        routes = _extract_routes_from_request(data)
        
        if not routes:
            return jsonify({
                "plot": "<div class='alert alert-warning'><i class='fas fa-exclamation-triangle'></i> No routes selected.</div>",
            }), 400
            
        from_time, to_time, _ = _parse_time_range(data)
        combined_df, _ = _collect_route_data(routes, from_time, to_time, chunked_processing=False)
        
        if combined_df.empty:
            return jsonify({
                "plot": "<div class='alert alert-warning'><i class='fas fa-exclamation-triangle'></i> No data found for the selected routes and time range.</div>",
                "stats": {"dataPoints": 0, "avgSpeed": 0, "movements": 0}
            })
        
        row_count = len(combined_df)
        plot_html = generate_plot(combined_df, low_detail_mode=True)
        
        movement_id_field = "Movement_id"
        stats = {
            "dataPoints": row_count,
            "avgSpeed": round(combined_df["avg_speed"].mean(), 1) if "avg_speed" in combined_df.columns and not combined_df.empty else 0,
            "movements": combined_df[movement_id_field].nunique() if movement_id_field in combined_df.columns else 1,
            "routes": len(routes)
        }
        
        return jsonify({
            "plot": plot_html, 
            "stats": stats,
            "has_more_detail": row_count > 5000
        })
        
    except Exception as e:
        logger.error(f"Error generating overview plot: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@main.route("/status", methods=["GET"])
def status():
    """API endpoint to check if the Movement Analysis module is operational"""
    try:
        route_count = len(load_routes())
        return jsonify({
            "status": "Movement Analysis module connected and working",
            "routes_available": route_count,
            "version": "2.0.0"
        })
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route("/upload_files", methods=["POST"])
def upload_files():
    """API endpoint to handle file uploads"""
    try:
        response = {}
        
        # Make sure upload folder exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
            logger.info(f"Created upload folder: {UPLOAD_FOLDER}")
        
        # Handle file uploads generically based on content
        uploaded_files = []
        
        # Process all file inputs, regardless of field name
        for field_name in request.files:
            file_obj = request.files[field_name]
            if file_obj.filename != '':
                # Secure the filename and save
                filename = secure_filename(file_obj.filename)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file_obj.save(save_path)
                logger.info(f"Saved uploaded file: {filename} to {save_path}")
                
                # Identify file type
                file_type = identify_file_type(save_path)
                
                if file_type == 'unknown':
                    # Remove file if we don't recognize it
                    os.remove(save_path)
                    error_msg = f"File {filename} doesn't match any expected CSV format"
                    logger.warning(error_msg)
                    response[f'{field_name}_error'] = error_msg
                else:
                    # File is valid, add to list of uploaded files
                    uploaded_files.append((filename, file_type, save_path))
                    response[f'{field_name}_status'] = f"Uploaded {filename} (detected as {file_type})"
                    logger.info(f"File {filename} successfully uploaded and identified as {file_type}")
        
        # If no files were successfully uploaded, return error
        if not uploaded_files:
            return jsonify({"error": "No valid files uploaded"}), 400
            
        # Clear cache after any successful upload
        from modules.movement_analysis.data_load_movement_analysis import clear_cache
        clear_cache()
        logger.info("Cache cleared after successful file upload")
        
        # Check if we now have the required uploads
        has_required, error_msg = has_required_uploads()
        response['system_ready'] = has_required
        if not has_required:
            response['missing'] = error_msg
            
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in file upload: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route("/reset_files", methods=["POST"])
def reset_files():
    """API endpoint to reset uploaded files"""
    try:
        deleted_files = []
        
        if os.path.exists(UPLOAD_FOLDER):
            # Delete all CSV files in the uploads folder
            for file in os.listdir(UPLOAD_FOLDER):
                if file.endswith('.csv'):
                    file_path = os.path.join(UPLOAD_FOLDER, file)
                    os.remove(file_path)
                    deleted_files.append(file)
                    logger.info(f"Removed uploaded file: {file_path}")
        
        # Clear the cache to force reload
        from modules.movement_analysis.data_load_movement_analysis import clear_cache
        clear_cache()
        logger.info("Cache cleared after files reset")
        
        if deleted_files:
            return jsonify({"status": f"Removed {len(deleted_files)} uploaded files", "deleted_files": deleted_files})
        else:
            return jsonify({"status": "No files to reset"})
    
    except Exception as e:
        logger.error(f"Error in reset_files: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route("/route_circuits", methods=["GET"])
def get_route_circuits():
    """API endpoint to get all route circuits from the chart"""
    try:
        # Get route chart file
        route_chart_file = get_best_file_of_type('route_chart')
        
        route_circuits = {}
        
        # Load from route chart file if available
        if route_chart_file:
            logger.info(f"Loading route circuits from route chart file: {route_chart_file}")
            df = pd.read_csv(route_chart_file)
            
            for _, row in df.iterrows():
                route_circuits[str(row['Route_id'])] = row['Route_circuit']
            
            logger.info(f"Loaded {len(route_circuits)} route circuits from route chart file")
            return jsonify(route_circuits)
        
        # If no files found
        logger.warning(f"No route chart file found to extract route circuits")
        return jsonify({}), 404
            
    except Exception as e:
        logger.error(f"Error in get_route_circuits: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@main.route("/movement_times", methods=["POST"])
def movement_times():
    """API endpoint to get movement times for selected routes"""
    try:
        data = request.json
        
        # Get routes
        routes = data.get("routes", [])
        if not routes:
            route_id = data.get("route_id")
            if route_id:
                routes = [route_id]
        
        if not routes:
            return jsonify({"error": "No routes provided"}), 400
        
        # Get time range
        from_time = None
        to_time = None
        if data.get("from_time") and data.get("to_time"):
            from_time = pd.to_datetime(data.get("from_time"))
            to_time = pd.to_datetime(data.get("to_time"))
        
        logger.info(f"Fetching movement times for routes: {routes}")
        
        # Get movement times
        all_movement_times = []
        
        for route_id in routes:
            movement_times_df = calculate_movement_times(route_id, from_time, to_time)
            
            if not movement_times_df.empty:
                movement_times_df["Route_id"] = route_id
                
                for _, row in movement_times_df.iterrows():
                    movement_dict = {
                        "Route_id": row["Route_id"],
                        "Movement_id": row["Movement_id"],
                        "Start_Time": row["Start_Time"].isoformat(),
                        "End_Time": row["End_Time"].isoformat(),
                        "Total_Journey_Time_Seconds": float(row["Total_Journey_Time_Seconds"]),
                        "Total_Journey_Time_Minutes": float(row["Total_Journey_Time_Minutes"]),
                        "Total_Circuit_Time_Seconds": float(row["Total_Circuit_Time_Seconds"]),
                        "Total_Circuit_Time_Minutes": float(row["Total_Circuit_Time_Minutes"]),
                        "Circuit_Count": int(row["Circuit_Count"]),
                        "Average_Circuit_Duration": float(row["Average_Circuit_Duration"])
                    }
                    all_movement_times.append(movement_dict)
        
        if not all_movement_times:
            logger.warning(f"No movement times found for routes: {routes}")
        
        return jsonify({
            "movement_times": all_movement_times,
            "route_count": len(routes)
        })
    
    except Exception as e:
        logger.error(f"Error in movement_times endpoint: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@main.route("/template/<template_type>", methods=["GET"])
def get_template(template_type):
    """Provide downloadable CSV templates"""
    try:
        if template_type not in ['route_chart', 'circuit_data']:
            return jsonify({"error": "Invalid template type"}), 400
        
        # Get template as StringIO object
        if template_type == 'route_chart':
            template = generate_route_chart_template()
            filename = 'Route_chart_template.csv'
        else:  # circuit_data
            template = generate_Movement_data_template()
            filename = 'Movement_data_template.csv'
        
        # Return as downloadable CSV
        from flask import Response
        return Response(
            template.getvalue(),
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error generating template: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route("/file_info", methods=["GET"])
def file_info():
    """API endpoint to get information about currently uploaded files"""
    try:
        from modules.movement_analysis.data_load_movement_analysis import find_files_by_type
        
        # Get counts for each file type
        route_chart_files = find_files_by_type('route_chart')
        circuit_data_files = find_files_by_type('circuit_data') 
        
        # Get information about all available files
        files = []
        for csv_file in get_available_csv_files():
            file_type = identify_file_type(csv_file)
            file_stats = os.stat(csv_file)
            files.append({
                "name": os.path.basename(csv_file),
                "type": file_type,
                "size": file_stats.st_size,
                "last_modified": file_stats.st_mtime
            })
        
        # Check if the system has required files
        has_required, error_msg = has_required_uploads()
        
        return jsonify({
            "files": files,
            "counts": {
                "route_chart": len(route_chart_files),
                "circuit_data": len(circuit_data_files),
            },
            "system_ready": has_required,
            "message": "" if has_required else error_msg
        })
    
    except Exception as e:
        logger.error(f"Error in file_info: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main.route("/route_details", methods=["GET"])
def get_all_route_details():
    """API endpoint to get details about all routes including their names"""
    try:
        # Get the appropriate route chart file
        route_chart_file = get_best_file_of_type('route_chart')
        
        if not route_chart_file:
            logger.warning("No route chart file found to extract route names")
            return jsonify({}), 404
            
        # Read the route chart file
        df = pd.read_csv(route_chart_file)
        
        # Create a dictionary with route details
        route_details = {}
        
        # Check if 'Route_name' column exists
        if 'Route_name' in df.columns:
            for _, row in df.iterrows():
                route_id = str(row['Route_id']).strip()
                route_details[route_id] = {
                    'Route_name': row['Route_name'],
                    'Route_circuit': row['Route_circuit'] if 'Route_circuit' in row else ''
                }
            
            logger.info(f"Loaded {len(route_details)} route details with names")
            return jsonify(route_details)
        else:
            logger.warning("Route_name column not found in route chart file")
            return jsonify({}), 404
            
    except Exception as e:
        logger.error(f"Error fetching route details: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@main.route("/validate_csv", methods=["POST"])
def validate_csv():
    """API endpoint to validate a CSV file without uploading it"""
    try:
        # Check if file was provided
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
            
        # Create a temporary file path
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, secure_filename(file.filename))
        
        # Save file temporarily
        file.save(temp_path)
        
        # Try to identify file type
        file_type = identify_file_type(temp_path)
        
        # Validate based on file type
        if file_type == 'route_chart':
            is_valid, message = validate_route_chart_csv(temp_path)
        elif file_type == 'circuit_data':
            is_valid, message = validate_circuit_data_csv(temp_path)
        else:
            is_valid = False
            message = "Unknown file format. Please ensure your CSV file follows one of the supported templates."
        
        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass
            
        return jsonify({
            "is_valid": is_valid,
            "message": message,
            "detected_type": file_type
        })
        
    except Exception as e:
        logger.error(f"Error validating CSV: {str(e)}")
        return jsonify({"error": str(e)}), 500
