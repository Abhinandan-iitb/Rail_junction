"""
Routes Module for Circuit and Switch Analysis

This module handles all HTTP endpoints for railway circuit and switch analysis,
including data visualization, filtering, CSV export, and file upload functionality.
"""

from flask import render_template, request, jsonify, current_app, redirect, url_for, session, flash, send_file
import pandas as pd
import os
import io
from datetime import datetime
import logging
from collections import OrderedDict
from werkzeug.utils import secure_filename
import traceback

from . import circuit_switch_analysis_bp
from modules.circuit_switch_analysis.load_data_circuit_switch_analysis import load_data_from_database
from modules.circuit_switch_analysis.filter_data_circuit_switch_analysis import (
    validate_circuit, filter_circuit_data, filter_short_duration_circuits,
    get_matching_switches, filter_switch_data, filter_short_duration_switches
)
from modules.circuit_switch_analysis.plot_circuit_switch_analysis import (
    plot_multiple_circuits, plot_multiple_short_duration_circuits,
    plot_multiple_switches, plot_multiple_short_duration_switches
)
from modules.circuit_switch_analysis.csv_download_circuit_switch_analysis import (
    prepare_csv_data, combine_dataframes_for_csv,
    collect_short_duration_switch_data, collect_circuit_data,
    collect_short_duration_circuit_data, collect_switch_data
)

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

circuit_df, switch_df = load_data_from_database()

if circuit_df is None or switch_df is None:
    logger.critical("Failed to load circuit or switch data.")
    circuit_df = circuit_df or pd.DataFrame(columns=[
        'Circuit_name', 'Down_date', 'Down_time', 'Up_date', 'Up_time', 
        'Duration', 'Start_Time_c', 'End_Time_c', 'Duration_sec_c'
    ])
    switch_df = switch_df or pd.DataFrame(columns=[
        'Switch_name', 'Up_date', 'Up_time', 'Down_date', 'Down_time', 
        'Duration', 'Start_Time_s', 'End_Time_s', 'Duration_sec_s'
    ])

unique_circuits = sorted(circuit_df['Circuit_name'].unique().tolist()) if len(circuit_df) > 0 else []



# ========================== DATA PROCESSING HELPERS ==========================

def process_regular_circuit_data(circuit_name, additional_circuits, from_time, to_time, min_duration):
    """
    Process regular circuit data for specified circuits and time range.
    
    Args:
        circuit_name: Primary circuit name
        additional_circuits: List of additional circuit names
        from_time: Start timestamp
        to_time: End timestamp
        min_duration: Minimum duration in seconds
        
    Returns:
        Tuple of (all_circuits_data, circuit_order, circuit_colors)
    """
    all_circuits_data = {}
    circuit_order = [circuit_name]
    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#a65628', '#f781bf', '#999999']
    circuit_colors = {}
    
    for c in additional_circuits:
        if c != circuit_name and validate_circuit(c, circuit_df) and c not in circuit_order:
            circuit_order.append(c)
    
    for i, c_name in enumerate(circuit_order):
        filtered_data = filter_circuit_data(c_name, circuit_df, from_time, to_time, min_duration)
        all_circuits_data[c_name] = filtered_data
        circuit_colors[c_name] = colors[i % len(colors)]
        
    return all_circuits_data, circuit_order, circuit_colors


def process_short_duration_circuit_data(circuit_order, from_time, to_time, max_duration_seconds):
    """
    Process short duration circuit data for specified circuits.
    
    Args:
        circuit_order: List of circuit names
        from_time: Start timestamp
        to_time: End timestamp
        max_duration_seconds: Maximum duration threshold in seconds
        
    Returns:
        Dictionary of circuit name to short duration DataFrame
    """
    all_short_duration_data = {}
    
    for c_name in circuit_order:
        short_duration_data = filter_short_duration_circuits(
            c_name, circuit_df, from_time, to_time, max_duration_seconds
        )
        
        if not short_duration_data.empty:
            all_short_duration_data[c_name] = short_duration_data
            logger.info(f"Added {c_name} with {len(short_duration_data)} short duration events")
    
    return all_short_duration_data


