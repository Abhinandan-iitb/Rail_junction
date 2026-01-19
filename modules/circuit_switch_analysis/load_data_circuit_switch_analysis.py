"""
Data Loading Module for Circuit and Switch Analysis

This module handles loading and preprocessing of circuit and switch data from CSV files,
with support for both default internal files and custom uploaded files.
"""

import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)


def _get_candidate_data_directories():
    """
    Returns list of directories to search for default CSV data files.
    
    Returns:
        List of unique directory paths to search
    """
    candidates = [
        os.environ.get("PHASE1_DATA_DIR"),
        os.path.join(PROJECT_ROOT, "uploads"),
        os.path.join(PROJECT_ROOT, "data"),
        os.path.join(PROJECT_ROOT, "Data"),
    ]

    return [path for path in candidates if path and path not in candidates[:candidates.index(path)]]


def _resolve_data_path(env_var_name, default_filename):
    """
    Resolves data file path using environment variables and known directories.
    
    Args:
        env_var_name: Environment variable name to check for explicit path
        default_filename: Default filename to search for
        
    Returns:
        Resolved file path (may not exist if not found)
    """
    explicit_path = os.environ.get(env_var_name)
    if explicit_path:
        return explicit_path

    for directory in _get_candidate_data_directories():
        candidate = os.path.join(directory, default_filename)
        if os.path.exists(candidate):
            return candidate

        if os.path.isdir(directory):
            for entry in os.listdir(directory):
                if entry.lower() == default_filename.lower():
                    return os.path.join(directory, entry)

    candidate_dirs = _get_candidate_data_directories()
    fallback_dir = candidate_dirs[0] if candidate_dirs else PROJECT_ROOT
    return os.path.join(fallback_dir, default_filename)


def _process_timestamps(df, timestamp_prefix, date_col, time_col):
    """
    Processes and standardizes timestamp columns in DataFrame.
    
    Args:
        df: DataFrame to process
        timestamp_prefix: Prefix for timestamp column (e.g., 'Down', 'Up')
        date_col: Date column name
        time_col: Time column name
        
    Returns:
        Boolean indicating if combined timestamp format was detected
    """
    timestamp_col = f"{timestamp_prefix}_timestamp"
    
    if timestamp_col in df.columns:
        logger.info(f"Detected combined datetime format ({timestamp_col})")
        return True
    
    if f"{timestamp_prefix}_time" in df.columns and f"{timestamp_prefix}_date" not in df.columns:
        logger.info(f"Detected combined datetime format ({timestamp_prefix}_time)")
        df.rename(columns={f"{timestamp_prefix}_time": timestamp_col}, inplace=True)
        return True
    
    logger.info(f"Detected separate date/time columns for {timestamp_prefix}")
    if date_col in df.columns and time_col in df.columns:
        df[timestamp_col] = pd.to_datetime(
            df[date_col] + ' ' + df[time_col], 
            errors='coerce'
        )
    return False


def _ensure_datetime_type(df, column_name):
    """
    Ensures a DataFrame column is of datetime type.
    
    Args:
        df: DataFrame to process
        column_name: Column name to check and convert
    """
    if column_name in df.columns and not pd.api.types.is_datetime64_any_dtype(df[column_name]):
        df[column_name] = pd.to_datetime(df[column_name], errors='coerce')


def _handle_missing_timestamps(df, start_col, end_col, down_timestamp, up_timestamp, is_circuit):
    """
    Handles missing timestamp values by setting defaults.
    
    Args:
        df: DataFrame to process
        start_col: Start time column name
        end_col: End time column name
        down_timestamp: Down timestamp column name
        up_timestamp: Up timestamp column name
        is_circuit: Boolean indicating if processing circuit data
    """
    now = pd.Timestamp.now()
    
    for idx, row in df.iterrows():
        if pd.isnull(row[start_col]):
            default_start = now - pd.Timedelta(hours=1) if not is_circuit else now
            df.at[idx, start_col] = default_start
            df.at[idx, down_timestamp if is_circuit else up_timestamp] = default_start
        
        if pd.isnull(row[end_col]):
            df.at[idx, end_col] = now
            df.at[idx, up_timestamp if is_circuit else down_timestamp] = now


def _calculate_durations(df, start_col, end_col, duration_col):
    """
    Calculates duration in seconds between start and end times.
    
    Args:
        df: DataFrame to process
        start_col: Start time column name
        end_col: End time column name
        duration_col: Duration column name to populate
    """
    df[duration_col] = 0
    
    for idx, row in df.iterrows():
        try:
            df.at[idx, duration_col] = (row[end_col] - row[start_col]).total_seconds()
        except Exception as e:
            logger.warning(f"Error calculating duration for row {idx}: {str(e)}")
            df.at[idx, duration_col] = 0


