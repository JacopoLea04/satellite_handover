from skyfield.api import load
from datetime import datetime, timedelta
import numpy as np
import random

from satellite import Satellite
from channel_parameters import ChannelParameters

import math
import csv
import pandas as pd


def get_visible_satellites(df, service_sats, target_time):
    """
    Filters a pandas DataFrame and returns a list of tuples containing satellite 
    information for a specific datetime.
    """
    satellites = []
    
    # Check if target_time is a datetime object and format it to match the DataFrame
    if isinstance(target_time, datetime):
        # Formats to "YYYY-MM-DD HH:MM:SS" (e.g., "2025-06-08 00:00:00")
        target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Fallback just in case you pass a string directly
        target_time_str = str(target_time)
    
    try:
        # 1. Filter the DataFrame
        # .astype(str) ensures it safely compares strings, even if pandas 
        # auto-converted your time column to datetime objects when loading the CSV.
        matched_data = df[df['time'].astype(str) == target_time_str]
        
        # 2. Iterate through the matching rows
        for index, row in matched_data.iterrows():
            sat_info = (
                row['sat_name'],
                float(row['sat_lat']),
                float(row['sat_lon']),
                float(row['sat_height']),
                float(row['elevation']),
                float(row['slant']),
                float(row['snr_dl']),
                float(row['snr_ul']),
                float(row['thr_dl']),
                float(row['thr_ul']),
                int(row['connected_users'])
            )
            satellites.append(sat_info)
            
    except KeyError as e:
        print(f"Error: Missing expected column in DataFrame - {e}")
    except ValueError as e:
        print(f"Error: Data format issue (e.g., empty or non-numeric values) - {e}")
        
    return satellites

def get_satellites_at_time(df, target_time):
    """
    Filters a pandas DataFrame and returns a list of tuples containing satellite 
    information for a specific datetime.
    """
    satellites = []
    
    # Check if target_time is a datetime object and format it to match the DataFrame
    if isinstance(target_time, datetime):
        # Formats to "YYYY-MM-DD HH:MM:SS" (e.g., "2025-06-08 00:00:00")
        target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Fallback just in case you pass a string directly
        target_time_str = str(target_time)
    
    try:
        # 1. Filter the DataFrame
        # .astype(str) ensures it safely compares strings, even if pandas 
        # auto-converted your time column to datetime objects when loading the CSV.
        matched_data = df[df['time'].astype(str) == target_time_str]
        
        # 2. Iterate through the matching rows
        for index, row in matched_data.iterrows():
            sat_info = (
                row['sat_name'],
                float(row['sat_lat']),
                float(row['sat_lon']),
                float(row['sat_height']),
                float(row['elevation']),
                float(row['slant']),
                float(row['snr_dl']),
                float(row['snr_ul']),
                float(row['thr_dl']),
                float(row['thr_ul']),
                int(row['connected_users']),
                float(row['occurrence_countdown'])
            )
            satellites.append(sat_info)
            
    except KeyError as e:
        print(f"Error: Missing expected column in DataFrame - {e}")
    except ValueError as e:
        print(f"Error: Data format issue (e.g., empty or non-numeric values) - {e}")
        
    return satellites

def get_max_thr(df, sat_name, target_time):
    """
    Return max DL and UL throughput for a specific satellite at a given time instant
    """
    satellites = []
    
    # Check if target_time is a datetime object and format it to match the DataFrame
    if isinstance(target_time, datetime):
        # Formats to "YYYY-MM-DD HH:MM:SS" (e.g., "2025-06-08 00:00:00")
        target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Fallback just in case you pass a string directly
        target_time_str = str(target_time)
    
    try:
        matched_data = df[df['time'].astype(str) == target_time_str]
        matched_data = matched_data[matched_data['sat_name'].astype(str) == sat_name]
        
        dl_thr = float(matched_data['thr_dl'].iloc[0])
        ul_thr = float(matched_data['thr_ul'].iloc[0])
    
    
    except KeyError as e:
        print(f"Error: Missing expected column in DataFrame - {e}")
    except ValueError as e:
        print(f"Error: Data format issue (e.g., empty or non-numeric values) - {e}")
        
    return dl_thr, ul_thr

