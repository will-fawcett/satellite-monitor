# Satellite Monitor

This tool will tell you what satellite imagery is available for a location of your choice. It checks multiple satellite operators, and lists recent and upcoming image captures. 
If configured with a weather API key, it will also check current cloud cover and visibility conditions, and provide smart recommendations on which satellites to use based on the weather -- for example, optical imagery will not be useful if there is heavy cloud cover!



## Key Features

- **Weather-Aware Recommendations**: Automatically checks cloud cover and recommends suitable satellites
- **Cost Optimization**: From FREE (Sentinel) to $10,000+ (commercial SAR) per image
- **Multi-Provider Support**: ESA, Maxar, Planet Labs, Airbus, BlackSky, ICEYE, Capella
- **Real-time Availability**: Shows when the next satellite pass will occur
- **Any Location**: Works for any coordinates, not just Brussels
- **Smart Weather Integration**: Knows when optical won't work and suggests SAR alternatives

## Installation

### From PyPI

```bash
pip install satellite-monitor
```

### From Source

```bash
git clone https://github.com/trillium/satellite-monitor.git
cd satellite-monitor
pip install -e .
```

### Optional Dependencies

```bash
# For Sentinel data download
pip install satellite-monitor[sentinel]

# For orbit calculations
pip install satellite-monitor[orbit]

# All optional features
pip install satellite-monitor[all]
```

## Quick Start

### Command Line

```bash
# Check satellite availability (default: Brussels)
satellite-monitor check

# Use a named location (60+ presets available)
satellite-monitor --location London check
satellite-monitor -l "New York" check
satellite-monitor -l Tokyo recommend

# Or use exact coordinates
satellite-monitor --lat 48.8566 --lon 2.3522 check

# List all preset locations
satellite-monitor locations

# Get weather-aware recommendations with constraints
satellite-monitor recommend --budget 1000 --resolution 1.0

# Download Sentinel data (requires Copernicus account)
satellite-monitor download --days 14 --dry-run

# Configure weather APIs for real cloud data
satellite-monitor setup

# Run interactive demo
satellite-monitor demo
```

### Python API

```python
from satellite_monitor import (
    Location,
    SatelliteChecker,
    SmartSatelliteAdvisor,
    resolve_location,
)

# Use default location (Brussels)
checker = SatelliteChecker()
checker.run()

# Use a preset location by name
london = resolve_location("London")
checker = SatelliteChecker(location=london, area_sqkm=150)
checker.run()

# Or create custom location with coordinates
paris = Location(name="Paris", latitude=48.8566, longitude=2.3522)
checker = SatelliteChecker(location=paris, area_sqkm=150)
checker.run()

# Geocode any location via OpenStreetMap
remote = resolve_location("Reykjavik, Iceland")  # Works for any place!
checker = SatelliteChecker(location=remote)
checker.run()

# Get programmatic recommendations
advisor = SmartSatelliteAdvisor(location=paris)
weather = advisor.weather_service.get_weather()
recommendations = advisor.get_recommendations(
    weather,
    max_budget=1000,
    min_resolution=5.0
)

for rec in recommendations[:3]:
    print(f"{rec.satellite_name}: {rec.score:.0f} score, {rec.cost}")
```

## Example Output

