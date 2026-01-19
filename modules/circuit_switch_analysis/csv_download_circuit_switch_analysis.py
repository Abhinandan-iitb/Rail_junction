"""
CSV Data Export Module for Circuit and Switch Analysis

This module provides functionality to prepare and export circuit and switch
analysis data to CSV format with proper filtering and data source labeling.
"""

import logging
import pandas as pd

from .filter_data_circuit_switch_analysis import (
    validate_circuit,
    filter_circuit_data,
    filter_short_duration_circuits,
    get_matching_switches,
    filter_switch_data,
    filter_short_duration_switches
)

logger = logging.getLogger(__name__)


def prepare_data_for_csv(data):
    """
    Prepares filtered data for CSV export by selecting relevant columns.
    
    Args:
        data: pandas DataFrame containing circuit or switch data
        
    Returns:
        DataFrame with only relevant columns for export
    """
    if data is None or data.empty:
        return pd.DataFrame()

    if 'Down_timestamp' in data.columns:
        columns_to_export = [
            'Circuit_name', 'switch_name', 'Down_timestamp', 'Up_timestamp', 
            'Duration', 'Duration_sec_c'
        ]
    else:
        columns_to_export = [
            'Circuit_name', 'switch_name', 'Down_date', 'Down_Time',
            'Up_date', 'Up_Time', 'Duration', 'Duration_sec_c'
        ]
    
    valid_columns = [col for col in columns_to_export if col in data.columns]
    return data[valid_columns]


def prepare_csv_data(circuit_name, additional_circuits, circuit_df, switch_df, 
                     from_time, to_time, min_duration, max_duration):
    """
    Prepare comprehensive data for CSV export from all data sources.
    
    Args:
        circuit_name: Primary circuit identifier
        additional_circuits: List of additional circuit identifiers
        circuit_df: DataFrame containing circuit data
        switch_df: DataFrame containing switch data
        from_time: Start time for filtering
        to_time: End time for filtering
        min_duration: Minimum duration threshold (seconds)
        max_duration: Maximum duration threshold for short events (seconds)
        
    Returns:
        Dictionary containing filtered data from all sources
    """
    result = {
        'primary_circuit': None,
        'additional_circuits': {},
        'primary_switch': None,
        'short_duration_circuit': None,
        'short_duration_switch': None
    }
    
    if circuit_name and validate_circuit(circuit_name, circuit_df):
        result['primary_circuit'] = filter_circuit_data(
            circuit_name, circuit_df, from_time, to_time, min_duration, for_csv=True
        )
        result['short_duration_circuit'] = filter_short_duration_circuits(
            circuit_name, circuit_df, from_time, to_time, max_duration, for_csv=True
        )
    
    if additional_circuits:
        for add_circuit in additional_circuits:
            if add_circuit != circuit_name and validate_circuit(add_circuit, circuit_df):
                result['additional_circuits'][add_circuit] = filter_circuit_data(
                    add_circuit, circuit_df, from_time, to_time, min_duration, for_csv=True
                )
    
    if circuit_name:
        matching_switches = get_matching_switches(circuit_name, switch_df)
        if matching_switches is not None:
            result['primary_switch'] = filter_switch_data(
                matching_switches, from_time, to_time, min_duration, for_csv=True
            )
            result['short_duration_switch'] = filter_short_duration_switches(
                matching_switches, from_time, to_time, max_duration, for_csv=True
            )
    
    return result


