from skyfield.api import load
from datetime import datetime, timedelta
import numpy as np

from satellite import Satellite
from channel_parameters import ChannelParameters

import math

import utils

# =========================================================
# 1. LOAD TLE FILE
# =========================================================
with open('Starlink_TLE.txt', 'r') as f:
    lines = [l.strip() for l in f.readlines()]

beam_footprint_m = 200_000  # 200 km

# Simulation time
time = datetime(2025, 6, 8, 0, 0, 0) # year, month, day, hour, minute, second
outer_time = datetime(2025, 6, 8, 1, 0, 0)

# =========================================================
# 2. UE LOCATION AND SYSTEM PARAMETERS
# =========================================================
lat_ue, lon_ue = 45.4384, 11.0086  # Verona

# eirp_gt = 45.01            # UL EIRP [dBW]
# gt_sat = 5.0               # UL G/T satellite
# eirp_sat = 36.02           # DL EIRP [dBW]
# gt_ue = 21.44              # DL G/T UE
# bandwidth = 400e6          # 400 MHz


eirp_gt = -10            # UL EIRP [dBW]
gt_sat = 1.1              # UL G/T satellite
eirp_sat = 48.8          # DL EIRP [dBW]
gt_ue = -31.6             # DL G/T UE
bandwidth = 30e6          # 400 MHz

HANDOVER_FLAG = 5 # dB (DL SNR)


print(f"UE Location: Lat {lat_ue}°  Lon {lon_ue}°")
print(f"System Parameters at S Band:")
print(f"  UL EIRP: {eirp_gt} dBW")
print(f"  UL G/T Satellite: {gt_sat} dB/K")
print(f"  DL EIRP Satellite: {eirp_sat} dBW")
print(f"  DL G/T UE: {gt_ue} dB/K")
print(f"  Bandwidth: {bandwidth/1e6} MHz")
print(f"  Handover SNR Threshold: {HANDOVER_FLAG} dB")


while True:
    if time > outer_time:
        break
    # =========================================================
    # 3. FIND CANDIDATE SATELLITES WITHIN RANGE
    # =========================================================
    candidates = utils.find_candidate_satellite(lines, time, lat_ue, lon_ue, beam_footprint_m)
    candidates = utils.sort_satellites_weighted(candidates)


    # =========================================================
    # 4. SELECT BEST SATELLITE AND CONNECT TO IT
    # =========================================================
    best_satellite = candidates[0]
    print("Connect to satellite:", best_satellite[0])
    print(f"  Lat: {best_satellite[1][0]:.3f}°  Lon: {best_satellite[1][1]:.3f}° Alt: {best_satellite[2]/1000:.2f} km")
    print(f"  Elevation angle: {best_satellite[3]:.2f}°")
    print(f"  Slant range: {best_satellite[4]/1000:.2f} km\n")


    # =========================================================
    # 5. CONSTANT MONITOR & HANDOVER
    # =========================================================
    handover_event = False
    sat_lat, sat_lon = best_satellite[1]
    sat_height_m = best_satellite[2]
    elevation = best_satellite[3]
    slant_range = best_satellite[4]
    sat = best_satellite[5]

    while not handover_event:
        # increase time by delta
        time += timedelta(seconds=10)

        # update values for the current time
        sat_lat, sat_lon, sat_height_m = sat.get_position(time)
        elevation = ChannelParameters.elevation_angle_deg(lat_ue, lon_ue,sat_lat, sat_lon,sat_height_m)
        slant_range = ChannelParameters.get_distance(elevation, sat_height_m)


        ul_rate, dl_rate, ul_snr, dl_snr = ChannelParameters.calculate_ue_rate(
            lat_ue, lon_ue,
            sat_lat, sat_lon,
            elevation,
            slant_range,
            eirp_gt, 
            eirp_sat,
            gt_ue,
            gt_sat,
            bandwidth
        )

        print(f"Time: {time}  elevation: {elevation:.2f}°   DL SNR: {dl_snr:.2f} dB ")
        if dl_snr < HANDOVER_FLAG:
            print(f"\n Time: {time}  Handover event triggered! DL SNR below threshold.\n")
            handover_event = True
