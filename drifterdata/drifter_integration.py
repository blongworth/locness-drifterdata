"""
Drifter Data Integration Module

This module provides functionality to combine data from multiple sources for a drifter:
- GPX files for position tracking
- Fluorometer sensor data files
- AquaTROLL sensor data HTML files

The module aligns all data by timestamp and interpolates positions between recorded GPS points.
"""

import logging
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import interpolate

from .aquatroll_parser import parse_aquatroll_file, parse_aquatroll_folder
from .fluorometer_parser import parse_fluorometer_file, parse_fluorometer_folder
from .gpx_parser import parse_gpx_to_dataframe
from .logging_config import setup_logging

logger = logging.getLogger(__name__)

# Suppress pandas warnings for interpolation
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


class DrifterDataIntegrator:
    """
    Class for integrating multiple data sources from a drifter deployment.
    """
    
    def __init__(self):
        self.gpx_data = None
        self.fluorometer_data = None
        self.aquatroll_data = None
        self.integrated_data = None
        
    def load_gpx_data(self, gpx_path: str | Path) -> pd.DataFrame:
        """
        Load GPX position data.
        
        Args:
            gpx_path: Path to GPX file
            
        Returns:
            DataFrame with GPS positions and timestamps
        """
        gpx_path = Path(gpx_path)
        logger.info(f"Loading GPX data from {gpx_path.name}")
        
        self.gpx_data = parse_gpx_to_dataframe(gpx_path)
        
        # Ensure datetime column is timezone-aware (UTC)
        if 'timestamp' in self.gpx_data.columns:
            if self.gpx_data['timestamp'].dt.tz is None:
                self.gpx_data['timestamp'] = pd.to_datetime(self.gpx_data['timestamp'], utc=True)
            else:
                self.gpx_data['timestamp'] = self.gpx_data['timestamp'].dt.tz_convert('UTC')
        
        logger.info(f"Loaded {len(self.gpx_data)} GPS positions")
        return self.gpx_data
    
    def load_fluorometer_data(self, fluorometer_path: str | Path) -> pd.DataFrame:
        """
        Load fluorometer sensor data.
        
        Args:
            fluorometer_path: Path to fluorometer file or folder
            
        Returns:
            DataFrame with fluorometer readings and timestamps
        """
        fluorometer_path = Path(fluorometer_path)
        logger.info(f"Loading fluorometer data from {fluorometer_path}")
        
        if fluorometer_path.is_dir():
            self.fluorometer_data = parse_fluorometer_folder(fluorometer_path)
        else:
            self.fluorometer_data = parse_fluorometer_file(fluorometer_path)
        
        # Ensure datetime column is timezone-aware (UTC)
        if 'time_sec' in self.fluorometer_data.columns:
            self.fluorometer_data['datetime'] = pd.to_datetime(
                self.fluorometer_data['time_sec'], unit='s', utc=True
            )
        
        logger.info(f"Loaded {len(self.fluorometer_data)} fluorometer readings")
        return self.fluorometer_data
    
    def load_aquatroll_data(self, aquatroll_path: str | Path) -> pd.DataFrame:
        """
        Load AquaTROLL sensor data.
        
        Args:
            aquatroll_path: Path to AquaTROLL HTML file or folder
            
        Returns:
            DataFrame with AquaTROLL sensor readings and timestamps
        """
        aquatroll_path = Path(aquatroll_path)
        logger.info(f"Loading AquaTROLL data from {aquatroll_path}")
        
        if aquatroll_path.is_dir():
            self.aquatroll_data = parse_aquatroll_folder(aquatroll_path)
        else:
            result = parse_aquatroll_file(aquatroll_path)
            self.aquatroll_data = result['data']
        
        # Ensure datetime column is timezone-aware (UTC)
        if 'datetime' in self.aquatroll_data.columns:
            if self.aquatroll_data['datetime'].dt.tz is None:
                self.aquatroll_data['datetime'] = pd.to_datetime(
                    self.aquatroll_data['datetime'], utc=True
                )
            else:
                self.aquatroll_data['datetime'] = self.aquatroll_data['datetime'].dt.tz_convert('UTC')
        
        logger.info(f"Loaded {len(self.aquatroll_data)} AquaTROLL readings")
        return self.aquatroll_data
    
    def interpolate_positions(self, target_times: pd.DatetimeIndex, method: str = 'linear') -> pd.DataFrame:
        """
        Interpolate GPS positions for target timestamps.
        
        Args:
            target_times: Timestamps to interpolate positions for
            method: Interpolation method ('linear', 'cubic', 'nearest')
            
        Returns:
            DataFrame with interpolated positions
        """
        if self.gpx_data is None or len(self.gpx_data) == 0:
            logger.warning("No GPX data available for interpolation")
            return pd.DataFrame({
                'datetime': target_times,
                'latitude': np.nan,
                'longitude': np.nan,
                'interpolated': True
            })
        
        # Prepare GPS data for interpolation
        gps_times = self.gpx_data['timestamp'].values
        gps_lats = self.gpx_data['latitude'].values
        gps_lons = self.gpx_data['longitude'].values
        
        # Convert timestamps to numeric for interpolation
        gps_times_numeric = pd.to_datetime(gps_times).astype(np.int64)
        target_times_numeric = pd.to_datetime(target_times).astype(np.int64)
        
        # Remove any NaN values from GPS data
        valid_idx = ~(np.isnan(gps_lats) | np.isnan(gps_lons))
        if not np.any(valid_idx):
            logger.warning("No valid GPS coordinates for interpolation")
            return pd.DataFrame({
                'datetime': target_times,
                'latitude': np.nan,
                'longitude': np.nan,
                'interpolated': True
            })
        
        gps_times_clean = gps_times_numeric[valid_idx]
        gps_lats_clean = gps_lats[valid_idx]
        gps_lons_clean = gps_lons[valid_idx]
        
        # Sort by time for interpolation
        sort_idx = np.argsort(gps_times_clean)
        gps_times_clean = gps_times_clean[sort_idx]
        gps_lats_clean = gps_lats_clean[sort_idx]
        gps_lons_clean = gps_lons_clean[sort_idx]
        
        # Perform interpolation
        try:
            if method == 'cubic' and len(gps_times_clean) >= 4:
                # Use cubic spline interpolation
                lat_interp = interpolate.interp1d(
                    gps_times_clean, gps_lats_clean, 
                    kind='cubic', bounds_error=False, fill_value='extrapolate'
                )
                lon_interp = interpolate.interp1d(
                    gps_times_clean, gps_lons_clean, 
                    kind='cubic', bounds_error=False, fill_value='extrapolate'
                )
            else:
                # Use linear interpolation
                lat_interp = interpolate.interp1d(
                    gps_times_clean, gps_lats_clean, 
                    kind='linear', bounds_error=False, fill_value='extrapolate'
                )
                lon_interp = interpolate.interp1d(
                    gps_times_clean, gps_lons_clean, 
                    kind='linear', bounds_error=False, fill_value='extrapolate'
                )
            
            interpolated_lats = lat_interp(target_times_numeric)
            interpolated_lons = lon_interp(target_times_numeric)
            
        except Exception as e:
            logger.warning(f"Interpolation failed, using nearest neighbor: {e}")
            # Fallback to nearest neighbor
            interpolated_lats = np.interp(target_times_numeric, gps_times_clean, gps_lats_clean)
            interpolated_lons = np.interp(target_times_numeric, gps_times_clean, gps_lons_clean)
        
        # Create result DataFrame
        result = pd.DataFrame({
            'datetime': target_times,
            'latitude': interpolated_lats,
            'longitude': interpolated_lons,
            'interpolated': True
        })
        
        # Mark actual GPS points as not interpolated
        for gps_time in self.gpx_data['timestamp']:
            mask = np.abs((result['datetime'] - gps_time).dt.total_seconds()) < 30  # Within 30 seconds
            result.loc[mask, 'interpolated'] = False
        
        logger.info(f"Interpolated positions for {len(result)} timestamps")
        return result
    
    def integrate_data(self, interpolation_method: str = 'linear') -> pd.DataFrame:
        """
        Integrate all loaded data sources into a single DataFrame.
        
        Args:
            interpolation_method: Method for position interpolation
            
        Returns:
            Integrated DataFrame with all sensor data and interpolated positions
        """
        logger.info("Starting data integration")
        
        # Collect all timestamps
        all_times = []
        
        if self.fluorometer_data is not None and len(self.fluorometer_data) > 0:
            all_times.extend(self.fluorometer_data['datetime'].tolist())
        
        if self.aquatroll_data is not None and len(self.aquatroll_data) > 0:
            all_times.extend(self.aquatroll_data['datetime'].tolist())
        
        if self.gpx_data is not None and len(self.gpx_data) > 0:
            all_times.extend(self.gpx_data['timestamp'].tolist())
        
        if not all_times:
            raise ValueError("No data loaded for integration")
        
        # Create unified time index
        all_times = pd.to_datetime(all_times, utc=True)
        unified_times = pd.DatetimeIndex(sorted(set(all_times)))
        
        logger.info(f"Integrating data over {len(unified_times)} timestamps")
        
        # Start with interpolated positions
        integrated = self.interpolate_positions(unified_times, method=interpolation_method)
        
        # Merge fluorometer data
        if self.fluorometer_data is not None and len(self.fluorometer_data) > 0:
            fluoro_data = self.fluorometer_data.copy()
            fluoro_data = fluoro_data.set_index('datetime')
            
            # Prefix fluorometer columns to avoid conflicts
            fluoro_columns = {col: f'fluoro_{col}' for col in fluoro_data.columns 
                             if col not in ['datetime']}
            fluoro_data = fluoro_data.rename(columns=fluoro_columns)
            
            integrated = integrated.set_index('datetime')
            integrated = integrated.join(fluoro_data, how='left')
            integrated = integrated.reset_index()
        
        # Merge AquaTROLL data
        if self.aquatroll_data is not None and len(self.aquatroll_data) > 0:
            aqua_data = self.aquatroll_data.copy()
            aqua_data = aqua_data.set_index('datetime')
            
            # Prefix AquaTROLL columns to avoid conflicts (except common ones)
            exclude_prefix = ['datetime', 'latitude', 'longitude']
            aqua_columns = {col: f'aqua_{col}' for col in aqua_data.columns 
                           if col not in exclude_prefix}
            aqua_data = aqua_data.rename(columns=aqua_columns)
            
            integrated = integrated.set_index('datetime')
            integrated = integrated.join(aqua_data, how='left')
            integrated = integrated.reset_index()
        
        # Add derived columns
        integrated = self._add_derived_columns(integrated)
        
        # Sort by datetime
        integrated = integrated.sort_values('datetime').reset_index(drop=True)
        
        self.integrated_data = integrated
        logger.info(f"Integration complete: {len(integrated)} records with {len(integrated.columns)} columns")
        
        return integrated
    
    def _add_derived_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived columns to the integrated dataset."""
        df = df.copy()
        
        # Add time-based columns
        df['hour'] = df['datetime'].dt.hour
        df['day_of_year'] = df['datetime'].dt.dayofyear
        
        # Calculate time differences
        df['time_diff_seconds'] = df['datetime'].diff().dt.total_seconds()
        
        # Calculate distance and speed if we have position data
        if 'latitude' in df.columns and 'longitude' in df.columns:
            df['distance_km'] = self._calculate_distance(df)
            df['speed_kmh'] = df['distance_km'] / (df['time_diff_seconds'] / 3600)
            df['speed_kmh'] = df['speed_kmh'].replace([np.inf, -np.inf], np.nan)
        
        return df
    
    def _calculate_distance(self, df: pd.DataFrame) -> pd.Series:
        """Calculate distance between consecutive points using Haversine formula."""
        lat1 = np.radians(df['latitude'].shift(1))
        lon1 = np.radians(df['longitude'].shift(1))
        lat2 = np.radians(df['latitude'])
        lon2 = np.radians(df['longitude'])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        # Earth's radius in kilometers
        r = 6371
        
        return c * r
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the integrated dataset."""
        if self.integrated_data is None:
            return {"error": "No integrated data available"}
        
        df = self.integrated_data
        
        summary = {
            "total_records": len(df),
            "time_range": {
                "start": df['datetime'].min(),
                "end": df['datetime'].max(),
                "duration_hours": (df['datetime'].max() - df['datetime'].min()).total_seconds() / 3600
            },
            "data_sources": {},
            "spatial_extent": {},
            "columns": list(df.columns)
        }
        
        # Count data availability by source
        if any(col.startswith('fluoro_') for col in df.columns):
            fluoro_cols = [col for col in df.columns if col.startswith('fluoro_')]
            summary["data_sources"]["fluorometer"] = {
                "columns": len(fluoro_cols),
                "records_with_data": df[fluoro_cols].dropna(how='all').shape[0]
            }
        
        if any(col.startswith('aqua_') for col in df.columns):
            aqua_cols = [col for col in df.columns if col.startswith('aqua_')]
            summary["data_sources"]["aquatroll"] = {
                "columns": len(aqua_cols),
                "records_with_data": df[aqua_cols].dropna(how='all').shape[0]
            }
        
        # Spatial summary
        if 'latitude' in df.columns and 'longitude' in df.columns:
            valid_pos = df[['latitude', 'longitude']].dropna()
            if len(valid_pos) > 0:
                summary["spatial_extent"] = {
                    "lat_min": valid_pos['latitude'].min(),
                    "lat_max": valid_pos['latitude'].max(),
                    "lon_min": valid_pos['longitude'].min(),
                    "lon_max": valid_pos['longitude'].max(),
                    "total_distance_km": df['distance_km'].sum() if 'distance_km' in df.columns else None,
                    "interpolated_positions": df['interpolated'].sum() if 'interpolated' in df.columns else None
                }
        
        return summary


