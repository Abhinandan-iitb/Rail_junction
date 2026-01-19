"""
Plotting Module for Circuit and Switch Analysis

This module provides comprehensive visualization functions for railway circuit and switch
data analysis, including standard plots, multi-item plots, and short duration event analysis.
"""

import logging
import pandas as pd
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


# ========================== CONFIGURATION & STYLING ==========================

def _create_plot_config(filename_prefix):
    """
    Creates standard Plotly configuration with download options.
    
    Args:
        filename_prefix: Prefix for downloaded filename
        
    Returns:
        Dictionary containing Plotly configuration options
    """
    return {
        'displayModeBar': True,
        'scrollZoom': True,
        'responsive': True,
        'toImageButtonOptions': {
            'format': 'png',
            'filename': filename_prefix,
            'height': 600,
            'width': 1200,
            'scale': 2
        },
        'modeBarButtonsToRemove': ['lasso2d'],
        'doubleClick': 'reset+autosize',
    }


def _add_background_and_borders(fig, length):
    """
    Adds background styling and border lines to multi-item plots.
    
    Args:
        fig: Plotly figure object
        length: Number of items to create borders for
        
    Returns:
        Modified figure object
    """
    fig.update_layout(
        plot_bgcolor="rgba(240, 240, 240, 0.5)",
        paper_bgcolor="white",
    )
    
    fig.add_shape(
        type="line", x0=0, y0=0, x1=1, y1=0, xref="paper", 
        line=dict(color="black", width=3)
    )
    fig.add_shape(
        type="line", x0=0, y0=length, x1=1, y1=length, xref="paper", 
        line=dict(color="black", width=3)
    )
    
    for i in range(1, length):
        fig.add_shape(
            type="line", x0=0, y0=i, x1=1, y1=i, xref="paper", 
            line=dict(color="black", width=2, dash="solid")
        )
    
    return fig


def _add_alternating_backgrounds(fig, item_order):
    """
    Adds alternating background shading for improved visual separation.
    
    Args:
        fig: Plotly figure object
        item_order: List of items to create backgrounds for
        
    Returns:
        Modified figure object
    """
    for i in range(len(item_order)):
        fillcolor = "rgba(200, 200, 200, 0.4)" if i % 2 == 1 else "rgba(245, 245, 245, 0.8)"
        fig.add_shape(
            type="rect", x0=0, y0=i, x1=1, y1=i + 1, xref="paper",
            fillcolor=fillcolor, line_width=0, layer="below"
        )
    
    return fig


def _create_standard_xaxis():
    """Returns standard x-axis configuration."""
    return dict(
        title="Time", 
        type="date", 
        rangeslider=dict(
            visible=True,
            bgcolor="rgba(211, 211, 211, 0.7)",
            bordercolor="black",
            borderwidth=1,
            thickness=0.1
        ),
        gridcolor="rgba(100, 100, 100, 0.3)",
        linecolor="black",
        linewidth=2,
        mirror=True
    )


def _create_standard_yaxis(item_count, item_type="Items"):
    """Returns standard y-axis configuration for multi-item plots."""
    return dict(
        title=dict(text=item_type, font=dict(size=14, color="black")),
        range=[-0.2, item_count + 0.2] if item_count else [0, 1],
        showticklabels=False,
        gridcolor="rgba(100, 100, 100, 0.3)",
        showgrid=True,
        zeroline=True,
        zerolinecolor="black",
        zerolinewidth=2,
        fixedrange=True,
        linecolor="black",
        linewidth=2,
        mirror=True
    )


def _update_standard_layout(fig, title, item_count, item_type="Items"):
    """
    Updates figure layout with standard formatting for multi-item plots.
    
    Args:
        fig: Plotly figure object
        title: Plot title
        item_count: Number of items being plotted
        item_type: Type description (e.g., "Circuits", "Switches")
        
    Returns:
        Modified figure object
    """
    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        xaxis=_create_standard_xaxis(),
        yaxis=_create_standard_yaxis(item_count, item_type),
        showlegend=True,
        hovermode='closest',
        height=max(400, 150 * item_count) if item_count else 400,
        margin=dict(l=150, r=30, t=70, b=50),
        autosize=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            bgcolor="white", bordercolor="black", borderwidth=1
        )
    )
    
    return fig


