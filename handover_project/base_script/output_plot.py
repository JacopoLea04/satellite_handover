import pandas as pd
from datetime import datetime, timedelta
import utils
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from pathlib import Path
import seaborn as sns
import numpy as np

pd.options.mode.chained_assignment = None  # default='warn'

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
# 6. Number of handover processes handled by each satellite
ho_handled = False
# 7. Average throughput
get_throughput = False
# 7.3 throughput considering HO outage time
get_throuthput_ho = False
# 7.3.2 throughput considering HO outage time 
get_throuthput_ho_v2 = False
# 8. Average number and duration of out of services
out_of_service = False
# 9. Number of ping-pong handovers
ping_pong_handovers = True

save_plot_values = False



output_folder = "plots"
# df_name = "75km_satellite_df.csv"
df_padova = "200km_sc9_padova_countdown.csv"
df_munich = "200km_sc9_munich_countdown.csv"
df_lucerna = "200km_sc9_lucerna_countdown.csv"
dfnames = [df_padova, df_munich, df_lucerna]
fnames = ["padova", "munich", "lucerna"]

period = '20 min'
simTimeStart = datetime(2026, 2, 19, 0, 0, 0) 
simTimeEnd = datetime(2026, 2, 19, 0, 20, 0) 
time_step = timedelta(seconds=1)
N = 5 # to select only a subset of objects (it is used only from function #2 and #7)
num_ues_to_plot = 2
colors1 = ['skyblue', 'lightcoral', 'palegreen', 'mocassin', 'plum', 'tan', 'lightpink', 'lightgray', 'darkkhaki', 'paleturquoise']
colors2 = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']


# ========================================================================================================= # 

# 1. How many satellites in visibility over time
if(visible_sats_over_time):
    print("1. Printing the number of visible satellites ...")
    for df_name, fname in zip(dfnames, fnames):
        data_frame = pd.read_csv(df_name)
        time = datetime(2026, 2, 19, 0, 0, 0)
        end_sim_time = datetime(2026, 2, 19, 0, 20, 0)

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
        file_path = os.path.join(output_folder, fname, file_name)
        os.makedirs(os.path.join(output_folder, fname), exist_ok=True)
        plt.savefig(file_path, dpi=300, bbox_inches='tight')

        if(save_plot_values):
            values_df = pd.DataFrame({'timestamp': timestamps, 'elapsed_seconds': np.arange(len(timestamps)), 'visible_satellites': visible_sats})
            csv_file_name = "1-satellite_visibility_values.csv"
            csv_file_path = os.path.join(output_folder, fname, csv_file_name)
            values_df.to_csv(csv_file_path, index=False)
        plt.close()

    print("   Completed!\n")

# ========================================================================================================= # 

# 2. Evolution of N satellites SNR over time
if(snr_over_time):
    print("2. Printing the SNR over time ...")
    for df_name, fname in zip(dfnames, fnames):
        print("\texamining ", fname, " ...")
        data_frame = pd.read_csv(df_name)
        time = datetime(2026, 2, 19, 0, 0, 0)
        end_sim_time = datetime(2026, 2, 19, 0, 20, 0)

        visible_satellites = utils.get_satellites_at_time(data_frame, time)
        n_visible = min(N, len(visible_satellites))
        visible_sats = visible_satellites[:n_visible]
        plt.figure(figsize=(10, 5))
        for sat in visible_sats:
            print("\t\tSAT ID", sat[0])
            timestamps = []
            snr = []
            time = datetime(2026, 2, 19, 0, 0, 0) 
            while time < end_sim_time:
                dl_snr = utils.compute_dl_snr(data_frame, sat[0], time)
                if(dl_snr is None):
                    pass
                    # print("DL SNR NONE for satellite", sat[0], "at time", time)
                else:
                    pass #dl_snr += np.random.normal(0, 0.5)  # add gaussian noise
                snr.append(dl_snr)
                timestamps.append(time)
                time += timedelta(seconds=1)
            lab = sat[0]
            plt.plot(timestamps, snr, linestyle='-', label=lab)

        plt.title('DL SNR over time')
        plt.xlabel('Time (HH:MM:SS)')
        plt.ylabel('DL SNR [dB]')
        plt.ylim((0, 20))
        plt.grid(True)
        plt.legend()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        os.makedirs(output_folder, exist_ok=True)
        file_name = "2-dl_snr.png"
        file_path = os.path.join(output_folder, fname, file_name)
        os.makedirs(os.path.join(output_folder, fname), exist_ok=True)
        plt.savefig(file_path, dpi=300, bbox_inches='tight')
        plt.close()
    print("\tCompleted!\n")