def _process_dataframe(df, is_circuit=True):
    """
    Processes circuit or switch DataFrame to standardize timestamps and calculate durations.
    
    Args:
        df: DataFrame to process
        is_circuit: Boolean indicating if processing circuit data (True) or switch data (False)
        
    Returns:
        Processed DataFrame with standardized timestamps and calculated durations
    """
    if df is None or df.empty:
        return df
        
    if is_circuit:
        down_prefix, up_prefix = 'Down', 'Up'
        start_col, end_col = 'Start_Time_c', 'End_Time_c'
        duration_col = 'Duration_sec_c'
    else:
        down_prefix, up_prefix = 'Down', 'Up'
        start_col, end_col = 'Start_Time_s', 'End_Time_s'
        duration_col = 'Duration_sec_s'
    
    _process_timestamps(df, down_prefix, f'{down_prefix}_date', f'{down_prefix}_time')
    _process_timestamps(df, up_prefix, f'{up_prefix}_date', f'{up_prefix}_time')
    
    down_timestamp = f'{down_prefix}_timestamp'
    up_timestamp = f'{up_prefix}_timestamp'
    
    _ensure_datetime_type(df, down_timestamp)
    _ensure_datetime_type(df, up_timestamp)
    
    if is_circuit:
        df[start_col] = df[down_timestamp]
        df[end_col] = df[up_timestamp]
    else:
        df[start_col] = df[up_timestamp]
        df[end_col] = df[down_timestamp]
    
    _handle_missing_timestamps(df, start_col, end_col, down_timestamp, up_timestamp, is_circuit)
    _calculate_durations(df, start_col, end_col, duration_col)
    
    return df.dropna(how='all')


def _get_empty_dataframes():
    """
    Creates empty DataFrames with appropriate column structure.
    
    Returns:
        Tuple of (empty_circuit_df, empty_switch_df)
    """
    empty_circuit_df = pd.DataFrame(
        columns=['Circuit_name', 'Down_timestamp', 'Up_timestamp', 'Duration']
    )
    empty_switch_df = pd.DataFrame(
        columns=['Switch_name', 'Up_timestamp', 'Down_timestamp', 'Duration']
    )
    return empty_circuit_df, empty_switch_df


def _load_csv_file(file_path, file_type, is_circuit=True):
    """
    Loads and processes a CSV file.
    
    Args:
        file_path: Path to the CSV file
        file_type: Type of file ('circuit' or 'switch') for logging
        is_circuit: Boolean indicating if this is circuit data
        
    Returns:
        Processed DataFrame or empty DataFrame on error
    """
    empty_circuit_df, empty_switch_df = _get_empty_dataframes()
    empty_df = empty_circuit_df if is_circuit else empty_switch_df
    
    if not os.path.exists(file_path):
        logger.error(
            f"Error: {file_type.capitalize()} data file not found at {file_path} "
            f"(searched directories: {_get_candidate_data_directories()})"
        )
        return empty_df
    
    try:
        df = pd.read_csv(file_path)
        logger.debug(f"Loaded {file_type} data from CSV: {len(df)} rows")
        return _process_dataframe(df, is_circuit=is_circuit)
    except Exception as e:
        logger.error(f"Error reading {file_type} data file: {str(e)}")
        return empty_df


def load_data_from_database(circuit_path=None, switch_path=None):
    """
    Loads circuit and switch data from CSV files.
    
    Supports both default internal files and custom uploaded files with automatic
    path resolution through environment variables and search directories.
    
    Args:
        circuit_path: Path to custom circuit data CSV file (optional)
        switch_path: Path to custom switch data CSV file (optional)
        
    Returns:
        Tuple of (circuit_df, switch_df) DataFrames
    """
    try:
        default_circuit_csv_path = _resolve_data_path(
            "PHASE1_CIRCUIT_DATA_PATH",
            "gandhipuram_circuit_interval.csv"
        )
        default_switch_csv_path = _resolve_data_path(
            "PHASE1_SWITCH_DATA_PATH",
            "switch_intervals.csv"
        )
        
        circuit_csv_path = circuit_path or default_circuit_csv_path
        switch_csv_path = switch_path or default_switch_csv_path
        
        logger.info(f"Loading circuit data from: {circuit_csv_path}")
        logger.info(f"Loading switch data from: {switch_csv_path}")
        
        circuit_df = _load_csv_file(circuit_csv_path, 'circuit', is_circuit=True)
        switch_df = _load_csv_file(switch_csv_path, 'switch', is_circuit=False)
        
        return circuit_df, switch_df
        
    except Exception as e:
        logger.error(f"ERROR loading data from CSV files: {str(e)}")
        empty_circuit_df, empty_switch_df = _get_empty_dataframes()
        return empty_circuit_df, empty_switch_df
