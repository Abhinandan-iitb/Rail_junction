import pandas as pd
import os
import logging
import traceback
import glob

logger = logging.getLogger(__name__)

# Add route circuits cache
_route_circuits_cache = {}
_file_type_cache = {}

# Define path for uploaded files
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

def clear_cache():
    """
    Clear all caches to force reloading data
    """
    global _route_circuits_cache, _file_type_cache
    _route_circuits_cache = {}
    _file_type_cache = {}
    logger.info("All caches cleared")

def identify_file_type(filepath):
    """
    Identify the type of CSV file based on its columns
    
    Args:
        filepath (str): Path to the CSV file
    
    Returns:
        str: File type ('route_chart', 'circuit_data', 'unknown')
    """
    # Check cache first
    if filepath in _file_type_cache:
        return _file_type_cache[filepath]
    
    try:
        # Read just the header to check columns
        df = pd.read_csv(filepath, nrows=1)
        columns = set(df.columns.str.lower())
        
        # Identify route chart files (containing Route_id and Route_circuit columns)
        if 'route_id' in columns and 'route_circuit' in columns:
            _file_type_cache[filepath] = 'route_chart'
            return 'route_chart'
            
        # Identify circuit data files using either timestamp or date/time format
        if ('circuit_name' in columns or 'circuit' in columns):
            # Check for timestamp columns
            if ('down_timestamp' in columns and 'up_timestamp' in columns):
                _file_type_cache[filepath] = 'circuit_data'
                return 'circuit_data'
            # Check for traditional date/time columns
            elif ('down_date' in columns and 'up_date' in columns):
                _file_type_cache[filepath] = 'circuit_data'
                return 'circuit_data'
            
        # Unknown file type
        _file_type_cache[filepath] = 'unknown'
        return 'unknown'
        
    except Exception as e:
        logger.error(f"Error identifying file type for {filepath}: {str(e)}")
        return 'unknown'

def get_available_csv_files():
    """
    Get a list of all available CSV files in the uploads folder
    
    Returns:
        list: List of file paths
    """
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        logger.info(f"Created upload folder: {UPLOAD_FOLDER}")
        return []
        
    # Find all CSV files in uploads folder
    csv_files = glob.glob(os.path.join(UPLOAD_FOLDER, "*.csv"))
    if csv_files:
        logger.info(f"Found {len(csv_files)} CSV files in upload folder")
    return csv_files

def find_files_by_type(file_type):
    """
    Find all uploaded files of a specific type
    
    Args:
        file_type (str): Type of file to find ('route_chart', 'circuit_data')
    
    Returns:
        list: Paths to matching files
    """
    csv_files = get_available_csv_files()
    matching_files = []
    
    for file in csv_files:
        if identify_file_type(file) == file_type:
            matching_files.append(file)
            
    return matching_files

def has_uploaded_files():
    """Check if any usable CSV files exist in the uploads folder
    
    Returns:
        bool: True if any relevant CSV files exist in the uploads folder
    """
    # Get all CSV files
    csv_files = get_available_csv_files()
    
    # Check if any file can be identified as a supported type
    for file in csv_files:
        file_type = identify_file_type(file)
        if file_type in ('route_chart', 'circuit_data'):
            return True
            
    return False

def has_required_uploads():
    """Check if we have the required uploaded files to run the system
    
    Returns:
        tuple: (bool, str) - (True if we have required files, error message if not)
    """
    # Find files by type
    route_chart_files = find_files_by_type('route_chart')
    circuit_data_files = find_files_by_type('circuit_data')
    
    if route_chart_files and circuit_data_files:
        return True, ""
    elif not has_uploaded_files():
        return False, "No valid CSV files have been uploaded. Please upload both a route chart file and a circuit data file."
    elif route_chart_files and not circuit_data_files:
        return False, "Route chart file(s) uploaded but circuit data file is missing."
    elif not route_chart_files and circuit_data_files:
        return False, "Circuit data file(s) uploaded but route chart file is missing."
    else:
        return False, "Missing required files. Please upload appropriate CSV files."

def get_best_file_of_type(file_type):
    """
    Get the best available file of a specific type
    
    Args:
        file_type (str): Type of file to find ('route_chart', 'circuit_data')
    
    Returns:
        str: Path to best matching file or None
    """
    matching_files = find_files_by_type(file_type)
    
    if not matching_files:
        logger.warning(f"No {file_type} files found in uploads folder")
        return None
    
    # Select the most recent file if multiple are available
    if len(matching_files) > 1:
        newest_file = max(matching_files, key=os.path.getmtime)
        logger.info(f"Multiple {file_type} files found, using the most recent: {os.path.basename(newest_file)}")
        return newest_file
    
    logger.info(f"Using {file_type} file: {os.path.basename(matching_files[0])}")
    return matching_files[0]

def load_routes():
    """
    Loads route names from any suitable uploaded CSV file.
    
    Returns:
        list: List of unique route IDs found in the CSV
    """
    try:
        # Check if we have required uploads
        has_required, error_msg = has_required_uploads()
        if not has_required:
            logger.error(f"Cannot load routes: {error_msg}")
            return []
            
        # First try to find a route chart file
        route_chart_file = get_best_file_of_type('route_chart')
        if route_chart_file:
            logger.info(f"Loading routes from route chart file: {route_chart_file}")
            df = pd.read_csv(route_chart_file)
            if 'Route_id' in df.columns:
                routes = df["Route_id"].astype(str).str.strip().tolist()
                logger.info(f"Successfully loaded {len(routes)} routes from route chart")
                return routes
            else:
                logger.error(f"Column 'Route_id' not found in route chart file")
        
        # If we get here, we couldn't load routes from any file
        logger.error("Could not load routes from any uploaded file")
        return []
    
    except Exception as e:
        logger.error(f"Error in load_routes: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def get_route_circuits():
    """
    Read and cache the route circuits from any suitable uploaded file.
    
    Returns:
        dict: Mapping of route IDs to lists of circuits in sequence
    """
    global _route_circuits_cache
    
    if _route_circuits_cache:
        return _route_circuits_cache
        
    route_circuits = {}
    try:
        # Check if we have required uploads
        has_required, error_msg = has_required_uploads()
        if not has_required:
            logger.error(f"Cannot load route circuits: {error_msg}")
            return {}
            
        # First try to find a route chart file
        route_chart_file = get_best_file_of_type('route_chart')
        if route_chart_file:
            logger.info(f"Loading route circuits from route chart file: {route_chart_file}")
            route_df = pd.read_csv(route_chart_file)
            
            for _, row in route_df.iterrows():
                route_id = str(row['Route_id']).strip()
                # Split by dash to get individual circuits and strip any whitespace
                circuits = [circuit.strip() for circuit in str(row['Route_circuit']).split('-')]
                route_circuits[route_id] = circuits
                
            logger.info(f"Loaded {len(route_circuits)} route sequences from route chart file")
                    
        _route_circuits_cache = route_circuits
        logger.info(f"Total routes with circuit sequences: {len(route_circuits)}")
        return route_circuits
        
    except Exception as e:
        logger.error(f"Error reading route circuits: {str(e)}")
        return {}