# ========================================================================================================= # 

# 3. Average handover rate
if(average_handover_rate):
    print("3. Printing the average handover rate ...")
    for i, (df_name, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + " dataframes")
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
        sns.kdeplot(ho_count, fill=False, color="orange", alpha=0, ax=ax2)
        ax2.set_ylabel('Probability Density', color='orange')
        ax2.tick_params(axis='y', labelcolor='orange')

        plt.title(f'Distribution & Density of Handovers ({period} Period)')
        os.makedirs(output_folder, exist_ok=True)
        file_path_png = os.path.join(output_folder, fname, f"3.1-pdf_ho_plot.png")
        plt.savefig(file_path_png, dpi=300, bbox_inches='tight')

        if(save_plot_values):
            # Export the discrete Histogram data (for LaTeX \addplot ybar)
            ho_count_counts = pd.Series(ho_count).value_counts().sort_index()
            hist_df = pd.DataFrame({
                'number_of_handovers': ho_count_counts.index, 
                'count': ho_count_counts.values
            })
            csv_file_name_hist = f"3.1-handover_counts.csv"
            csv_file_path_hist = os.path.join(output_folder, fname, csv_file_name_hist)
            hist_df.to_csv(csv_file_path_hist, index=False)
            
            # Export the continuous KDE data (for LaTeX smooth plot)
            # We extract from ax2 because that's where the KDE was drawn
            kde_line = ax2.lines[0]
            kde_x = kde_line.get_xdata()
            kde_y = kde_line.get_ydata()
            
            kde_df = pd.DataFrame({
                'number_of_handovers': kde_x, 
                'density': kde_y
            })
            csv_file_name_kde = f"3.1-handover_kde.csv"
            csv_file_path_kde = os.path.join(output_folder, fname, csv_file_name_kde)
            kde_df.to_csv(csv_file_path_kde, index=False)

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
        file_path = os.path.join(output_folder, fname, file_name)
        plt.savefig(file_path, dpi=300, bbox_inches='tight')
        if(save_plot_values):
            values_df = pd.DataFrame({'number_of_handovers': sorted_data, 'probability': yvals})
            csv_file_name = "3.2-cdf_ho_rate_values.csv"
            csv_file_path = os.path.join(output_folder, fname, csv_file_name)
            values_df.to_csv(csv_file_path, index=False)
        plt.close()

    print("   Completed!\n")

# ========================================================================================================= # 

