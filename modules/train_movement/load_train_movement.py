"""
Train Movement Data Loading Module

This module handles loading and preprocessing railway data for train movement visualization.
It provides functions to load node, edge, and circuit interval data, and transforms
circuit intervals into a time-ordered event log.
"""
import os
import pandas as pd
from typing import Dict, List, Tuple, Set, Any, Optional, Union
from flask import current_app, session

#######################
# FILE HANDLING       #
#######################

def get_data_paths(use_uploaded: bool = False) -> Tuple[str, str, str]:
    """
    Get file paths for data sources.
    
    Args:
        use_uploaded: Flag to use uploaded files instead of default files
        
    Returns:
        Tuple of file paths (nodes_path, edges_path, circuit_path)
    """
    if use_uploaded and 'uploaded_files' in session:
        # Use uploaded files from session
        uploaded_files = session['uploaded_files']
        nodes_path = uploaded_files['nodes']
        edges_path = uploaded_files['edges'] 
        circuit_path = uploaded_files['circuit']
        current_app.logger.info(f"Using uploaded files: {nodes_path}, {edges_path}, {circuit_path}")
    else:
        # Use default data paths
        data_dir = os.path.join(current_app.root_path, 'Data')
        nodes_path = os.path.join(data_dir, 'nodes.csv')
        edges_path = os.path.join(data_dir, 'edges.csv')
        circuit_path = os.path.join(data_dir, 'final_circuit_interval_chain_id_net_id_route_id.csv')
    
    return nodes_path, edges_path, circuit_path

#######################
# DATA PROCESSING     #
#######################

def modify_track_circuit(row: pd.Series) -> str:
    """
    Modify Circuit_Name ID based on switch position.
    
    For tracks controlled by switches, the ID is prefixed with 'N' or 'R'
    depending on the switch position (Normal or Reverse).
    
    Args:
        row: DataFrame row containing circuit information
    
    Returns:
        Modified track circuit ID
    """
    if row['switch_name'] == "No switch":
        return row['Circuit_Name']
    elif "Switch position N" in row['switch_status']:
        return row['Circuit_Name']
    elif "Switch position R" in row['switch_status']:
        return row['Circuit_Name']
    else:
        return row['Circuit_Name']

def create_event_log(circuit_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create event log DataFrame from circuit intervals.
    
    Transforms circuit interval data (with down and up times) into a time-ordered
    sequence of signal events.
    
    Args:
        circuit_df: DataFrame with circuit interval data
        
    Returns:
        Event log DataFrame with signal events in chronological order
    """
    # Create empty list for log entries
    log_entries = []
    
    # Process each circuit interval
    for _, row in circuit_df.iterrows():
        # Add 'down' event
        log_entries.append({
            'SIGNAL NAME': row['Circuit_Name'],
            'SIGNAL STATUS': 'Down',
            'SIGNAL TIME': pd.to_datetime(row['Down_timestamp'])
        })
        
        # Add 'up' event
        log_entries.append({
            'SIGNAL NAME': row['Circuit_Name'],
            'SIGNAL STATUS': 'Up',
            'SIGNAL TIME': pd.to_datetime(row['Up_timestamp'])
        })
    
    # Create DataFrame from log entries and sort by time
    log_df = pd.DataFrame(log_entries)
    log_df.columns = log_df.columns.str.strip()
    log_df['SIGNAL TIME'] = pd.to_datetime(log_df['SIGNAL TIME'])
    log_df.sort_values(by='SIGNAL TIME', inplace=True)
    log_df.reset_index(drop=True, inplace=True)
    
    return log_df

#######################
# MAIN FUNCTION       #
#######################

def load_and_process_data(use_uploaded: bool = False) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Load and process railway data files.
    
    This function loads nodes, edges, and circuit interval data, processes track circuits 
    based on switch positions, and creates an event log from circuit intervals.
    
    Args:
        use_uploaded: Flag to use uploaded files instead of default files
        
    Returns:
        Tuple containing:
        - DataFrame with node data
        - DataFrame with edge data
        - DataFrame with log events
        - DataFrame with circuit data
    """
    try:
        # Get file paths
        nodes_path, edges_path, circuit_path = get_data_paths(use_uploaded)
        
        # Load data files
        nodes_df = pd.read_csv(nodes_path)
        edges_df = pd.read_csv(edges_path)
        circuit_df = pd.read_csv(circuit_path)
        
        # Process circuit data
        circuit_df['Circuit_Name'] = circuit_df.apply(modify_track_circuit, axis=1)
        circuit_df = circuit_df.dropna(subset=['Down_timestamp', 'Up_timestamp'])
        
        # Create event log from circuit intervals
        log_df = create_event_log(circuit_df)
        
        return nodes_df, edges_df, log_df, circuit_df
        
    except FileNotFoundError as e:
        current_app.logger.error(f"Data file not found: {str(e)}")
        return None, None, None, None
    except pd.errors.EmptyDataError as e:
        current_app.logger.error(f"Empty data file: {str(e)}")
        return None, None, None, None
    except Exception as e:
        current_app.logger.error(f"Error loading and processing data: {str(e)}")
        return None, None, None, None
