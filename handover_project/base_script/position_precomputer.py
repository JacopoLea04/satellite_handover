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
    # Create a range of offsets in seconds, then add to start time
    return start_time + np.arange(0, offset_seconds + step_seconds, step_seconds).astype('timedelta64[s]')

def evaluate_time_instant(time_instant, cluster, tle_list, lat_ue, lon_ue, beam_footprint_m, eirp_gt, gt_sat, eirp_sat, gt_ue, frequency_dl, frequency_ul, bandwidth_dl, bandwidth_ul):
    results = []
    for satellite_name, line1, line2 in tle_list:
        # Create the satellite object
        sat = Satellite(satellite_name, (satellite_name, line1, line2))
        sat_lat, sat_lon, sat_height_m = sat.get_position(time_instant.astype('datetime64[us]').item())
        within = ChannelParameters.within_range(
            lat_ue,
            lon_ue,
            sat_lat,
            sat_lon,
            beam_footprint_m * 5
        )

        if within is not None:
            elevation_angle = ChannelParameters.elevation_angle_deg(
                lat_ue, lon_ue,
                sat_lat, sat_lon,
                sat_height_m
            )

            slant_range = ChannelParameters.get_distance(elevation_angle, sat_height_m)
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
                bandwidth_ul
            )

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
    start_time = time.time()

    # transmission parameters
    beam_footprint_m = 100_000                  # beam diameter [m]
    epoch_time = np.datetime64('2025-06-08T00:00:00')  # epoch time for position computation [y, m, d, h, m, s]
    simulation_duration_seconds = 50            # total simulation duration [s]
    simulation_step_seconds = 2                           # time step for position computation [s]
    lat_ue, lon_ue = 45.4384, 11.0086           # ue location [decimal degrees]
    cluster_id = 0
    eirp_gt = -7                # UL EIRP [dBW]
    gt_sat = 1.1                # UL G/T satellite [dB/K]
    eirp_sat = 48.8             # DL EIRP [dBW]
    gt_ue = -31.6               # DL G/T UE [dB/K]
    bandwidth_dl = 30e6         # 30 MHz DL bandwidth [MHz]
    bandwidth_ul = 0.4e6        # UL bandwidth [MHz]
    frequency_dl = 2            # DL carrier frequency [GHz]
    frequency_ul = 2            # UL carrier frequency [GHz]
    max_workers = None          # none to use all availabe cpu cores, or set to a specific number

    with open('Starlink_TLE.txt', 'r') as f:
        lines = [l.strip() for l in f.readlines()]
    tle_list = [(lines[i], lines[i+1], lines[i+2]) for i in range(0, len(lines)-2, 3)]
    print(f"Loaded {len(tle_list)} satellites from TLE file")

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
        bandwidth_ul=bandwidth_ul
    )

    # generate the vector of time instants for which to compute the satellite positions
    print(f"Generating time vector for {simulation_duration_seconds} s with step of {simulation_step_seconds} s...")
    times = generate_time_vector(epoch_time, simulation_duration_seconds, simulation_step_seconds)
    print(times[:3]) # Show first three

    print("\n=== starting main computation cycle ===")
    # with concurrent.futures.ProcessPoolExecutor(max_workers) as executor:
    #     results_list = list(executor.map(worker_evaluate_time_instant, times))
    results_list = process_map(
        worker_evaluate_time_instant, 
        times, 
        max_workers=None,  # Specify your core count
        chunksize=1     # How many items to send to a worker at once
    )
    
    flat_results = list(itertools.chain.from_iterable(results_list))
    df = pd.DataFrame(flat_results)

    df['time'] = pd.to_datetime(df['time'])

    print("finished main computation cycle, results preview: \n")
    print(df.head())
    print(f"total records: {len(df)}")

    end_time = time.time()
    print(f"processed in {end_time - start_time:.2f} seconds.")

    print("\n=== saving output file ===")
    filename = "satellite_df"
    df.to_csv(f'{filename}.csv', index=False)
    print(f"saved as {filename}.csv")
    df.to_parquet(f'{filename}.parquet', engine='pyarrow', compression='snappy')
    print(f"saved as {filename}.parquet")


# 5. Crucial: This guard is required for multiprocessing on Windows/macOS
if __name__ == '__main__':
    main()