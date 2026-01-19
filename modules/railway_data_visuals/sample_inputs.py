"""
Sample data definitions for Railway Data Visuals
This file contains sample data to show users the expected format of input files
"""

# Sample data for main dataset
MAIN_DATASET_SAMPLE = {
    "columns": ["Interval_id", "Circuit_Name", "Down_timestamp", "Up_timestamp", "Duration", "switch_name", "switch_status", "Net_id", "Chain_id", "shunting_status"],
    "data": [
        ["T2217", "C01TPR", "2025-05-15 02:22:42", "2025-05-15 02:23:46", "00:01:04", "No switch", "Switch position N", 156, 125, "Normal"],
        ["T2465", "H01TPR", "2025-05-15 02:22:49", "2025-05-15 02:23:53", "00:01:04", "No switch", "Switch position N", 156, 125, "Normal"]
    ]
}

# Sample data for chain dataset (chain interval dataset)
CHAIN_DATA_SAMPLE = {
    "columns": ["Net_id", "Chain_id", "Chain_interval"],
    "data": [
        [1, 1, "T1988 - T1683 - T48 - T100 - T50 - T1684 - T1783 - T1927 - T1145 - T665 - T506 - T666 - T1146 - T1929 - T1784 - T2751 - T2831 - T2752 - T1785 - T1930 - T1147 - T667 - T758"],
        [2, 13, "T1562 - T1614 - T1415 - T1479 - T1018 - T1197 - T717 - T539 - T2211 - T2573 - T2325"]
    ]
}

# Sample data for start-end dataset
START_END_DATASET_SAMPLE = {
    "columns": ["Net_id", "Chain_id", "Start_interval_id", "Start_Circuit_Name", "start_downtime", "End_interval_id", "End_Circuit_Name", "End_uptime"],
    "data": [
        [1, 1, "T1988", "113TPR", "2025-05-20 11:22:05", "T758", "R101BTPR", "2025-05-20 11:45:36"],
        [2, 13, "T1562", "R107ATPR", "2025-05-22 04:32:53", "T2325", "C01TPR", "2025-05-22 04:42:54"]
    ]
}

def get_sample_html(sample_data, file_type):
    """
    Generate HTML table for sample data with toggle functionality
    
    Args:
        sample_data (dict): Dictionary with columns and data
        file_type (str): Type of file for display purposes
        
    Returns:
        str: HTML string with sample data table
    """
    container_id = f"sample_{file_type.replace(' ', '_').lower()}_container"
    
    html = f"""
    <div class="mt-1">
        <button class="sample-data-toggle" onclick="toggleSampleData('{container_id}')">
            <i class="fas fa-table me-1"></i>View Sample Format
        </button>
        <div id="{container_id}" class="sample-data-container">
            <div class="table-responsive">
                <table class="table table-sm table-bordered sample-data-table mb-0">
                    <thead class="table-light">
                        <tr>
    """
    
    # Add column headers
    for col in sample_data["columns"]:
        html += f"<th>{col}</th>"
    
    html += """
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Add data rows
    for row in sample_data["data"]:
        html += "<tr>"
        for i, cell in enumerate(row):
            # For Chain_interval column, truncate the display
            if sample_data["columns"][i] == "Chain_interval":
                html += f'<td><span class="truncate" title="{cell}">{cell[:25]}...</span></td>'
            else:
                html += f"<td>{cell}</td>"
        html += "</tr>"
    
    html += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    
    return html

def get_all_samples():
    """
    Get HTML for all sample data tables
    
    Returns:
        dict: Dictionary with HTML for each sample
    """
    return {
        "main_file": get_sample_html(MAIN_DATASET_SAMPLE, "Main Dataset"),
        "json_file": get_sample_html(CHAIN_DATA_SAMPLE, "Chain Dataset"),
        "start_end_file": get_sample_html(START_END_DATASET_SAMPLE, "Start-End Dataset")
    }