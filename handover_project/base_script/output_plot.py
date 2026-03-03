import pandas as pd
from datetime import datetime, timedelta
import utils
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from pathlib import Path
import seaborn as sns
import numpy as np

# ========================================================================================================= # 

# 1. How many satellites in visibility over time
visible_sats_over_time = False
# 2. Evolution of N satellites SNR over time
snr_over_time = False
# 3. Average handover rate 
average_handover_rate = False
# 4. Average handover duration
average_handover_duration = False
# 5. Average service time before the next handover event
average_service_time = False
# 6. Number of handover processes handled by each satelliteprint
ho_handled = False


output_folder = "Output plots"
period = '1h'
N = 10 # to select only a subset of objects (it is used only from function #2)

# ========================================================================================================= # 

# 1. How many satellites in visibility over time
if(visible_sats_over_time):
    print("1. Priting the number of visible satellites ...")
    df_name = "200km_satellite_df.csv"
    data_frame = pd.read_csv(df_name)
    time = datetime(2025, 6, 8, 0, 0, 0) # 4. Average handover duration
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
    os.makedirs(output_folder, exist_ok=True)
    file_name = "1-satellite_visibility.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    print("   Completed!\n")

# ========================================================================================================= # 

# 2. Evolution of N satellites SNR over time
if(snr_over_time):
    print("2. Priting the SNR over time ...")
    df_name = "200km_satellite_df.csv"
    data_frame = pd.read_csv(df_name)
    time = datetime(2025, 6, 8, 0, 0, 0) 
    end_sim_time = datetime(2025, 6, 8, 0, 10, 0)

    visible_satellites = utils.get_satellites_at_time(data_frame, time)
    N = min(N, len(visible_satellites))
    visible_sats = visible_satellites[:N]
    plt.figure(figsize=(10, 5))
    for sat in visible_sats:
        print("  ", sat[0])
        timestamps = []
        snr = []
        time = datetime(2025, 6, 8, 0, 0, 0) 
        while time < end_sim_time:# 4. Average handover duration
            dl_snr = utils.compute_dl_snr(data_frame, sat[0], time)
            snr.append(dl_snr)
            timestamps.append(time)
            time += timedelta(seconds=1)
        lab = sat[0]
        plt.plot(timestamps, snr, linestyle='-', label=lab)

    plt.title('DL SNR over time')
    plt.xlabel('Time (HH:MM:SS)')
    plt.ylabel('DL SNR [dB]')
    plt.grid(True)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    os.makedirs(output_folder, exist_ok=True)
    file_name = "2-dl_snr.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    print("   Completed!\n")

# ========================================================================================================= # 

# 3. Average handover rate
if(average_handover_rate):
    print("3. Priting the average handover rate ...")
    folder_path = Path('Ue dataframes')
    ho_count = []
    num_ues = 0
    for file_path in folder_path.glob('*.csv'):
        df = pd.read_csv(file_path)
        count = len(df[df['event_type'] == 'out_ho'])
        ho_count.append(count)
        num_ues += 1

    # 3.1
    plt.figure(figsize=(10, 5))
    plt.hist(ho_count, bins=range(min(ho_count), max(ho_count) + 2), color='skyblue', edgecolor='black', align='left')
    plt.title(f'Distribution of Handovers per {num_ues} UEs ({period} Period)')
    plt.xlabel('Number of Handovers')
    plt.ylabel('Number of UEs')
    plt.grid(axis='y', alpha=0.3)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "3.1-hist_ho_rate.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 3.2
    plt.figure(figsize=(10, 5))
    sns.kdeplot(ho_count, fill=True, color="orange")
    plt.title(f'Probability Density of Handover Counts per {num_ues} UEs ({period} Period)')
    plt.xlabel('Handovers')
    os.makedirs(output_folder, exist_ok=True)
    file_name = "3.2-pdf_ho_rate.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 3.3
    sorted_data = np.sort(ho_count)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Handovers per {num_ues} UEs ({period} Period)')
    plt.xlabel('Number of Handovers')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "3.3-cdf_ho_rate.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    
    
    print("   Completed!\n")

