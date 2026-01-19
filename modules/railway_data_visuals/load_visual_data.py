"""
Module to handle file uploads and data loading for Railway Data Visuals.
This module separates the file handling logic from the routes.
"""

import os
import logging
from werkzeug.utils import secure_filename

# Configure logging
logger = logging.getLogger(__name__)

# Define global constants with environment overrides
PROJECT_ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

ALLOWED_EXTENSIONS = {'csv'}

UPLOAD_FOLDER = os.environ.get(
    "RAILWAY_VISUALS_UPLOAD_DIR",
    os.path.join(PROJECT_ROOT, 'uploads', 'railway_data_visuals')
)

DATA_FOLDER = os.environ.get(
    "RAILWAY_VISUALS_DATA_DIR",
    os.path.join(PROJECT_ROOT, 'Data')
)

DEFAULT_MAIN_DATASET = os.environ.get(
    "RAILWAY_VISUALS_MAIN_DATA",
    os.path.join(DATA_FOLDER, 'Circuit_interval_with_net_chain_shunting_karimnagar.csv')
)
DEFAULT_SECOND_DATASET = os.environ.get(
    "RAILWAY_VISUALS_SECOND_DATA",
    os.path.join(DATA_FOLDER, 'start_end_data_karimnagar.csv')
)
DEFAULT_THIRD_DATASET = os.environ.get(
    "RAILWAY_VISUALS_THIRD_DATA",
    os.path.join(DATA_FOLDER, 'final_sucessor_to_chain_karimnagar.csv')
)
DEFAULT_START_END_DATASET = os.environ.get(
    "RAILWAY_VISUALS_START_END_DATA",
    os.path.join(DATA_FOLDER, 'start_end_data_updated.csv')
)

def check_allowed_file(filename, allowed_extensions=None):
    """
    Check if the file has an allowed extension
    
    Args:
        filename (str): The filename to check
        allowed_extensions (set): Set of allowed file extensions
        
    Returns:
        bool: True if the file is allowed, False otherwise
    """
    if not allowed_extensions:
        allowed_extensions = ALLOWED_EXTENSIONS
        
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def handle_file_upload(file, upload_folder=None, allowed_extensions=None, file_type=None, use_default=True):
    """
    Handle file upload and save to server
    
    Args:
        file: The file object from request.files
        upload_folder (str): Directory to save the file
        allowed_extensions (set): Set of allowed file extensions
        file_type (str): Type of file ('main_file', 'second_file', 'json_file') for default fallback
        use_default (bool): Whether to use default files if upload fails
        
    Returns:
        tuple: (success, message, filepath)
    """
    try:
        if not upload_folder:
            upload_folder = UPLOAD_FOLDER
            
        if not allowed_extensions:
            allowed_extensions = ALLOWED_EXTENSIONS
            
        if file.filename == '':
            # If no file is selected, use default file if allowed
            if use_default and file_type:
                return use_default_file(file_type)
            return False, "No file selected", None
        
        # Check if the file has an allowed extension
        if not check_allowed_file(file.filename, allowed_extensions):
            # If extension is not allowed, use default file if allowed
            if use_default and file_type:
                return use_default_file(file_type)
            return False, f"File extension not allowed. Allowed extensions: {', '.join(allowed_extensions)}", None
            
        # Secure the filename to prevent security issues
        filename = secure_filename(file.filename)
            
        # Ensure upload folder exists
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Verify the file exists and is readable
        if not os.path.exists(filepath):
            logger.error(f"File {filename} was not saved properly")
            if use_default and file_type:
                return use_default_file(file_type)
            return False, "File was not saved properly", None
            
        # Log success
        logger.info(f"File {filename} uploaded successfully to {filepath}")
        return True, f"File {filename} uploaded successfully", filepath
        
    except Exception as e:
        logger.error(f"Error handling file upload: {str(e)}")
        if use_default and file_type:
            return use_default_file(file_type)
        return False, f"Error handling file upload: {str(e)}", None

def use_default_file(file_type):
    """
    Use the default file for a given file type
    
    Args:
        file_type (str): Type of file ('main_file', 'second_file', 'json_file')
        
    Returns:
        tuple: (success, message, filepath)
    """
    if file_type == 'main_file':
        default_file = DEFAULT_MAIN_DATASET
    elif file_type == 'second_file':
        default_file = DEFAULT_SECOND_DATASET
    elif file_type == 'json_file' or file_type == 'third_file':
        default_file = DEFAULT_THIRD_DATASET
    else:
        return False, f"Unknown file type: {file_type}", None
        
    # Check if default file exists
    if not os.path.exists(default_file):
        logger.error(f"Default {file_type} not found at {default_file}")
        return False, f"Default {file_type} not found", None
        
    logger.info(f"Using default {file_type} from {default_file}")
    return True, f"Using default {file_type}", default_file

def validate_uploaded_files(files_dict, required_types=None):
    """
    Validate that all required file types are present in the uploaded files
    
    Args:
        files_dict (dict): Dictionary of file objects
        required_types (list): List of required file types
        
    Returns:
        tuple: (is_valid, missing_files)
    """
    if not required_types:
        required_types = ['main_file', 'second_file', 'json_file']
        
    missing_files = [req for req in required_types if req not in files_dict or not files_dict[req]]
    
    return len(missing_files) == 0, missing_files

def get_file_extension(filename):
    """
    Get the file extension from a filename
    
    Args:
        filename (str): The filename
        
    Returns:
        str: The file extension or empty string if no extension
    """
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()

def create_upload_directory():
    """
    Create the upload directory if it doesn't exist
    
    Returns:
        bool: True if directory exists or was created, False otherwise
    """
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating upload directory: {str(e)}")
        return False

def check_default_data_available():
    """
    Check if the default data files are available
    
    Returns:
        dict: Status of each default file
    """
    status = {
        "main_file": os.path.exists(DEFAULT_MAIN_DATASET),
        "json_file": os.path.exists(DEFAULT_THIRD_DATASET),
        "start_end_file": os.path.exists(DEFAULT_START_END_DATASET)
    }
    
    # We don't require the second file for the application to work
    # So we exclude it from the all_available check
    required_files = ["main_file", "json_file", "start_end_file"]
    status["all_available"] = all(status[file] for file in required_files)
    
    if not status["all_available"]:
        # Create Data folder if it doesn't exist
        try:
            os.makedirs(DATA_FOLDER, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create Data folder: {e}")
    
    # Log the results
    if status["all_available"]:
        logger.info("All required default data files are available")
    else:
        missing = [file for file in required_files if not status[file]]
        logger.warning(f"Missing required default data files: {missing}")
        logger.info(f"Default data folder path: {DATA_FOLDER}")
    
    return status