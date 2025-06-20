import pandas as pd
import yaml
from pricing_service import PricingService


def test_fetch_prices(monkeypatch, tmp_path):
    # Create a temporary configuration file
    config = {
        "api": {
            "token": "dummy-token",
        },
        "zones": {
            "SE4": {
                "name": "Sweden - South",
                "code": "SE_4",
                "timezone": "Europe/Stockholm",
                "description": "Southern Sweden bidding zone",
            }
        },
        "service": {
            "default_zones": ["SE4"],
            "default_days_back": 7,
            "output": {
                "include_statistics": True,
                "include_time_columns": True,
            },
        },
    }
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.safe_dump(config))

    # Replace API client initialization with a dummy object
    monkeypatch.setattr(PricingService, "_initialize_client", lambda self: object())

    # Mock _fetch_zone_prices to avoid real API calls
    def fake_fetch(self, zone, start, end):
        return pd.DataFrame({
            "timestamp": [pd.Timestamp("2024-01-01T00:00:00+01:00")],
            "price_eur_mwh": [50.0],
            "zone": [zone],
            "zone_name": [self.config["zones"][zone]["name"]],
        })

    monkeypatch.setattr(PricingService, "_fetch_zone_prices", fake_fetch)

    service = PricingService(str(config_file))
    data = service.fetch_prices(zones=["SE4"])  # Should use mocked method

    assert "SE4" in data
    df = data["SE4"]
    assert not df.empty
    assert df.iloc[0]["price_eur_mwh"] == 50.0

