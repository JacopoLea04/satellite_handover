from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import argparse

from cluster_v2 import Cluster
from ue import Ue
from satellite import Satellite

# initial configuration
df_name = "200km_satellite_df.csv"
data_frame = pd.read_csv(df_name)

# satellites parameters
servers = 1
mu = 1/(30*1e-3) # default is 1/(30*1e-3)
num_ues = 50
ho_condition = "SNR"
sat_selection_condition = "AVL_THR"

# parsing input parameters
parser = argparse.ArgumentParser(description="Satellite Simulation Script")
parser.add_argument('--servers', type=int, default=servers, help='Number of servers')
parser.add_argument('--num_ues', type=int, default=num_ues, help='Number of User Equipments')
args= parser.parse_args()
servers = args.servers
num_ues = args.num_ues

# 3. Parse the arguments
args = parser.parse_args()

# (name, position, num_ues, satellites_frame, threshold_snr, satellite servers, satellite mu)
cluster = Cluster("Cluster1", (45.4384, 11.0086, 0), num_ues, data_frame, -10, servers, mu)

# (# year, month, day, hour, minute, second)
time = datetime(2025, 6, 8, 0, 0, 0) 
end_sim_time = datetime(2025, 6, 8, 0, 1, 0)

# Initial connection phase: each ue connects to a random satellite
service_sats = cluster.initial_connection_phase(time)

# increment the time by 1 sec
time += timedelta(seconds=1)

total_iterations = int((end_sim_time - time).total_seconds())

print("\nStarting Simulation...")

with tqdm(total=total_iterations, desc="Simulating") as pbar:
    
    # Monitor the SNR of the current connections and apply conditional handover if needed
    while time < end_sim_time:

        # update the df of each UEs according to its operation at each time instant and update 
        # the list of service satellites
        service_sats = cluster.monitor(time, service_sats, ho_condition, sat_selection_condition)
        
        # Display the current time on the right side of the progress bar instead of printing it
        pbar.set_postfix(time=time.strftime("%H:%M:%S"))

        # increment the time by 1 sec
        time += timedelta(seconds=1)
        
        # Manually advance the progress bar by 1 tick
        pbar.update(1)

print("Simulation Complete!\n")
print("Creating the folder with the ue dataframes ...")

for sat in service_sats:
    sat.deactivate()

print("Folder created!\n")

print("Creating the folder with the sat dataframes ...")

for ue in cluster.list_ues:
    ue.deactivate()

print("Folder created!\n")