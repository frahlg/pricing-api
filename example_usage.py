#!/usr/bin/env python3
"""
Example Usage of the ENTSO-E Pricing Service

This script demonstrates how to use the pricing service to fetch electricity
pricing data for different scenarios that team members might need.
"""

import asyncio
import requests
from datetime import datetime, timedelta
from pricing_service import PricingService

def example_basic_usage():
    """Example 1: Basic usage of the pricing service."""
    print("=== Example 1: Basic Pricing Service Usage ===")
    
    try:
        # Initialize the service
        service = PricingService("config.yaml")
        
        # Get available zones
        zones = service.get_available_zones()
        print(f"Available zones: {list(zones.keys())}")
        
        # Fetch pricing data for default zones (last 3 days)
        print("\nFetching pricing data for default zones (last 3 days)...")
        data = service.fetch_prices(days_back=3)
        
        # Display results
        for zone, df in data.items():
            if df is not None and not df.empty:
                print(f"\n--- Zone: {zone} ---")
                print(f"Data points: {len(df)}")
                print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
                
                # Show sample data
                print("\nSample data:")
                print(df[['timestamp', 'price_eur_mwh', 'hour']].head(3))
                
                # Show statistics
                stats = service.get_price_statistics(df)
                print(f"\nPrice statistics:")
                print(f"  Mean: {stats['mean']:.2f} EUR/MWh")
                print(f"  Min:  {stats['min']:.2f} EUR/MWh")
                print(f"  Max:  {stats['max']:.2f} EUR/MWh")
        
        return True
        
    except Exception as e:
        print(f"Error in basic usage example: {e}")
        return False


def example_specific_zones_and_dates():
    """Example 2: Fetch data for specific zones and date range."""
    print("\n=== Example 2: Specific Zones and Date Range ===")
    
    try:
        service = PricingService("config.yaml")
        
        # Fetch data for specific zones and date range
        zones = ['SE4', 'SE3']  # Southern Sweden zones
        start_date = '2024-01-01'
        end_date = '2024-01-07'
        
        print(f"Fetching data for zones {zones} from {start_date} to {end_date}")
        
        data = service.fetch_prices(
            zones=zones,
            start_date=start_date,
            end_date=end_date
        )
        
        # Compare zones
        print("\nComparing zones:")
        for zone, df in data.items():
            if df is not None and not df.empty:
                avg_price = df['price_eur_mwh'].mean()
                print(f"  {zone}: {avg_price:.2f} EUR/MWh average")
        
        # Save data to files
        saved_files = service.save_data(data, output_dir="output", file_format="csv")
        print(f"\nSaved files: {saved_files}")
        
        return True
        
    except Exception as e:
        print(f"Error in specific zones example: {e}")
        return False


def example_hourly_pattern_analysis():
    """Example 3: Analyze hourly price patterns."""
    print("\n=== Example 3: Hourly Price Pattern Analysis ===")
    
    try:
        service = PricingService("config.yaml")
        
        # Fetch data for the last week
        data = service.fetch_prices(zones=['SE4'], days_back=7)
        
        df = data.get('SE4')
        if df is not None and not df.empty:
            print(f"Analyzing hourly patterns for SE4 ({len(df)} data points)")
            
            # Calculate average price by hour
            hourly_avg = df.groupby('hour')['price_eur_mwh'].agg(['mean', 'min', 'max'])
            
            print("\nAverage prices by hour of day:")
            print("Hour  |  Avg   |  Min   |  Max")
            print("------|--------|--------|--------")
            for hour in range(24):
                if hour in hourly_avg.index:
                    row = hourly_avg.loc[hour]
                    print(f" {hour:2d}   | {row['mean']:6.2f} | {row['min']:6.2f} | {row['max']:6.2f}")
            
            # Find peak and off-peak hours
            peak_hour = hourly_avg['mean'].idxmax()
            off_peak_hour = hourly_avg['mean'].idxmin()
            print(f"\nPeak hour: {peak_hour}:00 ({hourly_avg.loc[peak_hour, 'mean']:.2f} EUR/MWh)")
            print(f"Off-peak hour: {off_peak_hour}:00 ({hourly_avg.loc[off_peak_hour, 'mean']:.2f} EUR/MWh)")
        
        return True
        
    except Exception as e:
        print(f"Error in hourly pattern analysis: {e}")
        return False


