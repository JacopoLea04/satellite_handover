from skyfield.api import load
from datetime import datetime
import numpy as np

from satellite import Satellite
from channel_parameters import ChannelParameters

import math


# =========================================================
#  FIND ALL SATELLITE WITHIN RANGE
# =========================================================
def find_candidate_satellite(lines, time, lat_ue, lon_ue, beam_footprint_m):

    candidates = []

    found_satellite = None
    found_coords = None
    found_altitude_m = None

    # TLEs are in blocks of 3 lines: NAME, LINE1, LINE2
    for i in range(0, len(lines) - 2, 3):
        satellite_name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        tle_data = (satellite_name, line1, line2)

        sat = Satellite(satellite_name, tle_data)
        sat_lat, sat_lon, sat_height_m = sat.get_position(time)

        within = ChannelParameters.within_range(
            lat_ue,
            lon_ue,
            sat_lat,
            sat_lon,
            beam_footprint_m * 5 / 1000
        )

        if within is not None:
            found_satellite = satellite_name
            found_coords = within
            found_altitude_m = sat_height_m
            elev_ue = ChannelParameters.elevation_angle_deg(lat_ue, lon_ue,sat_lat, sat_lon,sat_height_m)
            slant_ue = ChannelParameters.get_distance(elev_ue, sat_height_m)

            candidates.append((satellite_name, within, sat_height_m, elev_ue, slant_ue, sat))

    return candidates


# =========================================================
# SORT SATELLITES BY ELEVATION
# =========================================================
def sort_satellites_by_elevation(sat_data):
    sat_data.sort(key=lambda x: x[3], reverse=True)
    return sat_data

# =========================================================
# SORT SATELLITES BY SLANT RANGE AND ELEVATION (50/50 WEIGHT)
# =========================================================
def sort_satellites_weighted(candidates):
    if not candidates:
        return []
    
    # to avoi meaningless candidates
    candidates = [sat for sat in candidates if sat[3] >= 0 and sat[4] >= 0 and sat[4] < 5000*1e3]

    # 1. Extract elevations (index 3) and slant ranges (index 4) to find min/max
    elevs = [c[3] for c in candidates]
    slants = [c[4] for c in candidates]
    
    max_el, min_el = max(elevs), min(elevs)
    max_sl, min_sl = max(slants), min(slants)

    def calculate_score(target_tuple):
        _, _, _, el, sl, _ = target_tuple
        
        # Normalize Elevation (0 to 1) - Higher is better
        # Handle case where all elevations are the same to avoid division by zero
        norm_el = (el - min_el) / (max_el - min_el) if max_el != min_el else 1.0
        
        # Normalize Slant Range (0 to 1) - Lower is better, so we subtract from 1
        norm_sl = 1 - ((sl - min_sl) / (max_sl - min_sl)) if max_sl != min_sl else 1.0
        
        # Apply 50/50 Weights
        return (0.5 * norm_el) + (0.5 * norm_sl)

    # Sort the list based on the calculated score in descending order
    candidates.sort(key=calculate_score, reverse=True)
    return candidates