# 4. Average handover duration
if(average_handover_duration):
    print("4. Priting the average handover duration ...")
    for i, (df_name, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + " dataframes")
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

        # 1. Assign the plot to 'ax' so we can extract the data later
        ax = sns.kdeplot(ho_duration, fill=True, color="orange")
        sns.kdeplot(ho_duration, fill=False, color="orange", alpha=0, ax=ax)

        plt.title(f'Probability Density of Handover Duration per {num_ues} UEs ({period} Period)')
        plt.xlabel('Duration [ms]')

        os.makedirs(output_folder, exist_ok=True)

        # save the original PNG visualization
        file_name_png = "4.1-pdf_ho_duration.png"
        file_path_png = os.path.join(output_folder, fname, file_name_png)
        plt.savefig(file_path_png, dpi=300, bbox_inches='tight')
        if(save_plot_values):
            # Extract the computed coordinates
            kde_line = ax.lines[0]
            x_data = kde_line.get_xdata()
            y_data = kde_line.get_ydata()

            # Save the CSV to the same output folder
            file_name_csv = "4.1-pdf_ho_duration.csv"
            file_path_csv = os.path.join(output_folder, fname, file_name_csv)

            df = pd.DataFrame({'Duration_ms': x_data, 'Density': y_data})
            df.to_csv(file_path_csv, index=False)
        plt.close()

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
        file_path = os.path.join(output_folder, fname, file_name)
        plt.savefig(file_path, dpi=300, bbox_inches='tight')
        if(save_plot_values):
            values_df = pd.DataFrame({'duration': sorted_data, 'probability': yvals})
            csv_file_name = "4.2-cdf_ho_duration_values.csv"
            csv_file_path = os.path.join(output_folder, fname, csv_file_name)
            values_df.to_csv(csv_file_path, index=False)
        plt.close()

    
    print("   Completed!\n")

# ========================================================================================================= # 

# 5. Average service time before the next handover event
if(average_service_time):
    print("5. Priting the average time before next handover ...")
    for i, (df_name, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + " dataframes")
        service_time = []
        num_ues = 0

        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            df['arrival_time'] = pd.to_datetime(df['arrival_time'], errors='coerce')
            time_diffs_series = []
            # take two consecutive rows per iteration
            for r1, r2 in zip(df.itertuples(), df.iloc[1:].itertuples()):
                
                # Ora r1 è la riga attuale, r2 è la successiva
                t1, ev1 = r1.arrival_time, r1.event_type
                t2, ev2 = r2.arrival_time, r2.event_type
                

                if ev1 != "out_serv" and ev2 != "out_serv":
                    duration = (t2 - t1).total_seconds()
                    time_diffs_series.append(duration)

            service_time.append(np.mean(time_diffs_series))
            num_ues += 1

        ''' # Old version
        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            df['arrival_time'] = pd.to_datetime(df['arrival_time'], errors='coerce')
            time_diffs_series = df['arrival_time'].diff().dt.total_seconds().dropna().astype(int).tolist()
            service_time.append(np.mean(time_diffs_series))
            num_ues += 1
        '''

        # 5.1
        plt.figure(figsize=(10, 5))
        
        # Assign the plot to 'ax'
        ax = sns.kdeplot(service_time, fill=True, color="orange")
        
        plt.title(f'Probability Density of Service Time per {num_ues} UEs ({period} Period)')
        plt.xlabel('Duration [s]')
        os.makedirs(output_folder, exist_ok=True)
        
        # Save PNG
        file_name = f"5.1-pdf_service_time.png"
        file_path = os.path.join(output_folder, fname, file_name)
        plt.savefig(file_path, dpi=300, bbox_inches='tight')
        
        if(save_plot_values):
            # 2. Import SciPy and NumPy (make sure these are at the top of your script if you prefer)
            from scipy.stats import gaussian_kde
            import numpy as np
            
            # Initialize the exact same KDE math that Seaborn uses
            kde = gaussian_kde(service_time)
            
            # Grab the exact X-axis boundaries that Seaborn calculated for the visual plot
            x_min, x_max = ax.get_xlim()
            
            # Generate 200 smooth coordinates across that exact range
            kde_x = np.linspace(x_min, x_max, 200)
            kde_y = kde(kde_x)
            
            # Create the DataFrame
            values_df = pd.DataFrame({
                'Duration_s': kde_x, 
                'Density': kde_y
            })
            
            csv_file_name = f"5.1-pdf_service_time_values_{folder_path.name}.csv"
            csv_file_path = os.path.join(output_folder, fname, csv_file_name)
            values_df.to_csv(csv_file_path, index=False)
        plt.close()

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
        file_path = os.path.join(output_folder, fname, file_name)
        plt.savefig(file_path, dpi=300, bbox_inches='tight')
        if(save_plot_values):
            values_df = pd.DataFrame({'service_time': sorted_data, 'probability': yvals})
            csv_file_name = "5.2-cdf_service_time_values.csv"
            csv_file_path = os.path.join(output_folder, fname, csv_file_name)
            values_df.to_csv(csv_file_path, index=False)
        plt.close()
    
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

    plt.title(f'Out and In Handovers Distribution & Density per {num_sats} Serving Satellites ({period})')
    os.makedirs(output_folder, exist_ok=True)
    combined_file = os.path.join(output_folder, "6.1-pdf_satellite_ho.png")
    plt.savefig(combined_file, dpi=300, bbox_inches='tight')
    plt.close()


    # 6.2
    sorted_data = np.sort(ho_count)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Out and In Handovers per {num_sats} serving satellites ({period} Period)')
    plt.xlabel('Number of Handovers')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "6.2-cdf_ho_handled.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print("   Completed!\n")