def process_switch_data(circuit_name, from_time, to_time, min_duration):
    """
    Process switch data for specified circuit.
    
    Args:
        circuit_name: Circuit name
        from_time: Start timestamp
        to_time: End timestamp
        min_duration: Minimum duration in seconds
        
    Returns:
        Tuple of (filtered_switches, switch_data_dict) or (None, None)
    """
    matching_switches = get_matching_switches(circuit_name, switch_df)
    
    if matching_switches is None:
        return None, None
    
    filtered_switches = filter_switch_data(matching_switches, from_time, to_time, min_duration)
    
    if filtered_switches is None or filtered_switches.empty:
        return None, None
    
    switch_data_dict = {
        switch: filtered_switches[filtered_switches['Switch_name'] == switch] 
        for switch in filtered_switches['Switch_name'].unique()
    }
    
    return filtered_switches, switch_data_dict


def process_short_duration_switch_data(circuit_name, from_time, to_time, max_duration_seconds):
    """
    Process short duration switch data for specified circuit.
    
    Args:
        circuit_name: Circuit name
        from_time: Start timestamp
        to_time: End timestamp
        max_duration_seconds: Maximum duration threshold in seconds
        
    Returns:
        Dictionary of switch name to short duration DataFrame or None
    """
    matching_switches = get_matching_switches(circuit_name, switch_df)
    
    if matching_switches is None:
        return None
    
    short_duration_switches = filter_short_duration_switches(
        matching_switches, from_time, to_time, max_duration_seconds
    )
    
    if short_duration_switches is None or short_duration_switches.empty:
        return None
    
    short_duration_switch_dict = {}
    
    for switch in short_duration_switches['Switch_name'].unique():
        switch_data = short_duration_switches[short_duration_switches['Switch_name'] == switch]
        
        required_cols = ['Start_Time_s', 'End_Time_s', 'Duration_sec_s']
        if all(col in switch_data.columns for col in required_cols):
            for col in ['Start_Time_s', 'End_Time_s']:
                if not pd.api.types.is_datetime64_any_dtype(switch_data[col]):
                    switch_data[col] = pd.to_datetime(switch_data[col], errors='coerce')
            
            if not switch_data.empty:
                short_duration_switch_dict[switch] = switch_data
    
    return short_duration_switch_dict if short_duration_switch_dict else None


def generate_plots(all_circuits_data, circuit_order, all_short_duration_data, 
                   switch_data_dict, short_duration_switch_dict, 
                   all_short_duration_switch_data, circuit_name, max_duration_seconds):
    """
    Generate all visualization plots.
    
    Returns:
        Tuple of (circuit_plots, switch_plots, short_duration_plots, short_duration_switch_plots)
    """
    circuit_plots = OrderedDict()
    switch_plots = {}
    short_duration_plots = OrderedDict()
    short_duration_switch_plots = OrderedDict()
    
    if len(all_circuits_data) >= 1:
        circuit_plots["combined"] = plot_multiple_circuits(
            all_circuits_data, title="Combined Circuits", circuit_order=circuit_order
        )
    
    if all_short_duration_data:
        short_duration_order = [c for c in circuit_order if c in all_short_duration_data]
        try:
            short_duration_plots["combined"] = plot_multiple_short_duration_circuits(
                all_short_duration_data, max_duration_seconds,
                title="Short Duration Events Analysis", circuit_order=short_duration_order
            )
        except Exception as e:
            logger.error(f"Error generating short duration circuit plot: {str(e)}")
            short_duration_plots["combined"] = f"<div class='alert alert-warning'>Error: {str(e)}</div>"
    
    if switch_data_dict:
        switch_plots[circuit_name] = plot_multiple_switches(
            switch_data_dict, title=f"All Switches for {circuit_name}"
        )
    
    if short_duration_switch_dict:
        try:
            short_duration_switch_plots[f"{circuit_name}_switches"] = plot_multiple_short_duration_switches(
                short_duration_switch_dict, max_duration_seconds,
                title=f"Short Duration Switch Events for {circuit_name}"
            )
        except Exception as e:
            logger.error(f"Error generating short duration switch plot: {str(e)}")
            short_duration_switch_plots[f"{circuit_name}_switches"] = f"<div class='alert alert-warning'>Error: {str(e)}</div>"
    
    if all_short_duration_switch_data:
        try:
            short_duration_switch_plots["all_combined"] = plot_multiple_short_duration_switches(
                all_short_duration_switch_data, max_duration_seconds,
                title="All Short Duration Switch Events"
            )
        except Exception as e:
            logger.error(f"Error generating combined short duration switch plot: {str(e)}")
            short_duration_switch_plots["all_combined"] = f"<div class='alert alert-warning'>Error: {str(e)}</div>"
    
    return circuit_plots, switch_plots, short_duration_plots, short_duration_switch_plots


