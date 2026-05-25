from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import argparse
import os 
import shutil
import re

from cluster import Cluster
import utils


# initial configuration
df_name_1 = "100km_25beams_sc9_padova.csv"
ho_condition_1 = ("ELEVATION", 30)
sat_selection_condition_1 = "AVL_THR"
enable_elevation_threshold = True
elevation_threshold = 30

simTime = timedelta(minutes=20)
num_ues = 100
mu_inter = 30 * 1e-3
mu_intra = 1 * 1e-3 
servers = 1
scenario = utils.sc9_parameters
handover_timer = 40

####################################
########### ho_condition ###########
####################################
# ("SNR", dl_threshold, ul_threshold): if the SNR goes under certain thresholds then handover to a new satellite
# ("ELEVATION", elev_threshold): if the elevation angle goes under certain thresholds then handover to a new satellite
# ("TIMER", handover_timer): if not already triggered, handover to a new satellite after handover_timer seconds
# ("VISIBILITY"): standard approach, no input needed, handover when satellite goes out of visibility

###############################################
########### sat_selection_condition ###########
###############################################
# "RANDOM": a random satellite within the ones in visibility
# "MAX_ELEVATION": the satellite with the highest elevation angle from the current time instant
# "MAX_VISIBILITY": the satellite with the longer visibility window from the current time instant
# "AVL_THR": the satellite with the highest available throughput is selected as target satellite



# retrive parameters
data_frame_1 = pd.read_csv(df_name_1)
numbers = re.findall(r'\d+', df_name_1)
beam_size_km = int(numbers[0])
num_beams = int(numbers[1])



# parsing input parameters 
parser = argparse.ArgumentParser(description="Satellite Simulation Script")
parser.add_argument('--servers', type=int, default=servers, help='Number of servers')
parser.add_argument('--num_ues', type=int, default=num_ues, help='Number of User Equipments')
args= parser.parse_args()
servers = args.servers
num_ues = args.num_ues

# (name, position, num_ues, satellites_frame, threshold_snr, satellite servers, satellite mu)
cluster1 = Cluster("Cluster1", (45.40996, 11.89261, 0), num_ues, beam_size_km, num_beams, data_frame_1, servers, mu_inter, mu_intra, scenario, enable_elevation_threshold, elevation_threshold)
clusters = [cluster1] 

# (# year, month, day, hour, minute, second)
time = datetime(2026, 2, 19, 0, 0, 0) 
end_sim_time = time + simTime

# Initial connection phase: each ue connects to a random satellite
service_sats = {}
for cluster in clusters:    
    cluster.initial_connection_phase(time, service_sats, handover_timer)


# increment the time by 100 ms
time += timedelta(seconds=1)

total_iterations = int((end_sim_time - time).total_seconds()) # *1000 (sec --> ms) & /100 (every 100)

print("\nStarting Simulation...")

with tqdm(total=total_iterations, desc="Simulating") as pbar:
    
    # Monitor the SNR of the current connections and apply conditional handover if needed
    while time < end_sim_time:

        cluster1.monitor(time, service_sats, ho_condition_1, sat_selection_condition_1)
        
        # Display the current time on the right side of the progress bar instead of printing it
        pbar.set_postfix(time=time.strftime("%H:%M:%S"))

        # ========================== TO FIX =========================
        """
        # save the instant throughput for all the ues
        for cluster in clusters:
            cluster.save_instant_thr(time, service_sats)
        """
        
        # increment the time by 1 sec
        time += timedelta(seconds=1)
        
        # Manually advance the progress bar by 1 tick
        pbar.update(1)


print("Simulation Complete!\n")

print("Creating the folder with the ue dataframes ...")


output_folders = (
    [f"{cluster.name} dataframes" for cluster in clusters] +
    [f"{cluster.name} throughput" for cluster in clusters] +
    ["Satellite dataframes"]
)

# if there are old results, delete them
for folder in output_folders:
    if os.path.exists(folder):
        shutil.rmtree(folder)

for name, sat in service_sats.items():
    sat.deactivate()

print("Folder created!\n")

print("Creating the folder with the sat dataframes ...")
for cluster in clusters:
    for mini_cluster in cluster.list_beams:
        for ue in mini_cluster.list_ues:
            ue.deactivate(cluster.name)

print("Folder created!\n")