def get_best_satellite(visible_sats, service_sats):

    if(len(visible_sats) == 0):
        return None

    for index, vis_sat in enumerate(visible_sats):
        if(vis_sat[0] in service_sats):
            temp = list(visible_sats[index])
            temp[10] = service_sats[vis_sat[0]].connected_ues
            visible_sats[index] = temp

    # Find the satellite that maximizes: thr_dl / (connected_users + 1)
    # sat[8] is thr_dl, sat[10] is connected_users
    best_satellite = max(
        visible_sats, 
        key=lambda sat: sat[8] / (sat[10] + 1)
    )
    
    return best_satellite

def get_random_satellite(visible_sats):

    num = len(visible_sats)
    if(num == 0):
        return None
    
    random_index = random.randint(0, num-1)
    best_satellite = visible_sats[random_index]

    return best_satellite

def get_max_visibility_satellite(visible_sats, time, df): # old function, unused

    if(len(visible_sats) == 0):
        return None

    for index, vis_sat in enumerate(visible_sats):
        temp = list(vis_sat)
        temp[10] = get_visibility_time(vis_sat[0], time, df)
        vis_sat = temp
    # best_satellite = max(visible_sats, key=lambda sat: sat[10])
    visible_sats.sort(key=lambda sat: sat[10])
    length = min(5, len(visible_sats))-1
    best_satellite = random.choice(visible_sats[:length])


    return best_satellite

def get_visibility_time(sat_name, target_time, df):

    vis_time = 0

    # Convert the entire 'time' column from strings to datetime objects
    df['time'] = pd.to_datetime(df['time'])
    vis_time = len(df[(df['sat_name'] == sat_name) & (df['time'] >= target_time)])

    return vis_time

def get_max_visibility_satellite_v2(visible_sats, time, df, fraction = 0.3, n_min=1):

    if(len(visible_sats) == 0):
        return None
    visible_sats.sort(key=lambda sat : sat[11], reverse = True)
    # best_sat = max(visible_sats, key=lambda sat: sat[11])
    print("we have ", len(visible_sats), " visible satellites.")
    if(n_min > len(visible_sats)):
        print("only ", len(visible_sats), " visible. returning ", visible_sats[0][0], " with residual visibility of ", visible_sats[0][11], " (and others).")
        return visible_sats
    else: 
        n_min = max(n_min, int(len(visible_sats)*fraction))
        print("returning top ", n_min, " satellites. Top one ", visible_sats[0][0], " with residual visibility of ", visible_sats[0][11], " (and others).")
        return visible_sats[:n_min]
    #return sorted_visible_satellites[0]
    # visible_sats.sort(key=lambda sat: sat[11])
    # length = min(5, len(visible_sats))-1
    # print("returning ", visible_sats[0][0], " with residual visibility of ", visible_sats[0][11], ".")
    # best_satellite = random.choice(visible_sats[:length])
    # return best_satellite

def get_best_satellite_v2(visible_sats, service_sats):

    # fast lookup dictionary mapping {satellite_name: connected_ues}, better than the nested loop
    # This loops through service_sats exactly once.
    service_loads = {sat.name: sat.connected_ues for sat in service_sats}

    def calculate_score(sat):
        name = sat[0]
        thr_dl = sat[8]
        
        # fast dictionary lookup: get the load if it's active, otherwise default to 0
        connected_users = service_loads.get(name, 0)
        
        # calculate and return the metric
        return thr_dl / (connected_users + 1)
        
    # find the best satellite
    best_satellite = max(visible_sats, key=calculate_score)
    
    return best_satellite

