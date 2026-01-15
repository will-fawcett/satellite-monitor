#!/usr/bin/env python3
"""Example using a custom location with satellite-monitor.

This example shows how to monitor satellites for any location,
not just the default Brussels.
"""

from satellite_monitor import (
    Area,
    Location,
    SatelliteChecker,
    SmartSatelliteAdvisor,
    WeatherService,
)


def main():
    # Define a custom location (Paris)
    paris = Location(
        name="Paris",
        latitude=48.8566,
        longitude=2.3522,
        elevation_m=35
    )

    # You can also create from coordinates
    london = Location.from_coordinates(
        latitude=51.5074,
        longitude=-0.1278,
        name="London"
    )

    # Create an area from a center point
    paris_area = Area.from_center(
        name="Paris Metro",
        latitude=paris.latitude,
        longitude=paris.longitude,
        radius_km=20
    )

    print(f"Monitoring location: {paris.name}")
    print(f"  Coordinates: {paris.latitude}, {paris.longitude}")
    print(f"  Coverage area: ~{paris_area.area_sqkm:.0f} km2")
    print()

    # Create a checker for the custom location
    checker = SatelliteChecker(location=paris, area_sqkm=paris_area.area_sqkm)

    # Get weather for this location
    weather_service = WeatherService(location=paris)
    weather = weather_service.get_weather()

    print(f"Weather in {paris.name}:")
    print(f"  Cloud cover: {weather.current_cloud_cover}%")
    print(f"  Conditions: {weather.current_conditions}")
    print()

    # Get smart recommendations
    advisor = SmartSatelliteAdvisor(location=paris, area_sqkm=paris_area.area_sqkm)
    recommendations = advisor.get_recommendations(
        weather,
        max_budget=1000,  # USD
        min_resolution=5.0  # meters
    )

    print("Top 3 satellite recommendations:")
    for i, rec in enumerate(recommendations[:3], 1):
        print(f"  {i}. {rec.satellite_name} ({rec.provider})")
        print(f"     Score: {rec.score:.0f}, Quality: {rec.estimated_quality}")
        print(f"     Cost: {rec.cost}, ETA: {rec.eta_hours:.0f}h")
        print(f"     Weather suitable: {rec.weather_suitable}")
        print()

    # Run the full display
    print("=" * 50)
    print("Full satellite availability display:")
    print("=" * 50)
    checker.run()


if __name__ == "__main__":
    main()