# ========================================================================================================= #

# 7. Average throughput
# if(get_throughput):
    
#     print("7. Average trhoguhput ...")
#     folder_path = Path('Ue dataframes')

#     # Phase 1: know which satellite the ue_x is connected to for each time instant
#     # list to collect connection data and time instant for all ues
#     ues = []
#     count = 0 # compute the throughput for only N UEs to avoid crowded plots
#     for file_path in folder_path.glob('*.csv'): # scan all the ue dataframes (ClusterN-UeXX_handover_events.csv)
#         suffix = "_handover_events.csv"
#         ue_id = file_path.name.replace(suffix, "") # ClusterN-UeXX
#         if(count == N):
#             break
#         df = pd.read_csv(file_path) # read the current UE dataframe
#         result = list(df[['arrival_time', 'dest_satellite']].to_records(index=False))

#         # list where it is saved at which satellite the ue is connected for all time instants
#         # index 0 correpsonds to time instant 0s, index 1 correpsonds to time instant 1s, ...
#         connected_to = []
#         ho_times = [0]
#         for ii, xx in enumerate(result):
#             ti = datetime.strptime(result[ii][0], "%Y-%m-%d %H:%M:%S")
#             if(ii == len(result)-1):
#                 tf = simTimeEnd
#             else:
#                 tf = datetime.strptime(result[ii+1][0], "%Y-%m-%d %H:%M:%S")
#             sec = int((tf-ti).total_seconds())
#             ho_times.append(sec+ho_times[-1])
#             connected_to = connected_to + [result[ii][1]]*sec
        
#         # the last element (out of scope for the sim time) is the ue_id and the ho time instances
#         connected_to.append((ue_id, ho_times[1:]))
#         ues.append(connected_to)
#         count += 1

#     # Phase 2: know the max DL/UL thr. of satellite y at specific time instant
#     # Phase 3: know  how many users a satellite is connected to at a specific time instnat
#     all_thr = []
#     data_frame = pd.read_csv(df_name) # TODO we now have multiple dataframe names
#     for ue in ues:
#         ue_id = ue[-1][0]
#         ho_times = ue[-1][1]
#         print("   UE ID", ue_id)
#         thr = []
#         for sec, sat_name in enumerate(ue[:-1]):
#             time = simTimeStart + timedelta(seconds=sec)
            
#             #the ue is not connected to any satellite
#             if(pd.isna(sat_name)): 
#                 thr.append((0,0))
#                 continue

#             # the ue is connected to a satellite
#             max_dl_thr, max_ul_thr = utils.get_max_thr(data_frame, sat_name, time)

#             folder_name = "Satellite dataframes"
#             file_name = sat_name + "_handover_events.csv"
#             file_path = Path(folder_name) / file_name
#             curr_sat_df = pd.read_csv(file_path)
#             curr_sat_df['arrival_time'] = pd.to_datetime(curr_sat_df['arrival_time'])
#             curr_sat_df = curr_sat_df[curr_sat_df['arrival_time'] <= time]
#             num_ues = 0
#             for index, row in curr_sat_df.iterrows():
#                 if row['event_type'] == 'init_con':
#                     num_ues += 1
#                 elif row['event_type'] == 'out_ho':
#                     num_ues -= 1
#                 elif row['event_type'] == 'in_ho':
#                     num_ues += 1
#             dl_thr = max_dl_thr / num_ues 
#             ul_thr = max_ul_thr / num_ues 
#             thr.append((dl_thr, ul_thr))

