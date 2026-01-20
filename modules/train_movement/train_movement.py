"""
Train Movement Visualization Module

This module provides functions to visualize train movements across a railway network.
It builds a graph representation of the railway network and generates animation frames
showing train movements based on signal log data.
"""
import os
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import plotly.utils
import json
import math
import numpy as np
from typing import Dict, List, Tuple, Set, Any, Optional, Union
from flask import current_app, session

# Import data loading functions from the load_train_movement module
from .load_train_movement import load_and_process_data

def apply_datetime_filter_internal(log_df: pd.DataFrame, start_datetime=None, end_datetime=None) -> pd.DataFrame:
    """
    Apply datetime filtering to log DataFrame.
    
    Args:
        log_df: Signal log DataFrame with 'SIGNAL TIME' column
        start_datetime: Start datetime for filtering
        end_datetime: End datetime for filtering
        
    Returns:
        Filtered DataFrame
    """
    try:
        if log_df.empty:
            return log_df
            
        # Ensure SIGNAL TIME is datetime
        if not pd.api.types.is_datetime64_any_dtype(log_df['SIGNAL TIME']):
            log_df['SIGNAL TIME'] = pd.to_datetime(log_df['SIGNAL TIME'])
        
        original_count = len(log_df)
        
        # Apply start datetime filter
        if start_datetime is not None:
            if isinstance(start_datetime, str):
                start_datetime = pd.to_datetime(start_datetime)
            log_df = log_df[log_df['SIGNAL TIME'] >= start_datetime]
            current_app.logger.info(f"After start filter ({start_datetime}): {len(log_df)} entries")
        
        # Apply end datetime filter
        if end_datetime is not None:
            if isinstance(end_datetime, str):
                end_datetime = pd.to_datetime(end_datetime)
            log_df = log_df[log_df['SIGNAL TIME'] <= end_datetime]
            current_app.logger.info(f"After end filter ({end_datetime}): {len(log_df)} entries")
        
        current_app.logger.info(f"Datetime filtering: {original_count} → {len(log_df)} entries")
        return log_df
        
    except Exception as e:
        current_app.logger.error(f"Error applying datetime filter: {str(e)}")
        return log_df

def update_figure_title_with_dates(fig: go.Figure, start_datetime=None, end_datetime=None) -> None:
    """Update figure title to include date range information."""
    try:
        base_title = 'Track Circuit Layout - Dynamic Train Movement'
        
        if start_datetime is not None or end_datetime is not None:
            date_info = []
            if start_datetime is not None:
                start_str = start_datetime.strftime('%Y-%m-%d %H:%M') if hasattr(start_datetime, 'strftime') else str(start_datetime)
                date_info.append(f"From: {start_str}")
            if end_datetime is not None:
                end_str = end_datetime.strftime('%Y-%m-%d %H:%M') if hasattr(end_datetime, 'strftime') else str(end_datetime)
                date_info.append(f"To: {end_str}")
            
            fig.update_layout(title=f"{base_title}<br><sub>{' | '.join(date_info)}</sub>")
        else:
            fig.update_layout(title=base_title)
            
    except Exception as e:
        current_app.logger.error(f"Error updating figure title: {str(e)}")

#######################
# GRAPH CONSTRUCTION  #
#######################