# ========================== HOVER TEXT GENERATION ==========================

def _create_hover_text(data_type, name, row, additional_fields=None):
    """
    Creates standardized hover text for plot interactions.
    
    Args:
        data_type: Type of data ('circuit' or 'switch')
        name: Name of the circuit or switch
        row: DataFrame row containing the data
        additional_fields: Optional dict with additional metadata
        
    Returns:
        Formatted hover text string
    """
    if data_type == 'circuit':
        hover_text = (
            f"Circuit: {name}<br>"
            f"Start: {row['Start_Time_c']}<br>"
            f"End: {row['End_Time_c']}"
        )
    else:
        hover_text = (
            f"Switch: {name}<br>"
            f"Start: {row['Start_Time_s']}<br>"
            f"End: {row['End_Time_s']}"
        )
    
    if 'Duration' in row and not pd.isnull(row['Duration']):
        duration_label = "Short Duration:" if (additional_fields and 
                                               additional_fields.get('short_duration')) else "Duration:"
        hover_text += f"<br>{duration_label} {row['Duration']}"
    
    timestamp_cols = _get_timestamp_columns(data_type)
    for col_name, col_key in timestamp_cols.items():
        if col_key in row and not pd.isnull(row[col_key]):
            hover_text += f"<br>{col_name}: {row[col_key]}"
    
    return hover_text


def _get_timestamp_columns(data_type):
    """Returns dictionary mapping display names to column names for timestamps."""
    if data_type == 'circuit':
        return {
            'Down Timestamp': 'Down_timestamp',
            'Up Timestamp': 'Up_timestamp',
            'Down Date': 'Down_date',
            'Up Date': 'Up_date'
        }
    else:
        return {
            'Up Timestamp': 'Up_timestamp',
            'Down Timestamp': 'Down_timestamp',
            'Up Date': 'Up_date',
            'Down Date': 'Down_date'
        }


# ========================== COMMON PLOTTING UTILITIES ==========================

def _get_safe_duration(row, duration_col, max_duration):
    """
    Safely retrieves duration value with fallback calculation.
    
    Args:
        row: DataFrame row
        duration_col: Name of duration column
        max_duration: Maximum duration for fallback
        
    Returns:
        Duration in seconds as float
    """
    try:
        duration_sec = row.get(duration_col, 0)
        if pd.isnull(duration_sec) or not isinstance(duration_sec, (int, float)):
            if duration_col.endswith('_c'):
                time_diff = row['End_Time_c'] - row['Start_Time_c']
            else:
                time_diff = row['End_Time_s'] - row['Start_Time_s']
            return time_diff.total_seconds()
        return duration_sec
    except Exception as e:
        logger.warning(f"Error calculating duration: {str(e)}")
        return max_duration


def _calculate_opacity(duration_sec, max_duration):
    """
    Calculates opacity value based on duration relative to maximum.
    
    Args:
        duration_sec: Duration in seconds
        max_duration: Maximum duration threshold
        
    Returns:
        Opacity value between 0.4 and 1.0
    """
    try:
        if duration_sec <= 0:
            return 1.0
        ratio = min(1.0, duration_sec / max_duration)
        opacity = min(1.0, max(0.4, 1.0 - ratio * 0.5))
        return opacity if 0.0 <= opacity <= 1.0 else 0.8
    except (ZeroDivisionError, TypeError, ValueError) as e:
        logger.warning(f"Error calculating opacity: {str(e)}")
        return 0.8


def _get_safe_midpoint(start_time, end_time):
    """
    Safely calculates midpoint between two timestamps.
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        Midpoint timestamp or start_time if calculation fails
    """
    try:
        time_diff = end_time - start_time
        return start_time + (time_diff / 2)
    except Exception as e:
        logger.warning(f"Error calculating midpoint: {str(e)}")
        return start_time