def create_csv_response(df, filename_prefix):
    """
    Create CSV file response from DataFrame.
    
    Args:
        df: DataFrame to export
        filename_prefix: Prefix for the filename
        
    Returns:
        Flask send_file response or None if DataFrame is empty
    """
    if df.empty:
        return None
    
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"
    
    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode()),
        mimetype='text/csv',
        download_name=filename,
        as_attachment=True
    )



# ========================== MAIN ROUTE HANDLERS ==========================

@circuit_switch_analysis_bp.route('/')
@circuit_switch_analysis_bp.route('')
def index():
    """Render the main circuit analysis page."""
    global circuit_df, switch_df, unique_circuits
    
    if session.get('using_uploaded_data', False):
        circuit_df, switch_df = load_data_from_database(
            circuit_path=session.get('circuit_file_path'),
            switch_path=session.get('switch_file_path')
        )
        unique_circuits = sorted(circuit_df['Circuit_name'].unique().tolist()) if circuit_df is not None else []
    
    return render_template("circuit_switch_feature_global.html", 
                          unique_circuits=unique_circuits,
                          circuit_plots={},
                          switch_plots={},
                          short_duration_plots={},
                          short_duration_switch_plots={},
                          selected_details=None,
                          error=None)


@circuit_switch_analysis_bp.route("/plot", methods=["POST"])
def plot():
    """Handle circuit and switch plotting requests with short-duration analysis."""
    circuit_name = request.form.get("circuit_name")
    from_time = request.form.get("from_time")
    to_time = request.form.get("to_time")
    min_duration = request.form.get("min_duration")
    additional_circuits = request.form.getlist("additional_circuits")
    max_duration = request.form.get("max_duration", "00:01:00")
    max_duration_seconds = pd.to_timedelta(max_duration).total_seconds()

    session['selected_details'] = {
        'circuit_name': circuit_name,
        'from_time': from_time,
        'to_time': to_time,
        'min_duration': min_duration,
        'max_duration': max_duration,
        'additional_circuits': additional_circuits
    }

    circuit_plots = {}
    switch_plots = {}
    short_duration_plots = {}
    short_duration_switch_plots = {}
    error = None

    if circuit_df is None or len(circuit_df) == 0:
        error = "No circuit data available. Please upload data or check your data source."
        flash(error, "danger")
        return render_template("circuit_switch_feature_global.html", 
                              unique_circuits=unique_circuits,
                              circuit_plots=circuit_plots,
                              switch_plots=switch_plots,
                              short_duration_plots=short_duration_plots,
                              short_duration_switch_plots=short_duration_switch_plots,
                              selected_details=None,
                              error=error)

    if not all([circuit_name, from_time, to_time, min_duration]):
        error = "Missing required fields"
        return render_template("circuit_switch_feature_global.html", 
                              unique_circuits=unique_circuits,
                              circuit_plots=circuit_plots,
                              switch_plots=switch_plots,
                              short_duration_plots=short_duration_plots,
                              short_duration_switch_plots=short_duration_switch_plots,
                              selected_details=None,
                              error=error)

    try:
        from_time = pd.to_datetime(from_time)
        to_time = pd.to_datetime(to_time)
        min_duration = pd.to_timedelta(min_duration).total_seconds()

        if not validate_circuit(circuit_name, circuit_df):
            error = f"Invalid Circuit Name: {circuit_name}"
            return render_template("circuit_switch_feature_global.html", 
                                unique_circuits=unique_circuits,
                                circuit_plots=circuit_plots,
                                switch_plots=switch_plots,
                                short_duration_plots=short_duration_plots,
                                short_duration_switch_plots=short_duration_switch_plots,
                                selected_details=None,
                                error=error)

        all_short_duration_switch_data = {}

        all_circuits_data, circuit_order, circuit_colors = process_regular_circuit_data(
            circuit_name, additional_circuits, from_time, to_time, min_duration
        )
        
        all_short_duration_data = process_short_duration_circuit_data(
            circuit_order, from_time, to_time, max_duration_seconds
        )
        
        filtered_switches, switch_data_dict = process_switch_data(
            circuit_name, from_time, to_time, min_duration
        )
        
        short_duration_switch_dict = process_short_duration_switch_data(
            circuit_name, from_time, to_time, max_duration_seconds
        )
        
        if short_duration_switch_dict:
            all_short_duration_switch_data.update(short_duration_switch_dict)

        for add_circuit in additional_circuits:
            if add_circuit != circuit_name and validate_circuit(add_circuit, circuit_df):
                add_filtered_switches, add_switch_data_dict = process_switch_data(
                    add_circuit, from_time, to_time, min_duration
                )
                
                if add_switch_data_dict:
                    switch_plots.update({add_circuit: plot_multiple_switches(
                        add_switch_data_dict, title=f"All Switches for {add_circuit}"
                    )})
                
                add_short_duration_switch_dict = process_short_duration_switch_data(
                    add_circuit, from_time, to_time, max_duration_seconds
                )
                
                if add_short_duration_switch_dict:
                    all_short_duration_switch_data.update(add_short_duration_switch_dict)

        circuit_plots, switch_plots_main, short_duration_plots, short_duration_switch_plots = generate_plots(
            all_circuits_data, circuit_order, all_short_duration_data,
            switch_data_dict, short_duration_switch_dict,
            all_short_duration_switch_data, circuit_name, max_duration_seconds
        )
        
        switch_plots.update(switch_plots_main)

    except Exception as e:
        error = f"Error processing data: {str(e)}"
        logger.error(f"Exception in plot route: {str(e)}")
        logger.error(traceback.format_exc())
    
    ordered_circuit_plots = OrderedDict()
    ordered_short_duration_plots = OrderedDict()
    ordered_short_duration_switch_plots = OrderedDict()
    
    if "combined" in circuit_plots:
        ordered_circuit_plots["combined"] = circuit_plots["combined"]
    if "combined" in short_duration_plots:
        ordered_short_duration_plots["combined"] = short_duration_plots["combined"]
    if "all_combined" in short_duration_switch_plots:
        ordered_short_duration_switch_plots["all_combined"] = short_duration_switch_plots["all_combined"]
    
    for c_name in circuit_order if 'circuit_order' in locals() else []:
        if f"{c_name}_switches" in short_duration_switch_plots:
            ordered_short_duration_switch_plots[f"{c_name}_switches"] = short_duration_switch_plots[f"{c_name}_switches"]
    
    selected_details = session.get('selected_details')
            
    return render_template("circuit_switch_feature_global.html", 
                         unique_circuits=unique_circuits,
                         circuit_plots=ordered_circuit_plots,
                         switch_plots=switch_plots,
                         short_duration_plots=ordered_short_duration_plots,
                         short_duration_switch_plots=ordered_short_duration_switch_plots,
                         selected_details=selected_details,
                         error=error)



