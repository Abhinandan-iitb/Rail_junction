"""
Railway Visualization Filter Features Module

This module provides filtering functionality for railway visualization data,
including datetime filtering, route filtering, and related utility functions.
"""
import pandas as pd
from typing import List, Optional, Dict, Tuple, Set, Any
from datetime import datetime
from flask import current_app


def apply_datetime_filter(
    log_df: pd.DataFrame, 
    start_datetime: Optional[datetime] = None, 
    end_datetime: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Filter signal log DataFrame based on start and end datetime.
    
    Args:
        log_df: DataFrame containing signal log data
        start_datetime: Optional start datetime for filtering
        end_datetime: Optional end datetime for filtering
        
    Returns:
        Filtered DataFrame based on datetime range
    """
    filtered_df = log_df.copy()
    
    # Apply start datetime filter if provided
    if start_datetime is not None:
        filtered_df = filtered_df[filtered_df['SIGNAL TIME'] >= start_datetime]
        
    # Apply end datetime filter if provided
    if end_datetime is not None:
        filtered_df = filtered_df[filtered_df['SIGNAL TIME'] <= end_datetime]
    
    # Reset index after filtering
    filtered_df.reset_index(drop=True, inplace=True)
    
    current_app.logger.info(f"Datetime filter applied: {len(filtered_df)} rows from {len(log_df)} original rows")
    
    return filtered_df


def apply_route_filter(
    log_df: pd.DataFrame, 
    circuit_df: pd.DataFrame,
    route_id: str
) -> pd.DataFrame:
    """
    Filter signal log DataFrame based on route ID.
    
    Args:
        log_df: DataFrame containing signal log data
        circuit_df: DataFrame containing circuit and route information
        route_id: Route ID to filter by (e.g., "R1", "R2")
        
    Returns:
        Filtered DataFrame containing only signals for the specified route
    """
    # Extract track circuits belonging to the specified route
    route_circuits = set(circuit_df[circuit_df['Route_id'] == route_id]['Circuit_Name'].unique())
    
    # Filter log DataFrame to include only signals from the specified route
    if route_circuits:
        filtered_df = log_df[log_df['SIGNAL NAME'].isin(route_circuits)]
        filtered_df.reset_index(drop=True, inplace=True)
        
        current_app.logger.info(f"Route filter applied for route {route_id}: {len(filtered_df)} rows from {len(log_df)} original rows")
        return filtered_df
    else:
        current_app.logger.warning(f"No circuits found for route {route_id}")
        return log_df  # Return original if no matching circuits


def get_available_routes(circuit_df: pd.DataFrame) -> List[str]:
    """
    Extract available route IDs from circuit data.
    
    Args:
        circuit_df: DataFrame containing circuit and route information
        
    Returns:
        List of unique route IDs
    """
    # Filter out empty or "Not_matched" route IDs
    routes = circuit_df['Route_id'].dropna().unique().tolist()
    valid_routes = [r for r in routes if r and r != "Not_matched"]
    
    return sorted(valid_routes)


def update_figure_title_with_dates(fig: Any, start_datetime: Optional[datetime], end_datetime: Optional[datetime]) -> None:
    """
    Update Plotly figure title with date range information.
    
    Args:
        fig: Plotly Figure object
        start_datetime: Start datetime of the filter
        end_datetime: End datetime of the filter
    """
    if start_datetime is not None and end_datetime is not None:
        start_str = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_datetime.strftime('%Y-%m-%d %H:%M:%S')
        new_title = f"Track Circuit Layout - Train Movement ({start_str} to {end_str})"
        fig.update_layout(title=new_title)
    elif start_datetime is not None:
        start_str = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
        fig.update_layout(title=f"Track Circuit Layout - Train Movement (From {start_str})")
    elif end_datetime is not None:
        end_str = end_datetime.strftime('%Y-%m-%d %H:%M:%S')
        fig.update_layout(title=f"Track Circuit Layout - Train Movement (Until {end_str})")


def parse_datetime_parameters(start_param: str, end_param: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse and validate datetime parameters from string format.
    
    Args:
        start_param: Start datetime string in ISO format
        end_param: End datetime string in ISO format
        
    Returns:
        Tuple containing start and end datetime objects (if valid)
    """
    # Parse datetime strings if provided
    start_date = None
    end_date = None
    
    if start_param:
        try:
            # Handle different ISO formats
            if 'Z' in start_param:
                start_param = start_param.replace('Z', '+00:00')
            start_date = datetime.fromisoformat(start_param)
        except ValueError:
            raise ValueError(f"Invalid start datetime format: {start_param}")
            
    if end_param:
        try:
            # Handle different ISO formats
            if 'Z' in end_param:
                end_param = end_param.replace('Z', '+00:00')
            end_date = datetime.fromisoformat(end_param)
        except ValueError:
            raise ValueError(f"Invalid end datetime format: {end_param}")
    
    # Validate that start is before end if both are provided
    if start_date and end_date and start_date > end_date:
        raise ValueError("Start datetime must be before end datetime")
        
    return start_date, end_date


def filter_circuit_by_chain(circuit_df: pd.DataFrame, chain_id: str) -> pd.DataFrame:
    """
    Filter circuit data by Chain_ID.
    
    Args:
        circuit_df: DataFrame containing circuit data
        chain_id: Chain ID to filter by
        
    Returns:
        Filtered DataFrame containing only circuits for the specified chain
    """
    return circuit_df[circuit_df['Chain_ID'] == chain_id].reset_index(drop=True)

def get_available_net_group_ids(circuit_df: pd.DataFrame) -> List[str]:
    """
    Extract available Net_Group_ID values from circuit data.
    
    Args:
        circuit_df: DataFrame containing circuit information
        
    Returns:
        List of unique Net_Group_ID values, sorted numerically
    """
    # Filter out empty or null Net_Group_ID values
    net_groups = circuit_df['Net_Group_ID'].dropna().astype(str).unique().tolist()
    valid_net_groups = [ng for ng in net_groups if ng and ng != "nan"]
    
    # Try to sort numerically if all values are numeric
    try:
        # Convert to integers for numeric sorting
        numeric_groups = [int(ng) for ng in valid_net_groups]
        return [str(ng) for ng in sorted(numeric_groups)]
    except ValueError:
        # Fall back to lexicographic sorting if conversion fails
        return sorted(valid_net_groups)

def get_interval_ids_by_net_group(circuit_df: pd.DataFrame, net_group_id: str) -> List[str]:
    """
    Get a list of Interval_id values associated with a specific Net_Group_ID.
    
    Args:
        circuit_df: DataFrame containing circuit and Net_Group_ID information
        net_group_id: Net_Group_ID to filter by
        
    Returns:
        List of Interval_id values associated with the given Net_Group_ID
    """
    # Convert net_group_id to string for comparison since it might be stored as various types
    filtered_df = circuit_df[circuit_df['Net_Group_ID'].astype(str) == str(net_group_id)]
    interval_ids = filtered_df['Interval_id'].unique().tolist()
    
    current_app.logger.info(f"Found {len(interval_ids)} Interval_ids for Net_Group_ID {net_group_id}")
    return interval_ids

def filter_by_interval_ids(
    log_df: pd.DataFrame, 
    circuit_df: pd.DataFrame,
    interval_ids: List[str]
) -> pd.DataFrame:
    """
    Filter signal log DataFrame based on specific Interval_ids.
    
    Args:
        log_df: DataFrame containing signal log data
        circuit_df: DataFrame containing circuit information
        interval_ids: List of Interval_ids to filter by
        
    Returns:
        Filtered DataFrame containing only signals for the specified Interval_ids
    """
    if not interval_ids:
        current_app.logger.warning("No Interval_ids provided for filtering")
        return log_df  # Return original if no interval ids provided
    
    # Create a mapping from Interval_id to Circuit_Name
    interval_to_circuit = circuit_df.set_index('Interval_id')['Circuit_Name'].to_dict()
    
    # Get the circuit names corresponding to our interval IDs
    circuit_names = [interval_to_circuit.get(interval_id) for interval_id in interval_ids 
                     if interval_id in interval_to_circuit]
    
    if not circuit_names:
        current_app.logger.warning(f"No circuit names found for the provided Interval_ids")
        return log_df  # Return original if no matching circuit names
    
    # Filter log DataFrame to include only signals from the specified circuits
    # Changed 'Circuit_Name' to 'SIGNAL NAME' to match the log DataFrame's column name
    filtered_df = log_df[log_df['SIGNAL NAME'].isin(circuit_names)]
    filtered_df.reset_index(drop=True, inplace=True)
    
    current_app.logger.info(f"Interval filter applied: {len(filtered_df)} rows from {len(log_df)} original rows")
    return filtered_df

def apply_net_group_filter(
    log_df: pd.DataFrame, 
    circuit_df: pd.DataFrame,
    net_group_id: str
) -> pd.DataFrame:
    """
    Filter signal log DataFrame based on Net_Group_ID using Interval_ids.
    
    Args:
        log_df: DataFrame containing signal log data
        circuit_df: DataFrame containing circuit and Net_Group_ID information
        net_group_id: Net_Group_ID to filter by
        
    Returns:
        Filtered DataFrame containing only signals for the specified Net_Group_ID
    """
    # Get interval IDs for the specified net_group_id
    interval_ids = get_interval_ids_by_net_group(circuit_df, net_group_id)
    
    if not interval_ids:
        current_app.logger.warning(f"No Interval_ids found for Net_Group_ID {net_group_id}")
        return log_df  # Return original if no matching interval ids
    
    # Use the filter_by_interval_ids function to filter the log DataFrame
    return filter_by_interval_ids(log_df, circuit_df, interval_ids)
