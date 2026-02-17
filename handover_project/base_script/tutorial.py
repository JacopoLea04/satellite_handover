from skyfield.api import load
from datetime import datetime
import numpy as np

from satellite import Satellite
from channel_parameters import ChannelParameters

import math
from datetime import datetime

# =========================================================
# 1. LOAD TLE FILE
# =========================================================
with open('Starlink_TLE.txt', 'r') as f:
    lines = [l.strip() for l in f.readlines()]

beam_footprint_m = 200_000  # 200 km

# Simulation time
time = datetime(2025, 6, 8, 0, 0, 0) # year, month, day, hour, minute, second

# =========================================================
# 2. UE LOCATION
# =========================================================
lat_ue, lon_ue = 45.4384, 11.0086  # Verona
print(f"\nUE location: ({lat_ue}, {lon_ue})")

# =========================================================
# 3. FIND FIRST SATELLITE WITHIN RANGE
# =========================================================
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
        beam_footprint_m * 5
    )

    if within is not None:
        found_satellite = satellite_name
        found_coords = within
        found_altitude_m = sat_height_m
        break   # FIRST satellite only

# =========================================================
# 4. RESULT
# =========================================================
if found_satellite is not None:
    print(f"\nSatellite loaded: {found_satellite}")
    print("Satellite position:")
    print(f"  Lat: {found_coords[0]:.3f}°")
    print(f"  Lon: {found_coords[1]:.3f}°")
    print(f"  Altitude: {found_altitude_m / 1000:.0f} km")
else:
    print("\nNo satellite within range.")

# =========================================================
# 5. LINK BUDGET PARAMETERS (SC9)
# =========================================================
eirp_gt = -7                # UL EIRP [dBW]
gt_sat = 1.1                # UL G/T satellite [dB/K]
eirp_sat = 48.8             # DL EIRP [dBW]
gt_ue = -31.6               # DL G/T UE [dB/K]
bandwidth_dl = 30e6         # 30 MHz DL bandwidth [MHz]
bandwidth_ul = 0.4e6        # UL bandwidth [MHz]
frequency_dl = 2            # DL carrier frequency [GHz]
frequency_ul = 2            # UL carrier frequency [GHz]

print("\nLink budget parameters loaded")

# =========================================================
# 6. UE TO SATELLITE GEOMETRY
# =========================================================
print("\n=== UE–SATELLITE GEOMETRY CHECK ===")

elev_ue = ChannelParameters.elevation_angle_deg(
    lat_ue, lon_ue,
    sat_lat, sat_lon,
    sat_height_m
)

slant_ue = ChannelParameters.get_distance(elev_ue, sat_height_m)

print(f"Elevation angle: {elev_ue:.2f} deg")
print(f"Slant range: {slant_ue/1000:.2f} km")

# =========================================================
# 7. ELEVATION ANGLES OVER FOOTPRINT
# =========================================================
print("\n=== ELEVATION ANGLES ===")

elevations = ChannelParameters.multi_antenna_elevations(
    sat_height_m,
    beam_footprint_m
)

print(f"Elevation angles (deg):")
print(f"  Center: {elevations[0]:.2f}")
print(f"  Min: {min(elevations):.2f}  Max: {max(elevations):.2f}")


# =========================================================
# 8. SLANT RANGES OVER FOOTPRINT
# =========================================================
print("\n=== SLANT RANGES ===")

slant_ranges = ChannelParameters.multi_antenna_distance(
    sat_height_m,
    beam_footprint_m
)

print(f"Slant ranges (km):")
print(f"  Min: {min(slant_ranges)/1000:.2f}")
print(f"  Max: {max(slant_ranges)/1000:.2f}")

# =========================================================
# 9. PER-BEAM UL / DL RATES
# =========================================================
print("\n=== PER-BEAM DATA RATES ===")

ul_rates, dl_rates = ChannelParameters.calculate_beam_rates(
    lat_ue, lon_ue,
    sat_lat, sat_lon,
    elevations,
    slant_ranges,
    eirp_gt,
    eirp_sat,
    gt_ue,
    gt_sat,
    frequency_dl,
    frequency_ul,
    bandwidth_dl,
    bandwidth_ul
)

print(f"UL rates (Mbps): {np.round(ul_rates, 2)}")
print(f"DL rates (Mbps): {np.round(dl_rates, 2)}")


# =========================================================
# 10. SINGLE UE DETAILED LINK (CENTER BEAM)
# =========================================================
print("\n=== CENTER UE LINK DETAILS ===")

ul_rate, dl_rate, ul_snr, dl_snr = ChannelParameters.calculate_ue_rate(
    lat_ue, lon_ue,
    sat_lat, sat_lon,
    elevations[0],
    slant_ranges[0],
    eirp_gt,
    eirp_sat,
    gt_ue,
    gt_sat,
    frequency_dl,
    frequency_ul,
    bandwidth_dl,
    bandwidth_ul
)

print(f"UL rate: {ul_rate:.2f} Mbps   SNR: {ul_snr:.2f} dB")
print(f"DL rate: {dl_rate:.2f} Mbps   SNR: {dl_snr:.2f} dB")


# =========================================================
# 11. PROPAGATION & TRANSMISSION DELAYS
# =========================================================
print("\n=== DELAYS ===")

prop_delays = ChannelParameters.calculate_propagation_delay(slant_ranges)
print(f"Propagation delay (center): {prop_delays[0]*1e3:.2f} ms")

num_ues = 10 # number of UEs

tx_delays = ChannelParameters.transmission_delay([dl_rates], num_ues)
print(f"Transmission delay (center UE): {tx_delays[0]*1e3:.3f} ms")


# =========================================================
# 12. ORBIT CLASSIFICATION
# =========================================================
print("\n=== ORBIT CATEGORY ===")
print(f"Orbit type: {ChannelParameters.categorize_orbit(sat_height_m)}")