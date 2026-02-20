from datetime import datetime, timedelta
import pandas as pd

from cluster import Cluster
from ue import Ue
from satellite import Satellite

# initial configuration
df_name = "data_frame/satellite_df.csv"
data_frame = pd.read_csv(df_name)

# (name, position, num_ues, satellites_frame, threshold_snr)
cluster = Cluster("Cluster1", (45.4384, 11.0086, 0), 13, data_frame, -10)

# (# year, month, day, hour, minute, second)
time = datetime(2025, 6, 8, 0, 0, 0) 
end_sim_time = datetime(2025, 6, 8, 1, 0, 0)

# Initial connection phase: each ue connects to a random satellite
service_sats = cluster.initial_connection_phase(time)

# increment the time by 1 sec
time += timedelta(seconds=1)

# Monitor the SNR of the current connections and apply conditional handover if needed
while time < end_sim_time:

    # update the df of each UEs according to its operation at each time instant and update 
    # the list of service satellites
    service_stats = cluster.monitor(time, service_stats)

    # increment the time by 1 sec
    time += timedelta(seconds=1)

# TODO print or handle the dataframe of all UEs and service satellites
# service_sats is a list containing all the service satellite objects created and their own dfs 
# ues_list should contain all the ues with their corrisponding dfs
# ues_list = cluster.get_ues_list()


