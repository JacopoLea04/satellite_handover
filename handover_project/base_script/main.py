from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import argparse

from cluster import Cluster
from ue import Ue
from satellite import Satellite

# initial configuration
df_name_1 = "250km_sc9_padova.csv"
data_frame_1 = pd.read_csv(df_name_1)


# satellites parameters
simTime = timedelta(minutes=20)
servers = 1
mu = 1/(30*1e-3) # default is 1/(30*1e-3)
num_ues = 100
num_beams = 25
beam_size_km = 50

########### ho_condtion ###########
# "SNR": if the SNR goes under a certain threshold then handover to a new satellite
# "VISIBILITY": handover only when the current service satellite goes out of visibility
########### sat_selection_condition ###########
# "AVL_THR": the satellite with the highest available throughput is selected as target satellite
# "SNR_THR": the satellite with hightest product thr*snr is selected as target satellite
# "RANDOM": a random satellite within the ones in visibility
# "MAX_VISIBILITY": the satellite with the longer visibility window from the current time instant
# "MAX_ELEVATION": the satellite with the highest elevation angle from the current time instant


# parsing input parameters 
parser = argparse.ArgumentParser(description="Satellite Simulation Script")
parser.add_argument('--servers', type=int, default=servers, help='Number of servers')
parser.add_argument('--num_ues', type=int, default=num_ues, help='Number of User Equipments')
args= parser.parse_args()
servers = args.servers
num_ues = args.num_ues

# (name, position, num_ues, satellites_frame, threshold_snr, satellite servers, satellite mu)
cluster1 = Cluster("Cluster1", (45.40996, 11.89261, 0), num_ues, beam_size_km, num_beams, data_frame_1, 7, servers, mu)
clusters = [cluster1]

# (# year, month, day, hour, minute, second)
time = datetime(2026, 2, 19, 0, 0, 0) 
end_sim_time = time + simTime

# Initial connection phase: each ue connects to a random satellite
service_sats = {}
for cluster in clusters:    
    cluster.initial_connection_phase(time, service_sats)

# increment the time by 100 ms
time += timedelta(seconds=1)

total_iterations = int((end_sim_time - time).total_seconds()) # *1000 (sec --> ms) & /100 (every 100)

print("\nStarting Simulation...")

with tqdm(total=total_iterations, desc="Simulating") as pbar:
    
    # Monitor the SNR of the current connections and apply conditional handover if needed
    while time < end_sim_time:

        cluster1.monitor(time, service_sats, "SNR", "AVL_THR")
        
        # Display the current time on the right side of the progress bar instead of printing it
        pbar.set_postfix(time=time.strftime("%H:%M:%S"))

        # save the instant throughpout for all the ues
        for cluster in clusters:
            cluster.save_instant_thr(time, service_sats)

        # increment the time by 1 sec
        time += timedelta(seconds=1)
        
        # Manually advance the progress bar by 1 tick
        pbar.update(1)

print("Simulation Complete!\n")
print("Creating the folder with the ue dataframes ...")

for name, sat in service_sats.items():
    sat.deactivate()

print("Folder created!\n")

print("Creating the folder with the sat dataframes ...")
for cluster in clusters:
    for ue in cluster.list_ues:
        ue.deactivate(cluster.name)

print("Folder created!\n")