#         # the last element (out of scope for the sim time) is the ue_id and the ho time instances
#         thr.append((ue_id, ho_times))
#         all_thr.append(thr)

#     # 7.1 DL thr plot
#     plt.figure(figsize=(10,5))
#     for ii, xx in enumerate(all_thr):
#         dl_thr = list(zip(*xx[:-1]))[0]
#         ho_times = xx[-1][1]
#         ho_values = [dl_thr[i-1] for i in ho_times] # avoid index overflow
#         ue_id = xx[-1][0]
#         plt.scatter(ho_times, ho_values, marker='x', label = f'UE ID {ue_id} ho', color=colors1[ii])
#         plt.plot(dl_thr, label = f'UE ID {ue_id}', linestyle="--", color=colors1[ii])
#     plt.title('DL throughputs')
#     plt.xlabel('Time [sec]')
#     plt.ylabel('Throghput [Mbit/s]')
#     plt.grid(True)
#     plt.legend()
#     os.makedirs(output_folder, exist_ok=True)
#     file_name = "7.1 DL Throughput.png"
#     file_path = os.path.join(output_folder, file_name)
#     plt.savefig(file_path, dpi=300, bbox_inches='tight')

#     # 7.2 UL thr plot
#     plt.figure(figsize=(10,5))
#     for ii, xx in enumerate(all_thr):
#         ul_thr = list(zip(*xx[:-1]))[1]
#         ho_times = xx[-1][1]
#         ho_values = [ul_thr[i-1] for i in ho_times] # avoid index overflow
#         ue_id = xx[-1][0]
#         plt.scatter(ho_times, ho_values, marker='x', label = f'UE ID {ue_id} ho', color=colors1[ii])
#         plt.plot(ul_thr, label = f'UE ID {ue_id}', linestyle="--", color=colors1[ii])
#     plt.title('UL throughputs')
#     plt.xlabel('Time [sec]')
#     plt.ylabel('Throghput [Mbit/s]')
#     plt.grid(True)
#     plt.legend()
#     os.makedirs(output_folder, exist_ok=True)
#     file_name = "7.2 UL Throughput.png"
#     file_path = os.path.join(output_folder, file_name)
#     plt.savefig(file_path, dpi=300, bbox_inches='tight')

        
#     print("   Completed!\n")



# # 7.3 Get the throughput considering the hadover outage time
# if(get_throuthput_ho):
#     print("7.3 Plotting the average throughput considering the hangover outage time ...")
#     current_cluster_name = "Cluster3"
#     current_master_name = "200km_sc9_lucerna_countdown.csv"
#     folder_path = Path(current_cluster_name + ' dataframes')
#     ues_handovers_lists = []
#     count = 0 # compute the throughput for only N UEs to avoid crowded plots
#     # loop for each ue in the current cluster
#     for file_path in folder_path.glob('*.csv'): # scan all the ue dataframes (ClusterN-UeXX_handover_events.csv)
#         suffix = "_handover_events.csv"
#         ue_id = file_path.name.replace(suffix, "") # ClusterN-UeXX
#         if(count == num_ues_to_plot):
#             break
#         ue_handovers_df = pd.read_csv(file_path) # read the current UE dataframe
#         ue_out_ho_df = ue_handovers_df[ue_handovers_df['event_type'] == 'out_ho']
#         # parse arrival time
#         arr_naive = pd.to_datetime(ue_out_ho_df['arrival_time'], errors='coerce')
#         # important: the arrival time is a datetime object with localization on a specific timezone, while unix epoch time is always UTC.
#         # to avoid offset issues, we need to specify that the time is in the timezone of the simulation, (in this case europe) and
#         # convert it to UTC timezone, so we can subtract it from the departure time with no issues.
#         arr = arr_naive.dt.tz_localize('Europe/Berlin').dt.tz_convert('UTC')
#         # parse departure time (unix time is always UTC)
#         dep = pd.to_datetime(ue_out_ho_df['departure_time'], unit='s', errors='coerce', utc=True)
#         # compute the difference
#         duration_series = dep - arr
#         # convert to milliseconds
#         duration_ms = duration_series.dt.total_seconds() * 1000
#         # add a first element zero to account for the initial connection happening instantly at the beginning of the simulation (initial condition)
#         duration_ms = pd.concat([pd.Series([0]), duration_ms], ignore_index=True)
#         # print("Examining UE ", ue_id)
#         # print("Duration ms (First 5):\n", duration_ms.head())
#         ue_handovers_df['ho_duration_ms'] = duration_ms.values
#         ue_handovers_list = list(ue_handovers_df[['arrival_time', 'dest_satellite', 'ho_duration_ms']].to_records(index=False))
#         ues_handovers_lists.append((ue_id, ue_handovers_list))
#         count = count + 1
    
