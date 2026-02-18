from datetime import datetime, timedelta
import numpy as np
import math
import csv
import pandas as pd
from scipy import cluster
import string
import matplotlib.pyplot as plt

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


# save all rates at the first iteration
list_ues = cluster.get_list_ues()
dl_thr_list = []

for ue in list_ues:
    connection_info = ue.get_connection_info()
    if connection_info is not None:
        dl_thr = utils.compute_dl_thr(data_frame, connection_info[0], time)
    else:
        dl_thr = 0
    dl_thr_list.append((ue, [dl_thr]))




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

    # each time save the corrispoding dl_thr value for each UE
    for ue in list_ues:
        connection_info = ue.get_connection_info()
        if connection_info is not None:
            dl_thr = utils.compute_dl_thr(data_frame, connection_info[0], time)
        else:
            dl_thr = 0
        # append the new dl_thr value to the list of dl_thr values for that UE
        for ue_dl_thr in dl_thr_list:
            if ue_dl_thr[0] == ue:
                ue_dl_thr[1].append(dl_thr)
                break
    
    # copy the number of connected ues for each satellite to the next time instant
    data_frame = utils.propagate_users_to_next_second(data_frame, time, timedelta(seconds=1))
    # TODO we are NOT considering the required time for handover for the same reasons of above
    time += timedelta(seconds=1)

# Create a figure and set its size (width, height in inches)
plt.figure(figsize=(10, 6))

# Loop through each tuple in your list
for ue, thr_list in dl_thr_list:
    
    # Generate generic time steps for the X-axis (0, 1, 2, 3...)
    # based on the length of the throughput list
    time_steps = range(len(thr_list))
    
    # Plot the line for this UE
    # marker='.' adds a small dot at each data point for clarity
    plt.plot(time_steps, thr_list, marker='.', label=f'{ue.id}')  # Label with UE ID for the legend
    
# Add chart titles and labels
plt.title('Downlink Throughput Over Time per UE', fontsize=14)
plt.xlabel('Time Step (Seconds)', fontsize=12)
plt.ylabel('DL Throughput', fontsize=12)

# Add a grid for easier reading
plt.grid(True, linestyle='--', alpha=0.7)

# Add a legend so we know which color belongs to which UE
# bbox_to_anchor moves the legend slightly outside the plot if you have many UEs
plt.legend(title='User Equipment (UE)', loc='upper left', bbox_to_anchor=(1, 1))

# Adjust layout so the legend doesn't get cut off
plt.tight_layout()

plt.savefig('dl_throughput_over_time.png')  # Save the figure as a PNG file

# Display the graph
# plt.show()


print("\n===================================================")
print(f"END OF THE SIMULATION AT TIME: {time}")
print("===================================================\n")