def get_best_satellite_by_snr_and_thr(visible_sats, service_sats):

    # fast lookup dictionary mapping {satellite_name: connected_ues}, better than the nested loop
    # This loops through service_sats exactly once.
    service_loads = {sat.name: sat.connected_ues for sat in service_sats}

    def calculate_score(sat):
        name = sat[0]
        snr_dl = sat[6] + np.random.normal(0, 1)  # add gaussian noise to the SNR measurement
        thr_dl = sat[8]
        
        # fast dictionary lookup: get the load if it's active, otherwise default to 0
        connected_users = service_loads.get(name, 0)
        
        # combine SNR and Throughput into a single score, for example by multiplying them together
        score = snr_dl * thr_dl / (connected_users + 1)

        return score
        
    # find the best satellite
    best_satellite = max(visible_sats, key=calculate_score)
    
    return best_satellite
    

def get_best_satellite_by_dl_snr(satellites_list):
    """
    Takes a list of satellite tuples and returns the satellite 
    with the highest Downlink SNR (snr_dl).
    """
    # Safety check: if the list is empty, return None to prevent errors
    if not satellites_list:
        print("Warning: The satellite list is empty.")
        return None

    # Find the tuple with the maximum value at index 6 (snr_dl)
    best_satellite = max(satellites_list, key=lambda sat: sat[6])
    
    return best_satellite


def get_best_satellite_by_available_dl_thr(satellites_list):
    """
    Takes a list of satellite tuples and returns the satellite 
    that offers the highest potential Downlink Throughput per user.
    """
    # Safety check: if the list is empty, return None to prevent errors
    if not satellites_list:
        print("Warning: The satellite list is empty.")
        return None

    # Find the satellite that maximizes: thr_dl / (connected_users + 1)
    # sat[8] is thr_dl, sat[10] is connected_users
    best_satellite = max(
        satellites_list, 
        key=lambda sat: sat[8] / (sat[10] + 1)
    )
    
    return best_satellite




def increment_connected_users_df(df, target_time, target_sat_name):
    """
    Finds a specific satellite at a specific time in a pandas DataFrame 
    and increments its 'connected_users' value by 1.
    """
    # Format the datetime object to a string to match the DataFrame
    if isinstance(target_time, datetime):
        target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        target_time_str = str(target_time)

    # Make sure the 'connected_users' column is treated as numbers (integers),
    # just in case it was read from the CSV as text strings.
    df['connected_users'] = pd.to_numeric(df['connected_users'], errors='coerce').fillna(0).astype(int)

    # Create a filter (mask) to find the exact row(s)
    # Note: If your df['time'] column was already converted to datetime objects, 
    # you would compare directly against `target_time` instead of `target_time_str`.
    mask = (df['time'].astype(str) == target_time_str) & (df['sat_name'] == target_sat_name)

    # Check if the satellite exists at that time
    if mask.any():
        # Use .loc to locate the exact cell and add 1
        df.loc[mask, 'connected_users'] += 1
        # print(f"Successfully updated users for {target_sat_name} at {target_time_str}.")
    #else:
        #print(f"Could not find {target_sat_name} at time {target_time_str}.")

    # Return the updated DataFrame
    return df

def decrement_connected_users_df(df, target_time, target_sat_name):
    """
    Finds a specific satellite at a specific time in a pandas DataFrame 
    and decrements its 'connected_users' value by 1.
    """
    # Format the datetime object to a string to match the DataFrame
    if isinstance(target_time, datetime):
        target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        target_time_str = str(target_time)

    # Make sure the 'connected_users' column is treated as numbers (integers),
    # just in case it was read from the CSV as text strings.
    df['connected_users'] = pd.to_numeric(df['connected_users'], errors='coerce').fillna(0).astype(int)

    # Create a filter (mask) to find the exact row(s)
    # Note: If your df['time'] column was already converted to datetime objects, 
    # you would compare directly against `target_time` instead of `target_time_str`.
    mask = (df['time'].astype(str) == target_time_str) & (df['sat_name'] == target_sat_name)

    # Check if the satellite exists at that time
    if mask.any():
        # Use .loc to locate the exact cell and decrement 1
        df.loc[mask, 'connected_users'] -= 1
        # print(f"Successfully updated users for {target_sat_name} at {target_time_str}.")
    # else:
        #print(f"Could not find {target_sat_name} at time {target_time_str}.")

    # Return the updated DataFrame
    return df





