import pandas as pd
import os
import logging
import traceback
import numpy as np
from .data_load_movement_analysis import get_route_circuits, UPLOAD_FOLDER, has_uploaded_files, has_required_uploads
from .data_load_movement_analysis import get_best_file_of_type, get_available_csv_files, identify_file_type

logger = logging.getLogger(__name__)

def process_timestamps(df):
    """
    Process timestamps in the dataframe - either use existing combined timestamps
    or create them from separate date and time fields
    
    Args:
        df (DataFrame): DataFrame to process
        
    Returns:
        DataFrame: DataFrame with processed timestamps
    """
    # Check if we already have the combined timestamp fields
    if 'Down_timestamp' in df.columns and 'Up_timestamp' in df.columns:
        # Ensure timestamp fields are datetime objects
        if not pd.api.types.is_datetime64_any_dtype(df['Down_timestamp']):
            df['Down_timestamp'] = pd.to_datetime(df['Down_timestamp'], errors='coerce')
        if not pd.api.types.is_datetime64_any_dtype(df['Up_timestamp']):
            df['Up_timestamp'] = pd.to_datetime(df['Up_timestamp'], errors='coerce')
        
        logger.info("Using existing Down_timestamp and Up_timestamp fields")
        return df
        
    # Create combined timestamp fields from separate date and time fields
    if 'Down_date' in df.columns and 'Down_time' in df.columns:
        logger.info("Creating Down_timestamp from separate Down_date and Down_time fields")
        df['Down_timestamp'] = pd.to_datetime(
            df['Down_date'] + " " + df['Down_time'],
            errors='coerce'
        )
    else:
        logger.warning("Missing Down_date or Down_time fields, cannot create Down_timestamp")
        
    if 'Up_date' in df.columns and 'Up_time' in df.columns:
        logger.info("Creating Up_timestamp from separate Up_date and Up_time fields")
        df['Up_timestamp'] = pd.to_datetime(
            df['Up_date'] + " " + df['Up_time'],
            errors='coerce'
        )
    else:
        logger.warning("Missing Up_date or Up_time fields, cannot create Up_timestamp")
    
    return df

def get_route_details(route_name):
    """
    Get details for a specific route
    
    Args:
        route_name (str): Name of the route
        
    Returns:
        dict: Route details or None if not found
    """
    try:
        # Check if we have required uploads
        has_required, error_msg = has_required_uploads()
        if not has_required:
            logger.error(f"Cannot get route details: {error_msg}")
            return None
            
        # First check for combined data files
        combined_file = get_best_file_of_type('combined_data')
        if combined_file:
            logger.info(f"Looking for route {route_name} in combined data file: {combined_file}")
            route_df = pd.read_csv(combined_file)
            
            # Normalize route ID
            route_name = str(route_name).strip()
            route_df['Route_id'] = route_df['Route_id'].astype(str).str.strip()
            
            # Try exact match first, then case-insensitive
            route_data = route_df[route_df["Route_id"] == route_name]
            if route_data.empty:
                route_data = route_df[route_df["Route_id"].str.upper() == route_name.upper()]
            
            if not route_data.empty:
                # Determine circuit column name
                circuit_col = 'Circuit_Name' if 'Circuit_Name' in route_df.columns else 'Circuit'
                
                # Get the list of circuit names in order
                circuits = route_data.sort_values(by="Down_date").reset_index()
                circuit_chain = "-".join(circuits[circuit_col].tolist())
                
                return {
                    "Route_id": route_name,
                    "Movement_count": len(route_data["Movement_id"].unique()),
                    "Successor_Chain": circuit_chain,
                    "Circuit_count": len(circuits)
                }
        
        # Then check for route chart files  
        route_chart_file = get_best_file_of_type('route_chart')
        if route_chart_file:
            logger.info(f"Looking for route {route_name} in route chart file: {route_chart_file}")
            route_df = pd.read_csv(route_chart_file)
            
            # Normalize route ID
            route_name = str(route_name).strip()
            route_df['Route_id'] = route_df['Route_id'].astype(str).str.strip()
            
            # Try exact match first, then case-insensitive
            route_data = route_df[route_df["Route_id"] == route_name]
            if route_data.empty:
                route_data = route_df[route_df["Route_id"].str.upper() == route_name.upper()]
            
            if not route_data.empty:
                # Create a dictionary with expected field names for compatibility
                route_dict = route_data.iloc[0].to_dict()
                # Map Route_circuit to Successor_Chain for compatibility with existing code
                if 'Route_circuit' in route_dict:
                    route_dict['Successor_Chain'] = route_dict['Route_circuit']
                    
                return route_dict
        
        logger.warning(f"Route {route_name} not found in any uploaded file")
        return None
        
    except Exception as e:
        logger.error(f"Error in get_route_details: {str(e)}")
        return None

