from skyfield.api import load
from datetime import datetime
import numpy as np
import random

from channel_parameters import ChannelParameters

import math
import pandas as pd


sc6_parameters = {
    'eirp_ue' : 76.2,   # dBm
    'gt_sat' : 13,      # dBi
    'eirp_sat' : 60,    # dBm
    'gt_ue' : 15.9,     # dBi
    'bw_dl' : 400e6,     # Hz
    'bw_ul' : 400e6,    # Hz
    'freq_dl' : 2e9,    # Hz
    'freq_ul' : 3e9,    # Hz
    'atm_loss' : 5.3,   # dB
    'dl_db_headroom' : 0, # dB
    'ul_db_headroom' : 0,  # dB
    'dlul_snr_variance' : 1 # variance of the noise added to the UE snr measurement to simulate real-world measurement imperfections,
}

sc9_parameters = {
    'eirp_ue' : 23,     # dBm
    'gt_sat' : 1.1,     # dBi
    'eirp_sat' : 78.8,  # dBm
    'gt_ue' : -31.6,    # dBi
    'bw_dl' : 30e6,     # Hz
    'bw_ul' : 0.4e6,    # Hz
    'freq_dl' : 2e9,    # Hz
    'freq_ul' : 3e9,    # Hz
    'atm_loss' : 0.8,   # dB
    'dl_db_headroom' : 2, # dB
    'ul_db_headroom' : 2,  # dB
    'dlul_snr_variance' : 1 # variance of the noise added to the UE snr measurement to simulate real-world measurement imperfections,
}

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

def get_max_visibility_satellite_v2(visible_sats, time, df, fraction = 0.3, n_min=1):

    if(len(visible_sats) == 0):
        return None
    visible_sats.sort(key=lambda sat : sat[11], reverse = True)
    # best_sat = max(visible_sats, key=lambda sat: sat[11])
    # print("we have ", len(visible_sats), " visible satellites.")
    if(n_min > len(visible_sats)):
        # print("only ", len(visible_sats), " visible. returning ", visible_sats[0][0], " with residual visibility of ", visible_sats[0][11], " (and others).")
        return visible_sats
    else: 
        n_min = max(n_min, int(len(visible_sats)*fraction))
        # print("returning top ", n_min, " satellites. Top one ", visible_sats[0][0], " with residual visibility of ", visible_sats[0][11], " (and others).")
        return visible_sats[:n_min]

def get_max_elevation_satellite(visible_sats, fraction = 0.3, n_min=1):

    if(len(visible_sats) == 0):
        return None

    visible_sats.sort(key=lambda sat : sat[4], reverse = True)
    n_min = max(n_min, int(len(visible_sats)*fraction))
    index = random.randint(0, len( visible_sats[:n_min])-1)
    best_satellite =  visible_sats[:n_min][index]
    return best_satellite

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

def lla_to_ecef(lat, lon, alt):
    # seting the parameters for the WGS84
    a = 6378137.0 # the semi-major axis in meters
    f = 1/298.257223563 # flattening factor
    e2 = 6.69437999014e-3 # square of the eccentricity
    b = 6356752.3142 # the semi-minor axis in meters

    n_lat = a / math.sqrt(1-e2*math.sin(math.radians(lat))**2)

    x = (n_lat + alt) * math.cos(math.radians(lat)) * math.cos(math.radians(lon))
    y = (n_lat + alt) * math.cos(math.radians(lat)) * math.sin(math.radians(lon))
    z = ((1-e2)*n_lat+alt) * math.sin(math.radians(lat))

    return x, y, z