def compute_dl_snr(frame, satellite_name, time):
    """
    Looks up a specific satellite at a specific time in a DataFrame 
    and returns its Downlink SNR (snr_dl).
    """
    # Format the time object to match the DataFrame string format
    if isinstance(time, datetime):
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = str(time)
        
    # Create a mask to find the exact row
    mask = (frame['time'].astype(str) == time_str) & (frame['sat_name'] == satellite_name)
    
    # Apply the mask to filter the DataFrame
    filtered_row = frame[mask]
    
    # Check if a match was found and return the value
    if not filtered_row.empty:
        # .iloc[0] extracts the value from the very first matching row
        snr_value = filtered_row['snr_dl'].iloc[0]
        return float(snr_value)
    else:
        #print(f"Warning: Could not find SNR data for {satellite_name} at {time_str}.")
        return None


def propagate_users_to_next_second(df, current_time, time_shift):
    """
    Looks at all satellites at 'current_time', copies their 'connected_users', 
    and assigns that value to the same satellites exactly 1 second later 
    (if they are still visible).
    """
    # Calculate the exact next second
    next_time = current_time + time_shift
    
    # Format times to strings 
    if isinstance(current_time, datetime):
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        next_time_str = next_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        # Fallback if you passed strings directly
        current_time_str = str(current_time)
        next_time_str = str(next_time) 

    # Get all satellites available at the CURRENT time
    current_time_mask = df['time'].astype(str) == current_time_str
    current_sats = df[current_time_mask]
    
    # Create a fast-lookup dictionary: {'Sat_Name': connected_users_count, ...}
    # This prevents us from having to loop through the DataFrame multiple times.
    users_map = dict(zip(current_sats['sat_name'], current_sats['connected_users']))
    
    # Create a baseline mask for the NEXT time instant
    next_time_mask = df['time'].astype(str) == next_time_str
    
    # Loop through our dictionary and update the next second's data
    for sat_name, users in users_map.items():
        
        # Isolate the specific satellite at the next time instant
        target_mask = next_time_mask & (df['sat_name'] == sat_name)
        
        # If this mask finds a match (meaning the sat is still visible 1s later)
        if target_mask.any():
            # Safely update the value in-place using .loc
            df.loc[target_mask, 'connected_users'] = users
            
    # Return the updated DataFrame 
    return df



def compute_dl_thr(frame, satellite_name, time):
    """
    Looks up a specific satellite at a specific time in a DataFrame 
    and returns its Downlink Throughput (thr_dl).
    """
    # Format the time object to match the DataFrame string format
    if isinstance(time, datetime):
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = str(time)
        
    # Create a mask to find the exact row
    mask = (frame['time'].astype(str) == time_str) & (frame['sat_name'] == satellite_name)
    
    # Apply the mask to filter the DataFrame
    filtered_row = frame[mask]
    
    # Check if a match was found and return the value
    if not filtered_row.empty:
        # .iloc[0] extracts the value from the very first matching row
        thr_value = filtered_row['thr_dl'].iloc[0] / (filtered_row['connected_users'].iloc[0])  # +1 to avoid division by zero
        return float(thr_value)
    else:
        #print(f"Warning: Could not find Throughput data for {satellite_name} at {time_str}.")
        return None


# ************************************************************************************************************************
# **************************************** OLD STUFF BELOW, IGNORE *******************************************************
# ************************************************************************************************************************




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