"""
Streamlit dashboard for displaying SPOT tracker drifter positions and traces.

This module provides a web interface for visualizing drifter position data
collected from SPOT trackers, including interactive maps and traces over time.
"""

# Reordered imports for better readability
import logging
import os
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


class DrifterDashboard:
    """Streamlit dashboard for drifter position visualization."""
    
    def __init__(self):
        """
        Initialize the dashboard.
        """
        self.api = None        

    def get_api_connection(self) -> SpotTrackerAPI | None:
        """
        Get or create SPOT API connection using Streamlit secrets.
        
        Returns:
            SpotTrackerAPI instance or None if credentials not available
        """
        if self.api is None:
            try:
                # Get feed_id from Streamlit secrets
                if hasattr(st, 'secrets') and 'spot' in st.secrets:
                    feed_id = st.secrets.spot.feed_id
                else:
                    # Fall back to environment variables
                    feed_id = os.getenv('SPOT_FEED_ID')
                
                if feed_id and feed_id != "your_spot_feed_id_here":
                    self.api = SpotTrackerAPI(feed_id=feed_id)
                else:
                    st.error("SPOT feed ID not found. Please configure .streamlit/secrets.toml")
                    self.api = None
                    
            except Exception as e:
                st.error(f"Error connecting to SPOT API: {e}")
                self.api = None
                
        return self.api
    
    @st.cache_data(ttl=180, show_spinner=False)
    def load_api_data(_self) -> pd.DataFrame:
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
            return df
            
        except Exception as e:
            st.error(f"Error loading data from SPOT API: {e}")
            return pd.DataFrame()

    def filter_time_range(self, df: pd.DataFrame, days_back: int = 7) -> pd.DataFrame:
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(['asset_id', 'timestamp'])
        # Ensure both sides of comparison are timezone-aware
        cutoff = pd.Timestamp(datetime.now() - timedelta(days=days_back), tz=df['timestamp'].dt.tz)
        df = df[df['timestamp'] > cutoff]
        return df

    def create_map(self, df: pd.DataFrame) -> folium.Map:
        """
        Create a Folium map with drifter traces, ESRI bathymetry tiles, and gridlines.
        
        Args:
            df: DataFrame with position data
            
        Returns:
            Folium map object
        """
        if df.empty:
            # Default map centered on the ocean
            m = folium.Map(location=[0, 0], zoom_start=2)
        else:
            # Calculate map center based on data
            center_lat = df['latitude'].mean()
            center_lon = df['longitude'].mean()
            m = folium.Map(location=[center_lat, center_lon], zoom_start=8)
        
        # Add ESRI bathymetry tile layer
        folium.TileLayer(
            tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
            attr="ESRI Ocean Basemap",
            name="ESRI Bathymetry",
            overlay=False,
            control=True
        ).add_to(m)
        
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
                
                # Add intermediate points as circle markers with hover tooltip
                for _, row in group.iterrows():
                    # Format timestamp without timezone info
                    ts_str = pd.to_datetime(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    folium.CircleMarker(
                        [row['latitude'], row['longitude']],
                        radius=3,
                        color=color,
                        fillColor=color,
                        fillOpacity=0.6,
                        weight=1,
                        tooltip=folium.Tooltip(
                            f"Drifter: {asset_id}<br>"
                            f"Time: {ts_str}<br>"
                            f"Lat: {row['latitude']:.6f}<br>"
                            f"Lon: {row['longitude']:.6f}"
                        )
                    ).add_to(m)
        
        folium.LayerControl().add_to(m)
        return m

    def create_sidebar(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Create sidebar controls.
        
        Returns:
            Dictionary with sidebar control values
        """
        st.sidebar.title("🌊 Drifter Dashboard")
        
        # Get available asset IDs
        asset_ids = []
        if not df.empty:
            asset_ids = sorted(df['asset_id'].unique().tolist())
        
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
            st.sidebar.warning("No drifters found via API")
        
        # Time range selection
        days_back = st.sidebar.slider(
            "Days of History",
            min_value=1,
            max_value=7,
            value=7,
            help="Number of days of position history to display"
        )
        
        # Show stats based on data source
        st.sidebar.markdown("### 📈 Statistics")
        
        if not df.empty:
            st.sidebar.metric("Live Positions", len(df))
            st.sidebar.metric("Active Drifters", df['asset_id'].nunique())
            latest_api = df['timestamp'].max()
            st.sidebar.metric("Latest Position", latest_api.strftime('%Y-%m-%d %H:%M'))
        else:
            st.sidebar.info("No recent positions found")
        
        return {
            'selected_assets': selected_assets,
            'days_back': days_back
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
        
        # Load data based on selected data source
        df = pd.DataFrame()
        # Load from API
        df = self.load_api_data()

        # Create sidebar controls
        controls = self.create_sidebar(df)
        
        # Filter by selected assets
        if not df.empty:
            df = df[df['asset_id'].isin(controls['selected_assets'])]
            
        df = self.filter_time_range(df, controls['days_back'])

        # Create two columns for layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader(f"🗺️ Drifter Traces Map")
            
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
        st.markdown("*Live data from SPOT API | Refresh page for latest positions*")


def main():
    """Main function to run the dashboard."""
    
    # Create and run dashboard
    dashboard = DrifterDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