```
Satellite Image Availability for Brussels | Cloud Cover: 75%

Satellite     Provider        Type     Resolution  Weather OK  Next Image  Cost
--------------------------------------------------------------------------------
Sentinel-1    ESA Copernicus  SAR      5m          yes         in 2d       FREE
Sentinel-2    ESA Copernicus  Optical  10m         no          in 3d       FREE
PlanetScope   Planet Labs     Optical  3m          no          in 20h      $250
ICEYE         ICEYE           SAR      0.25m       yes         in 14h      $10,000

Smart Recommendations
Current cloud cover: 75% (Mostly cloudy)

POOR CONDITIONS for optical satellites
   Optical satellites will not work well
   MUST use SAR satellites:
   Sentinel-1 (FREE) - 5m SAR
   Capella ($8,000) - 0.5m SAR
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `satellite-monitor check` | Check current satellite availability |
| `satellite-monitor recommend` | Get weather-aware recommendations |
| `satellite-monitor download` | Download Sentinel imagery |
| `satellite-monitor setup` | Configure weather API keys |
| `satellite-monitor locations` | List available preset locations |
| `satellite-monitor demo` | Run interactive demonstration |

### Global Options

| Option | Description |
|--------|-------------|
| `-l, --location TEXT` | Named location (e.g., "London", "Paris", "Tokyo") |
| `--lat FLOAT` | Latitude of target location |
| `--lon FLOAT` | Longitude of target location |
| `--area-km FLOAT` | Coverage area in km² (default: 100) |

### Location Resolution

Locations are resolved in this priority order:
1. **Explicit coordinates** (`--lat`/`--lon`) - Use exact coordinates
2. **Named location** (`--location`) - Tries preset first, then geocoding
3. **Default** - Brussels

The `--location` option supports:
- **60+ preset cities** - Instant lookup, no network needed (e.g., London, Paris, Tokyo, New York)
- **Any place name** - Falls back to OpenStreetMap Nominatim geocoding (e.g., "Reykjavik", "Auckland Airport")

## Satellite Options

### Free Satellites

- **Sentinel-1** (ESA): 5m SAR, works through clouds, 6-day revisit
- **Sentinel-2** (ESA): 10m optical, requires clear weather, 5-day revisit
- **Landsat-9** (USGS): 30m optical, 16-day revisit

### Commercial Satellites

**Budget Options ($250-500/image)**
- PlanetScope: 3m optical, daily
- BlackSky: 1m optical, sub-daily

**Premium Options ($1,000-3,000/image)**
- SkySat: 0.5m optical
- WorldView-3: 0.31m optical
- Pleiades-Neo: 0.3m optical

**SAR - All Weather ($8,000-10,000/image)**
- Capella: 0.5m SAR
- ICEYE: 0.25m SAR

## Weather Decision Logic

| Cloud Cover | Daylight | Recommendation | Best Choice |
|-------------|----------|----------------|-------------|
| < 30% | Yes | **Excellent** for optical | FREE Sentinel-2 or PlanetScope |
| 30-60% | Yes | **Moderate** for optical | Consider SAR or high-quality optical |
| > 60% | Yes | **Poor** for optical | Must use SAR (Sentinel-1 FREE) |
| Any | No | **Impossible** for optical | Only SAR satellites work |

## Weather API Setup

For accurate cloud cover data, configure a free weather API:

```bash
satellite-monitor setup
```

Supported APIs:
- **OpenWeatherMap**: 1,000 calls/day free - https://openweathermap.org/api
- **WeatherAPI.com**: 1M calls/month free - https://www.weatherapi.com/

Without API keys, the system uses simulated weather data.

## Downloading Sentinel Data

To download actual satellite images (FREE):

1. Register at [Copernicus Hub](https://scihub.copernicus.eu/dhus/#/self-registration)

2. Set credentials:
```bash
export COPERNICUS_USERNAME="your_username"
export COPERNICUS_PASSWORD="your_password"
```

3. Download:
```bash
# Search only (dry run)
satellite-monitor download --dry-run

# Download with custom parameters
satellite-monitor download --days 14 --cloud-max 15 --max-products 5
```

## Advanced Usage

### Watch Mode

Continuous monitoring with updates every minute:

```bash
satellite-monitor check --watch
```

### JSON Output

For automation and scripting:

```bash
satellite-monitor check --json
satellite-monitor recommend --json
```

### Custom Location with Constraints

```bash
# Using named location
satellite-monitor -l London recommend \
    --budget 500 \
    --resolution 1.0 \
    --urgent 24

# Using coordinates
satellite-monitor --lat 51.5074 --lon -0.1278 recommend \
    --budget 500 \
    --resolution 1.0 \
    --urgent 24
```

## Cost Savings Example

Weather awareness can save thousands:

- **Without weather info**: Order $2,500 optical imagery on cloudy day = **Wasted money**
- **With weather info**: System says "Use FREE Sentinel-1 SAR instead" = **$2,500 saved**

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/satellite_monitor
```

## License

MIT License. Sentinel data is provided free by ESA under the Copernicus programme.

## Resources

- **Copernicus Hub**: https://scihub.copernicus.eu/
- **OpenWeatherMap API**: https://openweathermap.org/api
- **Sentinel Documentation**: https://sentinel.esa.int/