def _add_item_label(fig, y_position, label_text, color, event_count=None):
    """
    Adds a label annotation for an item on the y-axis.
    
    Args:
        fig: Plotly figure object
        y_position: Y-axis position for the label
        label_text: Text to display
        color: Border color for the label
        event_count: Optional event count to append to label
    """
    display_text = f"{label_text} ({event_count})" if event_count is not None else label_text
    fig.add_annotation(
        x=0, y=y_position, xref="paper", yref="y",
        text=display_text,
        showarrow=False,
        font=dict(color="black", size=12, family="Arial Black"),
        align="left",
        bgcolor="white",
        bordercolor=color,
        borderwidth=2,
        borderpad=4
    )


def _add_hover_trace(fig, x, y, name, hover_text, legendgroup, show_legend):
    """Adds invisible trace for hover functionality."""
    fig.add_trace(go.Scatter(
        x=[x], y=[y],
        mode='markers',
        marker=dict(size=1, opacity=0),
        name=name,
        legendgroup=legendgroup,
        showlegend=show_legend,
        hovertext=hover_text,
        hoverinfo="text"
    ))


def _add_event_rectangle(fig, start_time, end_time, y_base, y_height, color, opacity=0.8):
    """Adds a filled rectangle representing an event."""
    fig.add_shape(
        type="rect",
        x0=start_time, x1=end_time,
        y0=y_base + 0.1, y1=y_height - 0.1,
        fillcolor=color,
        opacity=opacity,
        line=dict(width=1.5, color="black"),
        layer="above"
    )


# ========================== SINGLE ITEM PLOTTING ==========================

def _plot_single_item(data, item_name, item_type='circuit', color='blue'):
    """
    Generic function to plot single circuit or switch data.
    
    Args:
        data: DataFrame containing the data
        item_name: Name of the circuit or switch
        item_type: Type of item ('circuit' or 'switch')
        color: Color for the plot
        
    Returns:
        HTML string of the plot
    """
    if data.empty:
        return f"<h3>No data available for the selected criteria.</h3>"

    fig = go.Figure()
    time_cols = ('Start_Time_c', 'End_Time_c') if item_type == 'circuit' else ('Start_Time_s', 'End_Time_s')

    for _, row in data.iterrows():
        hover_text = _create_hover_text(item_type, item_name, row)
        
        fig.add_trace(go.Scatter(
            x=[row[time_cols[0]], row[time_cols[0]], row[time_cols[1]], row[time_cols[1]]],
            y=[0, 1, 1, 0],
            fill='tozeroy',
            mode='lines',
            line=dict(width=2, color=color),
            name=f"{row[time_cols[0]]} - {row[time_cols[1]]}",
            hovertext=hover_text,
            hoverinfo="text"
        ))

    fig.update_layout(
        title=f"{item_type.capitalize()} Plot: {item_name}",
        xaxis=_create_standard_xaxis(),
        yaxis=dict(title="State", range=[-0.2, 1.2], tickmode="array", tickvals=[0, 1]),
        showlegend=True,
        hovermode='closest',
        height=400,
        margin=dict(l=50, r=30, t=50, b=50),
        autosize=True,
    )
    
    config = _create_plot_config(f'{item_type}_{item_name}')
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)


def plot_circuit_data(data, circuit_name, color='blue'):
    """
    Plots single circuit data with enhanced hover functionality.
    
    Args:
        data: DataFrame containing circuit data
        circuit_name: Name of the circuit
        color: Color for the plot (default: blue)
        
    Returns:
        HTML string of the Plotly figure
    """
    return _plot_single_item(data, circuit_name, 'circuit', color)


def plot_switch_data(data, switch_name, color='red'):
    """
    Plots single switch data with enhanced hover functionality.
    
    Args:
        data: DataFrame containing switch data
        switch_name: Name of the switch
        color: Color for the plot (default: red)
        
    Returns:
        HTML string of the Plotly figure or empty plot message
    """
    if data is None or data.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[], y=[], mode='text', text=["No Switch"],
            textposition="middle center"
        ))
        fig.update_layout(
            title="No Switch",
            xaxis=_create_standard_xaxis(),
            yaxis=dict(title="State", range=[-0.2, 1.2], tickmode="array", tickvals=[0, 1]),
            showlegend=True,
            hovermode='closest',
            height=400,
            margin=dict(l=50, r=30, t=50, b=50),
            autosize=True,
        )
        config = _create_plot_config(f'switch_{switch_name}')
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)
    
    return _plot_single_item(data, switch_name, 'switch', color)