# ========================== CSV DOWNLOAD ROUTES ==========================

@circuit_switch_analysis_bp.route("/download_csv", methods=["POST"])
def download_csv():
    """Download filtered data as CSV based on specified data type."""
    try:
        if 'selected_details' not in session:
            flash('No analysis parameters found. Please run an analysis first.', 'warning')
            return redirect(url_for('circuit_switch_analysis.index'))
        
        details = session['selected_details']
        circuit_name = details.get('circuit_name')
        from_time = pd.to_datetime(details.get('from_time'))
        to_time = pd.to_datetime(details.get('to_time'))
        min_duration = details.get('min_duration')
        max_duration = details.get('max_duration')
        additional_circuits = details.get('additional_circuits', [])
        data_type = request.form.get('data_type', 'all')
        
        min_duration_seconds = pd.to_timedelta(min_duration).total_seconds() if min_duration else 0
        max_duration_seconds = pd.to_timedelta(max_duration).total_seconds() if max_duration else 60
        
        circuit_df, switch_df = load_data_from_database(
            circuit_path=session.get('circuit_file_path'),
            switch_path=session.get('switch_file_path')
        )
        
        if circuit_df is None or circuit_df.empty:
            flash('No circuit data available.', 'warning')
            return redirect(url_for('circuit_switch_analysis.index'))
        
        csv_handlers = {
            'short_duration_switches': lambda: collect_short_duration_switch_data(
                circuit_name, additional_circuits, circuit_df, switch_df, 
                from_time, to_time, max_duration_seconds
            ),
            'circuits': lambda: collect_circuit_data(
                circuit_name, additional_circuits, circuit_df, 
                from_time, to_time, min_duration_seconds
            ),
            'switches': lambda: collect_switch_data(
                circuit_name, additional_circuits, circuit_df, switch_df,
                from_time, to_time, min_duration_seconds
            ),
            'short_duration': lambda: collect_short_duration_circuit_data(
                circuit_name, additional_circuits, circuit_df, 
                from_time, to_time, max_duration_seconds
            )
        }
        
        if data_type in csv_handlers:
            combined_df = csv_handlers[data_type]()
            filename_prefix = data_type.replace('_', '_')
        else:
            csv_data = prepare_csv_data(
                circuit_name, additional_circuits, circuit_df, switch_df, 
                from_time, to_time, min_duration_seconds, max_duration_seconds
            )
            combined_df = combine_dataframes_for_csv(csv_data)
            filename_prefix = "railway_circuit_data"
        
        if combined_df.empty:
            flash('No data matched your filter criteria.', 'warning')
            return redirect(url_for('circuit_switch_analysis.index'))
        
        return create_csv_response(combined_df, filename_prefix)
        
    except Exception as e:
        logger.error(f"Error generating CSV: {str(e)}")
        logger.error(traceback.format_exc())
        flash(f'Error generating CSV file: {str(e)}', 'danger')
        return redirect(url_for('circuit_switch_analysis.index'))