def get_circuit_data(route_name, from_time=None, to_time=None):
    """
    Gets circuit data filtered by route and time range, grouped by movement ID
    
    Args:
        route_name (str): Name of the route
        from_time (datetime): Start time for filtering (optional)
        to_time (datetime): End time for filtering (optional)
        
    Returns:
        DataFrame: Filtered circuit data sorted by movement ID and route order
    """
    try:
        # Check if we have required uploads
        has_required, error_msg = has_required_uploads()
        if not has_required:
            logger.error(f"Cannot get circuit data: {error_msg}")
            return pd.DataFrame()
            
        # Ensure route_name is a string for comparisons
        route_name = str(route_name).strip()
        logger.info(f"Searching for circuit data for route: '{route_name}'")
        
        # Explicitly list all available uploaded files for debugging
        csv_files = get_available_csv_files()
        file_types = {file: identify_file_type(file) for file in csv_files}
        logger.info(f"Available CSV files: {file_types}")
        
        # Determine processing approach based on available file types
        processing_approach = None
        
        # First priority: Use combined data file if available
        combined_file = get_best_file_of_type('combined_data')
        if combined_file:
            processing_approach = ("combined", combined_file)
            logger.info(f"Using combined data approach with file: {combined_file}")
            
        # Second priority: Use route chart + circuit data files if both available
        route_chart_file = get_best_file_of_type('route_chart')
        circuit_data_file = get_best_file_of_type('circuit_data')
        if processing_approach is None and route_chart_file and circuit_data_file:
            processing_approach = ("route_track", (route_chart_file, circuit_data_file))
            logger.info(f"Using route chart + circuit data approach with files: {route_chart_file}, {circuit_data_file}")
            
        # If we don't have a processing approach by now, we can't proceed
        if processing_approach is None:
            logger.error("No valid file combination found in uploads folder")
            return pd.DataFrame()
            
        # Process based on the selected approach
        if processing_approach[0] == "combined":
            # Process using combined data file
            file_path = processing_approach[1]
            df = pd.read_csv(file_path)
            
            # Log column names for debugging
            logger.info(f"Columns in combined data file: {df.columns.tolist()}")
            
            # Determine circuit column name
            circuit_col = 'Circuit_Name' if 'Circuit_Name' in df.columns else 'Circuit'
            logger.info(f"Using circuit column: {circuit_col}")
            
            # Convert Route_id to string for consistent comparison
            if 'Route_id' in df.columns:
                # Before conversion, log a few route IDs for debugging
                sample_routes = df['Route_id'].head(5).tolist()
                logger.info(f"Sample route IDs before conversion: {sample_routes}")
                
                df['Route_id'] = df['Route_id'].fillna('').astype(str).str.strip()
                
                # After conversion, log the same routes
                converted_routes = df.loc[df.index[:5], 'Route_id'].tolist()
                logger.info(f"Sample route IDs after conversion: {converted_routes}")
                
                # Log available routes for debugging
                available_routes = df['Route_id'].unique()
                logger.info(f"Available routes in combined data file: {available_routes}")
                
                # More robust route matching
                filtered_df = df[df["Route_id"] == route_name]
                
                # If no exact match, try case-insensitive match
                if filtered_df.empty:
                    logger.info(f"No exact match for '{route_name}', trying case-insensitive match")
                    
                    # Convert to uppercase for case-insensitive comparison
                    upper_route = route_name.upper()
                    upper_df_routes = df["Route_id"].str.upper()
                    
                    # Try the match
                    filtered_df = df[upper_df_routes == upper_route]
                
                # If still no match, log the issue clearly
                if filtered_df.empty:
                    logger.warning(f"No data found for route '{route_name}' in combined data file")
                    logger.info(f"Available routes: {sorted(df['Route_id'].unique().tolist())}")
                    return pd.DataFrame()
                
                logger.info(f"Found {len(filtered_df)} rows for route '{route_name}'")
                
                # Process timestamps - use combined timestamp fields or create them
                filtered_df = process_timestamps(filtered_df)
                
                # Drop rows with invalid timestamps
                invalid_rows = filtered_df[pd.isna(filtered_df["Down_timestamp"]) | pd.isna(filtered_df["Up_timestamp"])]
                if not invalid_rows.empty:
                    logger.info(f"Dropping {len(invalid_rows)} rows with invalid timestamps")
                    filtered_df = filtered_df.dropna(subset=["Down_timestamp", "Up_timestamp"])
                
                # Filter by time range if provided
                if from_time is not None and to_time is not None:
                    before_count = len(filtered_df)
                    filtered_df = filtered_df[(filtered_df["Down_timestamp"] >= from_time) & 
                                            (filtered_df["Up_timestamp"] <= to_time)]
                    after_count = len(filtered_df)
                    if after_count < before_count:
                        logger.info(f"Time filter reduced data from {before_count} to {after_count} rows")
                
                # Calculate duration in seconds
                filtered_df["duration_seconds"] = (filtered_df["Up_timestamp"] - filtered_df["Down_timestamp"]).dt.total_seconds()
                
                # Ensure duration is positive
                neg_duration = filtered_df[filtered_df["duration_seconds"] <= 0]
                if not neg_duration.empty:
                    logger.warning(f"Found {len(neg_duration)} records with non-positive duration, filtering these out")
                    filtered_df = filtered_df[filtered_df["duration_seconds"] > 0]
                
                # Calculate average speed
                filtered_df["distance"] = 1.0
                filtered_df["avg_speed"] = filtered_df.apply(
                    lambda row: (row["distance"] / row["duration_seconds"] * 3.6) if row["duration_seconds"] > 0 else 0, 
                    axis=1
                )
                
                movement_id_field = "Movement_id"
                if movement_id_field in filtered_df.columns:
                    # Ensure Movement_id is string for consistent handling
                    filtered_df[movement_id_field] = filtered_df[movement_id_field].astype(str)
                    filtered_df = filtered_df.sort_values(by=[movement_id_field, "Down_timestamp"])
                    filtered_df["order"] = filtered_df.groupby(movement_id_field).cumcount()
                    
                    logger.info(f"Found {len(filtered_df)} records for route '{route_name}' across {filtered_df[movement_id_field].nunique()} movements")
                else:
                    logger.warning(f"Movement_id field not found in data, using sequential ordering")
                    filtered_df["order"] = range(len(filtered_df))
                    
                return filtered_df
            else:
                logger.error(f"Required column 'Route_id' not found in combined data file")
                logger.info(f"Available columns: {df.columns.tolist()}")
                return pd.DataFrame()
                
        elif processing_approach[0] == "route_track":
            # Process using Route chart + Circuit data files
            route_file, track_file = processing_approach[1]
            logger.info(f"Using route chart file {route_file} and circuit data file {track_file}")
            route_df = pd.read_csv(route_file)
            track_df = pd.read_csv(track_file)
            
            # Determine circuit column name
            circuit_col = 'Circuit_Name' if 'Circuit_Name' in track_df.columns else 'Circuit'
            logger.info(f"Using circuit column: {circuit_col}")
            
            # Log column names for debugging
            logger.info(f"Columns in route chart file: {route_df.columns.tolist()}")
            logger.info(f"Columns in circuit data file: {track_df.columns.tolist()}")
            
            # Convert Route_id to string for consistent matching
            if 'Route_id' in route_df.columns:
                route_df['Route_id'] = route_df['Route_id'].fillna('').astype(str).str.strip()
                available_routes = route_df['Route_id'].unique()
                logger.info(f"Available routes in route chart file: {available_routes}")
            else:
                logger.error("Required column 'Route_id' not found in route chart file")
                logger.info(f"Available columns: {route_df.columns.tolist()}")
                return pd.DataFrame()
            
            # Process track circuit data
            try:
                # Process timestamps - use combined timestamp fields or create them
                track_df = process_timestamps(track_df)
                
                # Drop rows with invalid timestamps
                invalid_rows = track_df[pd.isna(track_df["Down_timestamp"]) | pd.isna(track_df["Up_timestamp"])]
                if not invalid_rows.empty:
                    logger.info(f"Dropping {len(invalid_rows)} rows with invalid timestamps")
                    track_df = track_df.dropna(subset=["Down_timestamp", "Up_timestamp"])
                
                # Calculate duration in seconds
                track_df["duration_seconds"] = (track_df["Up_timestamp"] - track_df["Down_timestamp"]).dt.total_seconds()
                
                # Ensure duration is positive
                neg_duration = track_df[track_df["duration_seconds"] <= 0]
                if not neg_duration.empty:
                    logger.warning(f"Found {len(neg_duration)} records with non-positive duration, filtering these out")
                    track_df = track_df[track_df["duration_seconds"] > 0]
                    
                # Add distance and speed calculations
                if "distance" in track_df.columns:
                    track_df["avg_speed"] = track_df.apply(
                        lambda row: (row["distance"] / row["duration_seconds"] * 3.6) if row["duration_seconds"] > 0 else 0, 
                        axis=1
                    )
                else:
                    track_df["distance"] = 1.0
                    track_df["avg_speed"] = track_df.apply(
                        lambda row: (row["distance"] / row["duration_seconds"] * 3.6) if row["duration_seconds"] > 0 else 0, 
                        axis=1
                    )
                
                # Apply time range filter if provided
                if from_time is not None and to_time is not None:
                    before_count = len(track_df)
                    track_df = track_df[(track_df["Down_timestamp"] >= from_time) & 
                                      (track_df["Up_timestamp"] <= to_time)]
                    after_count = len(track_df)
                    if after_count < before_count:
                        logger.info(f"Time filter reduced data from {before_count} to {after_count} rows")
                
                # More robust route matching
                route_info = route_df.loc[route_df["Route_id"] == route_name]
                
                # If no exact match, try case-insensitive match
                if route_info.empty:
                    logger.info(f"No exact match for '{route_name}' in route_chart, trying case-insensitive match")
                    route_info = route_df.loc[route_df["Route_id"].str.upper() == route_name.upper()]
                
                # Additional fallbacks for numeric route IDs
                if route_info.empty and route_name.isdigit():
                    logger.info(f"Trying to match numeric route ID: {route_name}")
                    # Try without leading zeros
                    no_zeros = route_name.lstrip('0')
                    if no_zeros:
                        route_info = route_df.loc[route_df["Route_id"].str.lstrip('0') == no_zeros]
                    
                    # Try as integer if still no match
                    if route_info.empty:
                        try:
                            route_int = int(route_name)
                            numeric_routes = pd.to_numeric(route_df["Route_id"], errors='coerce')
                            route_info = route_df.loc[numeric_routes == route_int]
                            logger.info(f"Tried matching as integer {route_int}, found {len(route_info)} rows")
                        except:
                            pass
                
                if route_info.empty:
                    logger.error(f"Route '{route_name}' not found in route chart file")
                    logger.info(f"Available routes: {route_df['Route_id'].unique().tolist()}")
                    return pd.DataFrame()
                    
                successor_chain = route_info["Route_circuit"].values[0]
                circuit_ids = [cid.strip() for cid in successor_chain.split("-")]
                
                logger.info(f"Found {len(circuit_ids)} circuits in route '{route_name}'")
                
                # Map circuit interval ID or circuit name based on the file format
                circuit_col = "circuit_interval_id" if "circuit_interval_id" in track_df.columns else "Circuit_Name"
                filtered_df = track_df[track_df[circuit_col].isin(circuit_ids)]
                
                if filtered_df.empty:
                    logger.warning(f"No circuit data found for route '{route_name}' in the selected time range")
                    return pd.DataFrame()
                
                circuit_order = {cid: idx for idx, cid in enumerate(circuit_ids)}
                filtered_df["order"] = filtered_df[circuit_col].map(circuit_order)
                filtered_df = filtered_df.sort_values(by="order")
                
                # Add Route_id field if not present (for compatibility)
                if "Route_id" not in filtered_df.columns:
                    filtered_df["Route_id"] = route_name
                    
                # Add Movement_id field if not present (for compatibility)
                if "Movement_id" not in filtered_df.columns:
                    # Create a basic sequential movement ID
                    filtered_df["Movement_id"] = "M1"
                
                logger.info(f"Found {len(filtered_df)} matching circuit records for route '{route_name}'")
                return filtered_df
                
            except (IndexError, KeyError) as e:
                logger.error(f"Error extracting successor chain for route '{route_name}' from uploaded files: {str(e)}")
                logger.error(traceback.format_exc())
                return pd.DataFrame()
        
        # Return empty DataFrame if no matches found
        logger.warning(f"Route '{route_name}' not found in any uploaded file. Make sure the Route ID exists in your data.")
        return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"Error in get_circuit_data: {str(e)}")
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def calculate_movement_times(route_name, from_time=None, to_time=None):
    """
    Calculate the total time taken by each complete movement of a selected Route_id
    
    Args:
        route_name (str): Name of the route
        from_time (datetime): Start time for filtering (optional)
        to_time (datetime): End time for filtering (optional)
        
    Returns:
        DataFrame: Movement IDs with their total duration and other details
    """
    try:
        # Get circuit data for the route
        circuit_data = get_circuit_data(route_name, from_time, to_time)
        
        if circuit_data.empty:
            logger.warning(f"No circuit data found for route '{route_name}'")
            return pd.DataFrame()
        
        # Log movement IDs for debugging
        if "Movement_id" in circuit_data.columns:
            unique_movements = circuit_data["Movement_id"].unique()
            logger.info(f"Found {len(unique_movements)} unique movements for route {route_name}: {unique_movements}")
        
        # Group by Movement_id and calculate total times
        movement_results = []
        
        for movement_id, group in circuit_data.groupby("Movement_id"):
            # Get earliest Down_timestamp and latest Up_timestamp
            start_time = group["Down_timestamp"].min()
            end_time = group["Up_timestamp"].max()
            
            # Calculate total journey time
            total_journey_time = (end_time - start_time).total_seconds()
            
            # Sum the duration_seconds column to get total time spent in all circuits
            total_circuit_time = group["duration_seconds"].sum()
            
            # Get the number of circuits in this movement
            circuit_count = len(group)
            
            # Add data to results
            movement_results.append({
                "Movement_id": movement_id,
                "Start_Time": start_time,
                "End_Time": end_time,
                "Total_Journey_Time_Seconds": total_journey_time,
                "Total_Journey_Time_Minutes": total_journey_time / 60,
                "Total_Circuit_Time_Seconds": total_circuit_time,
                "Total_Circuit_Time_Minutes": total_circuit_time / 60,
                "Circuit_Count": circuit_count,
                "Average_Circuit_Duration": total_circuit_time / circuit_count if circuit_count > 0 else 0
            })
        
        # Create DataFrame from results
        result_df = pd.DataFrame(movement_results)
        
        if not result_df.empty:
            # Sort by start time
            result_df = result_df.sort_values("Start_Time")
            logger.info(f"Calculated times for {len(result_df)} movements of route '{route_name}'")
        
        return result_df
        
    except Exception as e:
        logger.error(f"Error in calculate_movement_times: {str(e)}")
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def apply_adaptive_sampling(df, time_span_hours, movement_id_field="Movement_id", route_id_field="Route_id"):
    """
    Apply adaptive sampling for large datasets to improve performance
    
    Args:
        df (DataFrame): Input dataframe
        time_span_hours (float): Time span in hours
        movement_id_field (str): Field name for movement ID
        route_id_field (str): Field name for route ID
        
    Returns:
        DataFrame: Sampled dataframe
    """
    if time_span_hours <= 24:  # Lower threshold (was 48)
        return df
    
    # Apply basic sampling for 1-7 days span
    if time_span_hours <= 168:  # Up to 1 week
        sample_size_factor = 0.5
    else:  # More than a week
        sample_size_factor = 0.25
        
    sampled_df = pd.DataFrame()
    
    for route_id in df[route_id_field].unique():
        route_data = df[df[route_id_field] == route_id]
        for mov_id in route_data[movement_id_field].unique():
            mov_data = route_data[route_data[movement_id_field] == mov_id]
            
            # Keep movement endpoints (critical points) plus intelligently sample middle
            if len(mov_data) > 20:
                # Always keep start/end of each circuit activation
                critical_points = []
                for circuit in mov_data['Circuit_Name'].unique():
                    circuit_data = mov_data[mov_data['Circuit_Name'] == circuit]
                    critical_points.append(circuit_data.iloc[0:1])  # First point
                    critical_points.append(circuit_data.iloc[-1:])  # Last point
                
                critical_df = pd.concat(critical_points)
                
                # Sample the remaining points to maintain visual fidelity
                remaining = mov_data[~mov_data.index.isin(critical_df.index)]
                if len(remaining) > 0:
                    sample_size = min(len(remaining), max(10, int(len(remaining) * sample_size_factor)))
                    sampled = remaining.sample(sample_size)
                    mov_sampled = pd.concat([critical_df, sampled])
                else:
                    mov_sampled = critical_df
            else:
                mov_sampled = mov_data
            
            sampled_df = pd.concat([sampled_df, mov_sampled])
    
    logger.info(f"Adaptive sampling applied: {len(df)} → {len(sampled_df)} points")
    return sampled_df