# ========================== MULTIPLE ITEMS PLOTTING ==========================

def _get_item_color(item_name, i, colors):
    """Determines color for an item based on name or index."""
    if isinstance(item_name, str):
        if 'NWKR' in item_name:
            return 'blue'
        elif 'RWKR' in item_name:
            return 'red'
    return colors[i % len(colors)]


def _plot_multiple_items(item_data_dict, item_type='circuit', title=None, item_order=None):
    """
    Generic function to plot multiple circuits or switches.
    
    Args:
        item_data_dict: Dictionary mapping item names to DataFrames
        item_type: Type of items ('circuit' or 'switch')
        title: Plot title
        item_order: Optional list specifying order of items
        
    Returns:
        HTML string of the Plotly figure
    """
    fig = go.Figure()
    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#a65628', '#f781bf', '#999999']
    
    time_cols = ('Start_Time_c', 'End_Time_c') if item_type == 'circuit' else ('Start_Time_s', 'End_Time_s')
    item_label = item_type.capitalize() + 's'
    
    if not item_data_dict:
        fig.add_trace(go.Scatter(
            x=[], y=[], mode='text', text=[f"No {item_label} Data"],
            textposition="middle center"
        ))
        item_order = []
    else:
        if item_order is None:
            item_order = sorted(list(item_data_dict.keys()))
        else:
            item_order = [c for c in item_order if c in item_data_dict]
            for item in item_data_dict.keys():
                if item not in item_order:
                    item_order.append(item)
        
        if item_type == 'circuit':
            fig.add_annotation(
                x=0.5, y=1.05, xref="paper", yref="paper",
                text=f"{item_label} Order: {', '.join(item_order)}",
                showarrow=False, font=dict(size=10, color="gray"), align="center"
            )
        
        fig = _add_background_and_borders(fig, len(item_order))
        fig = _add_alternating_backgrounds(fig, item_order)
        
        for i, item_name in enumerate(item_order):
            color = _get_item_color(item_name, i, colors)
            data = item_data_dict[item_name]
            y_base, y_height = i, i + 1
            
            if data is not None and not data.empty:
                for j, row in data.iterrows():
                    if pd.isnull(row[time_cols[0]]) or pd.isnull(row[time_cols[1]]):
                        continue
                    
                    _add_event_rectangle(fig, row[time_cols[0]], row[time_cols[1]], 
                                       y_base, y_height, color)
                    
                    try:
                        mid_time = _get_safe_midpoint(row[time_cols[0]], row[time_cols[1]])
                        hover_text = _create_hover_text(item_type, item_name, row)
                        _add_hover_trace(fig, mid_time, y_base + 0.5, item_name, 
                                       hover_text, item_name, j == 0)
                    except Exception as e:
                        logger.warning(f"Skipping problematic timestamp for {item_type} {item_name}: {str(e)}")
                        continue
            
            _add_item_label(fig, y_base + 0.5, item_name, color)

    title = title or f"Combined {item_label}"
    fig = _update_standard_layout(fig, title, len(item_order), item_label)
    
    config = _create_plot_config(f'combined_{item_type}s_{title}')
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)


def plot_multiple_circuits(circuit_data_dict, title="Combined Circuits", circuit_order=None):
    """
    Plots multiple circuits on the same graph with different y-axis ranges.
    
    Args:
        circuit_data_dict: Dictionary mapping circuit names to DataFrames
        title: Plot title
        circuit_order: Optional list specifying order of circuits
        
    Returns:
        HTML string of the Plotly figure
    """
    return _plot_multiple_items(circuit_data_dict, 'circuit', title, circuit_order)