#     all_thr_dl = []
#     all_thr_ul = []
#     satellite_df_path = Path("Satellite dataframes")
#     for ue_id, ue_handovers_list in ues_handovers_lists:

#         ho_timestamps = np.array(ue_handovers_list)['arrival_time'].tolist()
#         # print(ho_timestamps)

#         per_ue_throughputs_dl = []
#         per_ue_throughputs_ul = []
#         for ii, handover_item in enumerate(ue_handovers_list):
#             ho_time = datetime.strptime(handover_item[0], "%Y-%m-%d %H:%M:%S")
#             sat_name = handover_item[1]
#             ho_duration_ms = handover_item[2]
#             if(sat_name is not None and not pd.isna(sat_name)):
#                 satellite_file_path = satellite_df_path / f"{sat_name}_handover_events.csv"
#                 if satellite_file_path.exists():
#                     sat_df = pd.read_csv(satellite_file_path)
#                     sat_df['arrival_time'] = pd.to_datetime(sat_df['arrival_time'])
#                     num_ues = 0
#                     if(ii == len(ue_handovers_list)-1):
#                         next_ho_time = simTimeEnd
#                         break
#                     else:
#                         next_ho_time = datetime.strptime(ue_handovers_list[ii+1][0], "%Y-%m-%d %H:%M:%S")
#                     event_map = {
#                         'init_con': 1,  # Adds a user
#                         'in_ho': 1,      # Adds a user
#                         'out_ho': -1     # Removes a user
#                     }

#                     before_connecting_df = sat_df[sat_df['arrival_time'] < ho_time]
#                     before_connecting_df['user change'] = before_connecting_df['event_type'].map(event_map)
#                     net_sum_before = before_connecting_df['user change'].sum()
#                     after_connecting_df = sat_df[sat_df['arrival_time'].between(ho_time, next_ho_time)]
#                     after_connecting_df['user_change'] = after_connecting_df['event_type'].map(event_map)
#                     after_connecting_df.set_index('arrival_time', inplace=True)
#                     net_changes = after_connecting_df['user_change'].resample('1s').sum() 
#                     connected_users = net_changes.cumsum() + net_sum_before
#                     orbit_df = pd.read_csv(current_master_name)

#                     time = ho_time
#                     temp_dl_thr, temp_ul_thr = [], []

#                     while time < next_ho_time:
#                         max_dl_thr, max_ul_thr = utils.get_max_thr(orbit_df, sat_name, time)
#                         temp_dl_throughput = max_dl_thr / connected_users[time]
#                         temp_ul_throughput = max_ul_thr / connected_users[time]
#                         if(ho_duration_ms >= 1000):
#                             temp_dl_throughput = 0
#                             temp_ul_throughput = 0
#                             ho_duration_ms -= 1000
#                         elif(ho_duration_ms > 0):
#                             temp_dl_throughput = temp_dl_throughput * (1 - ho_duration_ms/1000)
#                             temp_ul_throughput = temp_ul_throughput * (1 - ho_duration_ms/1000)
#                             ho_duration_ms = 0
#                         per_ue_throughputs_dl.append(temp_dl_throughput)
#                         per_ue_throughputs_ul.append(temp_ul_throughput)
#                         time = time + timedelta(seconds = 1)
                     