def integrate_drifter_data(
    gpx_path: str | Path | None = None,
    fluorometer_path: str | Path | None = None,
    aquatroll_path: str | Path | None = None,
    interpolation_method: str = 'linear'
) -> pd.DataFrame:
    """
    Convenience function to integrate drifter data from multiple sources.
    
    Args:
        gpx_path: Path to GPX file (optional)
        fluorometer_path: Path to fluorometer file/folder (optional)
        aquatroll_path: Path to AquaTROLL file/folder (optional)
        interpolation_method: Position interpolation method
        
    Returns:
        Integrated DataFrame
    """
    integrator = DrifterDataIntegrator()
    
    if gpx_path:
        integrator.load_gpx_data(gpx_path)
    
    if fluorometer_path:
        integrator.load_fluorometer_data(fluorometer_path)
    
    if aquatroll_path:
        integrator.load_aquatroll_data(aquatroll_path)
    
    return integrator.integrate_data(interpolation_method)


if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python drifter_integration.py <data_folder>")
        print("  Looks for GPX, fluorometer, and AquaTROLL data in the specified folder")
        sys.exit(1)
    
    data_folder = Path(sys.argv[1])
    
    if not data_folder.exists():
        print(f"Folder not found: {data_folder}")
        sys.exit(1)
    
    integrator = DrifterDataIntegrator()
    
    # Try to find and load different data types
    gpx_files = list(data_folder.glob("*.gpx"))
    if gpx_files:
        print(f"Loading GPX data from {gpx_files[0]}")
        integrator.load_gpx_data(gpx_files[0])
    
    # Look for fluorometer data
    fluoro_files = list(data_folder.glob("*fluoro*")) + list(data_folder.glob("*Fluoro*"))
    if fluoro_files:
        print(f"Loading fluorometer data from {fluoro_files[0]}")
        integrator.load_fluorometer_data(fluoro_files[0])
    
    # Look for AquaTROLL data
    aqua_files = list(data_folder.glob("*.html")) + list(data_folder.glob("*.htm"))
    if aqua_files:
        print(f"Loading AquaTROLL data from {aqua_files[0]}")
        integrator.load_aquatroll_data(aqua_files[0])
    
    # Integrate data
    integrated_df = integrator.integrate_data()
    
    # Print summary
    summary = integrator.get_summary()
    print("\nIntegration Summary:")
    print(f"Total records: {summary['total_records']}")
    print(f"Time range: {summary['time_range']['start']} to {summary['time_range']['end']}")
    print(f"Duration: {summary['time_range']['duration_hours']:.2f} hours")
    print(f"Data sources: {list(summary['data_sources'].keys())}")
    print(f"Columns: {len(summary['columns'])}")
    
    if 'spatial_extent' in summary and summary['spatial_extent']:
        extent = summary['spatial_extent']
        print(f"Spatial extent: {extent['lat_min']:.4f} to {extent['lat_max']:.4f} lat, "
              f"{extent['lon_min']:.4f} to {extent['lon_max']:.4f} lon")
        if extent['total_distance_km']:
            print(f"Total distance: {extent['total_distance_km']:.2f} km")