def plot_multiple_switches(switch_data_dict, title="Combined Switches"):
    """
    Plots multiple switches on the same graph with different y-axis ranges.
    
    Args:
        switch_data_dict: Dictionary mapping switch names to DataFrames
        title: Plot title
        
    Returns:
        HTML string of the Plotly figure
    """
    return _plot_multiple_items(switch_data_dict, 'switch', title)



# ========================== SHORT DURATION EVENT ANALYSIS ==========================

def _plot_short_duration_single_item(data, item_name, item_type, max_duration, color='orange'):
    """
    Generic function to plot short duration events for a single circuit or switch.
    
    Args:
        data: DataFrame containing filtered short duration events
        item_name: Name of the circuit or switch
        item_type: Type of item ('circuit' or 'switch')
        max_duration: Maximum duration threshold in seconds
        color: Color for the plot
        
    Returns:
        HTML string of the Plotly figure
    """
    if data.empty:
        return "<h3>No short-duration events found within the selected criteria.</h3>"

    fig = go.Figure()
    time_cols = ('Start_Time_c', 'End_Time_c') if item_type == 'circuit' else ('Start_Time_s', 'End_Time_s')

    for _, row in data.iterrows():
        hover_text = _create_hover_text(item_type, item_name, row, {'short_duration': True})
        
        fig.add_trace(go.Scatter(
            x=[row[time_cols[0]], row[time_cols[0]], row[time_cols[1]], row[time_cols[1]]],
            y=[0, 1, 1, 0],
            fill='tozeroy',
            mode='lines',
            line=dict(width=2, color=color),
            name=f"{row[time_cols[0]]} - {row[time_cols[1]]}",
            hovertext=hover_text,
            hoverinfo="text"
        ))

    fig.update_layout(
        title=f"Short Duration Events (≤ {pd.to_timedelta(max_duration, unit='s')}) for {item_type.capitalize()}: {item_name}",
        xaxis=_create_standard_xaxis(),
        yaxis=dict(
            title="State", 
            range=[-0.2, 1.2], 
            tickmode="array", 
            tickvals=[0, 1],
            ticktext=["Off", "On"]
        ),
        showlegend=True,
        hovermode='closest',
        height=400,
        margin=dict(l=50, r=30, t=70, b=50),
        autosize=True,
        annotations=[
            dict(
                x=0.5, y=1.05, xref="paper", yref="paper",
                text=f"Showing {len(data)} events with duration ≤ {pd.to_timedelta(max_duration, unit='s')}",
                showarrow=False, font=dict(size=12, color="gray"), align="center"
            )
        ]
    )
    
    config = _create_plot_config(f'short_duration_events_{item_type}_{item_name}')
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)


