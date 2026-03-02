import pandas as pd
from datetime import datetime, timedelta
import utils
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# 1. How many satellites in visibility over time
visible_sats_over_time = False


# 1. How many satellites in visibility over time
if(visible_sats_over_time):
    print("Priting the number of visible satellites ...")
    df_name = "200km_satellite_df.csv"
    data_frame = pd.read_csv(df_name)
    time = datetime(2025, 6, 8, 0, 0, 0) 
    end_sim_time = datetime(2025, 6, 8, 1, 0, 0)

    visible_sats = []
    timestamps = []
    while time < end_sim_time:
        visible_satellites = utils.get_satellites_at_time(data_frame, time)
        visible_sats.append(len(visible_satellites))
        timestamps.append(time)
        time += timedelta(seconds=1)

    plt.figure(figsize=(10, 5))
    plt.plot(timestamps, visible_sats, color='blue', linestyle='-')
    plt.title('Visible Satellites Over Time')
    plt.xlabel('Time (HH:MM:SS)')
    plt.ylabel('Number of Visible Satellites')
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    output_folder = "Output plots"
    os.makedirs(output_folder, exist_ok=True)
    file_name = "satellite_visibility.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    print("Completed!\n")



# 2. How many connected UEs over time: plot multiple satellites on the same graph so as to see how users shift from one to another
# 3. Distribution function for the average handover time from when it is stanrd to when it is concluded
# 4. Distribution function for the average service time before the next handover event