def combine_dataframes_for_csv(data_dict):
    """
    Combines multiple dataframes into a single CSV-exportable dataframe.
    
    Args:
        data_dict: Dictionary containing DataFrames from various sources
        
    Returns:
        Combined DataFrame with Data_Source column for identification
    """
    dataframes = []
    
    source_mappings = [
        ('primary_circuit', 'Primary Circuit'),
        ('primary_switch', 'Associated Switch'),
        ('short_duration_circuit', 'Short Duration Circuit Event'),
        ('short_duration_switch', 'Short Duration Switch Event')
    ]
    
    for key, source_label in source_mappings:
        df = data_dict.get(key)
        if df is not None and not df.empty:
            df_copy = df.copy()
            df_copy['Data_Source'] = source_label
            dataframes.append(df_copy)
    
    for circuit_name, df in data_dict.get('additional_circuits', {}).items():
        if not df.empty:
            df_copy = df.copy()
            df_copy['Data_Source'] = f'Additional Circuit: {circuit_name}'
            dataframes.append(df_copy)
    
    return pd.concat(dataframes, ignore_index=True, sort=False) if dataframes else pd.DataFrame()


def create_csv_from_dataframe(df, filename_prefix):
    """
    Generate CSV data from a DataFrame.
    
    Args:
        df: pandas DataFrame to convert
        filename_prefix: Prefix for the filename
        
    Returns:
        Tuple of (csv_string, filename_prefix) or None if DataFrame is empty
    """
    if df.empty:
        return None
    
    csv_buffer = df.to_csv(index=False)
    return csv_buffer, filename_prefix


def _add_source_label(df, source_label, circuit_name=None):
    """
    Add data source label and optionally circuit name to DataFrame.
    
    Args:
        df: DataFrame to label
        source_label: Label describing the data source
        circuit_name: Optional circuit name to add
        
    Returns:
        Labeled DataFrame copy or None if input is empty
    """
    if df is None or df.empty:
        return None
    
    df_copy = df.copy()
    df_copy['Data_Source'] = source_label
    
    if circuit_name:
        df_copy['Circuit_Name'] = circuit_name
    
    return df_copy


def _collect_data_from_circuits(circuit_name, additional_circuits, circuit_df, 
                                 from_time, to_time, threshold, filter_func, 
                                 source_prefix, is_short_duration=False):
    """
    Generic function to collect data from primary and additional circuits.
    
    Args:
        circuit_name: Primary circuit identifier
        additional_circuits: List of additional circuits
        circuit_df: Circuit DataFrame
        from_time: Start time filter
        to_time: End time filter
        threshold: Duration threshold (min or max)
        filter_func: Function to apply filtering
        source_prefix: Prefix for data source label
        is_short_duration: Whether this is for short duration events
        
    Returns:
        Combined DataFrame from all circuits
    """
    dataframes = []
    
    if circuit_name and validate_circuit(circuit_name, circuit_df):
        primary_data = filter_func(
            circuit_name, circuit_df, from_time, to_time, threshold, for_csv=True
        )
        
        labeled_df = _add_source_label(
            primary_data,
            f'Primary Circuit{" Short Duration" if is_short_duration else ""}'
        )
        if labeled_df is not None:
            dataframes.append(labeled_df)
    
    if additional_circuits:
        for add_circuit in additional_circuits:
            if add_circuit != circuit_name and validate_circuit(add_circuit, circuit_df):
                add_data = filter_func(
                    add_circuit, circuit_df, from_time, to_time, threshold, for_csv=True
                )
                
                label = f'{source_prefix}: {add_circuit}'
                labeled_df = _add_source_label(add_data, label)
                if labeled_df is not None:
                    dataframes.append(labeled_df)
    
    return pd.concat(dataframes, ignore_index=True, sort=False) if dataframes else pd.DataFrame()


