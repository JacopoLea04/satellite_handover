import math
import random
from satellite import Satellite
from datetime import datetime, timedelta
import os
from skyfield.api import load, EarthSatellite
import pandas as pd
import numpy as np
from channel import Channel


class ChannelParameters:
    EARTH_RADIUS_KM = 6371.0    # Radius of Earth in kilometers
    DATA_SIZE_BITS = 80000      # bits
    
    @staticmethod
    def within_range(observer_lat, observer_lon, satellite_lat, satellite_lon, range_m):
        """
        Determines if the satellite is within the given range from the observer.
        This method uses range for Low LEO, LEO, MEO, GEO based on input range_m.
        """
        range_km = range_m / 1000  # Convert range to kilometers
        delta_x = math.degrees(range_km / ChannelParameters.EARTH_RADIUS_KM)
        delta_y = delta_x / abs(math.cos(math.radians(observer_lat)))
        # print("\n=== ChannelParameters::within_range ===")
        # print("range_km: {:.2f} km".format(range_km))
        # print("\nChecking satellite at ({:.4f}, {:.4f}) against observer at ({:.4f}, {:.4f}) with range {:.2f} km".format(satellite_lat, satellite_lon, observer_lat, observer_lon, range_km))
        # print("Calculated deltas: delta_x = {:.4f} degrees, delta_y = {:.4f} degrees".format(delta_x, delta_y))

        if observer_lat - delta_x < satellite_lat < observer_lat + delta_x:
            if observer_lon - delta_y < satellite_lon < observer_lon + delta_y:
                return satellite_lat, satellite_lon
        return None

    @staticmethod
    def elevation_angle_deg(device_lat, device_lon, satellite_lat, satellite_lon, satellite_height):
        """
        Calculates the elevation angle in degrees between the observer and the satellite.
        """
        satellite_lat_rad = math.radians(satellite_lat)
        satellite_lon_rad = math.radians(satellite_lon)
        satellite_height += ChannelParameters.EARTH_RADIUS_KM * 1000  # Convert to meters
        observer_lat_rad = math.radians(device_lat)
        observer_lon_rad = math.radians(device_lon)
        observer_height = ChannelParameters.EARTH_RADIUS_KM * 1000  # Convert to meters

        gamma = math.acos(
            math.cos(observer_lat_rad) * math.cos(satellite_lat_rad) * math.cos(satellite_lon_rad - observer_lon_rad)
            + math.sin(observer_lat_rad) * math.sin(satellite_lat_rad)
        )

        radius_ratio = observer_height / satellite_height
        cos_elevation_angle = math.sin(gamma) / math.sqrt(1 + radius_ratio**2 - 2 * radius_ratio * math.cos(gamma))

        elevation_angle = math.acos(cos_elevation_angle)
        return math.degrees(elevation_angle)