#                 else:
#                     print(f"Satellite dataframe for {sat_name} not found!")
#             else:
#                 print("UE is not connected to any satellite at time ", ho_time)
#         all_thr_dl.append((ue_id, per_ue_throughputs_dl, ho_timestamps))
#         all_thr_ul.append((ue_id, per_ue_throughputs_ul))
#         print("Completed UE ", ue_id)
        
#     print("Plotting the DL throughput considering the handover outage time ...")
#     plt.figure(figsize=(10,5))
#     for ii, id_throughput in enumerate(all_thr_dl):
#         dl_thr = list(id_throughput[1])
#         ue_id = id_throughput[0]
#         ho_times = id_throughput[2]
#         time_vector = pd.date_range(start=simTimeStart, periods=200, freq='1s')
#         plt.plot(time_vector,dl_thr[:200], label = f'UE ID {ue_id}', color=colors1[ii])
#     plt.title('DL throughputs')
#     plt.xlabel('Time [sec]')
#     plt.ylabel('Throghput [Mbit/s]')
#     plt.grid(True)
#     plt.legend()
#     os.makedirs(output_folder, exist_ok=True)
#     file_name = "7.3 DL Throughput_ho.png"
#     file_path = os.path.join(output_folder, file_name)
#     plt.savefig(file_path, dpi=300, bbox_inches='tight')

#     print("   Completed!\n")


# 7.3.2 Get the throughput considering the hadover outage time (v2)
if(get_throuthput_ho_v2):
    print("7.3.2 Plotting the average throughput considering the hangover outage time ...")
    for i, (df_name, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + " throughput")
        ues_thr = []
        for file_path in folder_path.glob('*.csv'):
            suffix = "_thr_over_time.csv"
            ue_id = file_path.name.replace(suffix, "") # ClusterN-UeXX
            df = pd.read_csv(file_path)
            thr = df['dl_thr'].tolist()
            ues_thr.append(thr)
        avg_thr = np.mean(ues_thr, axis=0).tolist()

        plt.figure(figsize=(10,5))
        time_vector = pd.date_range(start=simTimeStart, periods=len(avg_thr), freq='1s')
        plt.plot(time_vector, avg_thr, label = f'{fname}', color=colors1[2])
        print(f"{fname} avg thr: ", np.mean(avg_thr))
        plt.title('Average DL throughputs over time')
        plt.xlabel('Time')
        plt.ylabel('DL Throghput [Mbit/s]')
        plt.grid(True)
        plt.legend()
        os.makedirs(output_folder, exist_ok=True)
        file_name = "7.3.2-DL_throughput_ho.png"
        file_path = os.path.join(output_folder, fname, file_name)
        plt.savefig(file_path, dpi=300, bbox_inches='tight')
        # Export to CSV
        if(save_plot_values):
            df_export = pd.DataFrame({
                'Seconds': range(len(avg_thr)),  # Easy integer X-axis for LaTeX
                'Timestamp': time_vector,          # Preserved for reference
                'Cluster_Thr': avg_thr
            })
            
            csv_file_name = "7.3.2-DL_throughput_ho_values.csv"
            csv_file_path = os.path.join(output_folder, fname, csv_file_name)
            df_export.to_csv(csv_file_path, index=False)
        plt.close()

    print("   Completed!\n")

# ========================================================================================================= #