def direct_geodetic_problem(latitude, longitude, distance, bearing):
    """
    Computes the destination point coordinates given a starting point coordinates (latitude and longitude),
    the distance to travel, and the initial bearing in degrees. The Earth is assumed to be a perfect sphere
    (haversine formula).
    
    Args:
        latitude (float): latitude of the starting point in decimal degrees
        longitude (float): longitude of the starting point in decimal degrees
        distance (float): distance to travel in meters
        bearing (float): initial bearing in decimal degrees, clockwise from north (0 = north, 90 = east, ...)
    Returns:
        (float, float): latitude and longitude of the destination point in decimal degrees.
    """
    radius = 6371000 # Earth radius in meters

    # converting to radians for computaitons
    phi1 = math.radians(latitude)
    lambda1 = math.radians(longitude)
    theta = math.radians(bearing)
    delta = distance / radius

    # conversion formulae 
    phi2 = math.asin(math.sin(phi1) * math.cos(delta) + 
                     math.cos(phi1) * math.sin(delta) * math.cos(theta)) # destination latitude
    
    lambda2 = lambda1 + math.atan2(math.sin(theta) * math.sin(delta) * math.cos(phi1), 
                                   math.cos(delta) - math.sin(phi1) * math.sin(phi2)) # destination longitude
    
    return math.degrees(phi2), math.degrees(lambda2) # returning to degrees


def compute_cell_boundaries_lla(center_lat, center_lon, beam_size_m, beams_per_cell):
    """
    Computes the coordinates of the corners of a squared cell on the earth's surface centered on the 
    given point (center_lat, center_lon). The cell dimensions are computed from the given beam size
    in meters and the number of beams in the cell, assuming a square grid of beams.
    Args:
        center_lat (float): latitude of the cell centre in decimal degrees
        center_lon (float): longitude of the cell centre in decimal degrees
        beam_size_m (float): size of the beam footprint in meters
        beams_per_cell (int): number of beams in the cell in one direction 
            (e.g., if cell_width_in_beams=3, the cell is 3 beams wide and 3 beams tall)
    Returns:
        ((float, float), (float, float)): (nw_lat, nw_lon) coordinates of the north-west corner of the cell,
            (se_lat, se_lon) coordinates of the south-east corner of the cell, all in decimal degrees.
    """
    # bearings
    north = 0
    east = 90
    south = 180
    west = 270

    half_cell_size = (beam_size_m * beams_per_cell) / 2

    # starting from the center of the cell, we move west and north to find the north-west corner
    nw_lat, nw_lon = direct_geodetic_problem(center_lat, center_lon, half_cell_size, west)
    nw_lat, nw_lon = direct_geodetic_problem(nw_lat, nw_lon, half_cell_size, north)
    # starting from the center of the cell, we move east and south to find the south-east corner
    se_lat, se_lon = direct_geodetic_problem(center_lat, center_lon, half_cell_size, east)
    se_lat, se_lon = direct_geodetic_problem(se_lat, se_lon, half_cell_size, south)

    return (nw_lat, nw_lon), (se_lat, se_lon)

def check_clusters_visibility(cluster_centers_positions, cell_boundaries, cell_dim_beams):
    """
    checks which of the cluster centers are within the satellite cell boundaries defined by the north-west and
    south-east corners latitude and longitude in decimal degrees.
    Example of centers grid numbering for a 5x5 cluster:
        0   1   2   3   4
        5   6   7   8   9
        10  11  12  13  14
        15  16  17  18  19
        20  21  22  23  24

    Args:
        cluster_centers_positions (list of tuples): list of (lat, lon, alt) coordinates of the cluster centers
            in decimal degrees and meters.
        cell_boundaries ((float, float), (float, float)): (nw_lat, nw_lon) coordinates of the north-west 
            corner of the cell, (se_lat, se_lon) coordinates of the south-east corner of the cell,
            all in decimal degrees.
        cell_dim_beams (int): number of beams in the cell in one direction.
            e.g., if cell_dim_beams = 3, the cell is 3 beams wide and 3 beams tall, totalling 9 beams.
    Returns:
        numpy.ndarray: matrix with indices of the cluster centers that are within the cell boundaries.
    """
    nw_lat, nw_lon = cell_boundaries[0]
    se_lat, se_lon = cell_boundaries[1]
    
    visible_clusters_indices = []
    cluster_row = []
    rind = 0
    for index, (lat, lon, alt) in enumerate(cluster_centers_positions):
        if nw_lat >= lat >= se_lat and nw_lon <= lon <= se_lon:
            cluster_row.append(index)
        rind += 1
        if rind == cell_dim_beams:
            visible_clusters_indices.append(cluster_row)
            cluster_row = []
            rind = 0
    visible_clusters_indices = list(filter(None, visible_clusters_indices))
    visible_clusters_indices_matrix = np.array(visible_clusters_indices)

    return visible_clusters_indices_matrix

