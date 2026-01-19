"""
Helper Module for Railway Movement Analysis
Combines configuration, CSV templates, and file operations
"""
import os
import io
import pandas as pd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION SETTINGS
# ============================================================================

# Base directory path (override with MOVEMENT_ANALYSIS_PROJECT_ROOT if provided)
PROJECT_ROOT = os.environ.get(
    "MOVEMENT_ANALYSIS_PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

# Data paths (can be overridden per environment)
DATA_DIR = os.environ.get("MOVEMENT_ANALYSIS_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
ROUTE_DATA_PATH = os.environ.get(
    "MOVEMENT_ANALYSIS_ROUTE_DATA_PATH",
    os.path.join(DATA_DIR, "Route_table.csv")
)
TRACK_CIRCUIT_DATA_PATH = os.environ.get(
    "MOVEMENT_ANALYSIS_TRACK_CIRCUIT_DATA_PATH",
    os.path.join(DATA_DIR, "Track_circuit_table.csv")
)

# Alternative search paths for data files (fallbacks)
ALTERNATIVE_DATA_PATHS = [
    DATA_DIR,
    "./data",
    "../data",
    "../../data",
    os.path.join(PROJECT_ROOT, "Data"),
    os.path.join(PROJECT_ROOT, "uploads")
]

# Plotting settings
PLOT_COLORS = {
    "UP": "green",
    "DOWN": "red",
    "NORMAL": "blue",
    "BACKGROUND": "#f8f9fa"
}

# Default plot dimensions
PLOT_HEIGHT = 600
PLOT_MARGIN = dict(l=180, r=50, t=70, b=50)

# ============================================================================
# CSV TEMPLATE GENERATION
# ============================================================================

def generate_route_chart_template():
    """
    Generate a template CSV file for route chart data
    
    Returns:
        StringIO: CSV file content as a string buffer
    """
    # Create sample data matching the requested format
    data = {
        'Route_id': ['R1', 'R2', 'R3', 'R4'],
        'Route_name': ['main_line_up', 'main_line_down', 'loop_s01', 'loop_s02'],
        'Route_circuit': [
            'C01_TPR-10TPR-BRAC_VPR-101BTPR-103BTPR-OMATPR-OMBTPR-104BTPR-102BTPR-H02TPR-09TPR',
            '09TPR-H02TPR-102BTPR-104BTPR-OMBTPR-OMATPR-103BTPR-101BTPR-BRAC_VPR-10TPR-C01_TPR',
            'C01_TPR-10TPR-BRAC_VPR-101BTPR-101ATPR-02ATPR-02BTPR',
            'C01_TPR-10TPR-BRAC_VPR-101BTPR-103BTPR-103ATPR-01ATPR-01BTPR-106BTPR'
        ]
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Write to string buffer
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return output

def generate_Movement_data_template():
    """
    Generate a template CSV file for movement data with the requested format
    
    Returns:
        StringIO: CSV file content as a string buffer
    """
    # Create sample data matching the requested format with fixed dates
    data = {
        'Interval_id': ['T1153', 'T880', 'T1014', 'T236'],
        'Circuit_Name': ['C01_TPR', '10TPR', 'BRAC_VPR', '101BTPR'],
        'Down_timestamp': [
            '2025-07-09 22:44:32',
            '2025-07-09 22:44:40',
            '2025-07-09 22:44:57',
            '2025-07-09 22:45:20'
        ],
        'Up_timestamp': [
            '2025-07-09 22:46:04',
            '2025-07-09 22:46:33',
            '2025-07-09 22:46:56',
            '2025-07-09 22:47:12'
        ],
        'Duration': ['00:01:32', '00:01:53', '00:02:24', '00:02:20'],
        'switch_name': ['No switch', 'No switch', 'No switch', '101_NWKR'],
        'switch_status': ['Switch_position_N', 'Switch_position_N', 'Switch_position_N', 'Switch_position_N'],
        'Movement_id': ['1', '1', '1', '1'],
        'Route_id': ['R1', 'R1', 'R1', 'R1'],
        'Route_name': ['S0102', 'S0102', 'S0102', 'S0102']
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Write to string buffer without instructions
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return output

# REMOVED: Combined data template is no longer supported
# Users must upload separate route chart and circuit data files
# def generate_combined_data_template():
#     """Generate a template CSV file for combined route and circuit data"""
#     pass

# ============================================================================
# CSV VALIDATION
# ============================================================================

def validate_route_chart_csv(file_path):
    """
    Validate that a CSV file conforms to the route chart format
    
    Args:
        file_path (str): Path to the CSV file
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Check required columns
        required_columns = ['Route_id', 'Route_circuit']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return False, f"Missing required columns: {', '.join(missing_columns)}"
        
        # Check for empty values in required columns
        for col in required_columns:
            if df[col].isnull().any():
                return False, f"Column '{col}' contains empty values"
        
        # Check route_circuit format (should have at least one dash)
        invalid_routes = df[~df['Route_circuit'].str.contains('-')]
        if not invalid_routes.empty:
            return False, f"Invalid route circuit format in rows: {invalid_routes.index.tolist()}"
        
        return True, "Valid route chart CSV"
        
    except Exception as e:
        logger.error(f"Error validating route chart CSV: {str(e)}")
        return False, f"Validation error: {str(e)}"

def validate_circuit_data_csv(file_path):
    """
    Validate that a CSV file conforms to the circuit data format
    
    Args:
        file_path (str): Path to the CSV file
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Check circuit name column
        if not ('Circuit_Name' in df.columns or 'Circuit' in df.columns):
            return False, "Missing 'Circuit_Name' or 'Circuit' column"
        
        # Check timestamp format
        has_timestamps = 'Down_timestamp' in df.columns and 'Up_timestamp' in df.columns
        has_date_time = 'Down_date' in df.columns and 'Down_time' in df.columns and 'Up_date' in df.columns and 'Up_time' in df.columns
        
        if not (has_timestamps or has_date_time):
            return False, "Missing timestamp columns. Need either Down_timestamp/Up_timestamp OR Down_date/Down_time/Up_date/Up_time"
        
        # If using timestamps, check for valid datetime format
        if has_timestamps:
            try:
                pd.to_datetime(df['Down_timestamp'])
                pd.to_datetime(df['Up_timestamp'])
            except:
                return False, "Invalid datetime format in timestamp columns"
        
        # If using date/time columns, check for valid format
        if has_date_time:
            try:
                pd.to_datetime(df['Down_date'] + ' ' + df['Down_time'])
                pd.to_datetime(df['Up_date'] + ' ' + df['Up_time'])
            except:
                return False, "Invalid datetime format in date/time columns"
        
        return True, "Valid circuit data CSV"
        
    except Exception as e:
        logger.error(f"Error validating circuit data CSV: {str(e)}")
        return False, f"Validation error: {str(e)}"

# REMOVED: Combined data validation is no longer supported
# Users must upload separate route chart and circuit data files
# def validate_combined_data_csv(file_path):
#     """Validate that a CSV file conforms to the combined data format"""
#     pass

# ============================================================================
# FILE DETECTION AND ANALYSIS
# ============================================================================

def detect_file_format(file_path):
    """
    Detect the format of a CSV file based on its columns
    
    Args:
        file_path (str): Path to the CSV file
        
    Returns:
        dict: Information about the detected file format
    """
    try:
        # Read the first few rows
        df = pd.read_csv(file_path, nrows=5)
        columns = set(col.lower() for col in df.columns)
        
        # Check for route chart format
        if "route_id" in columns and "route_circuit" in columns:
            return {
                "type": "route_chart",
                "description": "Route chart defining route IDs and their circuit sequences",
                "required_columns": ["Route_id", "Route_circuit"],
                "example_data": df.head(3).to_dict(orient="records")
            }
            
        # Check for track circuit table format
        if "circuit_name" in columns and "down_date" in columns and "up_date" in columns:
            return {
                "type": "circuit_data",
                "description": "Track circuit data",
                "required_columns": ["Circuit_Name", "Down_date", "Down_time", "Up_date", "Up_time"],
                "example_data": df.head(3).to_dict(orient="records")
            }
                
        # Unknown format
        return {
            "type": "unknown",
            "description": "File format not recognized",
            "found_columns": list(columns)
        }
            
    except Exception as e:
        logger.error(f"Error detecting file format: {str(e)}")
        return {
            "type": "error",
            "description": f"Error analyzing file: {str(e)}"
        }

def list_uploaded_files(upload_folder):
    """
    Get information about all uploaded files
    
    Args:
        upload_folder (str): Path to the uploads folder
        
    Returns:
        list: Information about each uploaded file
    """
    if not os.path.exists(upload_folder):
        return []
        
    file_info = []
    
    for filename in os.listdir(upload_folder):
        if filename.lower().endswith('.csv'):
            file_path = os.path.join(upload_folder, filename)
            try:
                # Get file stats
                stats = os.stat(file_path)
                format_info = detect_file_format(file_path)
                
                file_info.append({
                    "name": filename,
                    "path": file_path,
                    "size": stats.st_size,
                    "modified": stats.st_mtime,
                    "format": format_info["type"],
                    "description": format_info.get("description", "Unknown format")
                })
            except Exception as e:
                logger.error(f"Error analyzing {filename}: {str(e)}")
                file_info.append({
                    "name": filename,
                    "path": file_path,
                    "error": str(e)
                })
                
    return file_info
