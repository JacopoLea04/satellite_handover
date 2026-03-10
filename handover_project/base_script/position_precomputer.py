from datetime import datetime
import numpy as np
from satellite import Satellite
from channel_parameters import ChannelParameters
import pandas as pd
import itertools

# for parallel processing
import time
from tqdm.contrib.concurrent import process_map
from functools import partial

def generate_time_vector(start_time, offset_seconds, step_seconds):
    """
        Generates a vector of time instants starting from `start_time`, with a total duration of `offset_seconds` and a step of `step_seconds`.

        Args:
            start_time (numpy.datetime64): The starting time instant
            offset_seconds (int): Total duration in seconds for which to generate time instants
            step_seconds (int): Time step in seconds between consecutive time instants
        Returns:
            numpy.ndarray: An array of time instants
    """
    return start_time + np.arange(0, offset_seconds + step_seconds, step_seconds).astype('timedelta64[s]')

def evaluate_time_instant(time_instant, cluster, tle_list, lat_ue, lon_ue, beam_footprint_m, eirp_gt, gt_sat, eirp_sat, gt_ue, frequency_dl, frequency_ul, bandwidth_dl, bandwidth_ul, sc6, sc9):
    """
    Given a time instant, a list of satellite TLEs, and some transmission parameters, this function 
    evaluates which satellites are within range of the UE and computes the relevant transmission parameters
    for those satellites.
        Args:
            time_instant (numpy.datetime64): The time instant to evaluate
            cluster (int): The cluster ID for which to evaluate the satellite positions (just copied to the dataframe)
            tle_list (list of tuples): List of TLE data for the satellites, where each tuple contains (satellite_name, line1, line2)
            lat_ue (float): Latitude of the user equipment (UE) in decimal degrees
            lon_ue (float): Longitude of the user equipment (UE) in decimal degrees
            beam_footprint_m (float): The diameter of the satellite beam footprint in meters
            eirp_gt (float): EIRP of the ground terminal in dBW
            gt_sat (float): G/T of the satellite in dB/K
            eirp_sat (float): EIRP of the satellite in dBW
            gt_ue (float): G/T of the user equipment in dB/K
            frequency_dl (float): Downlink carrier frequency in GHz
            frequency_ul (float): Uplink carrier frequency in GHz
            bandwidth_dl (float): Downlink bandwidth in Hz
            bandwidth_ul (float): Uplink bandwidth in Hz
            sc6 (boolean): operate in 3GPP SC6 scenario - affects the channel model and transmission parameters
            sc9 (boolean): operate in 3GPP SC9 scenario - affects the channel model and transmission parameters
        Returns:
            list of dicts: A list of dictionaries containing the computed parameters for each satellite within range in the following form:
                {
                    "cluster_id": cluster,
                    "time": time_instant,
                    "sat_name": satellite_name,
                    "sat_lat": sat_lat,
                    "sat_lon": sat_lon,
                    "sat_height": sat_height_m,
                    "elevation": elevation_angle,
                    "slant": slant_range,
                    "snr_dl": dl_snr,
                    "snr_ul": ul_snr,
                    "thr_dl": dl_rate,
                    "thr_ul": ul_rate
                }
    """

    results = [] # list to store results for all satellites within range at this time instant
    for satellite_name, line1, line2 in tle_list: 
        sat = Satellite(satellite_name, tle_data=(satellite_name, line1, line2)) # create satellite object from TLE data
        # get satellite position at the given time instant. Note that we need to convert the numpy.datetime64 to a standard Python datetime object
        sat_lat, sat_lon, sat_height_m = sat.get_position(time_instant.astype('datetime64[us]').item())
        # skip if the satellite height is negative or above 5000 km to filter out erroneous position calculations
        if(sat_height_m < 100 or sat_height_m > 5e6):
            continue

        # check if the satellite is within range of the UE based on the beam footprint
        within = ChannelParameters.within_range(
            lat_ue,
            lon_ue,
            sat_lat,
            sat_lon,
            beam_footprint_m * 5
        )

        # if the satellite is within range, compute the channel parameters and save the results.
        if within is not None:
            # compute the elevation angle
            elevation_angle = ChannelParameters.elevation_angle_deg(
                lat_ue, lon_ue,
                sat_lat, sat_lon,
                sat_height_m
            )

            # compute the slant range
            slant_range = ChannelParameters.get_distance(elevation_angle, sat_height_m)

            # compute the UL and DL rates and SNRs based on the channel parameters
            ul_rate, dl_rate, ul_snr, dl_snr = ChannelParameters.calculate_ue_rate(
                lat_ue, lon_ue,
                sat_lat, sat_lon,
                elevation_angle,
                slant_range,
                eirp_gt,
                eirp_sat,
                gt_ue,
                gt_sat,
                frequency_dl,
                frequency_ul,
                bandwidth_dl,
                bandwidth_ul,
                sc6,
                sc9
            )

            # save the results in the list as a dictionary
            results.append({
                "cluster_id": cluster,
                "time": time_instant,
                "sat_name": satellite_name,
                "sat_lat": sat_lat,
                "sat_lon": sat_lon,
                "sat_height": sat_height_m,
                "elevation": elevation_angle,
                "slant": slant_range,
                "snr_dl": dl_snr,
                "snr_ul": ul_snr,
                "thr_dl": dl_rate,
                "thr_ul": ul_rate,
                "connected_users": 0 # Placeholder, to be filled in later
            })

    return results