def get_coverage_beam_indices_matrix(visible_clusters_indices_matrix, cell_dim_beams):
    """
    given the matrix containing the indices of miniclusters that do have visibility with the satellite,
    this function returns a matrix of the same size containing the indices of the satellite beams that cover
    each of the mini clusters.
    Args:
        visible_clusters_indices_matrix (numpy.ndarray): matrix with indices of the cluster centers that are within the cell boundaries
        cell_dim_beams (int): number of beams in the cell in one direction
    Returns:
        numpy.ndarray: matrix with indices of the satellite beams that cover each of the mini clusters. The indices are arranged
            in the same way as the input matrix.
    """
    rows, cols = visible_clusters_indices_matrix.shape
    satellite_beams_matrix = np.arange(0, cell_dim_beams * cell_dim_beams).reshape(cell_dim_beams, cell_dim_beams)
    # print(satellite_beams_matrix)
    satellite_beams_matrix = np.roll(satellite_beams_matrix, shift=(-rows, cols), axis=(0, 1))
    # print(satellite_beams_matrix)
    coverage_beams_matrix = np.take(satellite_beams_matrix, visible_clusters_indices_matrix)
    # print(coverage_beams_matrix)
    return coverage_beams_matrix

def calculate_beams_grid(center_lat, center_lon, beam_size_km, num_beams):
    """
    This function calculates the positions of the beams' centers in a grid pattern around the center position.
    """
    grid_size = int(np.sqrt(num_beams))
    # Ensure inputs are treated as float64 (doubles)
    center_lat = np.float64(center_lat)
    center_lon = np.float64(center_lon)

    KM_PER_DEG_LAT = np.float64(111.32)
    km_per_deg_lon = KM_PER_DEG_LAT * np.cos(np.radians(center_lat))

    indices = np.arange(grid_size)
    center_idx = grid_size // 2 

    col_grid, row_grid = np.meshgrid(indices, indices)

    # Calculate offsets using float64 math
    delta_y_km = (center_idx - row_grid).astype(np.float64) * beam_size_km
    delta_x_km = (col_grid - center_idx).astype(np.float64) * beam_size_km

    # Final Lats and Lons
    lats = (center_lat + (delta_y_km / KM_PER_DEG_LAT)).flatten()
    lons = (center_lon + (delta_x_km / km_per_deg_lon)).flatten()

    # Create altitude as float64 zeros
    alts = np.zeros_like(lats, dtype=np.float64)

    return list(zip(lats, lons, alts))
    
def compute_shannon(distance_m, parameters):
    # Unpack parameters
    eirp_ue = parameters['eirp_ue']
    gt_sat = parameters['gt_sat']
    eirp_sat = parameters['eirp_sat']
    gt_ue = parameters['gt_ue']
    bw_dl = parameters['bw_dl']
    bw_ul = parameters['bw_ul']
    freq_dl = parameters['freq_dl']
    freq_ul = parameters['freq_ul']
    dl_db_headroom = parameters['dl_db_headroom']
    ul_db_headroom = parameters['ul_db_headroom']

    c = 299792458 
    path_loss_dl_db = 20 * math.log10(distance_m) + 20 * math.log10(freq_dl) + 20 * math.log10(4 * math.pi / c)
    path_loss_ul_db = 20 * math.log10(distance_m) + 20 * math.log10(freq_ul) + 20 * math.log10(4 * math.pi / c)

    # print(f"distance: {distance_m}m, dl pathloss: {path_loss_dl_db}dB, ul pathloss: {path_loss_ul_db}dB.")

    # Calculate received power in dBm
    received_power_dl_dbm = eirp_sat + gt_ue - path_loss_dl_db - dl_db_headroom
    received_power_ul_dbm = eirp_ue + gt_sat - path_loss_ul_db - ul_db_headroom
    # print(f"received_power_dl = {received_power_dl_dbm} dBm, received_power_ul = {received_power_ul_dbm} dBm.")

    snr_dl_db = received_power_dl_dbm + 198.6 - 10 * math.log10(bw_dl)
    snr_ul_db = received_power_ul_dbm + 198.6 - 10 * math.log10(bw_ul)
    # print(f"snr_dl = {snr_dl_db} dB, snr_ul = {snr_ul_db} dB.")

    snr_dl_linear = 10 ** (snr_dl_db / 10)
    snr_ul_linear = 10 ** (snr_ul_db / 10)

    dl_thr_mbps = round(bw_dl * math.log2(1 + snr_dl_linear) / 1e6, 4)
    ul_thr_mbps = round(bw_ul * math.log2(1 + snr_ul_linear) / 1e6, 4)
    # print(f"Estimated DL Throughput: {dl_thr_mbps} Mbps, Estimated UL Throughput: {ul_thr_mbps} Mbps.")
    return dl_thr_mbps, ul_thr_mbps

