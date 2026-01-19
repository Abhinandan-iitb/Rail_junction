"""
Data Filtering Module for Circuit and Switch Analysis

This module provides functions to filter, validate, and process circuit and switch
data based on time ranges, durations, and matching criteria.
"""

import re
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def validate_circuit(circuit_name, circuit_df):
    """
    Validates if a circuit name exists in the dataset.
    
    Args:
        circuit_name: Circuit identifier to validate
        circuit_df: DataFrame containing circuit data
        
    Returns:
        Boolean indicating if circuit exists
    """
    try:
        if circuit_df is None:
            logger.error("Cannot validate circuit - circuit_df is None")
            return False
        
        if 'Circuit_name' not in circuit_df.columns:
            logger.error("Circuit_name column not found in circuit_df")
            return False
            
        return circuit_name in circuit_df["Circuit_name"].values
    except Exception as e:
        logger.error(f"Error in validate_circuit: {str(e)}")
        return False


def _get_csv_columns(filtered_data, interval_type='circuit'):
    """
    Determines which columns to export for CSV based on available data.
    
    Args:
        filtered_data: DataFrame to check for columns
        interval_type: Type of data ('circuit' or 'switch')
        
    Returns:
        List of available columns for CSV export
    """
    if 'Down_timestamp' in filtered_data.columns or 'Up_timestamp' in filtered_data.columns:
        if interval_type == 'circuit':
            base_columns = ['Interval_id', 'Circuit_name', 'Down_timestamp', 'Up_timestamp', 
                          'Duration', 'switch_name', 'switch_status', 'Duration_sec_c']
        else:
            base_columns = ['Interval_id', 'Switch_name', 'Up_timestamp', 'Down_timestamp', 
                          'Duration', 'Duration_sec_s']
    else:
        if interval_type == 'circuit':
            base_columns = ['Interval_id', 'Circuit_name', 'Down_date', 'Down_time', 
                          'Up_date', 'Up_time', 'Duration', 'switch_name', 
                          'switch_status', 'Duration_sec_c']
        else:
            base_columns = ['Interval_id', 'Switch_name', 'Up_date', 'Up_time', 
                          'Down_date', 'Down_time', 'Duration', 'Duration_sec_s']
    
    return [col for col in base_columns if col in filtered_data.columns]


