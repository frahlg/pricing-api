"""
ENTSO-E Electricity Pricing Service

A Python service for fetching electricity pricing data from multiple bidding zones
using the ENTSO-E Transparency Platform API. Configuration is managed via YAML.
"""

import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import sys

import pandas as pd
import yaml
from entsoe import EntsoePandasClient

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PricingServiceError(Exception):
    """Custom exception for pricing service errors."""
    pass


class ConfigurationError(PricingServiceError):
    """Exception raised for configuration-related errors."""
    pass


class PricingService:
    """
    A service for fetching electricity pricing data from ENTSO-E API.
    
    This service provides methods to fetch day-ahead pricing data for multiple
    bidding zones as configured in a YAML configuration file.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the pricing service.
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.client = self._initialize_client()
        self._validate_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                logger.info(f"Configuration loaded from {self.config_path}")
                return config
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing YAML configuration: {e}")
    
    def _validate_config(self) -> None:
        """Validate the configuration structure."""
        required_sections = ['api', 'zones', 'service']
        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(f"Missing required configuration section: {section}")
        
        if 'token' not in self.config['api']:
            raise ConfigurationError("API token not found in configuration")
        
        if not self.config['zones']:
            raise ConfigurationError("No zones configured")
    
    def _initialize_client(self) -> EntsoePandasClient:
        """Initialize the ENTSO-E API client."""
        try:
            api_token = self.config['api']['token']
            if not api_token or api_token == "your-api-token-here":
                raise ConfigurationError(
                    "Please set a valid API token in the configuration file. "
                    "Get your token from https://transparency.entsoe.eu/"
                )
            
            client = EntsoePandasClient(api_key=api_token)
            logger.info("ENTSO-E API client initialized successfully")
            return client
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize API client: {e}")
    
    def get_available_zones(self) -> Dict[str, Dict[str, str]]:
        """
        Get information about all available bidding zones.
        
        Returns:
            Dictionary with zone information
        """
        return self.config['zones']
    
    def fetch_prices(
        self,
        zones: Optional[List[str]] = None,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        days_back: Optional[int] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch day-ahead pricing data for specified zones.
        
        Args:
            zones: List of zone codes to fetch (e.g., ['SE4', 'NO1']). 
                   If None, uses default zones from config.
            start_date: Start date for data (string 'YYYY-MM-DD' or datetime).
                       If None, calculated from days_back.
            end_date: End date for data (string 'YYYY-MM-DD' or datetime).
                     If None, uses current date.
            days_back: Number of days back from current date.
                      If None, uses default from config.
        
        Returns:
            Dictionary with zone codes as keys and DataFrames as values
        """
        # Set default zones if not provided
        if zones is None:
            zones = self.config['service'].get('default_zones', ['SE4'])
        
        # Set date range
        if end_date is None:
            end_date = datetime.now()
        elif isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_date is None:
            if days_back is None:
                days_back = self.config['service'].get('default_days_back', 7)
            start_date = end_date - timedelta(days=days_back)
        elif isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        logger.info(f"Fetching pricing data for zones {zones} from {start_date.date()} to {end_date.date()}")
        
        results = {}
        
        for zone in zones:
            try:
                results[zone] = self._fetch_zone_prices(zone, start_date, end_date)
                logger.info(f"Successfully fetched data for zone {zone}")
            except Exception as e:
                logger.error(f"Failed to fetch data for zone {zone}: {e}")
                results[zone] = None
        
        return results
    
    def _fetch_zone_prices(
        self, 
        zone: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Fetch pricing data for a specific zone.
        
        Args:
            zone: Zone code (e.g., 'SE4')
            start_date: Start date for data
            end_date: End date for data
        
        Returns:
            DataFrame with pricing data
        """
        if zone not in self.config['zones']:
            raise PricingServiceError(f"Zone {zone} not found in configuration")
        
        zone_config = self.config['zones'][zone]
        country_code = zone_config['code']
        timezone = zone_config['timezone']
        
        # Convert dates to pandas timestamps with timezone
        start_ts = pd.Timestamp(start_date, tz=timezone)
        end_ts = pd.Timestamp(end_date, tz=timezone)
        
        try:
            # Fetch day-ahead prices
            prices = self.client.query_day_ahead_prices(
                country_code=country_code,
                start=start_ts,
                end=end_ts
            )
            
            # Convert to DataFrame with additional columns
            df = pd.DataFrame({
                'timestamp': prices.index,
                'price_eur_mwh': prices.values,
                'zone': zone,
                'zone_name': zone_config['name']
            })
            
            # Add time-based columns if configured
            if self.config['service']['output'].get('include_time_columns', True):
                df['date'] = df['timestamp'].dt.date
                df['hour'] = df['timestamp'].dt.hour
                df['day_of_week'] = df['timestamp'].dt.day_name()
                df['weekday'] = df['timestamp'].dt.weekday
            
            logger.info(f"Fetched {len(df)} data points for zone {zone}")
            return df
            
        except Exception as e:
            raise PricingServiceError(f"Error fetching data for zone {zone}: {e}")
    
    def get_price_statistics(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate price statistics for a DataFrame.
        
        Args:
            df: DataFrame with pricing data
        
        Returns:
            Dictionary with statistics
        """
        if df is None or df.empty:
            return {}
        
        stats = {
            'count': len(df),
            'mean': df['price_eur_mwh'].mean(),
            'median': df['price_eur_mwh'].median(),
            'std': df['price_eur_mwh'].std(),
            'min': df['price_eur_mwh'].min(),
            'max': df['price_eur_mwh'].max(),
            'q25': df['price_eur_mwh'].quantile(0.25),
            'q75': df['price_eur_mwh'].quantile(0.75)
        }
        
        return {k: round(v, 2) if isinstance(v, float) else v for k, v in stats.items()}
    
    def save_data(
        self, 
        data: Dict[str, pd.DataFrame], 
        output_dir: str = "output",
        file_format: str = "csv"
    ) -> Dict[str, str]:
        """
        Save pricing data to files.
        
        Args:
            data: Dictionary with zone data
            output_dir: Output directory
            file_format: File format ('csv' or 'json')
        
        Returns:
            Dictionary with zone codes as keys and file paths as values
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        saved_files = {}
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for zone, df in data.items():
            if df is not None and not df.empty:
                filename = f"{zone}_prices_{timestamp}.{file_format}"
                filepath = output_path / filename
                
                try:
                    if file_format == 'csv':
                        df.to_csv(filepath, index=False)
                    elif file_format == 'json':
                        df.to_json(filepath, orient='records', date_format='iso')
                    else:
                        raise ValueError(f"Unsupported file format: {file_format}")
                    
                    saved_files[zone] = str(filepath)
                    logger.info(f"Saved {len(df)} records for zone {zone} to {filepath}")
                    
                except Exception as e:
                    logger.error(f"Failed to save data for zone {zone}: {e}")
        
        return saved_files


def main():
    """Main function to demonstrate the pricing service."""
    try:
        # Initialize the service
        service = PricingService()
        
        # Get available zones
        zones = service.get_available_zones()
        print(f"Available zones: {list(zones.keys())}")
        
        # Fetch pricing data for default zones
        data = service.fetch_prices()
        
        # Display results
        for zone, df in data.items():
            if df is not None:
                print(f"\n=== Zone: {zone} ===")
                print(f"Data points: {len(df)}")
                print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
                
                # Show statistics if configured
                if service.config['service']['output'].get('include_statistics', True):
                    stats = service.get_price_statistics(df)
                    print(f"Price statistics: {stats}")
                
                # Show sample data
                print("\nSample data:")
                print(df[['timestamp', 'price_eur_mwh', 'zone']].head())
            else:
                print(f"\n=== Zone: {zone} ===")
                print("Failed to fetch data")
        
        # Save data to files
        saved_files = service.save_data(data)
        print(f"\nSaved files: {saved_files}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
