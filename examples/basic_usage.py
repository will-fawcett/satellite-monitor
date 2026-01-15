#!/usr/bin/env python3
"""Basic usage example for satellite-monitor.

This example shows how to use the satellite-monitor library
to check satellite availability with the default Brussels location.
"""

from satellite_monitor import SatelliteChecker, WeatherService


def main():
    # Create a satellite checker with default location (Brussels)
    checker = SatelliteChecker()

    # Display satellite availability and recommendations
    print("Running satellite checker...")
    checker.run()

    # You can also access data programmatically
    print("\n" + "=" * 50)
    print("Programmatic Access Example")
    print("=" * 50)

    # Get weather data
    weather_service = WeatherService()
    weather = weather_service.get_weather()

    print(f"\nCurrent weather at {checker.location.name}:")
    print(f"  Cloud cover: {weather.current_cloud_cover}%")
    print(f"  Conditions: {weather.current_conditions}")
    print(f"  Daylight: {weather.is_daylight}")

    # Get satellite data as JSON
    print("\nSatellite data available via checker.to_json()")

    # Access individual satellites
    print("\nAvailable satellites:")
    for name, data in list(checker.satellites.items())[:3]:
        cost = checker.calculate_cost(data)
        print(f"  {name}: {data['type']}, {data['resolution_m']}m, {cost}")


if __name__ == "__main__":
    main()
