"""
ENTSO-E Electricity Pricing API Backend

A FastAPI backend service for fetching electricity pricing data from multiple bidding zones.
Provides REST endpoints for team members to access pricing data programmatically.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import traceback

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd

from pricing_service import PricingService, PricingServiceError, ConfigurationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ENTSO-E Electricity Pricing API",
    description="API for fetching electricity pricing data from multiple bidding zones",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pricing service
try:
    pricing_service = PricingService()
    logger.info("Pricing service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pricing service: {e}")
    pricing_service = None


# Pydantic models for API responses
class ZoneInfo(BaseModel):
    name: str
    code: str
    timezone: str
    description: str


class PriceData(BaseModel):
    timestamp: str
    price_eur_mwh: float
    zone: str
    zone_name: str
    date: Optional[str] = None
    hour: Optional[int] = None
    day_of_week: Optional[str] = None
    weekday: Optional[int] = None


class PriceStatistics(BaseModel):
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    q25: float
    q75: float


class ZonePriceResponse(BaseModel):
    zone: str
    zone_name: str
    data_points: int
    date_range: Dict[str, str]
    statistics: Optional[PriceStatistics] = None
    data: List[PriceData]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# API Endpoints

@app.get("/", summary="API Information")
async def root():
    """Get API information and status."""
    return {
        "name": "ENTSO-E Electricity Pricing API",
        "version": "1.0.0",
        "status": "running" if pricing_service else "error",
        "description": "API for fetching electricity pricing data from multiple bidding zones",
        "endpoints": {
            "zones": "/zones",
            "prices": "/prices",
            "zone_prices": "/zones/{zone}/prices",
            "docs": "/docs"
        }
    }


@app.get("/health", summary="Health Check")
async def health_check():
    """Health check endpoint."""
    if pricing_service is None:
        raise HTTPException(status_code=503, detail="Pricing service not available")
    
    try:
        zones = pricing_service.get_available_zones()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "available_zones": len(zones)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service health check failed: {e}")


@app.get("/zones", response_model=Dict[str, ZoneInfo], summary="Get Available Zones")
async def get_zones():
    """Get information about all available bidding zones."""
    if pricing_service is None:
        raise HTTPException(status_code=503, detail="Pricing service not available")
    
    try:
        zones = pricing_service.get_available_zones()
        return {
            zone_id: ZoneInfo(**zone_config) 
            for zone_id, zone_config in zones.items()
        }
    except Exception as e:
        logger.error(f"Error getting zones: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get zones: {e}")


@app.get("/zones/{zone}/prices", response_model=ZonePriceResponse, summary="Get Prices for Specific Zone")
async def get_zone_prices(
    zone: str = Path(..., description="Zone code (e.g., SE4, NO1)"),
    days_back: int = Query(7, ge=1, le=365, description="Number of days back from current date"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_statistics: bool = Query(True, description="Include price statistics")
):
    """Get pricing data for a specific bidding zone."""
    if pricing_service is None:
        raise HTTPException(status_code=503, detail="Pricing service not available")
    
    try:
        # Validate zone
        available_zones = pricing_service.get_available_zones()
        if zone not in available_zones:
            raise HTTPException(
                status_code=404, 
                detail=f"Zone '{zone}' not found. Available zones: {list(available_zones.keys())}"
            )
        
        # Fetch data
        data = pricing_service.fetch_prices(
            zones=[zone],
            start_date=start_date,
            end_date=end_date,
            days_back=days_back
        )
        
        df = data.get(zone)
        if df is None or df.empty:
            raise HTTPException(status_code=404, detail=f"No data available for zone {zone}")
        
        # Prepare response
        zone_config = available_zones[zone]
        
        # Convert DataFrame to list of PriceData
        price_data = []
        for _, row in df.iterrows():
            price_record = PriceData(
                timestamp=row['timestamp'].isoformat(),
                price_eur_mwh=row['price_eur_mwh'],
                zone=row['zone'],
                zone_name=row['zone_name']
            )
            
            # Add optional time columns if they exist
            if 'date' in row:
                price_record.date = str(row['date'])
            if 'hour' in row:
                price_record.hour = row['hour']
            if 'day_of_week' in row:
                price_record.day_of_week = row['day_of_week']
            if 'weekday' in row:
                price_record.weekday = row['weekday']
            
            price_data.append(price_record)
        
        # Calculate statistics if requested
        statistics = None
        if include_statistics:
            stats_dict = pricing_service.get_price_statistics(df)
            if stats_dict:
                statistics = PriceStatistics(**stats_dict)
        
        return ZonePriceResponse(
            zone=zone,
            zone_name=zone_config['name'],
            data_points=len(df),
            date_range={
                "start": df['timestamp'].min().isoformat(),
                "end": df['timestamp'].max().isoformat()
            },
            statistics=statistics,
            data=price_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prices for zone {zone}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get prices for zone {zone}: {e}")


@app.get("/prices", summary="Get Prices for Multiple Zones")
async def get_prices(
    zones: str = Query(..., description="Comma-separated zone codes (e.g., SE4,NO1,DK2)"),
    days_back: int = Query(7, ge=1, le=365, description="Number of days back from current date"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    include_statistics: bool = Query(True, description="Include price statistics")
):
    """Get pricing data for multiple bidding zones."""
    if pricing_service is None:
        raise HTTPException(status_code=503, detail="Pricing service not available")
    
    try:
        # Parse zone list
        zone_list = [zone.strip().upper() for zone in zones.split(',')]
        
        # Validate zones
        available_zones = pricing_service.get_available_zones()
        invalid_zones = [zone for zone in zone_list if zone not in available_zones]
        if invalid_zones:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid zones: {invalid_zones}. Available zones: {list(available_zones.keys())}"
            )
        
        # Fetch data
        data = pricing_service.fetch_prices(
            zones=zone_list,
            start_date=start_date,
            end_date=end_date,
            days_back=days_back
        )
        
        # Prepare response for each zone
        results = {}
        for zone in zone_list:
            df = data.get(zone)
            if df is None or df.empty:
                results[zone] = {
                    "error": f"No data available for zone {zone}",
                    "zone_name": available_zones[zone]['name']
                }
                continue
            
            # Convert DataFrame to list of PriceData
            price_data = []
            for _, row in df.iterrows():
                price_record = {
                    "timestamp": row['timestamp'].isoformat(),
                    "price_eur_mwh": row['price_eur_mwh'],
                    "zone": row['zone'],
                    "zone_name": row['zone_name']
                }
                
                # Add optional time columns if they exist
                if 'date' in row:
                    price_record['date'] = str(row['date'])
                if 'hour' in row:
                    price_record['hour'] = row['hour']
                if 'day_of_week' in row:
                    price_record['day_of_week'] = row['day_of_week']
                if 'weekday' in row:
                    price_record['weekday'] = row['weekday']
                
                price_data.append(price_record)
            
            # Calculate statistics if requested
            statistics = None
            if include_statistics:
                stats_dict = pricing_service.get_price_statistics(df)
                if stats_dict:
                    statistics = stats_dict
            
            results[zone] = {
                "zone": zone,
                "zone_name": available_zones[zone]['name'],
                "data_points": len(df),
                "date_range": {
                    "start": df['timestamp'].min().isoformat(),
                    "end": df['timestamp'].max().isoformat()
                },
                "statistics": statistics,
                "data": price_data
            }
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prices for zones {zones}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get prices: {e}")


@app.get("/prices/current", summary="Get Current/Latest Prices")
async def get_current_prices(
    zones: Optional[str] = Query(None, description="Comma-separated zone codes (default: all configured zones)")
):
    """Get the most recent available prices for zones."""
    if pricing_service is None:
        raise HTTPException(status_code=503, detail="Pricing service not available")
    
    try:
        # Parse zone list or use default zones
        if zones:
            zone_list = [zone.strip().upper() for zone in zones.split(',')]
        else:
            zone_list = pricing_service.config['service'].get('default_zones', ['SE4'])
        
        # Fetch data for the last day
        data = pricing_service.fetch_prices(
            zones=zone_list,
            days_back=1
        )
        
        # Get the latest price for each zone
        current_prices = {}
        for zone, df in data.items():
            if df is not None and not df.empty:
                latest_row = df.loc[df['timestamp'].idxmax()]
                current_prices[zone] = {
                    "zone": zone,
                    "zone_name": latest_row['zone_name'],
                    "timestamp": latest_row['timestamp'].isoformat(),
                    "price_eur_mwh": latest_row['price_eur_mwh'],
                    "hour": latest_row.get('hour'),
                    "date": str(latest_row.get('date'))
                }
            else:
                current_prices[zone] = {
                    "zone": zone,
                    "error": "No current data available"
                }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "current_prices": current_prices
        }
        
    except Exception as e:
        logger.error(f"Error getting current prices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get current prices: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 