def build_graph_and_traces(nodes_df: pd.DataFrame, edges_df: pd.DataFrame) -> Tuple[Optional[nx.DiGraph], Dict, Dict, List, List]:
    """
    Build network graph and create visualization traces.
    
    Args:
        nodes_df: DataFrame containing node information
        edges_df: DataFrame containing edge information
        
    Returns:
        Tuple containing:
        - NetworkX DiGraph object
        - Dictionary of node positions
        - Dictionary mapping track IDs to edge indices
        - List of edge traces for Plotly
        - List of label traces for Plotly
    """
    try:
        # Build graph
        G = nx.DiGraph()
        positions = {}
        
        # Add nodes
        for _, row in nodes_df.iterrows():
            G.add_node(row['node'], pos=(row['x'], row['y']))
            positions[row['node']] = (row['x'], row['y'])
        
        # Add edges
        for _, row in edges_df.iterrows():
            G.add_edge(
                row['from'], row['to'],
                track_circuit_id=row['track_circuit_id'],
                length=row['length'],
                switch_controlled_by=row.get('switch_controlled_by', '')
            )
        
        # Prepare visualization elements
        track_to_edge_idx = {}
        edge_traces = []
        label_traces = []
        
        # Create visualization traces
        for idx, (u, v, data) in enumerate(G.edges(data=True)):
            x0, y0 = positions[u]
            x1, y1 = positions[v]
            track_id = data['track_circuit_id']
            track_to_edge_idx[track_id] = idx
            
            # Create edge trace
            edge_trace = create_edge_trace(x0, y0, x1, y1, track_id)
            edge_traces.append(edge_trace)
            
            # Create label trace
            label_trace = create_label_trace(x0, y0, x1, y1, track_id)
            label_traces.append(label_trace)
            
            # Store track geometry for train animation
            data['geometry'] = {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}
        
        return G, positions, track_to_edge_idx, edge_traces, label_traces
        
    except Exception as e:
        current_app.logger.error(f"Error building graph: {str(e)}")
        return None, {}, {}, [], []

def create_edge_trace(x0: float, y0: float, x1: float, y1: float, track_id: str) -> go.Scatter:
    """Create a Plotly scatter trace for a track segment."""
    return go.Scatter(
        x=[x0, x1], y=[y0, y1],
        mode='lines',
        line=dict(width=3, color='#0066cc', dash='solid'),
        hoverinfo='text',
        text=[f'Track ID: {track_id}'],
        showlegend=False
    )

def create_label_trace(x0: float, y0: float, x1: float, y1: float, track_id: str) -> go.Scatter:
    """Create a Plotly scatter trace for a track label."""
    mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
    return go.Scatter(
        x=[mid_x], y=[mid_y],
        mode='text',
        text=[track_id],
        textposition="middle center",
        textfont=dict(size=14, color='darkblue', family='Arial Black'),
        hoverinfo='text',
        hoverlabel=dict(bgcolor='white'),
        hovertext=[f'Track ID: {track_id}'],
        showlegend=False
    )

def create_plotly_figure(edge_traces: List[go.Scatter], label_traces: List[go.Scatter], signal_traces: List[go.Scatter] = None) -> go.Figure:
    """Create a Plotly figure for railway visualization."""
    traces = edge_traces + label_traces
    if signal_traces:
        traces += signal_traces
        
    fig = go.Figure(data=traces)
    fig.update_layout(
        title='Track Circuit Layout - Dynamic Train Movement',
        title_x=0.5,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False, scaleanchor='x', scaleratio=8),
        plot_bgcolor='white',
        height=600
    )
    return fig

#######################
# ANIMATION GENERATION #
#######################

