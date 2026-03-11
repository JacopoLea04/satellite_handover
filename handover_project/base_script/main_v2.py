from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import argparse

from cluster_v2 import Cluster
from ue import Ue
from satellite import Satellite

# initial configuration
df_name_1 = "75km_sc9_padova.csv"
data_frame_1 = pd.read_csv(df_name_1)
df_name_2 = "75km_sc9_munich.csv"
data_frame_2 = pd.read_csv(df_name_2)
#df_name_3 = "75km_sc9_lucerna.csv"
#data_frame_3 = pd.read_csv(df_name_3)

# satellites parameters
simTime = timedelta(minutes=20)
servers = 1
mu = 1/(30*1e-3) # default is 1/(30*1e-3)
num_ues = 1000
ho_condition = "SNR"
sat_selection_condition = "AVL_THR"

# parsing input parameters 
parser = argparse.ArgumentParser(description="Satellite Simulation Script")
parser.add_argument('--servers', type=int, default=servers, help='Number of servers')
parser.add_argument('--num_ues', type=int, default=num_ues, help='Number of User Equipments')
args= parser.parse_args()
servers = args.servers
num_ues = args.num_ues

# (name, position, num_ues, satellites_frame, threshold_snr, satellite servers, satellite mu)
cluster1 = Cluster("Cluster1", (45.40996, 11.89261, 0), num_ues, data_frame_1, -10, servers, mu)
cluster2 = Cluster("Cluster2", (48.14295, 11.57997, 0), num_ues, data_frame_2, -10, servers, mu)
#cluster3 = Cluster("Cluster3", (47.04240, 8.328983, 0), num_ues, data_frame_3, -10, servers, mu)
clusters = [cluster1, cluster2]

# (# year, month, day, hour, minute, second)
time = datetime(2026, 2, 19, 0, 0, 0) 
end_sim_time = time + simTime

# Initial connection phase: each ue connects to a random satellite
service_sats = {}
for cluster in clusters:    
    cluster.initial_connection_phase(time, service_sats)

# increment the time by 100 ms
time += timedelta(milliseconds=100)

total_iterations = int((end_sim_time - time).total_seconds()*10) # *1000 (sec --> ms) & /100 (every 100)

print("\nStarting Simulation...")

with tqdm(total=total_iterations, desc="Simulating") as pbar:
    
    # Monitor the SNR of the current connections and apply conditional handover if needed
    while time < end_sim_time:
        for cluster in clusters:
            cluster.monitor(time, service_sats, ho_condition, sat_selection_condition)
        
        # Display the current time on the right side of the progress bar instead of printing it
        pbar.set_postfix(time=time.strftime("%H:%M:%S"))

        # increment the time by 1 sec
        time += timedelta(milliseconds=100)
        
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