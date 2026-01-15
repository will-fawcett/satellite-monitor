"""Satellite monitoring and recommendation modules."""

from .advisor import SmartSatelliteAdvisor
from .checker import QuickSatelliteChecker, SatelliteChecker
from .monitor import SatelliteMonitor

__all__ = [
    "SatelliteChecker",
    "QuickSatelliteChecker",  # Backwards compatibility alias
    "SatelliteMonitor",
    "SmartSatelliteAdvisor",
]
