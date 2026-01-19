import os
import pandas as pd
import json
from flask import current_app, session
import numpy as np

# =======================
# Net Class
# =======================
class Net:
    def __init__(self, main_data_source: str = None, second_data_source: str = None, third_data_source: str = None, start_end_data_source: str = None):
        self.df_main = pd.DataFrame()
        self.df_second = pd.DataFrame()
        self.df_third = pd.DataFrame()
        self.df_start_end = pd.DataFrame()  # DataFrame for start-end data
        
        # Load datasets if provided
        if main_data_source:
            self.load_main_dataset(main_data_source)
        
        if second_data_source:
            self.load_second_dataset(second_data_source)
            
        if third_data_source:
            self.load_third_dataset(third_data_source)
            
        if start_end_data_source:
            self.load_start_end_dataset(start_end_data_source)

    def load_main_dataset(self, main_data_source: str):
        try:
            self.df_main = pd.read_csv(main_data_source)
            return {"status": "success", "message": f"Main dataset loaded successfully from {main_data_source}"}
        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {main_data_source}"}
        except Exception as e:
            return {"status": "error", "message": f"Error loading main dataset: {str(e)}"}

    def load_second_dataset(self, second_data_source: str):
        try:
            self.df_second = pd.read_csv(second_data_source)
            return {"status": "success", "message": f"Second dataset loaded successfully from {second_data_source}"}
        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {second_data_source}"}
        except Exception as e:
            return {"status": "error", "message": f"Error loading second dataset: {str(e)}"}

    def load_third_dataset(self, third_data_source: str):
        try:
            self.df_third = pd.read_csv(third_data_source)
            return {"status": "success", "message": f"Third dataset loaded successfully from {third_data_source}"}
        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {third_data_source}"}
        except Exception as e:
            return {"status": "error", "message": f"Error loading third dataset: {str(e)}"}

    def load_start_end_dataset(self, start_end_data_source: str):
        """
        Load the start-end dataset
        
        Args:
            start_end_data_source: Path to the CSV file
            
        Returns:
            Dict with status and message
        """
        try:
            self.df_start_end = pd.read_csv(start_end_data_source)
            return {"status": "success", "message": f"Start-end dataset loaded successfully from {start_end_data_source}"}
        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {start_end_data_source}"}
        except Exception as e:
            return {"status": "error", "message": f"Error loading start-end dataset: {str(e)}"}

    # ---- Methods for main dataset ----
    def get_records_by_netid(self, net_id: int) -> pd.DataFrame:
        if self.df_main.empty:
            return pd.DataFrame()
        return self.df_main[self.df_main['Net_id'] == net_id]

    def get_unique_chains_by_netid(self, net_id: int) -> pd.DataFrame:
        if self.df_main.empty:
            return pd.DataFrame()
        chains = self.df_main[self.df_main['Net_id'] == net_id]['Chain_id'].unique()
        return pd.DataFrame({'Chain_id': chains})

    def get_unique_circuits_by_netid(self, net_id: int) -> pd.DataFrame:
        if self.df_main.empty:
            return pd.DataFrame()
        circuits = self.df_main[self.df_main['Net_id'] == net_id]['Circuit_Name'].unique()
        return pd.DataFrame({'Circuit_Name': circuits})

    # ---- Method for third dataset (Chain intervals) ----
    def get_chains_by_netid(self, net_id: int) -> pd.DataFrame:
        if self.df_third.empty:
            return pd.DataFrame()
        
        # Filter the third dataset by Net_id
        filtered_data = self.df_third[self.df_third['Net_id'] == net_id]
        if filtered_data.empty:
            return pd.DataFrame()
        
        # Prepare records with chain information
        records = []
        for _, row in filtered_data.iterrows():
            records.append({
                "Type": "Chain",
                "Chain_ID": row['Chain_id'],
                "Chain_interval": row['Chain_interval']
            })
        
        return pd.DataFrame(records)
    
    def get_chain_interval_by_chainid(self, Chain_id: int) -> pd.DataFrame:
        """
        Get chain interval information for a specific Chain_id from the third dataset.
        
        Args:
            Chain_id: The Chain_id to filter by
            
        Returns:
            DataFrame containing chain interval information for the specified Chain_id
        """
        if self.df_third.empty:
            return pd.DataFrame()
        
        # Filter the third dataset by Chain_id
        filtered_data = self.df_third[self.df_third['Chain_id'] == Chain_id]
        return filtered_data.reset_index(drop=True)
    
    def get_all_chain_intervals(self) -> pd.DataFrame:
        """
        Get all chain interval data from the third dataset.
        
        Returns:
            DataFrame containing all chain interval data
        """
        if self.df_third.empty:
            return pd.DataFrame()
        return self.df_third.copy()

    # ---- Methods for Chain_id ----
    def show_start_end_chain(self, Chain_id: int) -> pd.DataFrame:
        """
        Return start/end interval & circuit for a given Chain_id.
        """
        df = self.df_main[self.df_main['Chain_id'] == Chain_id]
        if df.empty:
            return pd.DataFrame()

        start_row = df.iloc[0]
        end_row = df.iloc[-1]

        return pd.DataFrame([{
            "Chain_id": Chain_id,
            "Start_Interval_id": start_row["Interval_id"],
            "Start_Circuit_Name": start_row["Circuit_Name"],
            "End_Interval_id": end_row["Interval_id"],
            "End_Circuit_Name": end_row["Circuit_Name"]
        }])

    def get_chain_sequence_length(self, Chain_id: int) -> pd.DataFrame:
        df = self.df_main[self.df_main['Chain_id'] == Chain_id]
        return pd.DataFrame({"Chain_id": [Chain_id], "Sequence_Length": [len(df)]})

    def get_chain_circuit_sequence(self, Chain_id: int) -> pd.DataFrame:
        df = self.df_main[self.df_main['Chain_id'] == Chain_id]
        if df.empty:
            return pd.DataFrame()
        return df[['Interval_id', 'Circuit_Name']].reset_index(drop=True)

    def feature_start_end(self, net_id=None):
        """
        Get start-end data for a specific Net ID or all data if no Net ID specified
        
        Args:
            net_id (str/int): The Net_id to filter by (numeric value)
            
        Returns:
            DataFrame containing start-end data for the specified Net ID or all data
        """
        if not hasattr(self, 'df_start_end') or self.df_start_end.empty:
            return pd.DataFrame()
        
        if net_id is not None:
            # Convert input to numeric
            try:
                if isinstance(net_id, str):
                    if net_id.isdigit():
                        numeric_net_id = int(net_id)
                    else:
                        # Try direct conversion, but remove "Net_" prefix if present
                        if net_id.startswith('Net_') and net_id[4:].isdigit():
                            numeric_net_id = int(net_id[4:])
                        else:
                            # If not convertible, just use as is
                            numeric_net_id = net_id
                else:
                    # Already numeric
                    numeric_net_id = int(net_id)
                
                # Convert Net_id column to numeric for comparison
                self.df_start_end['Net_id'] = pd.to_numeric(self.df_start_end['Net_id'])
                
                # Filter by Net_id (now numeric)
                return self.df_start_end[self.df_start_end['Net_id'] == numeric_net_id].reset_index(drop=True)
            except Exception as e:
                print(f"Error in feature_start_end: {e}")
                return pd.DataFrame()
        else:
            # Return all data
            return self.df_start_end.copy()
            
    def data_summary(self):
        """Return a summary of loaded data"""
        # Call the show_summary function instead of showing detailed dataset information
        return self.show_summary()
        
    def show_summary(self):
        """
        Show summary details focused on shunting status.
        Displays total Net-id and Chain_id with shunting status,
        and shows which Net-id contains which Chain-id for shunting records.
        """
        summary = {}
        
        # Check if main dataset is loaded
        if self.df_main.empty:
            summary["status"] = "error"
            summary["message"] = "Main dataset not loaded"
            return convert_numpy_types(summary)
            
        try:
            # Filter records with shunting status
            if 'shunting_status' in self.df_main.columns:
                shunting_data = self.df_main[self.df_main['shunting_status'] == 'shunting']
                
                # Get unique Net_id and Chain_id for shunting records
                shunting_net_ids = shunting_data['Net_id'].unique() if 'Net_id' in shunting_data.columns else []
                shunting_chain_ids = shunting_data['Chain_id'].unique() if 'Chain_id' in shunting_data.columns else []
                
                # Create mapping of Net_id to chain_ids
                net_to_chain_mapping = {}
                for net_id in shunting_net_ids:
                    chains = shunting_data[shunting_data['Net_id'] == net_id]['Chain_id'].unique()
                    net_to_chain_mapping[int(net_id) if isinstance(net_id, (int, float, np.number)) else net_id] = [
                        int(x) if isinstance(x, (int, float, np.number)) else x for x in chains
                    ]
                
                # Prepare summary data
                summary = {
                    "status": "success",
                    "shunting_summary": {
                        "total_records": len(shunting_data),
                        "unique_net_ids": [int(x) if isinstance(x, (int, float, np.number)) else x for x in shunting_net_ids],
                        "unique_chain_ids": [int(x) if isinstance(x, (int, float, np.number)) else x for x in shunting_chain_ids],
                        "net_id_to_chain_mapping": net_to_chain_mapping
                    }
                }
            else:
                summary = {
                    "status": "warning",
                    "message": "shunting_status column not found in the dataset"
                }
                
        except Exception as e:
            print(f"Error in shunting summary: {str(e)}")
            summary = {
                "status": "error",
                "message": f"Error generating shunting summary: {str(e)}"
            }
        
        # Apply conversion to ensure all values are JSON serializable
        return convert_numpy_types(summary)

