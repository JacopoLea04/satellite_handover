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
visible_sats_over_time = True
# 2. Evolution of N satellites SNR over time
snr_over_time = True
# 3. Average handover rate 
average_handover_rate = True
# 4. Average handover duration
average_handover_duration = True
# 5. Average service time before the next handover event
average_service_time = True
# 6. Number of handover processes handled by each satelliteprint
ho_handled = True
# 7. Average throughput
get_throughput = True


output_folder = "Output plots"
df_name = "200km_satellite_df.csv"
period = '20 min'
simTimeStart = datetime(2025, 6, 8, 0, 0, 0) 
simTimeEnd = datetime(2025, 6, 8, 0, 20, 0) 
N = 3 # to select only a subset of objects (it is used only from function #2 and #7)
colors1 = ['skyblue', 'lightcoral', 'palegreen', 'mocassin', 'plum', 'tan', 'lightpink', 'lightgray', 'darkkhaki', 'paleturquoise']
colors2 = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']


# ========================================================================================================= # 

# 1. How many satellites in visibility over time
if(visible_sats_over_time):
    print("1. Priting the number of visible satellites ...")
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
    data_frame = pd.read_csv(df_name)
    time = datetime(2025, 6, 8, 0, 0, 0) 
    end_sim_time = datetime(2025, 6, 8, 0, 10, 0)

    visible_satellites = utils.get_satellites_at_time(data_frame, time)
    N = min(N, len(visible_satellites))
    visible_sats = visible_satellites[:N]
    plt.figure(figsize=(10, 5))
    for sat in visible_sats:
        print("   SAT ID", sat[0])
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
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.hist(ho_count, bins=range(min(ho_count), max(ho_count) + 2), 
            color='skyblue', edgecolor='black', align='left', alpha=0.7)
    ax1.set_xlabel('Number of Handovers')
    ax1.set_ylabel('Number of UEs (Frequency)', color='skyblue')
    ax1.tick_params(axis='y', labelcolor='skyblue')
    ax1.grid(axis='y', alpha=0.3)

    ax2 = ax1.twinx() 
    sns.kdeplot(ho_count, fill=True, color="orange", ax=ax2)
    ax2.set_ylabel('Probability Density', color='orange')
    ax2.tick_params(axis='y', labelcolor='orange')

    plt.title(f'Distribution & Density of Handovers ({period} Period)')
    os.makedirs(output_folder, exist_ok=True)
    file_path = os.path.join(output_folder, "3.1-pdf_ho_plot.png")
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 3.2
    sorted_data = np.sort(ho_count)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Handovers per {num_ues} UEs ({period} Period)')
    plt.xlabel('Number of Handovers')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "3.2-cdf_ho_rate.png"
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
        df = df[df['event_type'] == 'out_ho']
        # parse arrival time
        arr_naive = pd.to_datetime(df['arrival_time'], errors='coerce')
        # important: the arrival time is a datetime object with localization on a specific timezone, while unix epoch time is always UTC.
        # to avoid offset issues, we need to specify that the time is in the timezone of the simulation, (in this case europe) and
        # convert it to UTC timezone, so we can subtract it from the departure time with no issues.
        arr = arr_naive.dt.tz_localize('Europe/Berlin').dt.tz_convert('UTC')

        # parse departure time (unix time is always UTC)
        dep = pd.to_datetime(df['departure_time'], unit='s', errors='coerce', utc=True)
        # compute the difference
        duration_series = dep - arr
        # convert to milliseconds
        duration_ms = duration_series.dt.total_seconds() * 1000
        # calculate the mean
        ho_duration.append(duration_ms.mean())

        # print("Duration ms (First 5):\n", duration_ms.head())
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
        # needed beacuse there are some saved satellites which have empty df
        try:
            df = pd.read_csv(file_path)
            count = len(df[df['event_type'] == 'out_ho'])
            count = count + len(df[df['event_type'] == 'in_ho'])
            ho_count.append(count)
            num_sats += 1
        except Exception as e:
            print("Empty satellite dataframe!")
            continue


    # 6.1
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.hist(ho_count, bins=range(min(ho_count), max(ho_count) + 2), 
            color='skyblue', edgecolor='black', align='left', alpha=0.6)
    ax1.set_xlabel('Number of Handovers')
    ax1.set_ylabel('Number of Serving Satellites', color='steelblue', fontweight='bold')
    ax1.tick_params(axis='y', labelcolor='steelblue')
    ax1.grid(axis='y', alpha=0.3)

    ax2 = ax1.twinx()
    sns.kdeplot(ho_count, fill=True, color="orange", ax=ax2, alpha=0.4)
    ax2.set_ylabel('Probability Density', color='darkorange', fontweight='bold')
    ax2.tick_params(axis='y', labelcolor='darkorange')

    plt.title(f'Handover Distribution & Density per {num_sats} Serving Satellites ({period})')
    os.makedirs(output_folder, exist_ok=True)
    combined_file = os.path.join(output_folder, "6.1-pdf_satellite_ho.png")
    plt.savefig(combined_file, dpi=300, bbox_inches='tight')


    # 6.2
    sorted_data = np.sort(ho_count)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Handovers per {num_sats} serving satellites ({period} Period)')
    plt.xlabel('Number of Handovers')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "6.2-cdf_ho_handled.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    
    
    print("   Completed!\n")