def generate_animation_frames(
    log_df: pd.DataFrame, 
    track_to_edge_idx: Dict[str, int], 
    edge_traces: List[go.Scatter],
    G: Optional[nx.DiGraph] = None, 
    positions: Optional[Dict] = None
) -> Tuple[List[Dict], List[str], Dict]:
    """Generate animation frames for train movement."""
    try:
        # Define a limited color palette
        color_palette = [
            '#FF0000',  # Red
            "#580505",  # Green
            '#FF69B4'   # Pink
        ]
        
        frames = []
        time_labels = []
        active_set = set()
        train_assignments = {}  # Maps track_circuits to train IDs
        train_count = 0
        trains = {}  # Information about each train
        
        # Process each signal log entry to create animation frames
        for _, row in log_df.iterrows():
            name = row['SIGNAL NAME']
            status = row['SIGNAL STATUS'].strip().lower()
            timestamp = row['SIGNAL TIME']
            
            # Update active tracks and train assignments
            train_count = update_active_tracks_and_trains(
                name, status, active_set, train_assignments, 
                trains, track_to_edge_idx, color_palette, train_count
            )
            
            # Create frame data
            frame_data = create_frame_data(
                active_set, train_assignments, edge_traces, 
                track_to_edge_idx, G, positions, trains
            )
            
            frames.append(frame_data)
            time_labels.append(timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        
        # Return empty dict for train info - removed color mapping
        return frames, time_labels, {}
        
    except Exception as e:
        current_app.logger.error(f"Error generating animation frames: {str(e)}")
        return [], [], {}

def update_active_tracks_and_trains(
    name: str, status: str, 
    active_set: Set[str], train_assignments: Dict[str, str], 
    trains: Dict[str, Dict], track_to_edge_idx: Dict[str, int], 
    color_palette: List[str], train_count: int
) -> int:
    """Update active tracks and train assignments based on signal status."""
    # Handle track activation
    if status == 'down' and name in track_to_edge_idx:
        # Track is becoming active
        active_set.add(name)
        
        # If this track doesn't belong to a train, create or assign one
        if name not in train_assignments:
            # Look for nearby active tracks already assigned to a train
            assigned_train = None
            for active_track in active_set:
                if active_track in train_assignments:
                    assigned_train = train_assignments[active_track]
                    break
            
            # If no connected tracks are assigned, create a new train
            if not assigned_train:
                train_count += 1
                train_id = f"Train-{train_count}"
                # Assign a color from the limited palette, cycling through the colors
                train_color = color_palette[(train_count - 1) % len(color_palette)]
                trains[train_id] = {
                    "color": train_color,
                    "active_tracks": set()
                }
                assigned_train = train_id
            
            # Assign track to this train
            if assigned_train:
                train_assignments[name] = assigned_train
                trains[assigned_train]["active_tracks"].add(name)
    
    # Handle track deactivation
    elif status == 'up' and name in active_set:
        # Track is becoming inactive
        active_set.remove(name)
        
        # Remove train assignment
        if name in train_assignments:
            train_id = train_assignments[name]
            if train_id in trains and name in trains[train_id]["active_tracks"]:
                trains[train_id]["active_tracks"].remove(name)
            del train_assignments[name]
    
    return train_count

def create_frame_data(
    active_set: Set[str], train_assignments: Dict[str, str],
    edge_traces: List[go.Scatter], track_to_edge_idx: Dict[str, int], 
    G: Optional[nx.DiGraph], positions: Optional[Dict], trains: Dict[str, Dict],
    signal_traces: Optional[List[go.Scatter]] = None
) -> Dict:
    """Create data for a single animation frame."""
    # Default color for inactive tracks is blue (#0066cc)
    color_map = ['#0066cc'] * len(edge_traces)
    
    # Default width for unoccupied tracks is 3
    width_map = [3] * len(edge_traces)
    
    # Prepare train positions for this frame
    train_positions = {}
    
    # Color tracks based on the train they're assigned to
    for track_id in active_set:
        if track_id in track_to_edge_idx:
            idx = track_to_edge_idx[track_id]
            
            # Get the train this track belongs to
            if track_id in train_assignments:
                train_id = train_assignments[track_id]
                # Use the train's color for this track
                train_color = trains[train_id]["color"]
                color_map[idx] = train_color
                
                # Increase width for tracks occupied by trains
                width_map[idx] = 6  # Double the width for occupied tracks
                
                # Calculate train position if graph is available
                if G and positions:
                    calculate_train_position(
                        track_id, train_assignments, train_positions, 
                        G, positions, trains
                    )
    
    # Update signal indicators if available
    signal_updates = None
    if signal_traces:
        signal_updates = update_signal_indicators(active_set, signal_traces)
    
    return {
        "colors": color_map,
        "widths": width_map,
        "trains": train_positions,
        "active_tracks": list(active_set),
        "signals": signal_updates
    }

def calculate_train_position(
    track_id: str, train_assignments: Dict[str, str], 
    train_positions: Dict[str, List], G: nx.DiGraph, 
    positions: Dict, trains: Dict[str, Dict]
) -> None:
    """Calculate train position on a specific track."""
    train_id = train_assignments[track_id]
    if train_id not in train_positions:
        train_positions[train_id] = []
    
    # Find the edge corresponding to this track
    for u, v, data in G.edges(data=True):
        if data.get('track_circuit_id') == track_id:
            if u in positions and v in positions:
                x0, y0 = positions[u]
                x1, y1 = positions[v]
                
                # Calculate angle of track in degrees
                dx = x1 - x0
                dy = y1 - y0
                angle = math.degrees(math.atan2(dy, dx))
                
                # Position train at 80% of the track length to show it near the head
                train_x = x0 + 0.8 * dx
                train_y = y0 + 0.8 * dy
                
                # Include the train's color in the position data
                train_positions[train_id].append({
                    'x': train_x, 
                    'y': train_y, 
                    'track_id': track_id,
                    'angle': angle,
                    'start': {'x': x0, 'y': y0},
                    'end': {'x': x1, 'y': y1},
                    'color': trains[train_id]["color"]
                })
                break

#######################
# SIGNAL INDICATORS   #
#######################

def create_signal_indicators(G: nx.DiGraph, positions: Dict) -> List[go.Scatter]:
    """
    Create circular signal indicators for tracks with 'R' or 'N' prefixes.
    
    Args:
        G: NetworkX DiGraph object representing the railway network
        positions: Dictionary of node positions
        
    Returns:
        List of Plotly scatter traces for signal indicators
    """
    signal_traces = []
    
    # Iterate through all edges to find switch-controlled tracks
    for u, v, data in G.edges(data=True):
        track_id = data.get('track_circuit_id', '')
        
        # Check if track ID starts with 'R' or 'N' (switch-controlled)
        if track_id.startswith('R') or track_id.startswith('N'):
            x0, y0 = positions[u]
            x1, y1 = positions[v]
            
            # Calculate position for signal indicator (slightly offset from the track)
            track_vector = (x1 - x0, y1 - y0)
            track_length = math.sqrt(track_vector[0]**2 + track_vector[1]**2)
            unit_normal = (-track_vector[1]/track_length, track_vector[0]/track_length)
            
            # Position the signal indicator at 30% along the track with a small offset
            signal_x = x0 + 0.3 * track_vector[0] + 0.1 * unit_normal[0]
            signal_y = y0 + 0.3 * track_vector[1] + 0.1 * unit_normal[1]
            
            # Default color is gray for inactive signals
            signal_color = '#888888'
            
            # Create signal indicator trace
            signal_trace = go.Scatter(
                x=[signal_x], 
                y=[signal_y],
                mode='markers',
                marker=dict(
                    symbol='circle',
                    size=10,
                    color=signal_color,
                    line=dict(width=2, color='black')
                ),
                hoverinfo='text',
                text=[f'Signal for {track_id}'],
                showlegend=False,
                customdata=[track_id]  # Store track_id for updating later
            )
            
            signal_traces.append(signal_trace)
    
    return signal_traces

def update_signal_indicators(active_tracks: Set[str], signal_traces: List[go.Scatter]) -> List[Dict]:
    """
    Update signal indicators based on active tracks.
    
    Args:
        active_tracks: Set of active track IDs
        signal_traces: List of signal indicator traces
        
    Returns:
        List of updated signal indicator traces data
    """
    updated_signals = []
    
    for signal_trace in signal_traces:
        # Get the track ID from customdata
        track_id = signal_trace.customdata[0]
        
        # Default color (gray for inactive)
        signal_color = '#888888'
        
        # Update color based on track status and prefix
        if track_id in active_tracks:
            if track_id.startswith('R'):
                signal_color = '#00FF00'  # Blue for R tracks
            elif track_id.startswith('N'):
                signal_color = '#00FF00'  # Green for N tracks
        
        # Create updated trace data
        updated_signal = {
            'marker.color': [signal_color]
        }
        
        updated_signals.append(updated_signal)
        
    return updated_signals

#######################
# DATA PROCESSING     #
#######################

def convert_numpy_types(obj):
    """
    Convert numpy data types to native Python types for JSON serialization.
    
    Args:
        obj: Any Python object that might contain numpy values
        
    Returns:
        Object with numpy values converted to native Python types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj

def get_train_movement_data(use_uploaded: bool = False, start_datetime=None, end_datetime=None, net_group_id=None) -> Dict:
    """Get train movement analysis data for the Flask route."""
    try:
        # Load and process data
        nodes_df, edges_df, log_df, circuit_df = load_and_process_data(use_uploaded=use_uploaded)
        
        if nodes_df is None or edges_df is None or log_df is None:
            return {"error": "Failed to load data files"}
        
        # Track filtered interval IDs and their status to display in UI
        filtered_interval_ids = []
        interval_statuses = {}
        filtered_track_ids = []  # Track IDs belonging to filtered intervals
            
        # Apply datetime filtering if specified
        if start_datetime is not None or end_datetime is not None:
            log_df = apply_datetime_filter_internal(log_df, start_datetime, end_datetime)
            
        # Apply Net_Group_ID filtering if specified
        if net_group_id:
            from .filter_features import get_interval_ids_by_net_group, apply_net_group_filter
            # Get the interval IDs before filtering
            filtered_interval_ids = get_interval_ids_by_net_group(circuit_df, net_group_id)
            log_df = apply_net_group_filter(log_df, circuit_df, net_group_id)
            
            # Get status information for each interval ID and collect track IDs
            filtered_track_ids = []
            for interval_id in filtered_interval_ids:
                interval_data = circuit_df[circuit_df['Interval_id'] == interval_id]
                
                if not interval_data.empty:
                    interval_data = interval_data.iloc[0]
                    circuit_name = interval_data['Circuit_Name']
                    
                    # Track the circuit names for visualization focus
                    if circuit_name not in filtered_track_ids:
                        filtered_track_ids.append(circuit_name)
                    
                    # Extract useful information
                    interval_statuses[interval_id] = {
                        'circuit_name': circuit_name,
                        'down_time': interval_data['Down_timestamp'],
                        'up_time': interval_data['Up_timestamp'],
                        'duration': interval_data['Duration'],
                        'switch_name': interval_data['switch_name'],
                        'switch_status': interval_data['switch_status'],
                        'chain_id': interval_data['Chain_ID']
                    }
                    
                    # Add route information if available
                    if 'Route_id' in interval_data and interval_data['Route_id'] != "Not_matched":
                        interval_statuses[interval_id]['route_id'] = interval_data['Route_id']
                        interval_statuses[interval_id]['route_name'] = interval_data.get('Route_name', '')
            
        # Check if we still have data after filtering
        if log_df.empty:
            return {"error": "No data available for the selected filters"}
        
        # Build graph and create traces
        G, positions, track_to_edge_idx, edge_traces, label_traces = build_graph_and_traces(nodes_df, edges_df)
        
        if G is None:
            return {"error": "Failed to build graph"}
        
        # Create signal indicators for tracks with R/N prefixes
        signal_traces = create_signal_indicators(G, positions)
        
        # Generate animation frames
        frames, time_labels, _ = generate_animation_frames(log_df, track_to_edge_idx, edge_traces, G, positions)
        
        if not frames:
            return {"error": "Failed to generate animation frames"}
        
        # Update frames with signal indicator data
        for frame in frames:
            signal_updates = update_signal_indicators(set(frame["active_tracks"]), signal_traces)
            frame["signals"] = signal_updates
        
        # Create the figure
        fig = create_plotly_figure(edge_traces, label_traces, signal_traces)
        
        # Add filter info to the figure title if filters are applied
        if start_datetime is not None or end_datetime is not None:
            update_figure_title_with_dates(fig, start_datetime, end_datetime)
        
        # Prepare data for JavaScript
        plot_json = json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
        
        # Include date range in response for UI feedback
        filter_info = {}
        if start_datetime is not None:
            filter_info['start'] = start_datetime.isoformat()
        if end_datetime is not None:
            filter_info['end'] = end_datetime.isoformat()
        if net_group_id:
            filter_info['net_group_id'] = net_group_id
            filter_info['interval_ids'] = filtered_interval_ids
            filter_info['filtered_track_ids'] = filtered_track_ids  # Add track IDs for focusing
            # Convert numpy types to native Python types for JSON serialization
            filter_info['interval_statuses'] = convert_numpy_types(interval_statuses)
        
        return {
            "plotly_data": plot_json,
            "frames": frames,
            "time_labels": time_labels,
            "filter_info": filter_info,
            "has_signals": len(signal_traces) > 0
        }
        
    except Exception as e:
        current_app.logger.error(f"Error generating visualization data: {str(e)}")
        return {"error": str(e)}
