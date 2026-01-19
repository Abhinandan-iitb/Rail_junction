"""
Load Shunting Visuals Data Module
Handles data loading, parsing, and management for shunting visuals
"""

import os
import csv
import json
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, IO
from io import StringIO

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.environ.get(
    "PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

DEFAULT_DATA_DIRECTORY = os.environ.get(
    "SHUNTING_VISUALS_DATA_DIR",
    os.path.join(PROJECT_ROOT, 'Data')
)

DEFAULT_CHAIN_SEQ_FILE = os.environ.get("SHUNTING_VISUALS_CHAIN_SEQ_FILE", 'chain_seq_dataset.csv')
DEFAULT_INTERVAL_FILE = os.environ.get("SHUNTING_VISUALS_INTERVAL_FILE", 'Circuit_interval_with_net.csv')

class ShuntingDataLoader:
    """Data loader for shunting visuals - handles CSV files, default data, and user uploads"""
    
    def __init__(self, data_directory: str = None):
        env_directory = os.environ.get("SHUNTING_VISUALS_DATA_DIR")
        self.data_directory = data_directory or env_directory or DEFAULT_DATA_DIRECTORY
        self.default_files = {
            'chain_seq': DEFAULT_CHAIN_SEQ_FILE,
            'interval': DEFAULT_INTERVAL_FILE
        }
    
    def _resolve_file_path(self, filename: str) -> str:
        """Return an absolute path for a default file."""
        if not filename:
            return ''
        if os.path.isabs(filename):
            return filename
        return os.path.join(self.data_directory, filename)

    def load_default_data(self) -> Dict[str, Any]:
        """
        Load default shunting data from CSV files in the Data directory
        
        Returns:
            Dict containing loaded data and status
        """
        try:
            chain_seq_path = self._resolve_file_path(self.default_files['chain_seq'])
            interval_path = self._resolve_file_path(self.default_files['interval'])
            
            # Check if files exist
            if not os.path.exists(chain_seq_path):
                raise FileNotFoundError(f"Chain sequence file not found: {chain_seq_path}")
            
            if not os.path.exists(interval_path):
                raise FileNotFoundError(f"Interval file not found: {interval_path}")
            
            # Load chain sequence data
            chain_seq_data = self._load_csv_file(chain_seq_path)
            
            # Load interval data
            interval_data = self._load_csv_file(interval_path)
            
            logger.info(f"Default data loaded: {len(chain_seq_data)} chain sequences, {len(interval_data)} intervals")
            
            return {
                "status": "success",
                "message": "Default railway shunting data loaded successfully",
                "data": {
                    "chain_seq": chain_seq_data,
                    "interval": interval_data
                },
                "summary": {
                    "chain_seq_records": len(chain_seq_data),
                    "interval_records": len(interval_data),
                    "source": "default_files"
                }
            }
            
        except Exception as e:
            logger.error(f"Error loading default data: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to load default data: {str(e)}",
                "data": None
            }
    
    def parse_uploaded_files(self, chain_seq_file: IO, interval_file: IO) -> Dict[str, Any]:
        """
        Parse uploaded CSV files
        
        Args:
            chain_seq_file: Chain sequence CSV file object
            interval_file: Interval CSV file object
            
        Returns:
            Dict containing parsed data and status
        """
        try:
            # Parse chain sequence file
            chain_seq_content = chain_seq_file.read()
            if isinstance(chain_seq_content, bytes):
                chain_seq_content = chain_seq_content.decode('utf-8')
            
            chain_seq_data = self._parse_csv_string(chain_seq_content)
            
            # Parse interval file
            interval_content = interval_file.read()
            if isinstance(interval_content, bytes):
                interval_content = interval_content.decode('utf-8')
            
            interval_data = self._parse_csv_string(interval_content)
            
            # Validate required columns
            validation_result = self._validate_data_structure(chain_seq_data, interval_data)
            if not validation_result['valid']:
                return {
                    "status": "error",
                    "message": f"Data validation failed: {validation_result['message']}",
                    "data": None
                }
            
            logger.info(f"Uploaded files parsed: {len(chain_seq_data)} chain sequences, {len(interval_data)} intervals")
            
            return {
                "status": "success",
                "message": "Files uploaded and processed successfully",
                "data": {
                    "chain_seq": chain_seq_data,
                    "interval": interval_data
                },
                "summary": {
                    "chain_seq_records": len(chain_seq_data),
                    "interval_records": len(interval_data),
                    "source": "user_upload"
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing uploaded files: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to parse files: {str(e)}",
                "data": None
            }
    
    def load_sample_data(self) -> Dict[str, Any]:
        """
        Load sample/demo data for testing purposes
        
        Returns:
            Dict containing sample data
        """
        try:
            # Generate sample chain sequence data
            chain_seq_sample = [
                {
                    "Chain_id": "1",
                    "Net_id": "101",
                    "Chain_interval": "INT_001 - INT_002 - INT_003"
                },
                {
                    "Chain_id": "2",
                    "Net_id": "101",
                    "Chain_interval": "INT_004 - INT_005"
                },
                {
                    "Chain_id": "3",
                    "Net_id": "102",
                    "Chain_interval": "INT_006 - INT_007 - INT_008 - INT_009"
                }
            ]
            
            # Generate sample interval data
            base_time = pd.Timestamp.now()
            interval_sample = []
            
            for i, interval_id in enumerate(['INT_001', 'INT_002', 'INT_003', 'INT_004', 'INT_005', 'INT_006', 'INT_007', 'INT_008', 'INT_009']):
                down_time = base_time + pd.Timedelta(hours=i)
                up_time = down_time + pd.Timedelta(minutes=30)
                
                interval_sample.append({
                    "Interval_id": interval_id,
                    "Circuit_Name": f"Circuit_{interval_id}",
                    "Down_timestamp": down_time.isoformat(),
                    "Up_timestamp": up_time.isoformat()
                })
            
            return {
                "status": "success",
                "message": "Sample data loaded for demonstration",
                "data": {
                    "chain_seq": chain_seq_sample,
                    "interval": interval_sample
                },
                "summary": {
                    "chain_seq_records": len(chain_seq_sample),
                    "interval_records": len(interval_sample),
                    "source": "sample_data"
                }
            }
            
        except Exception as e:
            logger.error(f"Error loading sample data: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to load sample data: {str(e)}",
                "data": None
            }

    def _load_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load CSV file and return as list of dictionaries"""
        data = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    # Clean and process the row data
                    cleaned_row = {}
                    for key, value in row.items():
                        # Clean the key and value
                        clean_key = key.strip() if key else ''
                        clean_value = value.strip() if value else ''
                        cleaned_row[clean_key] = clean_value
                    data.append(cleaned_row)
                    
            logger.info(f"Loaded {len(data)} records from {file_path}")
            return data
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as file:
                    csv_reader = csv.DictReader(file)
                    for row in csv_reader:
                        cleaned_row = {}
                        for key, value in row.items():
                            clean_key = key.strip() if key else ''
                            clean_value = value.strip() if value else ''
                            cleaned_row[clean_key] = clean_value
                        data.append(cleaned_row)
                        
                logger.info(f"Loaded {len(data)} records from {file_path} with latin-1 encoding")
                return data
                
            except Exception as e:
                logger.error(f"Error loading CSV file {file_path}: {str(e)}")
                raise FileNotFoundError(f"Could not load CSV file: {file_path}")
                
        except Exception as e:
            logger.error(f"Error loading CSV file {file_path}: {str(e)}")
            raise FileNotFoundError(f"Could not load CSV file: {file_path}")

    def _parse_csv_string(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parse CSV content string and return as list of dictionaries"""
        try:
            # Use csv module instead of manual parsing
            csv_file = StringIO(csv_content)
            csv_reader = csv.DictReader(csv_file)
            
            data = []
            for row in csv_reader:
                cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
                data.append(cleaned_row)
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing CSV string: {str(e)}")
            return []

    def _validate_data_structure(self, chain_seq_data: List[Dict], interval_data: List[Dict]) -> Dict[str, Any]:
        """Validate the structure of loaded data"""
        try:
            # Check chain sequence data structure
            if not chain_seq_data:
                return {"valid": False, "message": "Chain sequence data is empty"}
                
            chain_required_cols = ['Net_id', 'Chain_id', 'Chain_interval']
            chain_cols = list(chain_seq_data[0].keys()) if chain_seq_data else []
            
            missing_chain_cols = [col for col in chain_required_cols if col not in chain_cols]
            if missing_chain_cols:
                return {"valid": False, "message": f"Missing columns in chain data: {missing_chain_cols}"}
            
            # Check interval data structure
            if not interval_data:
                return {"valid": False, "message": "Interval data is empty"}
                
            interval_required_cols = ['Interval_id', 'Down_timestamp', 'Up_timestamp']
            interval_cols = list(interval_data[0].keys()) if interval_data else []
            
            missing_interval_cols = [col for col in interval_required_cols if col not in interval_cols]
            if missing_interval_cols:
                return {"valid": False, "message": f"Missing columns in interval data: {missing_interval_cols}"}
            
            return {"valid": True, "message": "Data structure is valid"}
            
        except Exception as e:
            return {"valid": False, "message": f"Validation error: {str(e)}"}

    def export_data_to_csv(self, data: Dict[str, Any], output_directory: str) -> Dict[str, str]:
        """Export processed data back to CSV files"""
        try:
            chain_seq_path = os.path.join(output_directory, 'processed_chain_seq.csv')
            interval_path = os.path.join(output_directory, 'processed_intervals.csv')
            
            # Export chain sequence data
            if 'chain_seq' in data:
                df_chain = pd.DataFrame(data['chain_seq'])
                df_chain.to_csv(chain_seq_path, index=False)
            
            # Export interval data
            if 'interval' in data:
                df_interval = pd.DataFrame(data['interval'])
                df_interval.to_csv(interval_path, index=False)
            
            return {
                "chain_seq_file": chain_seq_path,
                "interval_file": interval_path
            }
            
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            raise Exception(f"Failed to export data: {str(e)}")

    def get_data_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about the loaded data"""
        try:
            info = {
                "chain_seq_count": len(data.get('chain_seq', [])),
                "interval_count": len(data.get('interval', [])),
                "net_ids": [],
                "time_range": None
            }
            
            # Extract unique Net IDs
            if 'chain_seq' in data:
                net_ids = list(set([row.get('Net_id') for row in data['chain_seq'] if row.get('Net_id')]))
                info['net_ids'] = sorted([int(nid) for nid in net_ids if str(nid).isdigit()])
            
            # Calculate time range
            if 'interval' in data:
                timestamps = []
                for row in data['interval']:
                    if row.get('Down_timestamp'):
                        try:
                            timestamps.append(pd.to_datetime(row['Down_timestamp']))
                        except:
                            pass
                    if row.get('Up_timestamp'):
                        try:
                            timestamps.append(pd.to_datetime(row['Up_timestamp']))
                        except:
                            pass
                
                if timestamps:
                    info['time_range'] = {
                        'start': min(timestamps).isoformat(),
                        'end': max(timestamps).isoformat()
                    }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting data info: {str(e)}")
            return {}