# ========================================================================================================= #

# 7. Average throughput
if(get_throughput):
    
    print("7. Average trhoguhput ...")
    folder_path = Path('Ue dataframes')

    # Phase 1: know which satellite the ue_x is connected to for each time instant
    # list to collect connection data and time instant for all ues
    ues = []
    count = 0
    for file_path in folder_path.glob('*.csv'):
        suffix = "_handover_events.csv"
        ue_id = file_path.name.replace(suffix, "")

        if(count == N):
            break
        df = pd.read_csv(file_path)
        result = list(df[['arrival_time', 'dest_satellite']].to_records(index=False))

        # list where it is saved at which satellite the ue is connected for all time instants
        # index 0 correpsonds to time instant 0s, index 1 correpsonds to time instant 1s, ...
        connected_to = []
        ho_times = [0]
        for ii, xx in enumerate(result):
            ti = datetime.strptime(result[ii][0], "%Y-%m-%d %H:%M:%S")
            if(ii == len(result)-1):
                tf = simTimeEnd
            else:
                tf = datetime.strptime(result[ii+1][0], "%Y-%m-%d %H:%M:%S")
            sec = int((tf-ti).total_seconds())
            ho_times.append(sec+ho_times[-1])
            connected_to = connected_to + [result[ii][1]]*sec
        
        # the last element (out of scope for the sim time) is the ue_id and the ho time instances
        connected_to.append((ue_id, ho_times[1:]))
        ues.append(connected_to)
        count += 1

    # Phase 2: know the max DL/UL thr. of satellite y at specific time instant
    # Phase 3: know  how many users a satellite is connected to at a specific time instnat
    all_thr = []
    data_frame = pd.read_csv(df_name)
    for ue in ues:
        ue_id = ue[-1][0]
        ho_times = ue[-1][1]
        print("   UE ID", ue_id)
        thr = []
        for sec, sat_name in enumerate(ue[:-1]):
            time = simTimeStart + timedelta(seconds=sec)
            max_dl_thr, max_ul_thr = utils.get_max_thr(data_frame, sat_name, time)

            folder_name = "Satellite dataframes"
            file_name = sat_name + "_handover_events.csv"
            file_path = Path(folder_name) / file_name
            curr_sat_df = pd.read_csv(file_path)
            curr_sat_df['arrival_time'] = pd.to_datetime(curr_sat_df['arrival_time'])
            curr_sat_df = curr_sat_df[curr_sat_df['arrival_time'] <= time]
            num_ues = 0
            for index, row in curr_sat_df.iterrows():
                if row['event_type'] == 'init_con':
                    num_ues += 1
                elif row['event_type'] == 'out_ho':
                    num_ues -= 1
                elif row['event_type'] == 'in_ho':
                    num_ues += 1
            dl_thr = max_dl_thr / num_ues 
            ul_thr = max_ul_thr / num_ues 
            thr.append((dl_thr, ul_thr))

        # the last element (out of scope for the sim time) is the ue_id and the ho time instances
        thr.append((ue_id, ho_times))
        all_thr.append(thr)

    # 7.1 DL thr plot
    plt.figure(figsize=(10,5))
    for ii, xx in enumerate(all_thr):
        dl_thr = list(zip(*xx[:-1]))[0]
        ho_times = xx[-1][1]
        ho_values = [dl_thr[i-1] for i in ho_times] # avoid index overflow
        ue_id = xx[-1][0]
        plt.scatter(ho_times, ho_values, marker='x', label = f'UE ID {ue_id} ho', color=colors1[ii])
        plt.plot(dl_thr, label = f'UE ID {ue_id}', linestyle="--", color=colors1[ii])
    plt.title('DL throughputs')
    plt.xlabel('Time [sec]')
    plt.ylabel('Throghput [Mbit/s]')
    plt.grid(True)
    plt.legend()
    os.makedirs(output_folder, exist_ok=True)
    file_name = "7.1 DL Throughput.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 7.2 UL thr plot
    plt.figure(figsize=(10,5))
    for ii, xx in enumerate(all_thr):
        ul_thr = list(zip(*xx[:-1]))[1]
        ho_times = xx[-1][1]
        ho_values = [ul_thr[i-1] for i in ho_times] # avoid index overflow
        ue_id = xx[-1][0]
        plt.scatter(ho_times, ho_values, marker='x', label = f'UE ID {ue_id} ho', color=colors1[ii])
        plt.plot(ul_thr, label = f'UE ID {ue_id}', linestyle="--", color=colors1[ii])
    plt.title('UL throughputs')
    plt.xlabel('Time [sec]')
    plt.ylabel('Throghput [Mbit/s]')
    plt.grid(True)
    plt.legend()
    os.makedirs(output_folder, exist_ok=True)
    file_name = "7.2 UL Throughput.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

        
    print("   Completed!\n")