# ========================== UTILITY ROUTES ==========================

@circuit_switch_analysis_bp.route('/api/circuits', methods=['GET'])
def get_circuits():
    """API endpoint to retrieve available circuits."""
    return jsonify({"circuits": unique_circuits})


@circuit_switch_analysis_bp.route('/refresh_data', methods=['GET'])
def refresh_data():
    """Reload data from database or uploaded files."""
    global circuit_df, switch_df, unique_circuits
    circuit_df, switch_df = load_data_from_database(
        circuit_path=session.get('circuit_file_path'),
        switch_path=session.get('switch_file_path')
    )
    unique_circuits = sorted(circuit_df['Circuit_name'].unique().tolist()) if circuit_df is not None else []
    
    flash("Data has been refreshed", "success")
    return redirect(url_for('circuit_switch_analysis.index'))


@circuit_switch_analysis_bp.route('/short_duration_settings', methods=['GET', 'POST'])
def short_duration_settings():
    """Manage short-duration analysis settings."""
    if request.method == 'POST':
        max_duration = request.form.get('max_duration', '00:01:00')
        session['max_duration'] = max_duration
        return redirect(url_for('circuit_switch_analysis.index'))
    
    max_duration = session.get('max_duration', '00:01:00')
    return render_template('short_duration_settings.html', max_duration=max_duration)



# ========================== FILE UPLOAD ROUTES ==========================

@circuit_switch_analysis_bp.route('/upload_data', methods=['POST'])
def upload_data():
    """Handle CSV file uploads for circuit and switch data."""
    circuit_file = request.files.get('circuit_file')
    switch_file = request.files.get('switch_file')
    
    if not circuit_file and not switch_file:
        flash("Please select at least one CSV file to upload.", "warning")
        return redirect(url_for('circuit_switch_analysis.index'))
    
    global circuit_df, switch_df, unique_circuits
    success_messages = []
    
    if circuit_file and circuit_file.filename:
        try:
            circuit_filename = secure_filename(circuit_file.filename)
            circuit_path = os.path.join(UPLOAD_FOLDER, circuit_filename)
            circuit_file.save(circuit_path)
            
            session['circuit_file_path'] = circuit_path
            session['circuit_file_name'] = circuit_filename
            session['using_uploaded_data'] = True
            
            success_messages.append(f"Circuit data '{circuit_filename}' uploaded successfully.")
        except Exception as e:
            flash(f"Error uploading circuit data: {str(e)}", "danger")
            return redirect(url_for('circuit_switch_analysis.index'))
    
    if switch_file and switch_file.filename:
        try:
            switch_filename = secure_filename(switch_file.filename)
            switch_path = os.path.join(UPLOAD_FOLDER, switch_filename)
            switch_file.save(switch_path)
            
            session['switch_file_path'] = switch_path
            session['switch_file_name'] = switch_filename
            session['using_uploaded_data'] = True
            
            success_messages.append(f"Switch data '{switch_filename}' uploaded successfully.")
        except Exception as e:
            flash(f"Error uploading switch data: {str(e)}", "danger")
            return redirect(url_for('circuit_switch_analysis.index'))
    
    if success_messages:
        flash("<br>".join(success_messages), "success")
    
    circuit_df, switch_df = load_data_from_database(
        circuit_path=session.get('circuit_file_path'),
        switch_path=session.get('switch_file_path')
    )
    unique_circuits = sorted(circuit_df['Circuit_name'].unique().tolist()) if circuit_df is not None else []
    
    return redirect(url_for('circuit_switch_analysis.index'))