def get_max_beam_throughput(frame, target_time,satellite_name, mini_cluster_position, scenario):
    mini_cluster_lat, mini_cluster_lon, _ = mini_cluster_position
    dl_total_throughput, ul_total_throughput = 0, 0
    if isinstance(target_time, datetime):
        target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        target_time_str = str(target_time)
    
    try:
        matched_satellite = frame[frame['time'].astype(str) == target_time_str]
        matched_satellite = matched_satellite[matched_satellite['sat_name'].astype(str) == satellite_name]
        sat_lat = float(matched_satellite['sat_lat'].iloc[0])
        sat_long = float(matched_satellite['sat_lon'].iloc[0])
        sat_alt_m = float(matched_satellite['sat_height'].iloc[0])

        sat_x, sat_y, sat_z = lla_to_ecef(sat_lat, sat_long, sat_alt_m)
        ue_x, ue_y, ue_z = lla_to_ecef(mini_cluster_lat, mini_cluster_lon, 0)
        distance_m = round(math.sqrt((sat_x - ue_x)**2 + (sat_y - ue_y)**2 + (sat_z - ue_z)**2), 2)
        
        dl_total_throughput, ul_total_throughput = compute_shannon(distance_m, scenario)

    except KeyError as e:
        print(f"Error: Missing expected column in DataFrame - {e}")
    except ValueError as e:
        print(f"Error: Data format issue (e.g., empty or non-numeric values) - {e}")
        
    return dl_total_throughput, ul_total_throughput


def get_elevation(frame, target_time, satellite_name, mini_cluster_position):
    """
    Compute the satellite elevation given the minicluster and sat positions.
    Args:
        frame: the dataframe containing the constellation information over time
        satellite_name: name of the satellite we want to compute the snr
        mini_cluster_position: location of the ue we want to compute the snr
    Returns:
        sat_elev: satellite elevation angle in degrees
    """
    mini_cluster_lat, mini_cluster_lon, _ = mini_cluster_position
    sat_elev = 0
    if isinstance(target_time, datetime):
        target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        target_time_str = str(target_time)
    
    try:
        matched_satellite = frame[frame['time'].astype(str) == target_time_str]
        matched_satellite = matched_satellite[matched_satellite['sat_name'].astype(str) == satellite_name]
        sat_lat = float(matched_satellite['sat_lat'].iloc[0])
        sat_long = float(matched_satellite['sat_lon'].iloc[0])
        sat_alt_m = float(matched_satellite['sat_height'].iloc[0])

        sat_elev = ChannelParameters.elevation_angle_deg(
                mini_cluster_lat, mini_cluster_lon,
                sat_lat, sat_long,
                sat_alt_m
            )
        
    except KeyError as e:
        print(f"Error: Missing expected column in DataFrame - {e}")
    except ValueError as e:
        print(f"Error: Data format issue (e.g., empty or non-numeric values) - {e}")
        
    return sat_elev


