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
    def transmission_delay(rate_mbps_list, num_ues):
        transmission_delay_list = []
        for rate_mbps in rate_mbps_list[0]:
            # Convert rate from Mbps to bps (1 Mbps = 10^6 bps)
            rate_bps = rate_mbps * 10**6 / num_ues
            transmission_delay_list.append(ChannelParameters.DATA_SIZE_BITS / rate_bps)
        
        # Calculate transmission delay in seconds
        return transmission_delay_list
    
    @staticmethod
    def get_distance(elevation_angle, satellite_height):
        elevation_angle_rad = math.radians(elevation_angle)
        EARTH_RADIUS_M = ChannelParameters.EARTH_RADIUS_KM * 1000  # in meters

        try:
            # Calculate the distance using the provided formula
            distance = math.sqrt((EARTH_RADIUS_M**2) * (math.sin(elevation_angle_rad)**2) + satellite_height**2 +
                                 2 * satellite_height * EARTH_RADIUS_M) - EARTH_RADIUS_M * math.sin(elevation_angle_rad)
        except ValueError:
            return None  # In case of math domain error
        
        return distance
    
    @staticmethod
    def within_range(observer_lat, observer_lon, satellite_lat, satellite_lon, range_m):
        """
        Determines if the satellite is within the given range from the observer.
        This method uses range for Low LEO, LEO, MEO, GEO based on input range_m.
        """
        range_km = range_m / 1000  # Convert range to kilometers
        delta_x = math.degrees(range_km / ChannelParameters.EARTH_RADIUS_KM)
        delta_y = delta_x * abs(math.cos(math.radians(observer_lat)))
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

    @staticmethod
    def multi_antenna_elevations(sat_height, beam_footprint):
        """
        Earth-Moving
        Computes elevation angles for hexagonal UE grid relative to satellite position.
        
        Generates UE positions in hexagonal pattern and calculates elevation angle
        from each position to satellite, accounting for Earth curvature.
        
        Args:
            lat1, lon1, lat2, lon2: Coordinate pairs (not directly used for geometry)
            sat_height: Satellite altitude in meters
            beam_footprint: Beam footprint size in meters
            
        Returns:
            List of elevation angles for all 19 grid positions
        """
        # Device coordinates origin (0,0,0)
        x_sat, y_sat, z_sat = 0, 0, sat_height

        # Angles for coordinate rings
        angles_ring1_3_deg = [0, 60, 120, 180, 240, 300]
        angles_ring2_deg   = [30, 90, 150, 210, 270, 330]

        # Convert to radians
        angles_ring1_3_rad = [math.radians(a) for a in angles_ring1_3_deg]
        angles_ring2_rad   = [math.radians(a) for a in angles_ring2_deg]

        # Radii of rings in meters
        radius_ring1 = beam_footprint
        radius_ring2 = (3/2) * beam_footprint
        radius_ring3 = 2 * beam_footprint

        # Generate coordinates around device
        coordinates = []
        coordinates.append((0, 0, 0))
        for angle in angles_ring1_3_rad:
            x = x_sat + radius_ring1 * math.cos(angle)
            y = y_sat + radius_ring1 * math.sin(angle)
            coordinates.append((x, y, 0))

        for angle in angles_ring2_rad:
            x = x_sat + radius_ring2 * math.cos(angle)
            y = y_sat + radius_ring2 * math.sin(angle)
            coordinates.append((x, y, 0))

        for angle in angles_ring1_3_rad:
            x = x_sat + radius_ring3 * math.cos(angle)
            y = y_sat + radius_ring3 * math.sin(angle)
            coordinates.append((x, y, 0))

        # Function to compute elevation angle between two 3D points
        def compute_geometric_elevation_flatplane(x_ground, y_ground, z_ground, x_sat, y_sat, z_sat):
            """

            Geometric elevation calculation with Earth curvature correction.
            """
            # Earth's radius in meters
            R = 6371000.0

            # Vector from device to satellite
            dx = x_sat - x_ground
            dy = y_sat - y_ground
            dz = z_sat - z_ground
            slant_range = math.sqrt(dx**2 + dy**2 + dz**2)

            # Approximate angle between local zenith (radial up) and slant vector
            # Local zenith is (0, 0, 1) in your flat coordinate frame
            cos_angle = dz / slant_range  # dot product with (0,0,1)

            # But correct it slightly to account for Earth's curvature:
            # Adjust satellite height based on angle from center
            ground_dist = math.sqrt(dx**2 + dy**2)  # horizontal flat distance
            angle_center = math.atan2(ground_dist, R)  # angle from Earth center to sat direction
            cos_correction = math.cos(angle_center)

            corrected_cos = cos_angle * cos_correction
            corrected_cos = min(1.0, max(-1.0, corrected_cos))  # safe clamp

            elevation_rad = math.asin(corrected_cos)
            return math.degrees(elevation_rad)
        
        # Compute elevation angles for all generated points relative to satellite
        results = []
        for coord in coordinates:
            elev_angle = compute_geometric_elevation_flatplane(coord[0], coord[1], coord[2], x_sat, y_sat, z_sat)
            results.append(elev_angle)

        return results

    @staticmethod
    def multi_antenna_distance(sat_height, beam_footprint):
        """
        Earth-Moving
        Computes slant ranges for beam central positions in hexagonal UE grid.
        
        Calculates direct line-of-sight distances from satellite to each center of
         the beam footprint coverage area.
        
        Args:
            lat1, lon1, lat2, lon2: Coordinate pairs (not directly used)
            sat_height: Satellite altitude in meters
            beam_footprint: Beam footprint size in meters
            
        Returns:
            List of slant ranges for all 19 grid positions
        """
        # Device coordinates origin (0,0,0)
        x_dev, y_dev, z_dev = 0, 0, 0

        sat_height_m = sat_height  # assume input in meters
        x_sat, y_sat, z_sat = 0, 0, sat_height_m

        # Angles for coordinate rings
        angles_ring1_3_deg = [0, 60, 120, 180, 240, 300]
        angles_ring2_deg   = [30, 90, 150, 210, 270, 330]

        # Convert to radians
        angles_ring1_3_rad = [math.radians(a) for a in angles_ring1_3_deg]
        angles_ring2_rad   = [math.radians(a) for a in angles_ring2_deg]

        # Radii of rings in meters
        radius_ring1 = beam_footprint
        radius_ring2 = (3/2) * beam_footprint
        radius_ring3 = 2 * beam_footprint

        # print(f"radii: ring1 ({radius_ring1:.2f}m), ring2 ({radius_ring2:.2f}m), ring3 ({radius_ring3:.2f}m)")

        # Generate coordinates around device
        coordinates = []
        coordinates.append((0, 0, 0))
        for angle in angles_ring1_3_rad:
            x = x_dev + radius_ring1 * math.cos(angle)
            y = y_dev + radius_ring1 * math.sin(angle)
            coordinates.append((x, y, 0))

        for angle in angles_ring2_rad:
            x = x_dev + radius_ring2 * math.cos(angle)
            y = y_dev + radius_ring2 * math.sin(angle)
            coordinates.append((x, y, 0))

        for angle in angles_ring1_3_rad:
            x = x_dev + radius_ring3 * math.cos(angle)
            y = y_dev + radius_ring3 * math.sin(angle)
            coordinates.append((x, y, 0))

        # Function to compute elevation angle between two 3D points
        def compute_slant_range(x1, y1, z1, x2, y2, z2):
            dx = x2 - x1
            dy = y2 - y1
            dz = z2 - z1
            slant_range = math.sqrt(dx**2 + dy**2 + dz**2)
            return slant_range

        # Compute elevation angles for all generated points relative to satellite
        results = []
        for coord in coordinates:
            slant_range = compute_slant_range(coord[0], coord[1], coord[2], x_sat, y_sat, z_sat)
            results.append(slant_range)

        return results
    
    @staticmethod
    def calculate_beam_rates(device_lat, device_lon, satellite_lat, satellite_lon, elevation_angle_list, slant_range_list,
                        eirp_gt, eirp_satellite, gain_to_noise_gt, gain_to_noise_satellite, frequency_dl, frequency_ul, bandwidth_dl, bandwidth_ul):
        """
        Computes uplink and downlink data rates for multiple link conditions.
        
        Processes lists of elevation angles and slant ranges through the Channel model
        to calculate achievable throughput for each beam position.
        
        Args:
            device_lat, device_lon: Ground station coordinates
            satellite_lat, satellite_lon: Satellite coordinates
            elevation_angle_list: List of elevation angles
            slant_range_list: List of corresponding slant ranges
            eirp_gt, eirp_satellite: Effective Isotropic Radiated Powers
            gain_to_noise_gt, gain_to_noise_satellite: G/T values
            frequency_dl, frequency_ul: Carrier frequencies in GHz
            bandwidth_dl, bandwidth_ul: Channel bandwidths in Hz
            
        Returns:
            Tuple of (uplink_rates_list, downlink_rates_list) in Mbps
        """
        
        ul_rate_list = []
        dl_rate_list = []

        for elevation_angle, slant_range in zip(elevation_angle_list, slant_range_list):

            # Instantiate the channel object
            comm_channel = Channel(device_lat, device_lon, satellite_lat, satellite_lon, slant_range, elevation_angle,
                                eirp_gt, eirp_satellite, gain_to_noise_gt, gain_to_noise_satellite, frequency_dl, frequency_ul, bandwidth_dl, bandwidth_ul)

            # Compute uplink and downlink rates in Mbps
            ul_rate = comm_channel.compute_ul_rate() / 10**6
            dl_rate = comm_channel.compute_dl_rate() / 10**6
            
            ul_rate_list.append(ul_rate)
            dl_rate_list.append(dl_rate)

        return ul_rate_list, dl_rate_list
    
    def calculate_ue_rate(device_lat, device_lon, satellite_lat, satellite_lon, elevation_angle, slant_range,
                        eirp_gt, eirp_satellite, gain_to_noise_gt, gain_to_noise_satellite, frequency_dl, frequency_ul, bandwidth_dl, bandwidth_ul):
        """
        Calculates uplink and downlink rates based on various parameters.
        """

        # Instantiate the channel object
        comm_channel = Channel(device_lat, device_lon, satellite_lat, satellite_lon, slant_range, elevation_angle,
                            eirp_gt, eirp_satellite, gain_to_noise_gt, gain_to_noise_satellite, frequency_dl, frequency_ul, bandwidth_dl, bandwidth_ul)

        # Compute uplink and downlink rates in Mbps
        ul_rate = comm_channel.compute_ul_rate() / 10**6
        dl_rate = comm_channel.compute_dl_rate() / 10**6

        ul_snr = comm_channel.get_snr_ul()
        dl_snr = comm_channel.get_snr_dl()

        return ul_rate, dl_rate, ul_snr, dl_snr

    @staticmethod
    def calculate_propagation_delay(slant_range_list):
        SPEED_OF_LIGHT = 3.0 * 10**8  # meters per second
        propagation_delay_list = []
        
        for slant_range in slant_range_list:
            propagration_delay = slant_range / SPEED_OF_LIGHT  # Propagation delay in seconds
            propagation_delay_list.append(propagration_delay)
        return propagation_delay_list

    @staticmethod
    def categorize_orbit(height):
        """
        Categorizes the orbit type based on the height of the satellite.
        """
        if 150000 <= height <= 750000:
            return 'Low LEO'
        elif 750000 < height <= 2000000:
            return 'LEO'
        elif 2000000 < height <= 35780000:
            return 'MEO'
        else:
            return 'Other'