@circuit_switch_analysis_bp.route('/reset_to_default_data')
def reset_to_default_data():
    """Reset data to default database state."""
    global circuit_df, switch_df, unique_circuits
    
    try:
        circuit_df, switch_df = load_data_from_database()
        unique_circuits = sorted(circuit_df['Circuit_name'].unique().tolist()) if circuit_df is not None else []
        
        for key in ['circuit_file_path', 'switch_file_path', 'circuit_file_name', 
                    'switch_file_name', 'using_uploaded_data']:
            session.pop(key, None)
        
        flash("Data has been reset to default (database) state.", "success")
    except Exception as e:
        logger.error(f"Error resetting to default data: {str(e)}")
        flash(f"Error resetting to default data: {str(e)}", "danger")
        
    return redirect(url_for('circuit_switch_analysis.index'))


# ========================== DEBUG ROUTES ==========================

@circuit_switch_analysis_bp.route('/debug_app', methods=['GET'])
def debug_app():
    """Debug application configuration."""
    try:
        return jsonify({
            "routes": [str(rule) for rule in current_app.url_map.iter_rules()],
            "session_enabled": hasattr(current_app, 'secret_key') and current_app.secret_key is not None,
            "session_data": dict(session) if session else "No session data",
            "environment": current_app.config.get('ENV', 'Not set'),
            "debug_mode": current_app.config.get('DEBUG', 'Not set'),
            "app_config": {k: str(v) for k, v in current_app.config.items() if k not in ['SECRET_KEY']}
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@circuit_switch_analysis_bp.route('/debug/load', methods=['GET'])
def debug_load():
    """Debug data loading functionality."""
    try:
        test_circuit_df, test_switch_df = load_data_from_database()
        
        return jsonify({
            "circuit_df_rows": len(test_circuit_df) if test_circuit_df is not None else 0,
            "switch_df_rows": len(test_switch_df) if test_switch_df is not None else 0,
            "circuit_columns": test_circuit_df.columns.tolist() if test_circuit_df is not None else [],
            "switch_columns": test_switch_df.columns.tolist() if test_switch_df is not None else [],
            "unique_circuits": len(unique_circuits),
            "working_dir": os.getcwd(),
            "timestamp_info": {
                'circuit_combined_timestamps': 'Down_timestamp' in test_circuit_df.columns if test_circuit_df is not None else False,
                'switch_combined_timestamps': 'Up_timestamp' in test_switch_df.columns if test_switch_df is not None else False,
            }
        })
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})


@circuit_switch_analysis_bp.route('/debug_switches', methods=['GET'])
def debug_switches():
    """Debug switch data functionality."""
    try:
        test_circuit = unique_circuits[0] if unique_circuits else "NO_CIRCUIT"
        now = pd.Timestamp.now()
        from_time = now - pd.Timedelta(days=30)
        to_time = now
        
        matching_switches = get_matching_switches(test_circuit, switch_df)
        if matching_switches is None:
            return jsonify({"error": f"No switches found matching circuit {test_circuit}"})
            
        filtered_switches = filter_switch_data(matching_switches, from_time, to_time, 0)
        if filtered_switches is None or filtered_switches.empty:
            return jsonify({
                "error": "No switch data after filtering",
                "circuit": test_circuit,
                "switches_found": matching_switches['Switch_name'].unique().tolist(),
                "time_range": f"{from_time} to {to_time}"
            })    
        
        return jsonify({
            "success": True,
            "circuit": test_circuit,
            "switches_found": matching_switches['Switch_name'].unique().tolist(),
            "filtered_rows": len(filtered_switches),
            "time_range": f"{from_time} to {to_time}"
        })
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})



