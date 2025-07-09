"""
Streamlit dashboard for displaying SPOT tracker drifter positions and traces.

This module provides a web interface for visualizing drifter position data
collected from SPOT trackers, including interactive maps and traces over time.
"""

import logging
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import sqlite3
from pathlib import Path

from drifterdata.spot_database import SpotDatabase


# Configure logging
logger = logging.getLogger(__name__)


class DrifterDashboard:
    """Streamlit dashboard for drifter position visualization."""
    
    def __init__(self, db_path: str = "spot_positions.db"):
        """
        Initialize the dashboard.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db = SpotDatabase(db_path)
        
    def load_position_data(self, 
                          asset_ids: Optional[List[str]] = None,
                          days_back: int = 7) -> pd.DataFrame:
        """
        Load position data from the database.
        
        Args:
            asset_ids: List of asset IDs to filter by (None for all)
            days_back: Number of days back to load data
            
        Returns:
            DataFrame with position data
        """
        try:
            since_date = datetime.now() - timedelta(days=days_back)
            
            with sqlite3.connect(self.db_path) as conn:
                if asset_ids:
                    placeholders = ','.join(['?' for _ in asset_ids])
                    query = f"""
                        SELECT * FROM positions 
                        WHERE asset_id IN ({placeholders}) AND timestamp > ?
                        ORDER BY asset_id, timestamp ASC
                    """
                    params = asset_ids + [since_date.isoformat()]
                else:
                    query = """
                        SELECT * FROM positions 
                        WHERE timestamp > ?
                        ORDER BY asset_id, timestamp ASC
                    """
                    params = [since_date.isoformat()]
                
                df = pd.read_sql_query(query, conn, params=params)
                
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values(['asset_id', 'timestamp'])
                
                return df
                
        except Exception as e:
            logger.error(f"Error loading position data: {e}")
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()
    
    def create_map(self, df: pd.DataFrame) -> folium.Map:
        """
        Create a Folium map with drifter traces.
        
        Args:
            df: DataFrame with position data
            
        Returns:
            Folium map object
        """
        if df.empty:
            # Default map centered on the ocean
            m = folium.Map(location=[0, 0], zoom_start=2)
            return m
        
        # Calculate map center based on data
        center_lat = df['latitude'].mean()
        center_lon = df['longitude'].mean()
        
        # Create map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
        
        # Define colors for different drifters
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 
                 'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue', 
                 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 
                 'gray', 'black', 'lightgray']
        
        # Group by asset_id and create traces
        for i, (asset_id, group) in enumerate(df.groupby('asset_id')):
            color = colors[i % len(colors)]
            
            # Sort by timestamp to ensure proper trace order
            group = group.sort_values('timestamp')
            
            # Create trace line
            coordinates = group[['latitude', 'longitude']].values.tolist()
            
            if len(coordinates) > 1:
                folium.PolyLine(
                    coordinates,
                    color=color,
                    weight=3,
                    opacity=0.8,
                    popup=f"Drifter: {asset_id}"
                ).add_to(m)
            
            # Add markers for start and end positions
            if not group.empty:
                # Start position (oldest)
                start_row = group.iloc[0]
                folium.Marker(
                    [start_row['latitude'], start_row['longitude']],
                    popup=f"Start: {asset_id}<br>{start_row['timestamp']}",
                    icon=folium.Icon(color=color, icon='play'),
                    tooltip=f"{asset_id} - Start"
                ).add_to(m)
                
                # End position (newest)
                end_row = group.iloc[-1]
                folium.Marker(
                    [end_row['latitude'], end_row['longitude']],
                    popup=f"Latest: {asset_id}<br>{end_row['timestamp']}<br>"
                          f"Battery: {end_row['battery_state'] or 'Unknown'}",
                    icon=folium.Icon(color=color, icon='stop'),
                    tooltip=f"{asset_id} - Latest"
                ).add_to(m)
                
                # Add intermediate points as circle markers
                for _, row in group.iterrows():
                    folium.CircleMarker(
                        [row['latitude'], row['longitude']],
                        radius=3,
                        popup=f"Drifter: {asset_id}<br>"
                              f"Time: {row['timestamp']}<br>"
                              f"Lat: {row['latitude']:.6f}<br>"
                              f"Lon: {row['longitude']:.6f}<br>"
                              f"Battery: {row['battery_state'] or 'Unknown'}",
                        color=color,
                        fillColor=color,
                        fillOpacity=0.6,
                        weight=1
                    ).add_to(m)
        
        return m
    
    def create_sidebar(self) -> Dict[str, Any]:
        """
        Create sidebar controls.
        
        Returns:
            Dictionary with sidebar control values
        """
        st.sidebar.title("🌊 Drifter Dashboard")
        
        # Get available asset IDs
        try:
            asset_ids = self.db.get_asset_ids()
        except Exception as e:
            st.sidebar.error(f"Error loading asset IDs: {e}")
            asset_ids = []
        
        # Asset selection
        if asset_ids:
            selected_assets = st.sidebar.multiselect(
                "Select Drifters",
                options=asset_ids,
                default=asset_ids,
                help="Select which drifters to display on the map"
            )
        else:
            selected_assets = []
            st.sidebar.warning("No drifters found in database")
        
        # Time range selection
        days_back = st.sidebar.slider(
            "Days of History",
            min_value=1,
            max_value=30,
            value=7,
            help="Number of days of position history to display"
        )
        
        # Refresh button
        refresh = st.sidebar.button("🔄 Refresh Data")
        
        # Database stats
        try:
            stats = self.db.get_database_stats()
            st.sidebar.markdown("### 📊 Database Stats")
            st.sidebar.metric("Total Positions", stats['total_positions'])
            st.sidebar.metric("Active Drifters", stats['unique_assets'])
            
            if stats['latest_position']:
                latest_time = pd.to_datetime(stats['latest_position'])
                st.sidebar.metric("Last Update", latest_time.strftime('%Y-%m-%d %H:%M'))
                
        except Exception as e:
            st.sidebar.error(f"Error loading stats: {e}")
        
        return {
            'selected_assets': selected_assets,
            'days_back': days_back,
            'refresh': refresh
        }
    
    def create_data_table(self, df: pd.DataFrame):
        """
        Create a data table showing recent positions.
        
        Args:
            df: DataFrame with position data
        """
        if df.empty:
            st.info("No position data available for the selected criteria.")
            return
        
        st.subheader("📍 Recent Positions")
        
        # Show summary by drifter
        summary = df.groupby('asset_id').agg({
            'timestamp': ['min', 'max', 'count'],
            'latitude': 'last',
            'longitude': 'last',
            'battery_state': 'last'
        }).round(6)
        
        summary.columns = ['First_Seen', 'Last_Seen', 'Total_Points', 
                          'Latest_Lat', 'Latest_Lon', 'Battery_Status']
        
        st.dataframe(summary, use_container_width=True)
        
        # Show detailed data in expander
        with st.expander("📋 Detailed Position Data"):
            # Format the data for display
            display_df = df[['asset_id', 'timestamp', 'latitude', 'longitude', 
                           'altitude', 'battery_state', 'message_type']].copy()
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            display_df = display_df.round(6)
            
            st.dataframe(display_df, use_container_width=True)
    
    def run(self):
        """Run the Streamlit dashboard."""
        st.set_page_config(
            page_title="Drifter Tracker Dashboard",
            page_icon="🌊",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("🌊 SPOT Drifter Tracker Dashboard")
        st.markdown("Real-time visualization of drifter positions and movement traces")
        
        # Check if database exists
        if not Path(self.db_path).exists():
            st.error(f"Database file not found: {self.db_path}")
            st.info("Make sure the data collection system has been run to create position data.")
            return
        
        # Create sidebar controls
        controls = self.create_sidebar()
        
        # Load data based on controls
        if controls['selected_assets']:
            df = self.load_position_data(
                asset_ids=controls['selected_assets'],
                days_back=controls['days_back']
            )
        else:
            df = pd.DataFrame()
        
        # Create two columns for layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🗺️ Drifter Traces Map")
            
            if not df.empty:
                # Create and display map
                m = self.create_map(df)
                st_folium(m, width=700, height=500)
                
                # Show map info
                st.info(f"Displaying {len(df)} position points for {len(controls['selected_assets'])} drifter(s)")
                
            else:
                st.warning("No data available for the selected criteria.")
                # Show empty map
                empty_map = folium.Map(location=[0, 0], zoom_start=2)
                st_folium(empty_map, width=700, height=500)
        
        with col2:
            # Create data table
            self.create_data_table(df)
        
        # Footer
        st.markdown("---")
        st.markdown("*Dashboard updates automatically when new position data is collected*")


def main():
    """Main function to run the dashboard."""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Get database path from command line or environment
    import sys
    import os
    
    db_path = "spot_positions.db"
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    elif 'DB_PATH' in os.environ:
        db_path = os.environ['DB_PATH']
    
    # Create and run dashboard
    dashboard = DrifterDashboard(db_path)
    dashboard.run()


if __name__ == "__main__":
    main()