# ========================================================================================================= # 

# 4. Average handover duration
if(average_handover_duration):
    print("4. Priting the average handover duration ...")
    folder_path = Path('Ue dataframes')
    ho_duration = []
    num_ues = 0
    for file_path in folder_path.glob('*.csv'):
        df = pd.read_csv(file_path)
        duration_list = df[df['event_type'] == 'out_ho']['duration'].tolist()
        duration_ms = [x * 1000 for x in duration_list]
        ho_duration.append(np.mean(duration_ms))
        num_ues += 1

    # 4.1
    plt.figure(figsize=(10, 5))
    sns.kdeplot(ho_duration, fill=True, color="orange")
    plt.title(f'Probability Density of Handover Duration per {num_ues} UEs ({period} Period)')
    plt.xlabel('Duration [ms]')
    os.makedirs(output_folder, exist_ok=True)
    file_name = "4.1-pdf_ho_duration.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 4.2
    sorted_data = np.sort(ho_duration)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Handovers Duration per {num_ues} UEs ({period} Period)')
    plt.xlabel('Duration [ms]')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "4.2-cdf_ho_duration.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    
    
    print("   Completed!\n")

# ========================================================================================================= # 

# 5. Average service time before the next handover event
if(average_service_time):
    print("5. Priting the average time before next handover ...")
    folder_path = Path('Ue dataframes')
    service_time = []
    num_ues = 0
    for file_path in folder_path.glob('*.csv'):
        df = pd.read_csv(file_path)
        df['arrival_time'] = pd.to_datetime(df['arrival_time'], errors='coerce')
        time_diffs_series = df['arrival_time'].diff().dt.total_seconds().dropna().astype(int).tolist()
        service_time.append(np.mean(time_diffs_series))
        num_ues += 1

    # 5.1
    plt.figure(figsize=(10, 5))
    sns.kdeplot(service_time, fill=True, color="orange")
    plt.title(f'Probability Density of Service Time per {num_ues} UEs ({period} Period)')
    plt.xlabel('Duration [s]')
    os.makedirs(output_folder, exist_ok=True)
    file_name = "5.1-pdf_service_time.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 5.2
    sorted_data = np.sort(service_time)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Service Time per {num_ues} UEs ({period} Period)')
    plt.xlabel('Duration [s]')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "5.2-cdf_service_time.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    
    
    print("   Completed!\n")

# ========================================================================================================= # 

# 6. Number of handover processes handled by each satellite
if(ho_handled):
    print("6. Priting the average number of handover handled for each satellite ...")
    folder_path = Path('Satellite dataframes')
    ho_count = []
    num_sats = 0
    for file_path in folder_path.glob('*.csv'):
        try:
            df = pd.read_csv(file_path)
            count = len(df[df['event_type'] == 'out_ho'])
            ho_count.append(count)
            num_sats += 1
        except Exception as e:
            # print("Empty satellite dataframe!")
            continue


    # 6.1
    plt.figure(figsize=(10, 5))
    plt.hist(ho_count, bins=range(min(ho_count), max(ho_count) + 2), color='skyblue', edgecolor='black', align='left')
    plt.title(f'Distribution of Handovers per {num_sats} serving satellites ({period} Period)')
    plt.xlabel('Number of Handovers')
    plt.ylabel('Number of serving satellites')
    plt.grid(axis='y', alpha=0.3)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "6.1-hist_ho_handled.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 6.2
    plt.figure(figsize=(10, 5))
    sns.kdeplot(ho_count, fill=True, color="orange")
    plt.title(f'Probability Density of Handover Counts per {num_sats} serving satellites ({period} Period)')
    plt.xlabel('Handovers')
    os.makedirs(output_folder, exist_ok=True)
    file_name = "6.2-pdf_ho_handled.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 6.3
    sorted_data = np.sort(ho_count)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Handovers per {num_sats} serving satellites ({period} Period)')
    plt.xlabel('Number of Handovers')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "6.3-cdf_ho_handled.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    
    
    print("   Completed!\n")