def filter_circuit_data(circuit_name, circuit_df, from_time, to_time, min_duration, for_csv=False):
    """
    Filters circuit data based on time range and minimum duration.
    
    Args:
        circuit_name: Circuit identifier to filter
        circuit_df: DataFrame containing circuit data
        from_time: Start time for filtering
        to_time: End time for filtering
        min_duration: Minimum duration threshold (seconds)
        for_csv: If True, returns formatted data for CSV export
        
    Returns:
        Filtered DataFrame or empty DataFrame if no data matches
    """
    try:
        if circuit_df is None or circuit_df.empty:
            logger.error("Cannot filter circuit data - circuit_df is None or empty")
            return pd.DataFrame()
            
        required_columns = ['Circuit_name', 'Start_Time_c', 'End_Time_c', 'Duration_sec_c']
        missing_columns = [col for col in required_columns if col not in circuit_df.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns in circuit_df: {missing_columns}")
            return pd.DataFrame()
            
        filtered_data = circuit_df[
            (circuit_df['Circuit_name'] == circuit_name) &
            (circuit_df['Start_Time_c'] >= from_time) &
            (circuit_df['End_Time_c'] <= to_time) &
            (circuit_df['Duration_sec_c'] >= min_duration)
        ]
        
        if for_csv and not filtered_data.empty:
            available_cols = _get_csv_columns(filtered_data, 'circuit')
            return filtered_data[available_cols].copy()
        
        return filtered_data
    except Exception as e:
        logger.error(f"Error in filter_circuit_data: {str(e)}")
        return pd.DataFrame()


def filter_short_duration_circuits(circuit_name, circuit_df, from_time, to_time, max_duration, for_csv=False):
    """
    Filters circuit data for short duration events (duration <= max_duration).
    
    Args:
        circuit_name: Circuit identifier to filter
        circuit_df: DataFrame containing circuit data
        from_time: Start time for filtering
        to_time: End time for filtering
        max_duration: Maximum duration threshold (seconds)
        for_csv: If True, returns formatted data for CSV export
        
    Returns:
        Filtered DataFrame with short duration events
    """
    try:
        filtered_data = circuit_df[
            (circuit_df['Circuit_name'] == circuit_name) &
            (circuit_df['Start_Time_c'] >= from_time) &
            (circuit_df['End_Time_c'] <= to_time) &
            (circuit_df['Duration_sec_c'] <= max_duration)
        ]
        
        if for_csv and not filtered_data.empty:
            available_cols = _get_csv_columns(filtered_data, 'circuit')
            result = filtered_data[available_cols].copy()
            result['Event_Type'] = 'Short_Duration'
            return result
        
        return filtered_data
    except Exception as e:
        logger.error(f"Error in filter_short_duration_circuits: {str(e)}")
        return pd.DataFrame()


def get_matching_switches(circuit_name, switch_df):
    """
    Finds switches matching a circuit based on numeric substring extraction.
    
    Args:
        circuit_name: Circuit identifier to match
        switch_df: DataFrame containing switch data
        
    Returns:
        DataFrame of matching switches or None if no matches found
    """
    if not circuit_name or not isinstance(circuit_name, str):
        logger.error(f"Invalid circuit_name: {circuit_name}")
        return None
        
    if switch_df is None or switch_df.empty or 'Switch_name' not in switch_df.columns:
        logger.error("Invalid switch DataFrame")
        return None
    
    circuit_numeric = re.findall(r'\d+', circuit_name)
    if not circuit_numeric:
        logger.warning(f"No numeric part found in circuit name: {circuit_name}")
        return None

    circuit_numeric = circuit_numeric[0]
    logger.debug(f"Looking for switches matching circuit number: {circuit_numeric}")

    def extract_numeric(switch_name):
        if not isinstance(switch_name, str):
            return None
        numbers = re.findall(r'\d+', switch_name)
        return numbers[0] if numbers else None

    switch_df['Numeric_Switch'] = switch_df['Switch_name'].apply(extract_numeric)
    matching_switches = switch_df[switch_df['Numeric_Switch'] == circuit_numeric]

    if matching_switches.empty:
        logger.info(f"No matching switches found for circuit: {circuit_name}")
        return None
        
    logger.info(f"Found {len(matching_switches)} matching switches for circuit: {circuit_name}")
    return matching_switches


def _ensure_switch_columns(switch_df):
    """
    Ensures required time and duration columns exist in switch DataFrame.
    
    Args:
        switch_df: DataFrame containing switch data
        
    Returns:
        Tuple of (success: bool, modified_df or None)
    """
    df = switch_df.copy()
    
    if 'Start_Time_s' not in df.columns:
        if 'Up_timestamp' in df.columns:
            df['Start_Time_s'] = df['Up_timestamp']
        else:
            logger.error("Missing Start_Time_s or Up_timestamp column in switch data")
            return False, None
            
    if 'End_Time_s' not in df.columns:
        if 'Down_timestamp' in df.columns:
            df['End_Time_s'] = df['Down_timestamp']
        else:
            logger.error("Missing End_Time_s or Down_timestamp column in switch data")
            return False, None
    
    if not pd.api.types.is_datetime64_any_dtype(df['Start_Time_s']):
        df['Start_Time_s'] = pd.to_datetime(df['Start_Time_s'], errors='coerce')
        
    if not pd.api.types.is_datetime64_any_dtype(df['End_Time_s']):
        df['End_Time_s'] = pd.to_datetime(df['End_Time_s'], errors='coerce')
            
    if 'Duration_sec_s' not in df.columns:
        logger.warning("Missing Duration_sec_s column - calculating from timestamps")
        df['Duration_sec_s'] = (df['End_Time_s'] - df['Start_Time_s']).dt.total_seconds()
    
    return True, df


def filter_switch_data(matching_switches, from_time, to_time, min_duration, for_csv=False):
    """
    Filters switch data based on time range and minimum duration.
    
    Args:
        matching_switches: DataFrame containing matching switch data
        from_time: Start time for filtering
        to_time: End time for filtering
        min_duration: Minimum duration threshold (seconds)
        for_csv: If True, returns formatted data for CSV export
        
    Returns:
        Filtered DataFrame or None if no data matches
    """
    try:
        if matching_switches is None:
            return None

        success, prepared_df = _ensure_switch_columns(matching_switches)
        if not success:
            return None

        filtered_data = prepared_df[
            (prepared_df['Start_Time_s'] >= from_time) &
            (prepared_df['End_Time_s'] <= to_time) &
            (prepared_df['Duration_sec_s'] >= min_duration)
        ].dropna(subset=['Start_Time_s', 'End_Time_s'])
        
        if filtered_data.empty:
            logger.debug(f"Switch filtering resulted in empty dataset. Original had {len(matching_switches)} rows.")
            return None
        
        if for_csv:
            available_cols = _get_csv_columns(filtered_data, 'switch')
            return filtered_data[available_cols].copy()
            
        return filtered_data
    except Exception as e:
        logger.error(f"Error in filter_switch_data: {str(e)}")
        return None


def filter_short_duration_switches(matching_switches, from_time, to_time, max_duration, for_csv=False):
    """
    Filters switch data for short duration events (duration <= max_duration).
    
    Args:
        matching_switches: DataFrame containing matching switch data
        from_time: Start time for filtering
        to_time: End time for filtering
        max_duration: Maximum duration threshold (seconds)
        for_csv: If True, returns formatted data for CSV export
        
    Returns:
        Filtered DataFrame with short duration events or None if no data matches
    """
    try:
        if matching_switches is None:
            logger.warning("filter_short_duration_switches received None for matching_switches")
            return None

        logger.info(f"Filtering short duration switches with max_duration={max_duration}s")
        logger.info(f"Initial switch data size: {len(matching_switches)} rows")
        
        success, prepared_df = _ensure_switch_columns(matching_switches)
        if not success:
            return None
        
        filtered_data = prepared_df[
            (prepared_df['Start_Time_s'] >= from_time) & 
            (prepared_df['End_Time_s'] <= to_time) &
            (prepared_df['Duration_sec_s'] <= max_duration)
        ].dropna(subset=['Start_Time_s', 'End_Time_s', 'Duration_sec_s'])
        
        logger.info(f"After filtering: {len(filtered_data)} rows")
        
        if filtered_data.empty:
            return None
        
        if for_csv:
            available_cols = _get_csv_columns(filtered_data, 'switch')
            result = filtered_data[available_cols].copy()
            result['Event_Type'] = 'Short_Duration'
            return result

        return filtered_data
    except Exception as e:
        logger.error(f"Error in filter_short_duration_switches: {str(e)}")
        return None
