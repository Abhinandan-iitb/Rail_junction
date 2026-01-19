"""
Plot generator for the Railway Route Circuit Visualization application.
Creates Plotly cascading timeline visualizations based on circuit data.
"""
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import logging
from datetime import timedelta
import os
import time
from .data_load_movement_analysis import get_route_circuits, has_uploaded_files, UPLOAD_FOLDER, find_files_by_type
from .data_filter_movement_analysis import apply_adaptive_sampling, extract_circuit_sequence, calculate_y_positions

logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_OPACITY = 1.0  # Increased to full opacity for maximum visibility
CIRCUIT_HEIGHT = 0.7  # Increase this value to make circuit boxes taller
CIRCUIT_GAP = 0.3
ROUTE_GAP = 1.0
# Using extremely bright, high-contrast colors for maximum visibility on dark backgrounds
PLOT_COLORS = ['#00ffff', '#ff9500', '#00ff66', '#ff3838', '#c56cf0', 
               '#ffb142', '#ff6b81', '#7efff5', '#fbff00', '#18dcff']
LEGEND_ITEMS_PER_ROW = 5

# Dark theme configuration
DARK_THEME = {
    'paper_bg': '#1a1a1a',         # Dark background for the entire plot
    'plot_bg': '#262626',          # Slightly lighter dark for the plot area
    'grid_color': 'rgba(150, 150, 150, 0.2)',  # Light gray grid
    'text_color': '#ffffff',       # White text
    'axis_line_color': '#ffffff',  # White for axis lines (changed from gray)
    'info_bg': '#2d3035',          # Dark blue-gray for info boxes
    'info_text': '#e0e0e0',        # Light gray for info text
    'hover_bg': 'rgba(50, 50, 50, 0.9)',  # Dark hover background
    'separator_color': 'rgba(255, 255, 255, 0.6)',  # Brighter white separators
    'border_color': '#ffffff',      # White color for borders
    'movement_border_color': '#ffffff',  # White border for movement boxes
    'movement_border_width': 3,     # Even thicker borders for better visibility
    'movement_highlight_color': 'rgba(255, 255, 255, 0.3)'  # Brighter white glow
}

