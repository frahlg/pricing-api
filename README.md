# ENTSO-E Electricity Pricing API Service

A Python service and REST API for fetching electricity pricing data from multiple European bidding zones using the ENTSO-E Transparency Platform API.

## 🚀 Features

- **Multi-zone support**: Fetch pricing data from Swedish, Norwegian, Danish, and other European bidding zones
- **YAML configuration**: Easy configuration management for API credentials and zones
- **REST API**: FastAPI-based backend service for team integration
- **Data export**: Save pricing data to CSV or JSON formats
- **Price statistics**: Automatic calculation of price statistics (mean, median, min, max, etc.)
- **Time-based analysis**: Includes hourly, daily, and weekly price patterns
- **Error handling**: Robust error handling and logging
- **Caching**: Optional in-memory cache to reduce repeated API calls
- **Interactive documentation**: Auto-generated API documentation with OpenAPI/Swagger

## 📋 Prerequisites

- Python 3.12+
- ENTSO-E Transparency Platform API token (free registration required)

## 🛠️ Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone <your-repo-url>
   cd pricing-api
   ```

2. **Install dependencies** using uv:
   ```bash
   uv sync
   ```

3. **Get your ENTSO-E API token**:
   - Register at [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
   - Go to Account Settings > Web API Security Token
   - Copy your token

4. **Configure the service**:
   - Edit `config.yaml` and replace the API token with your actual token
   - Customize zones and settings as needed

## ⚙️ Configuration

The service is configured via `config.yaml`:

```yaml
api:
  token: "your-api-token-here"  # Replace with your ENTSO-E token
  base_url: "https://web-api.tp.entsoe.eu/api"
  timeout: 30

zones:
  SE4:
    name: "Sweden - South"
    code: "SE_4"
    timezone: "Europe/Stockholm"
    description: "Southern Sweden bidding zone"
  # ... more zones

service:
  default_zones:
    - SE4
    - SE3
  default_days_back: 7
  cache:
    enabled: true  # Use in-memory caching
    ttl_minutes: 60  # Cache duration in minutes
  output:
    include_statistics: true
    include_time_columns: true
```

### Available Zones

The service supports multiple European bidding zones:

- **Swedish zones**: SE1 (North), SE2 (Central), SE3 (South-Central), SE4 (South)
- **Norwegian zones**: NO1 (Oslo), NO2 (Kristiansand), and more
- **Danish zones**: DK1 (West), DK2 (East)
- Easy to add more zones in the configuration

## 📖 Usage

### Command Line Service

Run the standalone pricing service:

```bash
# Using uv
uv run python pricing_service.py

# Or activate environment and run
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python pricing_service.py
```

### REST API Server

Start the FastAPI server:

```bash
# Using uv
uv run python pricing_api.py

# Or with uvicorn directly
uv run uvicorn pricing_api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Python Library Usage

```python
from pricing_service import PricingService

# Initialize service
service = PricingService("config.yaml")

# Get available zones
zones = service.get_available_zones()
print(f"Available zones: {list(zones.keys())}")

# Fetch pricing data for specific zones
data = service.fetch_prices(
    zones=['SE4', 'NO1'],
    days_back=7
)

# Get statistics
for zone, df in data.items():
    if df is not None:
        stats = service.get_price_statistics(df)
        print(f"Zone {zone}: {stats}")

# Save data to files
saved_files = service.save_data(data, output_dir="output", file_format="csv")
```

## 🌐 API Endpoints

### Get Available Zones
```
GET /zones
```
Returns information about all configured bidding zones.

### Get Prices for Multiple Zones
```
GET /prices?zones=SE4,NO1&days_back=7
```
Parameters:
- `zones`: Comma-separated zone codes
- `days_back`: Number of days back from current date (1-365)
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `include_statistics`: Include price statistics (true/false)

### Get Prices for Specific Zone
```
GET /zones/{zone}/prices?days_back=7
```

### Get Current/Latest Prices
```
GET /prices/current?zones=SE4,NO1
```

### Health Check
```
GET /health
```

## 📊 Example API Responses