def get_snr(frame, target_time, satellite_name, mini_cluster_position, parameters):
    """
    Compute the dl and ul snr given the minicluster and sat positions.
    Args:
        frame: the dataframe containing the constellation information over time
        satellite_name: name of the satellite we want to compute the snr
        mini_cluster_position: location of the ue we want to compute the snr
        parameters: specify the scenario (ex. sc6_parameters or sc9_parameters)
    Returns:
        snr_dl_db: the actual dl snr in dB
        snr_ul_db: the actual ul snr in dB
    """
    mini_cluster_lat, mini_cluster_lon, _ = mini_cluster_position
    dl_snr, ul_snr = 0, 0
    if isinstance(target_time, datetime):
        target_time_str = target_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        target_time_str = str(target_time)
    
    try:
        matched_satellite = frame[frame['time'].astype(str) == target_time_str]
        matched_satellite = matched_satellite[matched_satellite['sat_name'].astype(str) == satellite_name]
        sat_lat = float(matched_satellite['sat_lat'].iloc[0])
        sat_long = float(matched_satellite['sat_lon'].iloc[0])
        sat_alt_m = float(matched_satellite['sat_height'].iloc[0])

        sat_x, sat_y, sat_z = lla_to_ecef(sat_lat, sat_long, sat_alt_m)
        ue_x, ue_y, ue_z = lla_to_ecef(mini_cluster_lat, mini_cluster_lon, 0)
        distance_m = round(math.sqrt((sat_x - ue_x)**2 + (sat_y - ue_y)**2 + (sat_z - ue_z)**2), 2)
        
        # Unpack parameters
        eirp_ue = parameters['eirp_ue']
        gt_sat = parameters['gt_sat']
        eirp_sat = parameters['eirp_sat']
        gt_ue = parameters['gt_ue']
        bw_dl = parameters['bw_dl']
        bw_ul = parameters['bw_ul']
        freq_dl = parameters['freq_dl']
        freq_ul = parameters['freq_ul']
        dl_db_headroom = parameters['dl_db_headroom']
        ul_db_headroom = parameters['ul_db_headroom']

        c = 299792458 
        path_loss_dl_db = 20 * math.log10(distance_m) + 20 * math.log10(freq_dl) + 20 * math.log10(4 * math.pi / c)
        path_loss_ul_db = 20 * math.log10(distance_m) + 20 * math.log10(freq_ul) + 20 * math.log10(4 * math.pi / c)

        # print(f"distance: {distance_m}m, dl pathloss: {path_loss_dl_db}dB, ul pathloss: {path_loss_ul_db}dB.")

        # Calculate received power in dBm
        received_power_dl_dbm = eirp_sat + gt_ue - path_loss_dl_db - dl_db_headroom
        received_power_ul_dbm = eirp_ue + gt_sat - path_loss_ul_db - ul_db_headroom
        # print(f"received_power_dl = {received_power_dl_dbm} dBm, received_power_ul = {received_power_ul_dbm} dBm.")

        snr_dl_db = received_power_dl_dbm + 198.6 - 10 * math.log10(bw_dl)
        snr_ul_db = received_power_ul_dbm + 198.6 - 10 * math.log10(bw_ul)

    except KeyError as e:
        print(f"Error: Missing expected column in DataFrame - {e}")
    except ValueError as e:
        print(f"Error: Data format issue (e.g., empty or non-numeric values) - {e}")
        
    return snr_dl_db, snr_ul_db
   
def get_visibility_time(sat_name, target_time, df):
    """
    Compute the dl and ul snr given the minicluster and sat positions.
    Args:
        frame: the dataframe containing the constellation information over time
        time: current simulation time
        satellite_name: name of the satellite we want to compute the snr
    Returns:
        visibility_time: remaining visibility time of the satellite
    """
    vis_time = 0

    # Convert the entire 'time' column from strings to datetime objects
    df['time'] = pd.to_datetime(df['time'])
    vis_time = df[(df['sat_name'] == sat_name) & (df['time'] == target_time)]['occurrence_countdown'].iloc[0]

    return vis_time