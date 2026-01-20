import pandas as pd
import os
import logging
import glob

logger = logging.getLogger(__name__)

_route_circuits_cache = {}
_file_type_cache = {}

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

def clear_cache():
    """Clear all caches to force reloading data"""
    global _route_circuits_cache, _file_type_cache
    _route_circuits_cache.clear()
    _file_type_cache.clear()
    logger.info("All caches cleared")

def identify_file_type(filepath):
    """
    Identify CSV file type based on column structure.
    
    Args:
        filepath: Path to CSV file
    
    Returns:
        'route_chart', 'circuit_data', or 'unknown'
    """
    if filepath in _file_type_cache:
        return _file_type_cache[filepath]
    
    try:
        df = pd.read_csv(filepath, nrows=1)
        columns = set(df.columns.str.lower())
        
        if 'route_id' in columns and 'route_circuit' in columns:
            file_type = 'route_chart'
        elif ('circuit_name' in columns or 'circuit' in columns) and \
             (('down_timestamp' in columns and 'up_timestamp' in columns) or \
              ('down_date' in columns and 'up_date' in columns)):
            file_type = 'circuit_data'
        else:
            file_type = 'unknown'
            
        _file_type_cache[filepath] = file_type
        return file_type
        
    except Exception as e:
        logger.error(f"Error identifying file type for {filepath}: {e}")
        return 'unknown'

def get_available_csv_files():
    """Get all CSV files in the uploads folder"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        logger.info(f"Created upload folder: {UPLOAD_FOLDER}")
        return []
        
    csv_files = glob.glob(os.path.join(UPLOAD_FOLDER, "*.csv"))
    if csv_files:
        logger.info(f"Found {len(csv_files)} CSV files in upload folder")
    return csv_files

def find_files_by_type(file_type):
    """
    Find all uploaded files of a specific type.
    
    Args:
        file_type: 'route_chart' or 'circuit_data'
    
    Returns:
        List of file paths matching the type
    """
    return [file for file in get_available_csv_files() 
            if identify_file_type(file) == file_type]

def has_uploaded_files():
    """Check if any usable CSV files exist in the uploads folder"""
    return any(identify_file_type(file) in ('route_chart', 'circuit_data') 
               for file in get_available_csv_files())

def has_required_uploads():
    """
    Check if we have the required uploaded files to run the system.
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    route_chart_files = find_files_by_type('route_chart')
    circuit_data_files = find_files_by_type('circuit_data')
    
    if route_chart_files and circuit_data_files:
        return True, ""
    
    if not has_uploaded_files():
        return False, "No valid CSV files have been uploaded. Please upload both a route chart file and a circuit data file."
    
    if route_chart_files and not circuit_data_files:
        return False, "Route chart file(s) uploaded but circuit data file is missing."
    
    if not route_chart_files and circuit_data_files:
        return False, "Circuit data file(s) uploaded but route chart file is missing."
    
    return False, "Missing required files. Please upload appropriate CSV files."

def get_best_file_of_type(file_type):
    """
    Get the most recent file of a specific type.
    
    Args:
        file_type: 'route_chart' or 'circuit_data'
    
    Returns:
        Path to the most recent matching file or None
    """
    matching_files = find_files_by_type(file_type)
    
    if not matching_files:
        logger.warning(f"No {file_type} files found in uploads folder")
        return None
    
    if len(matching_files) > 1:
        newest_file = max(matching_files, key=os.path.getmtime)
        logger.info(f"Multiple {file_type} files found, using most recent: {os.path.basename(newest_file)}")
        return newest_file
    
    logger.info(f"Using {file_type} file: {os.path.basename(matching_files[0])}")
    return matching_files[0]

def load_routes():
    """
    Load route names from uploaded CSV files.
    
    Returns:
        List of unique route IDs
    """
    try:
        has_required, error_msg = has_required_uploads()
        if not has_required:
            logger.error(f"Cannot load routes: {error_msg}")
            return []
            
        route_chart_file = get_best_file_of_type('route_chart')
        if not route_chart_file:
            logger.error("Could not find route chart file")
            return []
        
        logger.info(f"Loading routes from: {route_chart_file}")
        df = pd.read_csv(route_chart_file)
        
        if 'Route_id' not in df.columns:
            logger.error("Column 'Route_id' not found in route chart file")
            return []
        
        routes = df["Route_id"].astype(str).str.strip().tolist()
        logger.info(f"Successfully loaded {len(routes)} routes")
        return routes
    
    except Exception as e:
        logger.error(f"Error loading routes: {e}")
        return []

def get_route_circuits():
    """
    Read and cache route circuits from uploaded files.
    
    Returns:
        Dictionary mapping route IDs to lists of circuits in sequence
    """
    if _route_circuits_cache:
        return _route_circuits_cache
        
    try:
        has_required, error_msg = has_required_uploads()
        if not has_required:
            logger.error(f"Cannot load route circuits: {error_msg}")
            return {}
            
        route_chart_file = get_best_file_of_type('route_chart')
        if not route_chart_file:
            logger.error("Could not find route chart file")
            return {}
        
        logger.info(f"Loading route circuits from: {route_chart_file}")
        route_df = pd.read_csv(route_chart_file)
        
        route_circuits = {}
        for _, row in route_df.iterrows():
            route_id = str(row['Route_id']).strip()
            circuits = [circuit.strip() for circuit in str(row['Route_circuit']).split('-')]
            route_circuits[route_id] = circuits
            
        logger.info(f"Loaded {len(route_circuits)} route sequences")
        _route_circuits_cache.update(route_circuits)
        return _route_circuits_cache
        
    except Exception as e:
        logger.error(f"Error reading route circuits: {e}")
        return {}