def main():
    print("=== starting position pre-computation ===")
    start_time = time.time() # just to act cool and print the time taken for the computations at the end

    # simulation parameters
    # epoch_time = np.datetime64('2025-06-08T00:00:00')   # epoch time for position computation [y, m, d, h, m, s]
    epoch_time = np.datetime64('2026-02-19T00:00:00')   # epoch time for position computation [y, m, d, h, m, s]
    simulation_duration_seconds = 3600                  # total simulation duration [s]
    simulation_step_seconds = 1                         # time step for position computation [s]
    lat_ue, lon_ue = 18.29817, -64.82818                # ue location [decimal degrees]
    cluster_id = 0

    max_workers = None      # none to use all availabe cpu cores, or set to a specific number

    sc9 = True
    sc6 = False
    if sc9:
        beam_footprint_m = 75_000  # beam diameter [m]
        eirp_gt = -7                # UL EIRP [dBW]
        gt_sat = 1.1                # UL G/T satellite [dB/K]
        eirp_sat = 48.8             # DL EIRP [dBW]
        gt_ue = -31.6               # DL G/T UE [dB/K]
        bandwidth_dl = 30e6         # 30 MHz DL bandwidth [MHz]
        bandwidth_ul = 0.4e6        # UL bandwidth [MHz]
        frequency_dl = 2            # DL carrier frequency [GHz]
        frequency_ul = 2            # UL carrier frequency [GHz]
    elif sc6:
        beam_footprint_m = 20_000  # beam diameter [m]
        eirp_gt = 46.2              # UL EIRP [dBW]
        gt_sat = 13                 # UL G/T satellite [dB/K]
        eirp_sat = 30               # DL EIRP [dBW]
        gt_ue = 15.9                # DL G/T UE [dB/K]
        bandwidth_dl = 400e6        # DL bandwidth [MHz]
        bandwidth_ul = 400e6        # UL bandwidth [MHz]
        frequency_dl = 20           # DL carrier frequency [GHz]
        frequency_ul = 30           # UL carrier frequency [GHz]
    else:
        print("\nNo scenario selected. Please set sc9 or sc6 to True.")

    # loading the TLE parameters and create the list of tuples
    with open('Starlink_TLE.txt', 'r') as f:
        lines = [l.strip() for l in f.readlines()]
    tle_list = [(lines[i], lines[i+1], lines[i+2]) for i in range(0, len(lines)-2, 3)]
    print(f"Loaded {len(tle_list)} satellites from TLE file")

    # since the function we want to parallelize (evaluate_time_instant) takes multiple arguments,
    # we use functools.partial to create a new function with the other arguments fixed,
    # so that it only takes the time instant as input. This allows us to easily use it with process_map for parallel processing.
    worker_evaluate_time_instant = partial(
        evaluate_time_instant,
        cluster = cluster_id,
        tle_list=tle_list,
        lat_ue=lat_ue,
        lon_ue=lon_ue,
        beam_footprint_m=beam_footprint_m,
        eirp_gt=eirp_gt,
        gt_sat=gt_sat,
        eirp_sat=eirp_sat,
        gt_ue=gt_ue,
        frequency_dl=frequency_dl,
        frequency_ul=frequency_ul,
        bandwidth_dl=bandwidth_dl,
        bandwidth_ul=bandwidth_ul,
        sc6=sc6,
        sc9=sc9
    )

    # generate the vector of time instants for which to compute the satellite positions
    print(f"Generating time vector for {simulation_duration_seconds} s with step of {simulation_step_seconds} s...")
    times = generate_time_vector(epoch_time, simulation_duration_seconds, simulation_step_seconds)
    print(times[:3]) # Show first three

    print("\n=== starting main computation cycle ===")
    results_list = process_map(
        worker_evaluate_time_instant, 
        times, 
        max_workers=max_workers,  # Specify your core count
        chunksize=1
    )
    
    # flatten the list of lists of dictionaries into a single list of dictionaries, and convert to a dataframe
    flat_results = list(itertools.chain.from_iterable(results_list))
    df = pd.DataFrame(flat_results)

    # set the correct time format for the dataframe
    df['time'] = pd.to_datetime(df['time'])

    print("finished main computation cycle, results preview: \n")
    print(df.head())
    print(f"total records: {len(df)}")

    end_time = time.time()
    print(f"processed in {end_time - start_time:.2f} seconds.")

    print("\n=== saving output file ===")
    filename = "75km_sc9"
    df.to_csv(f'{filename}.csv', index=False)
    print(f"saved as {filename}.csv")
    df.to_parquet(f'{filename}.parquet', engine='pyarrow', compression='snappy')
    print(f"saved as {filename}.parquet")

# whatever
if __name__ == '__main__':
    main()