@circuit_switch_analysis_bp.route('/debug_switch_data', methods=['GET'])
def debug_switch_data():
    """Debug switch data structure and processing."""
    try:
        global circuit_df, switch_df
        
        result = {
            "switch_df_info": {
                "rows": len(switch_df) if switch_df is not None else 0,
                "columns": switch_df.columns.tolist() if switch_df is not None else [],
                "sample": switch_df.head(3).to_dict('records') if switch_df is not None and len(switch_df) > 0 else [],
                "dtypes": {col: str(dtype) for col, dtype in switch_df.dtypes.items()} if switch_df is not None else {}
            },
            "timestamp_columns": {
                "has_start_time_s": 'Start_Time_s' in switch_df.columns if switch_df is not None else False,
                "has_end_time_s": 'End_Time_s' in switch_df.columns if switch_df is not None else False,
                "has_up_timestamp": 'Up_timestamp' in switch_df.columns if switch_df is not None else False,
                "has_down_timestamp": 'Down_timestamp' in switch_df.columns if switch_df is not None else False
            }
        }
        
        if circuit_df is not None and len(circuit_df) > 0:
            test_circuit = circuit_df['Circuit_name'].iloc[0]
            matching_switches = get_matching_switches(test_circuit, switch_df)
            
            result["switch_matching_test"] = {
                "test_circuit": test_circuit,
                "found_matches": matching_switches is not None,
                "match_count": len(matching_switches) if matching_switches is not None else 0,
                "match_sample": matching_switches.head(2).to_dict('records') if matching_switches is not None else []
            }
            
            if matching_switches is not None:
                now = pd.Timestamp.now()
                from_time = now - pd.Timedelta(days=365)
                to_time = now
                filtered_switches = filter_switch_data(matching_switches, from_time, to_time, 0)
                
                result["switch_filtering_test"] = {
                    "filter_result_type": str(type(filtered_switches)),
                    "filter_success": filtered_switches is not None,
                    "filtered_count": len(filtered_switches) if filtered_switches is not None else 0,
                    "sample": filtered_switches.head(2).to_dict('records') if filtered_switches is not None else []
                }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})


@circuit_switch_analysis_bp.route('/debug_short_duration', methods=['GET'])
def debug_short_duration():
    """Debug short duration circuit data processing."""
    try:
        circuit_name = request.args.get('circuit', unique_circuits[0] if unique_circuits else "NO_CIRCUIT")
        now = pd.Timestamp.now()
        from_time = now - pd.Timedelta(days=365)
        to_time = now
        max_duration = 60
        
        short_duration_data = filter_short_duration_circuits(
            circuit_name, circuit_df, from_time, to_time, max_duration
        )
        
        result = {
            "circuit": circuit_name,
            "time_range": {"from": str(from_time), "to": str(to_time)},
            "max_duration": max_duration,
            "found_data": not short_duration_data.empty if short_duration_data is not None else False,
            "row_count": len(short_duration_data) if short_duration_data is not None else 0
        }
        
        if short_duration_data is not None and not short_duration_data.empty:
            sample = short_duration_data.head(3).copy()
            
            for col in sample.columns:
                if pd.api.types.is_datetime64_any_dtype(sample[col]):
                    sample[col] = sample[col].astype(str)
            
            result["sample_data"] = sample.to_dict('records')
            result["has_required_columns"] = {
                "Start_Time_c": "Start_Time_c" in short_duration_data.columns,
                "End_Time_c": "End_Time_c" in short_duration_data.columns,
                "Duration_sec_c": "Duration_sec_c" in short_duration_data.columns,
            }
            
            if "Duration_sec_c" in short_duration_data.columns:
                result["duration_stats"] = {
                    "min": float(short_duration_data["Duration_sec_c"].min()),
                    "max": float(short_duration_data["Duration_sec_c"].max()),
                    "mean": float(short_duration_data["Duration_sec_c"].mean()),
                    "has_zero": (short_duration_data["Duration_sec_c"] == 0).any(),
                    "has_negative": (short_duration_data["Duration_sec_c"] < 0).any(),
                    "has_null": short_duration_data["Duration_sec_c"].isnull().any()
                }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})

