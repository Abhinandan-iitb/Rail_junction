"""
Shunting Visuals Main Module
Contains the core business logic for shunting data visualization and analysis
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import json

logger = logging.getLogger(__name__)

class ShuntingVisualsProcessor:
    """Main processor for shunting visuals data analysis and visualization"""
    
    def __init__(self):
        self.chain_seq_data = []
        self.interval_data = []
        self.available_net_ids = []
        self.processed_data = {}
        
    def process_csv_data(self, chain_seq_data: List[Dict], interval_data: List[Dict]) -> Dict[str, Any]:
        """
        Process uploaded CSV data for shunting analysis
        
        Args:
            chain_seq_data: List of chain sequence records
            interval_data: List of interval records
            
        Returns:
            Dict containing processing results and statistics
        """
        try:
            self.chain_seq_data = chain_seq_data
            self.interval_data = interval_data
            
            # Process timestamps
            self._process_timestamps()
            
            # Extract available Net IDs
            self._extract_available_net_ids()
            
            # Generate data summary
            summary = self._generate_data_summary()
            
            return {
                "status": "success",
                "message": "Data processed successfully",
                "summary": summary,
                "available_net_ids": self.available_net_ids
            }
            
        except Exception as e:
            logger.error(f"Error processing CSV data: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to process data: {str(e)}"
            }
    
    def generate_shunting_plot_data(self, net_id: int, spacing: float = 20.0, chain_seq_data: List[Dict] = None, interval_data: List[Dict] = None) -> Dict[str, Any]:
        """
        Generate plot data for a specific Net ID
        
        Args:
            net_id: Network ID to filter chains
            spacing: Vertical spacing between intervals
            chain_seq_data: Chain sequence data (optional)
            interval_data: Interval data (optional)
            
        Returns:
            Dict containing plot data and statistics
        """
        try:
            # Use provided data or stored data
            if chain_seq_data is not None and interval_data is not None:
                # Process the provided data
                self.process_csv_data(chain_seq_data, interval_data)
            
            if not self.chain_seq_data or not self.interval_data:
                return {
                    "status": "error",
                    "message": "No data available. Please load data first.",
                    "plot_data": [],
                    "statistics": {}
                }
            
            # Filter chain sequences for the specified Net ID
            filtered_chains = [
                row for row in self.chain_seq_data 
                if row.get('Net_id') and int(row['Net_id']) == net_id
            ]
            
            if not filtered_chains:
                return {
                    "status": "error", 
                    "message": f"No chain sequences found for Net_id {net_id}",
                    "plot_data": [],
                    "statistics": {}
                }
            
            # Extract ordered intervals
            order_list = self._extract_ordered_intervals(filtered_chains)
            
            # Merge with interval data
            merged_data = self._merge_interval_data(order_list)
            
            if not merged_data:
                return {
                    "status": "error",
                    "message": f"No matching interval data found for Net_id {net_id}",
                    "plot_data": [],
                    "statistics": {}
                }
            
            # Prepare plot data
            plot_data = self._prepare_plot_data(merged_data, spacing)
            
            # Calculate statistics
            statistics = self._calculate_statistics(plot_data)
            
            logger.info(f"Generated plot data for Net_id {net_id}: {len(plot_data)} intervals")
            
            return {
                "status": "success",
                "message": f"Plot data generated for Net_id {net_id}",
                "plot_data": plot_data,
                "statistics": statistics
            }
            
        except Exception as e:
            logger.error(f"Error generating plot data for Net_id {net_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error generating plot: {str(e)}",
                "plot_data": [],
                "statistics": {}
            }
    
    def _process_timestamps(self):
        """Convert timestamp strings to datetime objects"""
        for row in self.interval_data:
            if row.get('Down_timestamp'):
                try:
                    row['Down_timestamp'] = pd.to_datetime(row['Down_timestamp'])
                except:
                    logger.warning(f"Failed to parse Down_timestamp: {row.get('Down_timestamp')}")
            
            if row.get('Up_timestamp'):
                try:
                    row['Up_timestamp'] = pd.to_datetime(row['Up_timestamp'])
                except:
                    logger.warning(f"Failed to parse Up_timestamp: {row.get('Up_timestamp')}")
    
    def _extract_available_net_ids(self):
        """Extract unique Net IDs from chain sequence data"""
        net_ids = set()
        for row in self.chain_seq_data:
            try:
                net_id = int(row.get('Net_id', 0))
                if net_id > 0:
                    net_ids.add(net_id)
            except (ValueError, TypeError):
                continue
        
        self.available_net_ids = sorted(list(net_ids))
    
    def _extract_ordered_intervals(self, chain_seq_filtered: List[Dict]) -> List[Dict]:
        """Extract intervals with their order from chain sequence data"""
        order_list = []
        
        for row in chain_seq_filtered:
            chain_interval = row.get('Chain_interval', '')
            if not chain_interval:
                continue
                
            intervals = chain_interval.split(' - ')
            for index, interval in enumerate(intervals):
                interval = interval.strip()
                if interval:
                    order_list.append({
                        'Chain_id': int(row.get('Chain_id', 0)),
                        'Interval_id': interval,
                        'Order': index,
                        'Net_id': int(row.get('Net_id', 0))
                    })
        
        return order_list
    
    def _merge_interval_data(self, order_list: List[Dict]) -> List[Dict]:
        """Merge order list with interval data"""
        merged = []
        
        # Create lookup dictionary for O(1) access
        interval_dict = {
            row.get('Interval_id', '').strip(): row 
            for row in self.interval_data 
            if row.get('Interval_id')
        }
        
        for order_row in order_list:
            interval_row = interval_dict.get(order_row['Interval_id'])
            if interval_row:
                merged_row = {**order_row, **interval_row}
                merged.append(merged_row)
        
        return merged
    
    def _prepare_plot_data(self, merged_data: List[Dict], spacing: float) -> List[Dict]:
        """Prepare data for plotting with calculated positions and durations"""
        plot_data = []
        
        for index, row in enumerate(merged_data):
            # Calculate duration
            down_time = row.get('Down_timestamp')
            up_time = row.get('Up_timestamp')
            
            if down_time and up_time:
                # Convert to datetime if they're strings
                if isinstance(down_time, str):
                    down_time = pd.to_datetime(down_time)
                if isinstance(up_time, str):
                    up_time = pd.to_datetime(up_time)
                
                duration = (up_time - down_time).total_seconds() * 1000  # milliseconds
            else:
                # Try to parse the Duration column if timestamps aren't available
                duration_str = row.get('Duration', '0')
                if duration_str and duration_str != '0':
                    duration = self._parse_duration_string(duration_str)
                else:
                    duration = 0
            
            plot_row = {
                **row,
                'Duration': duration,
                'Row': (index + 1) * spacing,
                'Index': index
            }
            plot_data.append(plot_row)
        
        # Sort by Chain_id and Order
        plot_data.sort(key=lambda x: (x.get('Chain_id', 0), x.get('Order', 0)))
        
        return plot_data
    
    def _parse_duration_string(self, duration_str: str) -> float:
        """Parse duration string like '00:01:04' to milliseconds"""
        try:
            if ':' in duration_str:
                parts = duration_str.split(':')
                if len(parts) == 3:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    return total_seconds * 1000  # Convert to milliseconds
            
            # If it's just a number, assume it's already in some unit
            return float(duration_str) * 1000
        except (ValueError, TypeError):
            return 0
    
    def _calculate_statistics(self, plot_data: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for the plot data"""
        if not plot_data:
            return {}
        
        # Count unique chains
        unique_chains = len(set(row.get('Chain_id', 0) for row in plot_data))
        
        # Total intervals
        total_intervals = len(plot_data)
        
        # Calculate average duration
        durations = [row.get('Duration', 0) for row in plot_data if row.get('Duration', 0) > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Format average duration
        avg_duration_formatted = self._format_duration(avg_duration)
        
        # Calculate time range
        timestamps = []
        for row in plot_data:
            if row.get('Down_timestamp'):
                timestamps.append(row['Down_timestamp'])
            if row.get('Up_timestamp'):
                timestamps.append(row['Up_timestamp'])
        
        time_range = {}
        if timestamps:
            time_range = {
                'start': min(timestamps).isoformat(),
                'end': max(timestamps).isoformat()
            }
        
        return {
            'total_chains': unique_chains,
            'total_intervals': total_intervals,
            'avg_duration': avg_duration_formatted,
            'avg_duration_ms': avg_duration,
            'time_range': time_range
        }
    
    def _format_duration(self, milliseconds: float) -> str:
        """Format duration in milliseconds to human readable format"""
        if milliseconds <= 0:
            return "0s"
        
        seconds = int(milliseconds / 1000)
        minutes = seconds // 60
        hours = minutes // 60
        
        if hours > 0:
            return f"{hours}h {minutes % 60}m"
        elif minutes > 0:
            return f"{minutes}m {seconds % 60}s"
        else:
            return f"{seconds}s"
    
    def _generate_data_summary(self) -> Dict[str, Any]:
        """Generate summary of loaded data"""
        return {
            'chain_seq_records': len(self.chain_seq_data),
            'interval_records': len(self.interval_data),
            'available_net_ids': len(self.available_net_ids),
            'net_id_range': {
                'min': min(self.available_net_ids) if self.available_net_ids else 0,
                'max': max(self.available_net_ids) if self.available_net_ids else 0
            }
        }
    
    def get_available_net_ids(self) -> List[int]:
        """Get list of available Net IDs"""
        return self.available_net_ids
    
    def validate_net_id(self, net_id: int) -> bool:
        """Validate if Net ID is available in the data"""
        return net_id in self.available_net_ids
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of current data state"""
        return {
            'has_data': bool(self.chain_seq_data and self.interval_data),
            'chain_seq_count': len(self.chain_seq_data),
            'interval_count': len(self.interval_data),
            'net_ids_count': len(self.available_net_ids),
            'available_net_ids': self.available_net_ids
        }