def hex_to_rgba(hex_color, alpha=DEFAULT_OPACITY):
    """
    Convert hex color to rgba format
    
    Args:
        hex_color (str): Hex color code (e.g., "#1f77b4")
        alpha (float): Alpha transparency value (0-1)
        
    Returns:
        str: RGBA color string
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f"rgba({r}, {g}, {b}, {alpha})"
    else:
        # Fallback to white with transparency if invalid hex
        return f"rgba(240, 240, 240, {alpha})"

def create_route_legend(fig, unique_routes, route_colors):
    """
    Create a route color legend at the top of the plot
    
    Args:
        fig (go.Figure): Plotly figure object
        unique_routes (list): List of unique route IDs
        route_colors (dict): Mapping of route IDs to colors
        
    Returns:
        list: Annotations for the legend
    """
    movement_annotations = []
    total_routes = len(unique_routes)
    
    for i, route_id in enumerate(unique_routes):
        color = route_colors[route_id]
        
        # Calculate which row and column this legend item should be in
        row = i // LEGEND_ITEMS_PER_ROW
        col = i % LEGEND_ITEMS_PER_ROW
        
        # Calculate horizontal position - adjust spacing based on number of items
        width_per_item = min(0.18, 0.9 / min(LEGEND_ITEMS_PER_ROW, total_routes))
        x_pos = 0.05 + (col * width_per_item)
        
        # Calculate vertical position - move down for additional rows
        y_pos_base = 1.11 - (row * 0.08)
        
        # Adjust width of boxes based on number of routes
        box_width = min(0.06, width_per_item * 0.4)
        
        # Create a colored box for the route
        fig.add_shape(
            type="rect",
            x0=x_pos - box_width,
            x1=x_pos + box_width,
            y0=y_pos_base - 0.03,
            y1=y_pos_base + 0.03,
            xref="paper",
            yref="paper",
            fillcolor=color,
            line=dict(color=DARK_THEME['border_color'], width=1),
            opacity=1.0,
            layer="above"
        )
        
        # Determine text color based on background color brightness
        text_color = "white" if sum(int(color.lstrip('#')[j:j+2], 16) for j in (0, 2, 4)) < 500 else "black"
        
        # Adjust font size based on number of routes
        font_size = max(8, min(11, 14 - total_routes // 3))
        
        # Add the route name directly inside the box
        # FIXED: Removed 'weight' property - use bold font family instead
        movement_annotations.append(dict(
            x=x_pos,
            y=y_pos_base,
            xref="paper",
            yref="paper",
            text=f"<b>R{route_id}</b>",  # Use HTML bold tag instead
            showarrow=False,
            font=dict(size=font_size, color=text_color, family="Arial Black, Arial, sans-serif"),  # Use bold font family
            align="center"
        ))
    
    # Add a title for the legend if needed, positioned correctly for multiple rows
    if total_routes > 0:
        movement_annotations.append(dict(
            x=0,
            y=1.11,
            xref="paper",
            yref="paper",
            text="<b>Legend:</b>",
            showarrow=False,
            font=dict(size=11, color="black"),  # Removed 'weight' property
            align="left",
            xanchor="right",
            xshift=-10
        ))
    
    return movement_annotations

def add_movement_elements(fig, movements, movement_to_route, df, y_positions, route_colors, 
                         low_detail_mode, movement_id_field="Movement_id"):
    """
    Add visual elements for each train movement
    
    Args:
        fig (go.Figure): Plotly figure object
        movements (list): List of movement IDs
        movement_to_route (dict): Mapping of movement IDs to route IDs
        df (DataFrame): DataFrame with circuit data
        y_positions (dict): Mapping of circuits to y-positions
        route_colors (dict): Mapping of route IDs to colors
        low_detail_mode (bool): Whether to use reduced detail for performance
        movement_id_field (str): Field name for movement ID
        
    Returns:
        list: All shape definitions for the figure
    """
    all_shapes = []
    opacity_base = 0.95 if low_detail_mode else 1.0
    border_width = 1 if low_detail_mode else DARK_THEME['movement_border_width']
    
    # Performance optimization - batch process movements
    batch_size = 50  # Process movements in groups of 50
    total_movements = len(movements)
    shape_batches = []
    
    for batch_start in range(0, total_movements, batch_size):
        batch_end = min(batch_start + batch_size, total_movements)
        current_batch = movements[batch_start:batch_end]
        
        logger.info(f"Processing movement batch {batch_start}-{batch_end} of {total_movements}")
        batch_start_time = time.time()
        batch_shapes = []
        
        # Process each movement in this batch
        for i, movement_id in enumerate(current_batch):
            # Get movement properties
            route_id = movement_to_route.get(movement_id, "Unknown")
            base_color = route_colors.get(route_id, PLOT_COLORS[0])
            color = base_color
            opacity = max(0.9, opacity_base - (i * 0.01))
            border_style = 'solid'
            
            # Filter data for this movement
            movement_data = df[df[movement_id_field] == movement_id].sort_values(by="Down_timestamp")
            
            # Skip visualization for extremely large movements in low detail mode
            if low_detail_mode and len(movement_data) > 500:
                logger.warning(f"Skipping detailed visualization for movement {movement_id} with {len(movement_data)} points")
                # Just add a few key points for hover data
                scatter_points = movement_data.iloc[::max(1, len(movement_data)//10)]
                scatter_x = []
                scatter_y = []
                hover_texts = []
                
                for _, row in scatter_points.iterrows():
                    circuit = row["Circuit_Name"]
                    y_pos = y_positions.get(f"{route_id}_{circuit}", 0)
                    
                    # Create hover text - use timestamps instead of separate date and time
                    hover_text = (
                        f"<b>Movement ID:</b> {movement_id}<br>" +
                        f"<b>Route:</b> {route_id}<br>" +
                        f"<b>Circuit:</b> {circuit}<br>" +
                        f"<b>Down:</b> {row['Down_timestamp']}<br>" +
                        f"<b>Up:</b> {row['Up_timestamp']}<br>" +
                        f"<b>Duration:</b> {row['duration_seconds']:.2f}s<br>"
                    )
                    
                    scatter_x.append(row["Down_timestamp"] + (row["Up_timestamp"] - row["Down_timestamp"])/2)
                    scatter_y.append(y_pos + CIRCUIT_HEIGHT/2)
                    hover_texts.append(hover_text)
                
                # Add a single shape to represent the entire movement
                if len(movement_data) > 0:
                    start_time = movement_data["Down_timestamp"].min()
                    end_time = movement_data["Up_timestamp"].max()
                    # Use the first circuit's position as reference
                    first_circuit = movement_data.iloc[0]["Circuit_Name"]
                    last_circuit = movement_data.iloc[-1]["Circuit_Name"]
                    first_y = y_positions.get(f"{route_id}_{first_circuit}", 0)
                    last_y = y_positions.get(f"{route_id}_{last_circuit}", 0)
                    
                    # Add representative shape
                    batch_shapes.append(
                        dict(
                            type="rect",
                            x0=start_time,
                            x1=end_time,
                            y0=min(first_y, last_y),
                            y1=max(first_y, last_y) + CIRCUIT_HEIGHT,
                            line=dict(color=DARK_THEME['movement_border_color'], width=border_width, dash='dot'),
                            fillcolor=hex_to_rgba(color, 0.3),
                            opacity=0.7,
                            layer="above"
                        )
                    )
                
                # Add scatter points
                if scatter_x:
                    fig.add_trace(
                        go.Scatter(
                            x=scatter_x,
                            y=scatter_y,
                            mode="markers",
                            marker=dict(size=8, opacity=0),
                            hoverinfo="text",
                            text=hover_texts,
                            name=f"Movement {movement_id}",
                            showlegend=False,
                            hovertemplate="%{text}<extra>Movement " + str(movement_id) + "</extra>"
                        )
                    )
                continue
            
            # Standard visualization for movements with reasonable data volume
            shapes = []
            scatter_x = []
            scatter_y = []
            hover_texts = []
            
            # Apply additional down-sampling for very large movements
            if len(movement_data) > 200:
                # Keep key circuit endpoints but sample middle points
                sample_rate = min(1.0, 200 / len(movement_data))
                sampled_indices = set(np.random.choice(
                    range(1, len(movement_data)-1), 
                    size=int(sample_rate * len(movement_data)),
                    replace=False
                ))
                # Always include first and last points
                sampled_indices.update([0, len(movement_data)-1])
                sampled_rows = [row for idx, row in enumerate(movement_data.iterrows()) if idx in sampled_indices]
            else:
                sampled_rows = movement_data.iterrows()
            
            for _, row in sampled_rows:
                circuit = row["Circuit_Name"]
                y_pos = y_positions.get(f"{route_id}_{circuit}", 0)
                
                # Create hover text with timestamps
                hover_text = (
                    f"<b>Movement ID:</b> {movement_id}<br>" +
                    f"<b>Route:</b> {route_id}<br>" +
                    f"<b>Circuit:</b> {circuit}<br>" +
                    f"<b>Down:</b> {row['Down_timestamp']}<br>" +
                    f"<b>Up:</b> {row['Up_timestamp']}<br>" +
                    f"<b>Duration:</b> {row['duration_seconds']:.2f}s<br>"
                )
                
                # Skip glow effect in low detail mode
                if not low_detail_mode:
                    shapes.append(
                        dict(
                            type="rect",
                            x0=row["Down_timestamp"],
                            x1=row["Up_timestamp"],
                            y0=y_pos - 0.1,
                            y1=y_pos + CIRCUIT_HEIGHT + 0.1,
                            line=dict(color="rgba(255,255,255,0)", width=0),
                            fillcolor=DARK_THEME['movement_highlight_color'],
                            opacity=0.9,
                            layer="below"
                        )
                    )
                
                # Add main rectangle
                shapes.append(
                    dict(
                        type="rect",
                        x0=row["Down_timestamp"],
                        x1=row["Up_timestamp"],
                        y0=y_pos,
                        y1=y_pos + CIRCUIT_HEIGHT,
                        line=dict(
                            color=DARK_THEME['movement_border_color'], 
                            width=border_width, 
                            dash=border_style
                        ),
                        fillcolor=color,
                        opacity=opacity,
                        layer="above"
                    )
                )
                
                # Add scatter data point for hover info
                scatter_x.append(row["Down_timestamp"] + (row["Up_timestamp"] - row["Down_timestamp"])/2)
                scatter_y.append(y_pos + CIRCUIT_HEIGHT/2)
                hover_texts.append(hover_text)
            
            # Add shapes for this movement to the batch
            batch_shapes.extend(shapes)
            
            # Add scatter trace for this movement
            if scatter_x:
                fig.add_trace(
                    go.Scatter(
                        x=scatter_x,
                        y=scatter_y,
                        mode="markers",
                        marker=dict(
                            size=10, 
                            opacity=0,
                            sizeref=2.0,
                            sizemode='area'
                        ),
                        hoverinfo="text",
                        text=hover_texts,
                        name=f"Movement {movement_id}",
                        showlegend=False,
                        hovertemplate="%{text}<extra>Movement " + str(movement_id) + "</extra>",
                        selectedpoints=[],
                        unselected=dict(marker={'opacity': 0}),
                        selected=dict(marker={'opacity': 0})
                    )
                )
        
        # Add shapes from this batch to the shape collection
        shape_batches.append(batch_shapes)
        logger.info(f"Batch {batch_start}-{batch_end} processed in {time.time() - batch_start_time:.2f}s with {len(batch_shapes)} shapes")
    
    # Combine all shape batches
    for batch in shape_batches:
        all_shapes.extend(batch)
    
    logger.info(f"Total movement elements: {len(all_shapes)} shapes")
    return all_shapes

def apply_enhanced_adaptive_sampling(df, time_span_hours, route_id_field="Route_id", movement_id_field="Movement_id"):
    """
    Apply more aggressive adaptive sampling for very long time spans
    
    Args:
        df (DataFrame): Input dataframe with circuit data
        time_span_hours (float): Time span in hours
        route_id_field (str): Field name for route ID
        movement_id_field (str): Field name for movement ID
        
    Returns:
        DataFrame: Aggressively sampled dataframe
    """
    # Define sampling strategy based on time span
    if time_span_hours <= 48:
        return df  # No sampling for shorter time spans
    elif time_span_hours <= 168:  # 1 week
        sample_rate = 0.3  # Keep 30% of points
        critical_window = 3  # Points to keep at start/end of each circuit
    elif time_span_hours <= 720:  # 1 month
        sample_rate = 0.15  # More aggressive - keep only 15% of points
        critical_window = 2  # Fewer critical points
    else:  # More than a month
        sample_rate = 0.05  # Very aggressive - keep only 5%
        critical_window = 1  # Just keep the absolute endpoints
    
    logger.info(f"Applying enhanced adaptive sampling for {time_span_hours}h span (rate={sample_rate})")
    start_time = time.time()
    
    sampled_df = pd.DataFrame()
    
    # Add a unique ID to each row for tracking
    df = df.copy()
    df['_temp_row_id'] = range(len(df))
    
    # Process each route separately to maintain route-specific patterns
    for route_id in df[route_id_field].unique():
        route_data = df[df[route_id_field] == route_id]
        
        # Process each movement separately
        for mov_id in route_data[movement_id_field].unique():
            mov_data = route_data[route_data[movement_id_field] == mov_id]
            
            # If very few points, keep them all
            if len(mov_data) <= 20:
                sampled_df = pd.concat([sampled_df, mov_data])
                continue
            
            # Extract critical points from each circuit (start and end points)
            critical_points = []
            critical_indices = set()
            
            for circuit in mov_data['Circuit_Name'].unique():
                circuit_data = mov_data[mov_data['Circuit_Name'] == circuit]
                
                if len(circuit_data) <= critical_window * 2:
                    # Keep all points for small circuits
                    critical_points.append(circuit_data)
                    critical_indices.update(circuit_data['_temp_row_id'])
                else:
                    # Keep beginning and end points
                    start_points = circuit_data.iloc[:critical_window]
                    end_points = circuit_data.iloc[-critical_window:]
                    critical_points.extend([start_points, end_points])
                    critical_indices.update(start_points['_temp_row_id'])
                    critical_indices.update(end_points['_temp_row_id'])
            
            # Process non-critical points - sample based on configuration
            remaining = mov_data[~mov_data['_temp_row_id'].isin(critical_indices)]
            
            if len(remaining) > 0:
                # Use stratified sampling to maintain pattern distribution
                sample_size = max(1, int(len(remaining) * sample_rate))
                
                # Try to stratify by time to keep distribution
                try:
                    # Create time buckets for stratified sampling using timestamp
                    remaining['time_bucket'] = pd.qcut(
                        remaining['Down_timestamp'].astype(int), 
                        min(10, len(remaining)), 
                        labels=False
                    )
                    
                    # Sample from each time bucket
                    strat_sampled = remaining.groupby('time_bucket', group_keys=False).apply(
                        lambda x: x.sample(min(max(1, int(len(x) * sample_rate)), len(x)))
                    )
                except Exception as e:
                    # Fall back to simple random sampling if stratified fails
                    strat_sampled = remaining.sample(sample_size)
                
                # Combine critical and sampled points
                if critical_points:
                    full_sample = pd.concat(critical_points + [strat_sampled])
                else:
                    full_sample = strat_sampled
            else:
                # No remaining points, just use critical points
                if critical_points:
                    full_sample = pd.concat(critical_points)
                else:
                    full_sample = pd.DataFrame()
            
            # Add this movement's sampled data to the overall result
            sampled_df = pd.concat([sampled_df, full_sample])
    
    # Clean up the temporary ID column
    if '_temp_row_id' in sampled_df.columns:
        sampled_df = sampled_df.drop(columns=['_temp_row_id'])
        
    # Sort by time to maintain chronology - use Down_timestamp
    if 'Down_timestamp' in sampled_df.columns:
        sampled_df = sampled_df.sort_values('Down_timestamp')
    
    logger.info(f"Sampling complete: {len(df)} → {len(sampled_df)} points ({(len(sampled_df)/len(df)*100):.1f}%) in {time.time()-start_time:.2f}s")
    return sampled_df

def add_visual_elements(fig, all_shapes, route_boundary_positions, min_time, max_time, 
                      total_plot_height, y_positions_ticks, y_labels, add_grid_lines, add_route_separators):
    """
    Add visual elements like separators, grid lines and circuit labels
    
    Args:
        fig (go.Figure): Plotly figure object
        all_shapes (list): Shape definitions to add to figure
        route_boundary_positions (list): Y-positions for route separators
        min_time, max_time: Time range for the plot
        total_plot_height (float): Total height of the plot
        y_positions_ticks (list): Y-positions for tick marks
        y_labels (list): Labels for each position
        add_grid_lines (bool): Whether to add grid lines
        add_route_separators (bool): Whether to add route separators
    """
    # Add all shapes at once
    fig.update_layout(shapes=all_shapes)
    
    # Add visual separators between routes with brighter white color
    if add_route_separators:
        for y_pos in route_boundary_positions:
            fig.add_shape(
                type="line",
                x0=min_time - timedelta(minutes=30) if min_time is not None else 0,
                x1=max_time + timedelta(minutes=30) if max_time is not None else 1,
                y0=y_pos,
                y1=y_pos,
                line=dict(color=DARK_THEME['separator_color'], width=2, dash="dash"),
                layer="below"
            )
    
    # Add grid lines with reasonable density
    if add_grid_lines:
        grid_step = max(1, int(total_plot_height / 40))  # Change 40 to adjust grid line density
        for y in range(0, int(total_plot_height), grid_step):
            fig.add_shape(
                type="line",
                x0=min_time - timedelta(minutes=30) if min_time is not None else 0,
                x1=max_time + timedelta(minutes=30) if max_time is not None else 1,
                y0=y,
                y1=y,
                line=dict(color=DARK_THEME['grid_color'], width=1, dash="dot"),
                layer="below"
            )

def add_circuit_labels(fig, y_positions_ticks, y_labels):
    """
    Add custom circuit labels directly inside the plot area, aligned with grid sections
    
    Args:
        fig (go.Figure): Plotly figure object
        y_positions_ticks (list): Y-positions for labels
        y_labels (list): Text labels to add
    """
    # Use consistent approach for all datasets regardless of size
    # Calculate appropriate step size based on total number of labels
    # to avoid overcrowding while ensuring good coverage
    total_labels = len(y_positions_ticks)
    
    # Target a reasonable number of labels (40-50 max) to avoid overcrowding
    target_label_count = min(total_labels, 40)
    label_step = max(1, total_labels // target_label_count)
    
    # Always include key positions: start, end, and some evenly distributed points
    label_indices = [i for i in range(len(y_positions_ticks)) 
                  if i % label_step == 0 or i == 0 or i == len(y_positions_ticks)-1]
    
    # Add midpoints for better distribution if we have few labels
    if len(label_indices) < 15 and total_labels > 15:
        mid_indices = [i for i in range(len(y_positions_ticks)) 
                     if i % (label_step//2) == label_step//4 and i not in label_indices]
        label_indices.extend(mid_indices[:15-len(label_indices)])
        label_indices.sort()
    
    # Add each label with optimized appearance
    for i in label_indices:
        y_pos = y_positions_ticks[i]
        label = y_labels[i]
        
        # Use consistent font size for all datasets
        font_size = 9
        
        # Add the label directly inside the plot area at the beginning of the row
        fig.add_annotation(
            x=0.001,  # Small offset from left edge of plot (not paper)
            y=y_pos,
            xref="x domain",  # Use x domain to position relative to plot area
            yref="y",
            text=label,
            showarrow=False,
            xanchor="left",  # Left-align the text
            yanchor="middle",  # Center vertically in the row
            font=dict(size=font_size, color=DARK_THEME['text_color'], family="Arial, sans-serif"),
            bgcolor="rgba(40, 40, 40, 0.9)",  # Dark background for better contrast
            bordercolor=DARK_THEME['border_color'],  # White border
            borderwidth=1,
            borderpad=2,  # Increase this for more padding inside labels
            opacity=1,
            align="left",
            width=100  # Increase this to make label boxes wider
        )
        
        # Add a subtle highlight line on the grid row to better identify it
        # Makes the row easier to spot even with many labels
        fig.add_shape(
            type="line",
            x0=0.001,  # Start just after the label
            x1=0.02,   # Extend slightly into the plot
            y0=y_pos,
            y1=y_pos,
            xref="x domain",
            yref="y",
            line=dict(color=DARK_THEME['border_color'], width=1),  # White line
            layer="above"
        )

def configure_axes(fig, min_time, max_time, y_min, y_max, y_positions_ticks, y_labels):
    """
    Configure axes settings for the plot
    
    Args:
        fig (go.Figure): Plotly figure object
        min_time, max_time: Time range for the plot
        y_min, y_max: Y-axis range
        y_positions_ticks (list): Y-positions for tick marks
        y_labels (list): Labels for each position
    """
    # Add padding to the time range for better visualization
    time_padding = (max_time - min_time) * 0.05
    x_min = min_time - time_padding
    x_max = max_time + time_padding
    
    # Configure x-axis with explicit range for both main view and rangeslider
    fig.update_xaxes(
        title="Time",
        showgrid=True,
        gridwidth=1,
        gridcolor=DARK_THEME['grid_color'],
        zeroline=False,
        constrain='domain',
        range=[x_min, x_max],  # Set explicit range for main view
        title_font=dict(size=14, color=DARK_THEME['text_color']),
        tickfont=dict(color=DARK_THEME['text_color']),
        linecolor=DARK_THEME['border_color'],  # White axis line
        linewidth=2,  # Slightly thicker for visibility
        type="date",
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1h", step="hour", stepmode="backward"),
                dict(count=6, label="6h", step="hour", stepmode="backward"),
                dict(count=12, label="12h", step="hour", stepmode="backward"),
                dict(count=1, label="1d", step="day", stepmode="backward"),
                dict(step="all", label="All")
            ]),
            bgcolor="rgba(60, 60, 60, 0.8)",
            bordercolor="rgba(100, 100, 100, 0.8)",
            borderwidth=1,
            x=0.05,
            y=1.02,
            font=dict(size=12, color=DARK_THEME['text_color'])
        ),
        rangeslider=dict(
            visible=True, 
            thickness=0.07,
            bgcolor="rgba(60, 60, 60, 0.5)",
            bordercolor="rgba(100, 100, 100, 0.5)",
            borderwidth=1,
            range=[x_min, x_max],  # Set explicit range for rangeslider to match data
            autorange=False        # Disable autorange to use our custom range
        )
    )
    
    # Configure y-axis with improved grid alignment
    fig.update_yaxes(
        title="Circuit",
        showgrid=True,  # Show grid lines to help identify sections
        gridcolor=DARK_THEME['grid_color'],
        gridwidth=1,
        zeroline=False,
        range=[y_min, y_max],
        scaleanchor="y",
        constrain="domain",
        tickmode='array',
        tickvals=y_positions_ticks,
        ticktext=y_labels,
        tickangle=0,
        fixedrange=True,  # Prevent y-axis from zooming
        showticklabels=False,  # Hide default tick labels since we use custom annotations
        side='left',
        title_font=dict(color=DARK_THEME['text_color']),
        linecolor=DARK_THEME['border_color'],  # White axis line
        linewidth=2,  # Slightly thicker for visibility
        # Add grid divisions that match circuit positions exactly
        dtick=1.0  # Assuming each circuit is 1.0 unit apart
    )

def generate_plot(df, low_detail_mode=False):
    """
    Generate a Plotly timeline visualization with optional low-detail mode
    for very large datasets.
    
    Args:
        df (DataFrame): DataFrame containing circuit data for one or more routes
        low_detail_mode (bool): If True, use simplified rendering for better performance
        
    Returns:
        str: HTML representation of the Plotly figure
    """
    try:
        start_time = time.time()
        logger.info("Starting plot generation")
        
        if df.empty:
            return "<div class='alert alert-warning'>No data to display</div>"
        
        # Calculate data size
        row_count = len(df)
        unique_routes_count = df["Route_id"].nunique()
        
        # Performance warning for large datasets
        if row_count > 10000 or unique_routes_count > 8:
            logger.warning(f"Large dataset detected: {row_count} rows, {unique_routes_count} routes")
        
        # Apply adaptive sampling for large datasets
        if row_count > 5000:  # Lower threshold for sampling (was 10000)
            # Calculate time span in hours
            time_range = df[["Down_timestamp", "Up_timestamp"]].stack().agg(["min", "max"])
            min_time, max_time = time_range["min"], time_range["max"]
            time_span_hours = (max_time - min_time).total_seconds() / 3600
            
            # Use enhanced sampling for long time spans
            if time_span_hours > 24:  # More than 24 hours (was 48)
                df = apply_enhanced_adaptive_sampling(df, time_span_hours)
            else:
                df = apply_adaptive_sampling(df, time_span_hours)
        else:
            # Get time range for automatic range setting
            time_range = df[["Down_timestamp", "Up_timestamp"]].stack().agg(["min", "max"])
            min_time, max_time = time_range["min"], time_range["max"]
        
        # Auto-enable low detail mode for large datasets
        if row_count > 20000 or (max_time - min_time).days > 3:
            logger.info(f"Auto-enabling low detail mode for large dataset ({row_count} rows, {(max_time - min_time).days} days)")
            low_detail_mode = True
            
        # Field identification
        movement_id_field = "Movement_id"
        route_id_field = "Route_id"
        
        # Get unique routes and their movements
        unique_routes = sorted(df[route_id_field].unique())
        logger.info(f"Routes to visualize: {unique_routes}")
        
        # Check if we're using uploaded files - using file type detection instead of hardcoded filenames
        using_uploads = has_uploaded_files()
        if using_uploads:
            # Find files by content type instead of specific filenames
            route_chart_files = find_files_by_type('route_chart')
            circuit_data_files = find_files_by_type('circuit_data')
            combined_data_files = find_files_by_type('combined_data')
            
            upload_files_info = {
                'route_chart': len(route_chart_files),
                'circuit_data': len(circuit_data_files),
                'combined_data': len(combined_data_files)
            }
            logger.info(f"Using uploaded files: {upload_files_info}")
        else:
            logger.info("Using default database files")
        
        # Load route circuit sequences
        route_circuits = get_route_circuits()
        
        # Check if we have circuit sequences for all routes
        missing_sequences = [r for r in unique_routes if r not in route_circuits]
        if missing_sequences:
            if using_uploads:
                logger.warning(f"Missing circuit sequences in uploaded files for routes: {missing_sequences}")
            else:
                logger.warning(f"Missing circuit sequences for routes: {missing_sequences}")
            
            # Extract missing sequences from the data
            for route_id in missing_sequences:
                circuits = extract_circuit_sequence(df, route_id, movement_id_field)
                if circuits:
                    route_circuits[route_id] = circuits
                    logger.info(f"Extracted circuit sequence for route {route_id} from data: {circuits}")
                else:
                    logger.warning(f"Could not extract circuit sequence for route {route_id} - visualization may be incorrect")
        
        # Get unique movements
        movements = sorted(df[movement_id_field].unique())
        logger.info(f"Displaying all {len(movements)} movements")
        
        # Map movements to their routes
        movement_to_route = dict(df.drop_duplicates([movement_id_field, route_id_field])
                              [[movement_id_field, route_id_field]].values)
        
        # Create a figure
        fig = go.Figure()
        
        # Map routes to colors
        route_colors = {route_id: PLOT_COLORS[i % len(PLOT_COLORS)] for i, route_id in enumerate(unique_routes)}
        
        # Force ultra low-detail mode if duration > 3 days (was 5 days)
        if (max_time - min_time).days > 3:
            logger.info("Long duration detected (>3 days): forcing ultra low-detail mode.")
            low_detail_mode = True

        # Adjust detail level based on mode and data size
        if low_detail_mode or len(df) > 50000:  # Lower threshold (was 100000)
            logger.info("Ultra low-detail mode activated for performance")
            enable_circuit_labels = True  # Changed: always enable circuit labels
            add_route_separators = True
            add_grid_lines = False
        else:
            # Normal detail level
            enable_circuit_labels = True
            add_route_separators = True
            add_grid_lines = True
        
        # Calculate y-positions for each circuit based on route organization
        (y_positions, y_labels, y_positions_ticks, route_boundary_positions,
         circuit_route_map, missing_route_data, total_plot_height) = calculate_y_positions(
            unique_routes, route_circuits, df)
        
        # Add route color legend
        movement_annotations = create_route_legend(fig, unique_routes, route_colors)
        
        # Performance measurement
        shapes_start_time = time.time()
        logger.info(f"Starting movement element generation at {shapes_start_time - start_time:.2f}s")
        
        # Add visual elements for each movement
        all_shapes = add_movement_elements(
            fig, movements, movement_to_route, df, y_positions, route_colors, 
            low_detail_mode, movement_id_field)
        
        logger.info(f"Movement elements generated in {time.time() - shapes_start_time:.2f}s")
        
        # Calculate y-axis padding to prevent elements from being cut off
        y_padding = max(2, total_plot_height * 0.05)
        y_max = total_plot_height + y_padding
        y_min = -y_padding
        
        # Add visual elements like separators and grid lines
        add_visual_elements(
            fig, all_shapes, route_boundary_positions, min_time, max_time, 
            total_plot_height, y_positions_ticks, y_labels, add_grid_lines, add_route_separators)
        
        # Add all annotations
        fig.update_layout(annotations=movement_annotations)
        
        # Add custom y-axis circuit labels if enabled (which is now always true)
        if enable_circuit_labels:
            # Always use the full set of labels and let add_circuit_labels handle the sampling
            # This ensures consistent label structure for both short and long duration plots
            add_circuit_labels(fig, y_positions_ticks, y_labels)
        
        # Configure axes
        configure_axes(fig, min_time, max_time, y_min, y_max, y_positions_ticks, y_labels)
        
        # Calculate optimal height based on number of circuits and routes
        plot_height = max(400, min(1000, total_plot_height * 40))  # Reduced multiplier for height make the whole plot taller
        
        # Calculate legend rows and top margin for layout placement
        legend_rows = (unique_routes_count // LEGEND_ITEMS_PER_ROW) + 1
        top_margin =  + (legend_rows - 1) * 30
        
        # Update layout without overriding movement shapes
        fig.update_layout(
            title={
                'text': "Railway Route Circuit Grid",
                'y': 0.98,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': dict(size=18, color=DARK_THEME['text_color'])
            },
            height=plot_height,
            showlegend=False,
            hovermode="closest",
            margin=dict(l=140, r=40, b=80, t=top_margin),
            paper_bgcolor=DARK_THEME['paper_bg'],
            plot_bgcolor=DARK_THEME['plot_bg'],
            dragmode='zoom',
            clickmode='event',
            autosize=True,
            yaxis_scaleanchor='x',
            transition={
                'duration': 200,
                'easing': 'cubic-in-out'
            },
            font=dict(color=DARK_THEME['text_color'])
        )
        
        # Add outer border shape without overwriting existing shapes
        fig.add_shape(
            dict(
                type='rect',
                xref='paper', yref='paper',
                x0=0, y0=0, x1=1, y1=1,
                line=dict(color=DARK_THEME['border_color'], width=3),
                fillcolor='rgba(0,0,0,0)',
                layer='below'
            )
        )
        
        # Simplified configuration for performance
        config = {
            'responsive': True,
            'displayModeBar': True,
            'modeBarButtonsToAdd': [
                'resetScale2d',
                'zoomIn2d',
                'zoomOut2d',
                'autoScale2d'
            ],
            'modeBarButtonsToRemove': [
                'lasso2d', 
                'select2d', 
                'hoverCompareCartesian'
            ],
            'displaylogo': False,
            'scrollZoom': True,
            'doubleClick': 'reset+autosize',
            'toImageButtonOptions': {
                'format': 'png',
                'filename': 'railway_route_grid'
            }
        }
        
        # Generate the plot HTML
        logger.info("Generating HTML...")
        plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)
        
        # Simplified JavaScript for improved performance
        zoom_enhancement_js = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                var plotDivs = document.querySelectorAll('.plotly-graph-div');
                plotDivs.forEach(function(div) {
                    if (div._fullLayout) {
                        div.on('plotly_relayout', function(eventdata) {
                            if (eventdata['yaxis.range[0]'] !== undefined || 
                                eventdata['yaxis.range[1]'] !== undefined) {
                                var update = {
                                    'yaxis.range': [%s, %s]
                                };
                                Plotly.relayout(div, update);
                            }
                        });
                    }
                });
            }, 1000);
        });
        </script>
        """ % (y_min, y_max)
        
        # Only include debug JS if not in low detail mode
        debug_js = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                var plotDivs = document.querySelectorAll('.plotly-graph-div');
                plotDivs.forEach(function(div) {
                    if (div._fullLayout) {
                        setTimeout(function() {
                            Plotly.redraw(div);
                        }, 500);
                    }
                });
            }, 1000);
        });
        </script>
        """ if not low_detail_mode else ""
        
        # Add custom CSS for dark theme with enhanced visibility
        dark_theme_css = """
        <style>
        .js-plotly-plot .plotly .modebar {
            background-color: rgba(40, 40, 40, 0.7) !important;
        }
        .js-plotly-plot .plotly .modebar-btn path {
            fill: #e0e0e0 !important;
        }
        .js-plotly-plot .plotly .modebar-btn.active path,
        .js-plotly-plot .plotly .modebar-btn:hover path {
            fill: #ffffff !important;
        }
        .js-plotly-plot .plotly .hoverlayer .hover {
            background-color: rgba(40, 40, 40, 0.95) !important;
            color: #ffffff !important;
            border-color: #ffffff !important;
            border-width: 2px !important;
            box-shadow: 0 0 10px rgba(255,255,255,0.5) !important;
        }
        .js-plotly-plot .plotly .hovertext text {
            fill: #ffffff !important;
            font-weight: bold !important;
        }
        /* Add outer border to the plot */
        .js-plotly-plot {
            border: 3px solid #ffffff !important;
            border-radius: 4px;
            box-shadow: 0 0 15px rgba(255,255,255,0.3) !important;
        }
        /* Enhance visibility of plot elements */
        .js-plotly-plot path.border {
            stroke: #ffffff !important;
            stroke-width: 3px !important;
        }
        /* Make text more readable */
        .js-plotly-plot .gtitle, .js-plotly-plot .xtitle, .js-plotly-plot .ytitle {
            font-weight: bold !important;
        }
        /* Force plot elements to be visible */
        .js-plotly-plot .plotly .layer-above rect {
            stroke: #ffffff !important;
            stroke-width: 3px !important;
            fill-opacity: 1 !important;
            stroke-opacity: 1 !important;
        }
        </style>
        """
        
        # Add performance metrics with dark-themed alert
        elapsed_time = time.time() - start_time
        logger.info(f"Plot generated in {elapsed_time:.2f} seconds")
        
        plot_html = f"""
        {dark_theme_css}
        <div class='alert alert-info p-1 mb-2' style='font-size: 0.8rem; background-color: {DARK_THEME['info_bg']}; color: {DARK_THEME['info_text']}; border-color: #444444;'>
            Data: {len(df)} points across {unique_routes_count} routes. Rendered in {elapsed_time:.2f}s.
            {f"<span style='color: #ffcc00;'>⚠️ Large dataset - performance optimizations applied</span>" if low_detail_mode or row_count > 10000 else ""}
        </div>
        {plot_html}
        {zoom_enhancement_js}
        {debug_js}
        """
        
        # Add route data warning if needed with dark theme
        if missing_route_data:
            warning_message = f"Unable to plot route(s): {', '.join(missing_route_data)} due to missing circuit data."
            
            # Add more specific message if using uploads
            if using_uploads:
                warning_message += " Please check that your uploaded files contain all necessary circuit data."
                
            plot_html = f"""
            <div class='alert alert-warning p-1 mb-2' style='background-color: #4d3800; color: #ffcc00; border-color: #664d00;'>
                ⚠️ {warning_message}
            </div>
            {plot_html}
            """
        
        return plot_html
            
    except Exception as e:
        logger.error(f"Error generating plot: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"<div class='alert alert-danger'>Error generating plot: {str(e)}</div>"