def extract_circuit_sequence(df, route_id, movement_id_field="Movement_id"):
    """
    Extract the circuit sequence for a route from the data
    
    Args:
        df (DataFrame): DataFrame with circuit data
        route_id: The route ID to extract sequence for
        movement_id_field (str): Field name for movement ID
        
    Returns:
        list: Ordered list of circuits
    """
    route_data = df[df["Route_id"] == route_id]
    ordered_circuits = []
    
    if not route_data.empty:
        for _, movement_group in route_data.groupby(movement_id_field):
            # Sort by timestamp to get order
            ordered = movement_group.sort_values("Down_time")["Circuit_Name"].tolist()
            if len(ordered) > len(ordered_circuits):
                # Keep the longest sequence
                ordered_circuits = ordered
    
    return ordered_circuits

def calculate_y_positions(unique_routes, route_circuits, df):
    """
    Calculate y-positions for circuits based on route organization
    
    Args:
        unique_routes (list): List of route IDs
        route_circuits (dict): Mapping of route IDs to circuit sequences
        df (DataFrame): DataFrame with circuit data
        
    Returns:
        tuple: (y_positions, y_labels, y_positions_ticks, route_boundary_positions, 
               circuit_route_map, missing_route_data, total_plot_height)
    """
    y_positions = {}       # Store y-positions for circuits
    current_y = 0          # Track the current y position
    route_y_ranges = {}    # Store the y-range for each route
    y_labels = []          # Store y-axis tick labels
    y_positions_ticks = [] # Store y-axis tick positions
    route_boundary_positions = []  # Track route boundary positions for visual separators
    circuit_route_map = {}  # Map circuits to their routes for reference
    missing_route_data = [] # Keep track of routes with missing circuit data
    
    # Position all circuits by route - maintain route-based organization
    for route_id in unique_routes:
        route_start_y = current_y
        route_circuit_sequence = route_circuits.get(route_id, [])
        
        # If no circuit sequence found for this route, extract from data
        if not route_circuit_sequence:
            route_circuit_sequence = extract_circuit_sequence(df, route_id)
            
            if route_circuit_sequence:
                logger.info(f"Using {len(route_circuit_sequence)} circuits from data for route {route_id}")
            else:
                missing_route_data.append(route_id)
                logger.warning(f"No circuit data available for route {route_id}")
                continue
        
        # Add route boundary indicator at start of each route (except first)
        if current_y > 0:
            route_boundary_positions.append(current_y - 0.5)
        
        # Map each circuit in this route to its y-position
        for i, circuit in enumerate(route_circuit_sequence):
            circuit_y = current_y + i * 1.0  # Each circuit is 1 unit apart
            y_positions[f"{route_id}_{circuit}"] = circuit_y
            circuit_route_map[circuit] = route_id
            
            # Add label for this circuit
            y_positions_ticks.append(circuit_y + 0.7/2)
            y_labels.append(circuit)
            
        # Update current_y for the next route
        if route_circuit_sequence:
            current_y += len(route_circuit_sequence) * 1.0 
            current_y += 1.0  # Add gap between routes
        else:
            current_y += 1.0
            
        # Store the y-range for this route
        route_y_ranges[route_id] = (route_start_y, current_y - 1.0)
    
    # Set total plot height
    top_padding = 3.0
    total_plot_height = current_y + top_padding
    
    return (y_positions, y_labels, y_positions_ticks, route_boundary_positions, 
            circuit_route_map, missing_route_data, total_plot_height)