# 8. Average number and duration of out of services
if(out_of_service):
    print("8. Priting the average number and durtation of out of services ...")
    folder_path = Path('Cluster1 dataframes')
    avg_lens = []
    avg_losses = []
    num_ues = 0

    for file_path in folder_path.glob('*.csv'):
        df = pd.read_csv(file_path)
        duration = []
        count = 0
        # take two consecutive rows per iteration
        for r1, r2 in zip(df.itertuples(), df.iloc[1:].itertuples()):
            ev1 = r1.event_type
            ev2 = r2.event_type
            
            if ev2 == "out_serv":
                count += 1
            elif ev1 == "out_serv" and ev2 != "out_serv":
                duration.append(count+1)
                count = 0
        if(len(duration)>0):
            avg_lens.append(np.mean(duration))
            avg_losses.append(len(duration))
        num_ues += 1

    if(len(avg_lens) > 0):
        print(f"   Averaged number of out of service events: {np.mean(avg_losses)} , for an average time of {np.mean(avg_lens)} ms")
    else:
        print("   No out of service events")
    

    # Do not plot anything since usually we never have out of service events.
    '''
    # 8.1
    #print(avg_lens)
    #print(avg_losses)
    plt.figure(figsize=(10, 5))
    sns.kdeplot(avg_lens, fill=True, color="orange")
    plt.title(f'Probability Density of Out of Service Duration per {num_ues} UEs ({period} Period)')
    plt.xlabel('Duration [s]')
    os.makedirs(output_folder, exist_ok=True)
    file_name = "8.1-pdf_oos_duration.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 8.2
    sorted_data = np.sort(avg_lens)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Out of Service per {num_ues} UEs ({period} Period)')
    plt.xlabel('Duration [s]')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "8.2-cdf_oos_duration.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')

    # 8.3
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.hist(avg_losses, bins=range(min(avg_losses), max(avg_losses) + 2), 
            color='skyblue', edgecolor='black', align='left', alpha=0.6)
    ax1.set_xlabel('Duration [s]')
    ax1.set_ylabel('Number of Out of Service', color='steelblue', fontweight='bold')
    ax1.tick_params(axis='y', labelcolor='steelblue')
    ax1.grid(axis='y', alpha=0.3)

    ax2 = ax1.twinx()
    sns.kdeplot(avg_losses, fill=True, color="orange", ax=ax2, alpha=0.4)
    ax2.set_ylabel('Probability Density', color='darkorange', fontweight='bold')
    ax2.tick_params(axis='y', labelcolor='darkorange')

    plt.title(f'Out of Service events per {num_ues} UEs ({period})')
    os.makedirs(output_folder, exist_ok=True)
    combined_file = os.path.join(output_folder, "8.3-pdf_oos_events.png")
    plt.savefig(combined_file, dpi=300, bbox_inches='tight')

    # 8.4
    sorted_data = np.sort(avg_lens)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.figure(figsize=(10,5))
    plt.plot(sorted_data, yvals, marker='.', linestyle='none')
    plt.title(f'Cumulative Distribution of Out of Service Events per {num_ues} UEs ({period} Period)')
    plt.xlabel('Duration [s]')
    plt.ylabel('CDF')
    plt.grid(True)
    os.makedirs(output_folder, exist_ok=True)
    file_name = "8.4-cdf_oos_duration.png"
    file_path = os.path.join(output_folder, file_name)
    plt.savefig(file_path, dpi=300, bbox_inches='tight')
    '''
    
    
    print("   Completed!\n")

# ========================================================================================================= #

# 9. Number of ping-pong handovers
if(ping_pong_handovers):
    print("9. Printing the average number of ping-pong handovers ...")
    folder_path = Path('Cluster2 dataframes')
    ping_pong_count = []
    num_ues = 0
    for file_path in folder_path.glob('*.csv'):
        df = pd.read_csv(file_path)
        count = 0
        for r1, r2 in zip(df.itertuples(), df.iloc[1:].itertuples()):
            ev1 = r1.from_satellite
            ev2 = r2.dest_satellite
            
            if ev1 == ev2:
                count += 1
        ping_pong_count.append(count)
        num_ues += 1

    print(f"   Average number of ping-pong handovers: {np.mean(ping_pong_count)}")