def _collect_switch_data_from_circuits(circuit_name, additional_circuits, circuit_df, 
                                       switch_df, from_time, to_time, threshold, 
                                       filter_func, is_short_duration=False):
    """
    Generic function to collect switch data from circuits.
    
    Args:
        circuit_name: Primary circuit identifier
        additional_circuits: List of additional circuits
        circuit_df: Circuit DataFrame
        switch_df: Switch DataFrame
        from_time: Start time filter
        to_time: End time filter
        threshold: Duration threshold
        filter_func: Function to apply filtering
        is_short_duration: Whether this is for short duration events
        
    Returns:
        Combined DataFrame from all circuit switches
    """
    dataframes = []
    circuits_to_process = [(circuit_name, 'Primary Circuit')]
    
    if additional_circuits:
        circuits_to_process.extend(
            [(circuit, 'Additional Circuit') for circuit in additional_circuits 
             if circuit != circuit_name and validate_circuit(circuit, circuit_df)]
        )
    
    for circuit, source_type in circuits_to_process:
        matching_switches = get_matching_switches(circuit, switch_df)
        
        if matching_switches is not None:
            switch_data = filter_func(
                matching_switches, from_time, to_time, threshold, for_csv=True
            )
            
            label = f'{source_type}: {circuit}'
            labeled_df = _add_source_label(switch_data, label, circuit_name=circuit)
            if labeled_df is not None:
                dataframes.append(labeled_df)
    
    return pd.concat(dataframes, ignore_index=True, sort=False) if dataframes else pd.DataFrame()


def collect_circuit_data(circuit_name, additional_circuits, circuit_df, 
                        from_time, to_time, min_duration_seconds):
    """
    Collect regular circuit data from primary and additional circuits.
    
    Args:
        circuit_name: Primary circuit identifier
        additional_circuits: List of additional circuits
        circuit_df: DataFrame containing circuit data
        from_time: Start time for filtering
        to_time: End time for filtering
        min_duration_seconds: Minimum duration threshold
        
    Returns:
        Combined DataFrame with all circuit data
    """
    return _collect_data_from_circuits(
        circuit_name, additional_circuits, circuit_df,
        from_time, to_time, min_duration_seconds,
        filter_circuit_data, 'Additional Circuit'
    )


def collect_short_duration_circuit_data(circuit_name, additional_circuits, circuit_df, 
                                       from_time, to_time, max_duration_seconds):
    """
    Collect short duration circuit event data.
    
    Args:
        circuit_name: Primary circuit identifier
        additional_circuits: List of additional circuits
        circuit_df: DataFrame containing circuit data
        from_time: Start time for filtering
        to_time: End time for filtering
        max_duration_seconds: Maximum duration threshold for short events
        
    Returns:
        Combined DataFrame with short duration circuit events
    """
    return _collect_data_from_circuits(
        circuit_name, additional_circuits, circuit_df,
        from_time, to_time, max_duration_seconds,
        filter_short_duration_circuits, 'Additional Circuit Short Duration',
        is_short_duration=True
    )


def collect_switch_data(circuit_name, additional_circuits, circuit_df, switch_df, 
                       from_time, to_time, min_duration_seconds):
    """
    Collect switch data associated with circuits.
    
    Args:
        circuit_name: Primary circuit identifier
        additional_circuits: List of additional circuits
        circuit_df: DataFrame containing circuit data
        switch_df: DataFrame containing switch data
        from_time: Start time for filtering
        to_time: End time for filtering
        min_duration_seconds: Minimum duration threshold
        
    Returns:
        Combined DataFrame with all switch data
    """
    return _collect_switch_data_from_circuits(
        circuit_name, additional_circuits, circuit_df, switch_df,
        from_time, to_time, min_duration_seconds, filter_switch_data
    )


def collect_short_duration_switch_data(circuit_name, additional_circuits, circuit_df, 
                                      switch_df, from_time, to_time, max_duration_seconds):
    """
    Collect short duration switch event data.
    
    Args:
        circuit_name: Primary circuit identifier
        additional_circuits: List of additional circuits
        circuit_df: DataFrame containing circuit data
        switch_df: DataFrame containing switch data
        from_time: Start time for filtering
        to_time: End time for filtering
        max_duration_seconds: Maximum duration threshold for short events
        
    Returns:
        Combined DataFrame with short duration switch events
    """
    return _collect_switch_data_from_circuits(
        circuit_name, additional_circuits, circuit_df, switch_df,
        from_time, to_time, max_duration_seconds, filter_short_duration_switches,
        is_short_duration=True
    )