def _plot_short_duration_multiple_items(item_data_dict, item_type, max_duration, title, item_order=None):
    """
    Generic function to plot short duration events for multiple circuits or switches.
    
    Args:
        item_data_dict: Dictionary mapping item names to DataFrames
        item_type: Type of items ('circuit' or 'switch')
        max_duration: Maximum duration threshold in seconds
        title: Plot title
        item_order: Optional list specifying order of items
        
    Returns:
        HTML string of the Plotly figure
    """
    if not isinstance(max_duration, (int, float)) or max_duration <= 0:
        logger.warning(f"Invalid max_duration: {max_duration}. Using default of 60.")
        max_duration = 60

    fig = go.Figure()
    colors = ['#ff4d00', '#ffaa00', '#00cc99', '#ff00ff', '#00aaff', '#aa00ff', '#ffcc00', '#ff0066']
    
    time_cols = ('Start_Time_c', 'End_Time_c') if item_type == 'circuit' else ('Start_Time_s', 'End_Time_s')
    duration_col = 'Duration_sec_c' if item_type == 'circuit' else 'Duration_sec_s'
    item_label = item_type.capitalize() + 's'
    
    if not item_data_dict:
        fig.add_trace(go.Scatter(
            x=[], y=[], mode='text', text=[f"No Short Duration {item_label} Found"],
            textposition="middle center"
        ))
        item_order = []
    else:
        if item_order is None:
            item_order = sorted(list(item_data_dict.keys()))
        else:
            item_order = [c for c in item_order if c in item_data_dict]
            for item in item_data_dict.keys():
                if item not in item_order:
                    item_order.append(item)
        
        fig.add_annotation(
            x=0.5, y=1.05, xref="paper", yref="paper",
            text=f"Events with duration ≤ {pd.to_timedelta(max_duration, unit='s')}",
            showarrow=False, font=dict(size=12, color="gray"), align="center"
        )
        
        fig = _add_background_and_borders(fig, len(item_order))
        fig = _add_alternating_backgrounds(fig, item_order)
        
        total_events = 0
        
        for i, item_name in enumerate(item_order):
            color = _get_item_color(item_name, i, colors)
            data = item_data_dict[item_name]
            y_base, y_height = i, i + 1
            
            if data is not None and not data.empty:
                total_events += len(data)
                
                for j, row in data.iterrows():
                    if pd.isnull(row[time_cols[0]]) or pd.isnull(row[time_cols[1]]):
                        continue
                    
                    duration_sec = _get_safe_duration(row, duration_col, max_duration)
                    opacity = _calculate_opacity(duration_sec, max_duration)
                    
                    _add_event_rectangle(fig, row[time_cols[0]], row[time_cols[1]], 
                                       y_base, y_height, color, opacity)
                    
                    try:
                        mid_time = _get_safe_midpoint(row[time_cols[0]], row[time_cols[1]])
                        hover_text = _create_hover_text(item_type, item_name, row, {'short_duration': True})
                        _add_hover_trace(fig, mid_time, y_base + 0.5, item_name, 
                                       hover_text, item_name, j == 0)
                    except Exception as e:
                        logger.warning(f"Skipping hover for {item_type} {item_name}: {str(e)}")
                        continue
            
            event_count = len(data) if data is not None and not data.empty else 0
            _add_item_label(fig, y_base + 0.5, item_name, color, event_count)

    title_with_count = f"Short Duration Events Analysis: {title} (Total: {total_events} events)"
    fig = _update_standard_layout(fig, title_with_count, len(item_order), item_label)
    
    config = _create_plot_config(f'short_duration_events_{item_type}s_{title}')
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config=config)


def plot_short_duration_events(data, circuit_name, max_duration, color='orange'):
    """
    Plots circuit data with events shorter than the specified duration.
    
    Args:
        data: DataFrame containing filtered circuit data
        circuit_name: Name of the circuit
        max_duration: Maximum duration threshold in seconds
        color: Color for the plot (default: orange)
        
    Returns:
        HTML string of the Plotly figure
    """
    return _plot_short_duration_single_item(data, circuit_name, 'circuit', max_duration, color)


def plot_multiple_short_duration_circuits(circuit_data_dict, max_duration, title="Short Duration Events", circuit_order=None):
    """
    Plots multiple circuits showing only events shorter than the specified duration.
    
    Args:
        circuit_data_dict: Dictionary mapping circuit names to DataFrames
        max_duration: Maximum duration threshold in seconds
        title: Plot title
        circuit_order: Optional list specifying order of circuits
        
    Returns:
        HTML string of the Plotly figure
    """
    return _plot_short_duration_multiple_items(circuit_data_dict, 'circuit', max_duration, title, circuit_order)


def plot_short_duration_switch_events(data, switch_name, max_duration, color='orange'):
    """
    Plots switch data with events shorter than the specified duration.
    
    Args:
        data: DataFrame containing filtered switch data
        switch_name: Name of the switch
        max_duration: Maximum duration threshold in seconds
        color: Color for the plot (default: orange)
        
    Returns:
        HTML string of the Plotly figure
    """
    return _plot_short_duration_single_item(data, switch_name, 'switch', max_duration, color)


def plot_multiple_short_duration_switches(switch_data_dict, max_duration, title="Short Duration Switch Events"):
    """
    Plots multiple switches showing only events shorter than the specified duration.
    
    Args:
        switch_data_dict: Dictionary mapping switch names to DataFrames
        max_duration: Maximum duration threshold in seconds
        title: Plot title
        
    Returns:
        HTML string of the Plotly figure
    """
    return _plot_short_duration_multiple_items(switch_data_dict, 'switch', max_duration, title)