### Zone Information
```json
{
  "SE4": {
    "name": "Sweden - South",
    "code": "SE_4",
    "timezone": "Europe/Stockholm",
    "description": "Southern Sweden bidding zone"
  }
}
```

### Price Data
```json
{
  "SE4": {
    "zone": "SE4",
    "zone_name": "Sweden - South",
    "data_points": 168,
    "date_range": {
      "start": "2024-01-01T00:00:00+01:00",
      "end": "2024-01-07T23:00:00+01:00"
    },
    "statistics": {
      "count": 168,
      "mean": 88.82,
      "median": 79.03,
      "std": 71.61,
      "min": 21.23,
      "max": 526.25
    },
    "data": [
      {
        "timestamp": "2024-01-01T00:00:00+01:00",
        "price_eur_mwh": 29.56,
        "zone": "SE4",
        "zone_name": "Sweden - South",
        "date": "2024-01-01",
        "hour": 0,
        "day_of_week": "Monday"
      }
    ]
  }
}
```

## 🔧 Development

### Project Structure
```
├── config.yaml              # Configuration file
├── pricing_service.py       # Core pricing service
├── pricing_api.py          # FastAPI REST API
├── get_prices.ipynb        # Original Jupyter notebook
├── pyproject.toml          # Project dependencies
└── README.md               # This file
```

### Adding New Zones

To add new bidding zones, edit `config.yaml`:

```yaml
zones:
  NEW_ZONE:
    name: "Zone Name"
    code: "ENTSOE_ZONE_CODE"  # From ENTSO-E documentation
    timezone: "Europe/Timezone"
    description: "Zone description"
```

### Error Handling

The service includes comprehensive error handling:
- Configuration validation
- API token validation
- Zone code validation
- Network error handling
- Data format validation

### Logging

The service uses Python's logging module. Logs include:
- Service initialization
- Data fetch operations
- Error details
- Performance metrics

## 🚀 Deployment

### Docker (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "pricing_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

For production, you can override config with environment variables:

```bash
export ENTSO_API_TOKEN="your-production-token"
export API_PORT="8000"
export LOG_LEVEL="INFO"
```

## 📝 Examples

### Get prices for Swedish zones for the last 3 days
```bash
curl "http://localhost:8000/prices?zones=SE1,SE2,SE3,SE4&days_back=3"
```

### Get current prices
```bash
curl "http://localhost:8000/prices/current"
```

### Get detailed statistics for a specific zone
```bash
curl "http://localhost:8000/zones/SE4/prices?days_back=7&include_statistics=true"
```

## 🤝 Team Integration

### For Frontend Developers
- Use the REST API endpoints to fetch pricing data
- All responses are in JSON format
- Interactive documentation available at `/docs`
- CORS is enabled for local development

### For Data Scientists
- Use the `PricingService` class directly in Python
- Data is returned as pandas DataFrames
- Export capabilities to CSV/JSON
- Built-in statistical analysis

### For DevOps
- Health check endpoint at `/health`
- Structured logging
- Environment variable support
- Docker-ready configuration

## 🔒 Security Notes

- **API Token**: Keep your ENTSO-E API token secure
- **Production**: Configure CORS properly for production
- **Rate Limits**: Be aware of ENTSO-E API rate limits
- **Environment**: Use environment variables for sensitive data in production

## 📚 Additional Resources

- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
- [ENTSO-E API Documentation](https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [pandas Documentation](https://pandas.pydata.org/docs/)

## 🐛 Troubleshooting

### Common Issues

1. **API Token Invalid**
   - Verify your token at ENTSO-E platform
   - Check token in `config.yaml`

2. **No Data Available**
   - Check if the zone code is correct
   - Verify date range (weekends might have limited data)
   - Some zones may have data delays

3. **Connection Issues**
   - Check internet connection
   - Verify ENTSO-E API is accessible
   - Check firewall settings

### Support

For team support, check:
1. API documentation at `/docs`
2. Service logs for error details
3. ENTSO-E platform status
4. This README file

---

*Last updated: January 2025*

