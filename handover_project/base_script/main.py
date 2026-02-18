from datetime import datetime, timedelta
import numpy as np
import math
import csv
import pandas as pd
from scipy import cluster
import string

from cluster import Cluster
from ue import Ue
import utils

# initial configuration
df_name = "data_frame/satellite_df.csv"
data_frame = pd.read_csv(df_name)

cluster = Cluster("Cluster1", (45.4384, 11.0086, 0), 13, data_frame, -10)

time = datetime(2025, 6, 8, 0, 0, 0) # year, month, day, hour, minute, second
end_sim_time = datetime(2025, 6, 8, 1, 0, 0)

# Initial connection phase and time translation 
data_frame, delay = cluster.initial_connection_phase(time)
# copy the number of connected ues for each satellite to the next time instant
data_frame = utils.propagate_users_to_next_second(data_frame, time, timedelta(seconds=1))
# update the time after the initial connection phase
time += delay

# print the updated DataFrame after the initial connection phase
# print(f"This process has required: {delay.total_seconds()*1000} ms")
print("\n", data_frame[data_frame['time'] == time.strftime("%Y-%m-%d %H:%M:%S")].to_string(), "\n")

#TODO: at the moment, the data frame step is 1 sec, so handover and connection processes times
# are negligible. In the future, we should consider smaller time steps and the time required for these processes.
time = time = (time + timedelta(seconds=1)).replace(microsecond=0)

# Monitor the SNR of the current connections and apply conditional handover if needed
while time < end_sim_time:
    # delay is a list of tuples (ue, delay) where delay is the time required for the handover process of that UE
    data_frame, delay = cluster.monitor(data_frame, time)
    print("\n", data_frame[data_frame['time'] == time.strftime("%Y-%m-%d %H:%M:%S")].to_string(), "\n")
    
    # copy the number of connected ues for each satellite to the next time instant
    data_frame = utils.propagate_users_to_next_second(data_frame, time, timedelta(seconds=1))
    # TODO we are NOT considering the required time for handover for the same reasons of above
    time += timedelta(seconds=1)

print("\n===================================================")
print(f"END OF THE SIMULATION AT TIME: {time}")
print("===================================================\n")