def example_api_requests():
    """Example 4: Using the REST API with HTTP requests."""
    print("\n=== Example 4: Using the REST API ===")
    
    base_url = "http://localhost:8000"
    
    try:
        # Check if API is running
        print("Checking API health...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✓ API is running")
        else:
            print("✗ API is not accessible. Start it with: uv run python pricing_api.py")
            return False
        
        # Get available zones
        print("\nGetting available zones...")
        response = requests.get(f"{base_url}/zones")
        if response.status_code == 200:
            zones = response.json()
            print(f"Available zones: {list(zones.keys())}")
        
        # Get prices for a specific zone
        print("\nGetting prices for SE4 (last 3 days)...")
        response = requests.get(f"{base_url}/zones/SE4/prices?days_back=3&include_statistics=true")
        if response.status_code == 200:
            data = response.json()
            print(f"Zone: {data['zone_name']}")
            print(f"Data points: {data['data_points']}")
            print(f"Date range: {data['date_range']['start']} to {data['date_range']['end']}")
            
            if data['statistics']:
                stats = data['statistics']
                print(f"Average price: {stats['mean']:.2f} EUR/MWh")
                print(f"Price range: {stats['min']:.2f} - {stats['max']:.2f} EUR/MWh")
        
        # Get current prices
        print("\nGetting current prices...")
        response = requests.get(f"{base_url}/prices/current")
        if response.status_code == 200:
            data = response.json()
            print("Current prices:")
            for zone, price_info in data['current_prices'].items():
                if 'price_eur_mwh' in price_info:
                    print(f"  {zone}: {price_info['price_eur_mwh']:.2f} EUR/MWh at {price_info['timestamp']}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"API request error: {e}")
        print("Make sure the API server is running: uv run python pricing_api.py")
        return False
    except Exception as e:
        print(f"Error in API example: {e}")
        return False


async def example_async_api_usage():
    """Example 5: Asynchronous API usage (for high-performance applications)."""
    print("\n=== Example 5: Asynchronous API Usage ===")
    
    import aiohttp
    
    base_url = "http://localhost:8000"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Fetch multiple zones in parallel
            zones = ['SE1', 'SE2', 'SE3', 'SE4']
            tasks = []
            
            for zone in zones:
                url = f"{base_url}/zones/{zone}/prices?days_back=1&include_statistics=true"
                tasks.append(session.get(url))
            
            print(f"Fetching data for {len(zones)} zones in parallel...")
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"  {zones[i]}: Error - {response}")
                else:
                    if response.status == 200:
                        data = await response.json()
                        stats = data.get('statistics', {})
                        mean_price = stats.get('mean', 0)
                        print(f"  {zones[i]}: {mean_price:.2f} EUR/MWh average")
                    else:
                        print(f"  {zones[i]}: HTTP {response.status}")
        
        return True
        
    except ImportError:
        print("aiohttp not installed. Install with: uv add aiohttp")
        return False
    except Exception as e:
        print(f"Error in async API example: {e}")
        return False


def main():
    """Run all examples."""
    print("ENTSO-E Pricing Service - Usage Examples")
    print("=" * 50)
    
    examples = [
        example_basic_usage,
        example_specific_zones_and_dates,
        example_hourly_pattern_analysis,
        example_api_requests,
    ]
    
    success_count = 0
    
    for example in examples:
        try:
            if example():
                success_count += 1
        except Exception as e:
            print(f"Example failed with error: {e}")
    
    # Run async example separately
    try:
        if asyncio.run(example_async_api_usage()):
            success_count += 1
    except Exception as e:
        print(f"Async example failed: {e}")
    
    print(f"\n=== Summary ===")
    print(f"Successfully ran {success_count}/5 examples")
    
    if success_count < 5:
        print("\nTroubleshooting tips:")
        print("1. Make sure you have a valid API token in config.yaml")
        print("2. Check your internet connection")
        print("3. For API examples, start the server: uv run python pricing_api.py")
        print("4. Install missing dependencies: uv sync")


if __name__ == "__main__":
    main()