# File handling has been moved to load_visual_data.py


# Helper to convert DataFrame to HTML table
def dataframe_to_html(df, max_rows=100):
    """Convert DataFrame to HTML table with styling"""
    if df is None or df.empty:
        return '<div class="alert alert-warning">No data available</div>'
        
    # Limit rows for display
    if len(df) > max_rows:
        df_display = df.head(max_rows)
        note = f'<div class="alert alert-info">Showing first {max_rows} of {len(df)} rows</div>'
    else:
        df_display = df
        note = ''
    
    # Convert DataFrame to HTML with proper alignment settings
    table_html = df_display.to_html(
        classes='table table-striped table-hover table-sm align-middle', 
        border=0, 
        index=True, 
        escape=False,
        justify='left'  # Align text left for better readability
    )
    
    # Fix alignment issues by adding CSS directly to the table
    table_html = table_html.replace('<table', '<table style="width:100%; table-layout:auto;"')
    table_html = table_html.replace('<th>', '<th style="text-align:left; vertical-align:middle; white-space:nowrap;">')
    table_html = table_html.replace('<td>', '<td style="text-align:left; vertical-align:middle;">')
    
    return note + table_html

# Custom JSON encoder to handle NumPy data types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, set):
            return list(obj)
        return super(NumpyEncoder, self).default(obj)

def convert_numpy_types(obj):
    """
    Recursively convert NumPy types to Python native types for JSON serialization
    
    Args:
        obj: Object that may contain NumPy data types
        
    Returns:
        Object with NumPy types converted to Python native types
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return convert_numpy_types(obj.tolist())
    elif isinstance(obj, set):
        return list(obj)
    else:
        return obj