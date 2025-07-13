"""
Streamlit dashboard for displaying SPOT tracker drifter positions and traces.

This module provides a web interface for visualizing drifter position data
collected from SPOT trackers, including interactive maps and traces over time.
"""

# Reordered imports for better readability
import argparse
import logging
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from drifterdata.logging_config import setup_logging
from drifterdata.spot_database import SpotDatabase
from drifterdata.spot_tracker import SpotTrackerAPI


# Setup logging for the dashboard
setup_logging()


logger = logging.getLogger(__name__)


# Updated type annotations
class DrifterDashboard:
    """Streamlit dashboard for drifter position visualization."""
    
    def __init__(self, db_path: str | None = None):
        """
        Initialize the dashboard.
        
        Args:
            db_path: Path to the SQLite database file. If provided, uses database mode.
                    If None, uses API mode.
        """
        self.db_path = db_path
        # Determine data source based on whether db_path is provided
        self.data_source = "database" if db_path else "api"
        self.db = SpotDatabase(db_path) if self.data_source == "database" else None
        self.api = None
        
    def get_api_connection(self) -> SpotTrackerAPI | None:
        """
        Get or create SPOT API connection using Streamlit secrets.
        
        Returns:
            SpotTrackerAPI instance or None if credentials not available
        """
        if self.api is None and self.data_source == "api":
            try:
                # Get feed_id from Streamlit secrets
                if hasattr(st, 'secrets') and 'spot' in st.secrets:
                    feed_id = st.secrets.spot.feed_id
                else:
                    # Fall back to environment variables
                    feed_id = os.getenv('SPOT_FEED_ID')
                
                if feed_id and feed_id != "your_spot_feed_id_here":
                    self.api = SpotTrackerAPI(feed_id=feed_id)
                    # Test the connection
                    if not self.api.test_connection():
                        st.error("Failed to connect to SPOT API with provided feed ID")
                        self.api = None
                else:
                    st.error("SPOT feed ID not found. Please configure .streamlit/secrets.toml")
                    self.api = None
                    
            except Exception as e:
                st.error(f"Error connecting to SPOT API: {e}")
                self.api = None
                
        return self.api
    
    @st.cache_data(ttl=180, show_spinner=False)
    def load_api_data(_self, days_back: int = 7) -> pd.DataFrame:
        """
        Load position data directly from SPOT API.
        
        Returns:
            DataFrame with position data
        """
        api = _self.get_api_connection()
        if not api:
            return pd.DataFrame()
            
        try:
            positions = api.get_messages()
            
            if not positions:
                return pd.DataFrame()
            
            # Convert positions to DataFrame
            data = []
            for pos in positions:
                data.append({
                    'asset_id': pos.asset_id,
                    'timestamp': pos.timestamp,
                    'latitude': pos.latitude,
                    'longitude': pos.longitude,
                    'altitude': pos.altitude,
                    'message_type': pos.message_type,
                    'battery_state': pos.battery_state
                })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values(['asset_id', 'timestamp'])
            # Ensure both sides of comparison are timezone-aware
            cutoff = pd.Timestamp(datetime.now() - timedelta(days=days_back), tz=df['timestamp'].dt.tz)
            df = df[df['timestamp'] > cutoff]
            return df
            
        except Exception as e:
            st.error(f"Error loading data from SPOT API: {e}")
            return pd.DataFrame()
        
    def load_position_data(self, asset_ids: list[str] | None = None, days_back: int = 7) -> pd.DataFrame:
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
    
    def create_sidebar(self) -> dict[str, Any]:
        """
        Create sidebar controls.
        
        Returns:
            Dictionary with sidebar control values
        """
        st.sidebar.title("🌊 Drifter Dashboard")
        
        # Show current data source
        source_icon = "📂" if self.data_source == "database" else "🌐"
        source_name = "Database" if self.data_source == "database" else "SPOT API (Live)"
        st.sidebar.markdown(f"### {source_icon} Data Source: {source_name}")
        
        # Get available asset IDs based on data source
        asset_ids = []
        if self.data_source == "api":
            # Get assets from API
            api = self.get_api_connection()
            if api:
                try:
                    api_df = self.load_api_data()
                    if not api_df.empty:
                        asset_ids = sorted(api_df['asset_id'].unique().tolist())
                except Exception:
                    pass
            else:
                st.sidebar.error("API connection failed")
        else:
            # Get from database
            if self.db and Path(self.db_path).exists():
                try:
                    asset_ids = self.db.get_asset_ids()
                except Exception as e:
                    st.sidebar.error(f"Error loading asset IDs: {e}")
                    asset_ids = []
            else:
                st.sidebar.error(f"Database not found: {self.db_path}")
        
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
            if self.data_source == "database":
                st.sidebar.warning("No drifters found in database")
            else:
                st.sidebar.warning("No drifters found via API")
        
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
        
        # Show stats based on data source
        st.sidebar.markdown("### 📈 Statistics")
        
        if self.data_source == "database" and self.db:
            try:
                stats = self.db.get_database_stats()
                st.sidebar.metric("Total Positions", stats['total_positions'])
                st.sidebar.metric("Active Drifters", stats['unique_assets'])
                
                if stats['latest_position']:
                    latest_time = pd.to_datetime(stats['latest_position'])
                    st.sidebar.metric("Last Update", latest_time.strftime('%Y-%m-%d %H:%M'))
                    
            except Exception as e:
                st.sidebar.error(f"Error loading stats: {e}")
        
        elif self.data_source == "api":
            api = self.get_api_connection()
            if api:
                try:
                    api_df = self.load_api_data(days_back=1)  # Just for stats
                    if not api_df.empty:
                        st.sidebar.metric("Live Positions", len(api_df))
                        st.sidebar.metric("Active Drifters", api_df['asset_id'].nunique())
                        latest_api = api_df['timestamp'].max()
                        st.sidebar.metric("Latest Position", latest_api.strftime('%Y-%m-%d %H:%M'))
                    else:
                        st.sidebar.info("No recent positions found")
                except Exception as e:
                    st.sidebar.error(f"Error loading API stats: {e}")
        
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
        
        # Create sidebar controls
        controls = self.create_sidebar()
        
        # Load data based on selected data source
        df = pd.DataFrame()
        data_source_info = ""
        
        if controls['selected_assets']:
            if self.data_source == "database":
                # Load from database
                if Path(self.db_path).exists():
                    df = self.load_position_data(
                        asset_ids=controls['selected_assets'],
                        days_back=controls['days_back']
                    )
                    data_source_info = "📂 Database"
                else:
                    st.error(f"Database file not found: {self.db_path}")
                    st.info("Make sure the data collection system has been run to create position data.")
                    
            elif self.data_source == "api":
                # Load from API
                api = self.get_api_connection()
                if api:
                    df = self.load_api_data(days_back=controls['days_back'])
                    # Filter by selected assets
                    if not df.empty:
                        df = df[df['asset_id'].isin(controls['selected_assets'])]
                    data_source_info = "🌐 SPOT API (Live)"
                else:
                    st.warning("SPOT API connection failed. Check your credentials in .streamlit/secrets.toml")
        
        # Create two columns for layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"🗺️ Drifter Traces Map {data_source_info}")
            
            if not df.empty:
                # Create and display map
                m = self.create_map(df)
                st_folium(m, width=700, height=500)
                
                # Show map info
                total_points = len(df)
                unique_drifters = len(controls['selected_assets'])
                st.info(f"Displaying {total_points} position points for {unique_drifters} drifter(s)")
                
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
        if self.data_source == "api":
            st.markdown("*Live data from SPOT API | Refresh page for latest positions*")
        else:
            st.markdown("*Database data | Dashboard updates when new data is collected*")


def main():
    """Main function to run the dashboard."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SPOT Drifter Dashboard")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Path to SQLite database file. If provided, uses database mode. If not provided, uses API mode."
    )
    
    # Parse args, handling both streamlit run and direct execution
    if len(sys.argv) > 1 and sys.argv[1] == "--":
        # Called via streamlit run script.py -- --db-path file.db
        args = parser.parse_args(sys.argv[2:])
    else:
        # Called directly
        args = parser.parse_args()
    
    # Create and run dashboard
    dashboard = DrifterDashboard(db_path=args.db_path)
    dashboard.run()


if __name__ == "__main__":
    main()
