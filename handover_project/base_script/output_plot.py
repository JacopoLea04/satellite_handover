import pandas as pd
from datetime import datetime, timedelta
import utils
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from pathlib import Path
from scipy.stats import gaussian_kde
import numpy as np
import re
import random
import seaborn as sns 

pd.options.mode.chained_assignment = None

USE_PREHO_DATA = True           # True: Legge i dati SDN. False: Legge i dati Baseline.
save_plot_values = False          # Salva i valori dei grafici singoli in formato CSV.

visible_sats_over_time = True     # 1. Quanti satelliti e beam sono visibili
average_handover_rate = True      # 2. Numero medio di handover (PDF)
average_handover_duration = True # 3. Durata media dell'esecuzione dell'handover
average_service_time = True     # 4. Tempo medio di servizio continuo
ho_handled = True                # 5. Carico di segnalazione (HO gestiti) per satellite
out_of_service = True           # 6. Durata dei periodi di Out of Service (OOS)
get_throuthput_ho_v2 = True     # 7. Throughput medio nel tempo con intervallo di confidenza
cdf_throughput = True            # 8. CDF del Throughput (Standard IEEE col 5% edge)
ping_pong_handovers = True       # 9. Statistiche sugli handover Ping-Pong
doppler_shifts = True           # 10. Doppler Shift nel tempo (DL/UL) con focus event
satellite_load_distribution = True       # 11. Distribuzione del carico di traffico per satellite (KDE)
beam_footprint_heatmap = True

# Grafici Comparativi 
comparative_plots = True

if USE_PREHO_DATA:
    print("\n--- ANALISI DEI DATI PREDICTIVE HANDOVER (PREHO) ---")
    dataframes_folder_suffix = " dataframes_sdn"
    throughput_folder_suffix = " throughput_sdn"
    output_folder = "plots_sdn"
else:
    print("\n--- ANALISI DEI DATI BASELINE (GREEDY / AVL_THR) ---")
    dataframes_folder_suffix = " dataframes_baseline"
    throughput_folder_suffix = " throughput_baseline"
    output_folder = "plots_baseline"

os.makedirs(output_folder, exist_ok=True)

# dataframes parameters
df_name = "50km_25beams_sc9_padova.csv"
padova_lat, padova_lon = 45.40996, 11.89261
dfnames = [df_name] 
fnames = ["padova"]
enable_elevation_threshold = True
elevation_threshold = 30

period = '30 min'
num_ues_label = 300
simTimeStart = datetime(2026, 2, 19, 0, 0, 0) 
simTimeEnd = datetime(2026, 2, 19, 0, 30, 0) 

beam_size_km = 50
num_beams = 25
padova_positions = utils.calculate_beams_grid(padova_lat, padova_lon, beam_size_km, num_beams)

colors1 = ['skyblue', 'lightcoral', 'palegreen', 'mocassin', 'plum', 'tan', 'lightpink', 'lightgray', 'darkkhaki', 'paleturquoise']
colors2 = ['navy', 'crimson', 'green', 'chocolate', 'purple', 'saddlebrown', 'deeppink', 'gray', 'olive', 'teal']

if visible_sats_over_time:
    """
    Generates time-series plots showing the physical resources available over the target cluster.
    It plots the number of visible satellites and the number of visible beams over the simulation duration.
    """
    print("1. Printing the number of visible satellites ...")
    plt.figure(figsize=(10, 5))
    index = 0
    for df_name_iter, fname in zip(dfnames, fnames):
        data_frame = pd.read_csv(df_name_iter)
        time = simTimeStart
        
        visible_sats = []
        timestamps = []
        while time < simTimeEnd:
            visible_satellites = utils.get_satellites_at_time(data_frame, time)
            visible_sats.append(len(visible_satellites))
            timestamps.append(time)
            time += timedelta(seconds=1)

        plt.plot(timestamps, visible_sats, color=colors1[index], linestyle='-', label=fname)
        index += 1
        
        if save_plot_values:
            values_df = pd.DataFrame({'timestamp': timestamps, 'elapsed_seconds': np.arange(len(timestamps)), 'visible_satellites': visible_sats})
            target_dir = os.path.join(output_folder, fname)
            os.makedirs(target_dir, exist_ok=True)
            values_df.to_csv(os.path.join(target_dir, "1-satellite_visibility_values.csv"), index=False)

    plt.title('Visible Satellites Over Time')
    plt.legend()
    plt.xlabel('Time (HH:MM:SS)')
    plt.ylabel('Number of Visible Satellites')
    plt.grid(True)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, "1-satellite_visibility.png"), dpi=300, bbox_inches='tight')
    plt.close()

    print("   Completed!")

    print("1.1 Printing the number of visible beams for each ue ...")
    for df_name_iter, fname in zip(dfnames, fnames):
        plt.figure(figsize=(10, 5))
        index = 0
        data_frame = pd.read_csv(df_name_iter)
        beams_names = ["Beam NO", "Beam Center", "Beam SE"]
        visible_sat_beam_NO, visible_sat_beam_center, visible_sat_beam_SE = [], [], []

        time = simTimeStart
        while time < simTimeEnd:
            visible_sats_now = utils.get_satellites_at_time(data_frame, time)
            visible_sats_for_each_minicluster = [[] for _ in range(num_beams)]
            
            for sat in visible_sats_now:
                sat_lat, sat_lon, sat_alt = sat[1], sat[2], sat[3]
                sat_cell_boundaries = utils.compute_cell_boundaries_lla(sat_lat, sat_lon, beam_size_km*1000, int(np.sqrt(num_beams)))
                visible_clusters_indices = utils.check_clusters_visibility(padova_positions, sat_cell_boundaries, int(np.sqrt(num_beams)), enable_elevation_threshold, elevation_threshold, sat_lat, sat_lon, sat_alt)
                
                if len(visible_clusters_indices) == 0: continue
                satellite_beam_indices = utils.get_coverage_beam_indices_matrix(visible_clusters_indices, int(np.sqrt(num_beams)))
                
                rows, cols = visible_clusters_indices.shape
                for ii in range(rows):
                    for jj in range(cols):
                        idx_cluster = visible_clusters_indices[ii][jj]
                        idx_sat_beam = satellite_beam_indices[ii][jj]
                        if idx_sat_beam != -1:
                            visible_sats_for_each_minicluster[idx_cluster].append((sat, idx_sat_beam))

            visible_sat_beam_NO.append(len(visible_sats_for_each_minicluster[0]))
            visible_sat_beam_center.append(len(visible_sats_for_each_minicluster[int(num_beams/2)]))
            visible_sat_beam_SE.append(len(visible_sats_for_each_minicluster[-1]))
            time += timedelta(seconds=1)

        total_seconds = int((simTimeEnd - simTimeStart).total_seconds())
        timestamps = [simTimeStart + timedelta(seconds=i) for i in range(total_seconds + 1)][:-1]

        plt.plot(timestamps, visible_sat_beam_NO, color=colors1[index], label=beams_names[index]); index += 1
        plt.plot(timestamps, visible_sat_beam_center, color=colors1[index], label=beams_names[index]); index += 1
        plt.plot(timestamps, visible_sat_beam_SE, color=colors1[index], label=beams_names[index])
            
        plt.title('Visible Beams Over Time')
        plt.legend()
        plt.xlabel('Time (HH:MM:SS)')
        plt.ylabel('Number of Visible Beams')
        plt.grid(True)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_folder, f"1.1-beam_visibility_{fname}.png"), dpi=300, bbox_inches='tight')

        if save_plot_values:
            values_df = pd.DataFrame({'timestamp': timestamps, 'elapsed_seconds': np.arange(len(timestamps)), 'visible_sat_beam_NO': visible_sat_beam_NO, 'visible_sat_beam_center': visible_sat_beam_center, 'visible_sat_beam_SE': visible_sat_beam_SE})
            target_dir = os.path.join(output_folder, fname)
            os.makedirs(target_dir, exist_ok=True)
            values_df.to_csv(os.path.join(target_dir, "1.1-satellite_visibility_values.csv"), index=False)
        plt.close()
    print("   Completed!\n")

if average_handover_rate:
    """
    Parses UE dataframes to calculate and plot the Probability Density Function (PDF) of the average number of intra-satellite and inter-satellite handovers performed per UE.
    """
    print("2. Printing the average handover rate ...")
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + dataframes_folder_suffix)
        intra_ho_count, inter_ho_count = [], []
        
        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            intra_ho_count.append(len(df[df['event_type'] == 'intra_ho']))
            inter_ho_count.append(len(df[df['event_type'] == 'inter_ho']))

        color = plt.cm.tab10(i)
        csv_data = {}
        
        if len(intra_ho_count) > 1 and min(intra_ho_count) != max(intra_ho_count):
            kde_intra = gaussian_kde(intra_ho_count)
            x_min_intra, x_max_intra = min(intra_ho_count), max(intra_ho_count)
            margin_intra = (x_max_intra - x_min_intra) * 0.2
            kde_x_intra = np.linspace(x_min_intra - margin_intra, x_max_intra + margin_intra, 500)
            kde_y_intra = kde_intra(kde_x_intra)

            ax.plot(kde_x_intra, kde_y_intra, color=color, linestyle='-', linewidth=1.5)
            ax.fill_between(kde_x_intra, kde_y_intra, alpha=0.2, color=color, label=f"Cluster {i+1}: {fname}, intra")
            
            idx_max = np.argmax(kde_y_intra)
            x_peak, y_peak = kde_x_intra[idx_max], kde_y_intra[idx_max]
            ax.plot(x_peak, y_peak, marker='*', color=color, markersize=14, markeredgecolor='black', zorder=5)
            ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=color, va='bottom')

            csv_data['intra_ho_x'] = kde_x_intra
            csv_data['intra_ho_density'] = kde_y_intra

        if len(inter_ho_count) > 1 and min(inter_ho_count) != max(inter_ho_count):
            kde_inter = gaussian_kde(inter_ho_count)
            x_min_inter, x_max_inter = min(inter_ho_count), max(inter_ho_count)
            margin_inter = (x_max_inter - x_min_inter) * 0.2
            kde_x_inter = np.linspace(x_min_inter - margin_inter, x_max_inter + margin_inter, 500)
            kde_y_inter = kde_inter(kde_x_inter)

            ax.plot(kde_x_inter, kde_y_inter, color=color, linestyle='--', linewidth=1.5)
            ax.fill_between(kde_x_inter, kde_y_inter, alpha=0.1, color=color, label=f"Cluster {i+1}: {fname}, inter")
            
            idx_max = np.argmax(kde_y_inter)
            x_peak, y_peak = kde_x_inter[idx_max], kde_y_inter[idx_max]
            ax.plot(x_peak, y_peak, marker='o', color=color, markersize=8, markeredgecolor='black', zorder=5)
            ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=color, va='bottom')

            csv_data['inter_ho_x'] = kde_x_inter
            csv_data['inter_ho_density'] = kde_y_inter

        if save_plot_values and csv_data:
            os.makedirs(os.path.join(output_folder, fname), exist_ok=True)
            kde_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in csv_data.items()])) 
            kde_df.to_csv(os.path.join(output_folder, fname, "2-handover.csv"), index=False)

    ax.set_title(f'Probability Density of Handovers - All Clusters ({period} Period) - {num_ues_label} UEs')
    ax.set_xlabel('Number of Handovers')
    ax.set_ylabel('Probability Density')
    ax.grid(axis='y', alpha=0.3)
    ax.legend(title="Clusters", bbox_to_anchor=(1.05, 1), loc='upper left')
    fig.savefig(os.path.join(output_folder, "2-handover_pdf.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("   Completed!\n")

if average_handover_duration:
    """
    Computes and plots the Probability Density Function of the execution duration for intra and inter handovers, extracting processing delays from the UE telemetry data.
    """
    print("3. Printing the average handover duration ...")
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + dataframes_folder_suffix)
        intra_ho_duration, inter_ho_duration = [], []
        
        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            df_1 = df[df['event_type'] == 'intra_ho']
            df_2 = df[df['event_type'] == 'inter_ho']

            arr_1 = pd.to_datetime(df_1['arrival_time'], errors='coerce', utc=True)
            arr_2 = pd.to_datetime(df_2['arrival_time'], errors='coerce', utc=True)
            dep_1 = pd.to_datetime(df_1['departure_time'], errors='coerce', utc=True)
            dep_2 = pd.to_datetime(df_2['departure_time'], errors='coerce', utc=True)
            
            mean_1 = (dep_1 - arr_1).dt.total_seconds().mean() * 1000
            mean_2 = (dep_2 - arr_2).dt.total_seconds().mean() * 1000
            
            if pd.notna(mean_1): intra_ho_duration.append(mean_1)
            if pd.notna(mean_2): inter_ho_duration.append(mean_2)

        color = plt.cm.tab10(i)
        csv_data = {}
        
        if len(intra_ho_duration) > 1 and min(intra_ho_duration) != max(intra_ho_duration):
            kde_intra = gaussian_kde(intra_ho_duration)
            x_min_intra, x_max_intra = min(intra_ho_duration), max(intra_ho_duration)
            margin_intra = (x_max_intra - x_min_intra) * 0.2
            kde_x_intra = np.linspace(x_min_intra - margin_intra, x_max_intra + margin_intra, 500)
            kde_y_intra = kde_intra(kde_x_intra)

            ax.plot(kde_x_intra, kde_y_intra, color=color, linestyle='-', linewidth=1.5)
            ax.fill_between(kde_x_intra, kde_y_intra, alpha=0.2, color=color, label=f"Cluster {i+1}: {fname}, intra")
            
            idx_max = np.argmax(kde_y_intra)
            x_peak, y_peak = kde_x_intra[idx_max], kde_y_intra[idx_max]
            ax.plot(x_peak, y_peak, marker='*', color=color, markersize=14, markeredgecolor='black', zorder=5)
            ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=color, va='bottom')

            csv_data['intra_ho_x'] = kde_x_intra
            csv_data['intra_ho_density'] = kde_y_intra

        if len(inter_ho_duration) > 1 and min(inter_ho_duration) != max(inter_ho_duration):
            kde_inter = gaussian_kde(inter_ho_duration)
            x_min_inter, x_max_inter = min(inter_ho_duration), max(inter_ho_duration)
            margin_inter = (x_max_inter - x_min_inter) * 0.2
            kde_x_inter = np.linspace(x_min_inter - margin_inter, x_max_inter + margin_inter, 500)
            kde_y_inter = kde_inter(kde_x_inter)

            ax.plot(kde_x_inter, kde_y_inter, color=color, linestyle='--', linewidth=1.5)
            ax.fill_between(kde_x_inter, kde_y_inter, alpha=0.1, color=color, label=f"Cluster {i+1}: {fname}, inter")
            
            idx_max = np.argmax(kde_y_inter)
            x_peak, y_peak = kde_x_inter[idx_max], kde_y_inter[idx_max]
            ax.plot(x_peak, y_peak, marker='o', color=color, markersize=8, markeredgecolor='black', zorder=5)
            ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=color, va='bottom')

            csv_data['inter_ho_x'] = kde_x_inter
            csv_data['inter_ho_density'] = kde_y_inter

        if save_plot_values and csv_data:
            os.makedirs(os.path.join(output_folder, fname), exist_ok=True)
            kde_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in csv_data.items()])) 
            kde_df.to_csv(os.path.join(output_folder, fname, "3-handover_duration.csv"), index=False)

    ax.set_title(f'Probability Density of Handovers Duration - All Clusters ({period} Period) - {num_ues_label} UEs')
    ax.set_xlabel('Duration [ms]')
    ax.set_ylabel('Probability Density')
    ax.grid(axis='y', alpha=0.3)
    ax.legend(title="Clusters", bbox_to_anchor=(1.05, 1), loc='upper left')
    fig.savefig(os.path.join(output_folder, "3-handover_duration.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("   Completed!\n")

if average_service_time:
    """
    Evaluates topological stability by calculating the continuous service time a UE maintains with a single beam or satellite before a new handover event is triggered.
    """
    print("4. Printing the average time before next handover ...")
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + dataframes_folder_suffix)
        cluster_beam_durations, cluster_sat_durations = [], []
        
        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            if df.empty: continue
            
            df['arrival_time'] = pd.to_datetime(df['arrival_time'], errors='coerce', utc=True)
            df = df.sort_values('arrival_time')
            
            curr_sat, curr_beam = None, None
            sat_start_time, beam_start_time = None, None
            
            for row in df.itertuples():
                t = row.arrival_time
                dest_sat = row.dest_satellite if pd.notna(row.dest_satellite) and str(row.dest_satellite) != 'None' else None
                dest_beam = row.dest_beam_index if pd.notna(row.dest_beam_index) and str(row.dest_beam_index) != 'None' else None

                if dest_sat is None:
                    if curr_sat is not None:
                        cluster_sat_durations.append((t - sat_start_time).total_seconds())
                        curr_sat = None
                    if curr_beam is not None:
                        cluster_beam_durations.append((t - beam_start_time).total_seconds())
                        curr_beam = None 
                else:
                    if (row.event_type == 'inter_ho' or row.event_type == 'init_con'):
                        if curr_sat is not None: cluster_sat_durations.append((t - sat_start_time).total_seconds())
                        if curr_beam is not None: cluster_beam_durations.append((t - beam_start_time).total_seconds())
                        curr_sat, curr_beam = dest_sat, dest_beam
                        sat_start_time, beam_start_time = t, t
                    elif (row.event_type == 'intra_ho'):
                        if curr_beam is not None: cluster_beam_durations.append((t - beam_start_time).total_seconds())
                        curr_beam = dest_beam
                        beam_start_time = t

        color = plt.cm.tab10(i)
        csv_data = {}
        
        if len(cluster_beam_durations) > 1 and min(cluster_beam_durations) != max(cluster_beam_durations):
            kde_intra = gaussian_kde(cluster_beam_durations)
            x_min_intra, x_max_intra = min(cluster_beam_durations), max(cluster_beam_durations)
            margin_intra = (x_max_intra - x_min_intra) * 0.2
            kde_x_intra = np.linspace(x_min_intra - margin_intra, x_max_intra + margin_intra, 500)
            kde_y_intra = kde_intra(kde_x_intra)

            ax.plot(kde_x_intra, kde_y_intra, color=color, linestyle='-', linewidth=1.5)
            ax.fill_between(kde_x_intra, kde_y_intra, alpha=0.2, color=color, label=f"Cluster {i+1}: {fname}, intra")
            
            idx_max = np.argmax(kde_y_intra)
            x_peak, y_peak = kde_x_intra[idx_max], kde_y_intra[idx_max]
            ax.plot(x_peak, y_peak, marker='*', color=color, markersize=14, markeredgecolor='black', zorder=5)
            ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=color, va='bottom')

            csv_data['intra_ho_x'] = kde_x_intra
            csv_data['intra_ho_density'] = kde_y_intra

        if len(cluster_sat_durations) > 1 and min(cluster_sat_durations) != max(cluster_sat_durations):
            kde_inter = gaussian_kde(cluster_sat_durations)
            x_min_inter, x_max_inter = min(cluster_sat_durations), max(cluster_sat_durations)
            margin_inter = (x_max_inter - x_min_inter) * 0.2
            kde_x_inter = np.linspace(x_min_inter - margin_inter, x_max_inter + margin_inter, 500)
            kde_y_inter = kde_inter(kde_x_inter)

            ax.plot(kde_x_inter, kde_y_inter, color=color, linestyle='--', linewidth=1.5)
            ax.fill_between(kde_x_inter, kde_y_inter, alpha=0.1, color=color, label=f"Cluster {i+1}: {fname}, inter")
            
            idx_max = np.argmax(kde_y_inter)
            x_peak, y_peak = kde_x_inter[idx_max], kde_y_inter[idx_max]
            ax.plot(x_peak, y_peak, marker='o', color=color, markersize=8, markeredgecolor='black', zorder=5)
            ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=color, va='bottom')

            csv_data['inter_ho_x'] = kde_x_inter
            csv_data['inter_ho_density'] = kde_y_inter

        if save_plot_values and csv_data:
            os.makedirs(os.path.join(output_folder, fname), exist_ok=True)
            kde_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in csv_data.items()])) 
            kde_df.to_csv(os.path.join(output_folder, fname, "4-service_time.csv"), index=False)

    ax.set_title(f'Probability Density of Service Time - All Clusters ({period} Period) - {num_ues_label} UEs')
    ax.set_xlabel('Service Time [s]')
    ax.set_ylabel('Probability Density')
    ax.grid(axis='y', alpha=0.3)
    ax.legend(title="Clusters", bbox_to_anchor=(1.05, 1), loc='upper left')
    fig.savefig(os.path.join(output_folder, "4-service_time.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("   Completed!\n")

if ho_handled:
    """
    Analyzes the signaling load on the space segment by plotting the cumulative distribution of handovers processed by each individual satellite node.
    """
    print("5. Priting the average number of handover handled for each satellite ...")
    folder_path = Path('Satellite' + dataframes_folder_suffix)
    intra_ho_count, inter_ho_count = [], []
    num_sats = 0
    fname = 'Satellite'
    fig, ax = plt.subplots(figsize=(12, 6))

    for file_path in folder_path.glob('*.csv'):
        try:
            df = pd.read_csv(file_path)
            intra_ho_count.append(len(df[df['event_type'] == 'intra_ho']))
            inter_ho_count.append(len(df[df['event_type'] == 'inter_ho']))
            num_sats += 1
        except Exception:
            continue

    csv_data = {}
    if len(intra_ho_count) > 1 and min(intra_ho_count) != max(intra_ho_count):
        kde_intra = gaussian_kde(intra_ho_count)
        x_min_intra, x_max_intra = min(intra_ho_count), max(intra_ho_count)
        margin_intra = (x_max_intra - x_min_intra) * 0.2
        kde_x_intra = np.linspace(x_min_intra - margin_intra, x_max_intra + margin_intra, 500)
        kde_y_intra = kde_intra(kde_x_intra)

        ax.plot(kde_x_intra, kde_y_intra, color=colors1[0], linestyle='-', linewidth=1.5)
        ax.fill_between(kde_x_intra, kde_y_intra, alpha=0.2, color=colors1[0], label=f"Intra-handovers")
        
        idx_max = np.argmax(kde_y_intra)
        x_peak, y_peak = kde_x_intra[idx_max], kde_y_intra[idx_max]
        ax.plot(x_peak, y_peak, marker='*', color=colors1[0], markersize=14, markeredgecolor='black', zorder=5)
        ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=colors1[0], va='bottom')

        csv_data['intra_ho_x'] = kde_x_intra
        csv_data['intra_ho_density'] = kde_y_intra

    if len(inter_ho_count) > 1 and min(inter_ho_count) != max(inter_ho_count):
        kde_inter = gaussian_kde(inter_ho_count)
        x_min_inter, x_max_inter = min(inter_ho_count), max(inter_ho_count)
        margin_inter = (x_max_inter - x_min_inter) * 0.2
        kde_x_inter = np.linspace(x_min_inter - margin_inter, x_max_inter + margin_inter, 500)
        kde_y_inter = kde_inter(kde_x_inter)

        ax.plot(kde_x_inter, kde_y_inter, color=colors1[1], linestyle='--', linewidth=1.5)
        ax.fill_between(kde_x_inter, kde_y_inter, alpha=0.1, color=colors1[1], label=f"Inter-handovers")
        
        idx_max = np.argmax(kde_y_inter)
        x_peak, y_peak = kde_x_inter[idx_max], kde_y_inter[idx_max]
        ax.plot(x_peak, y_peak, marker='o', color=colors1[1], markersize=8, markeredgecolor='black', zorder=5)
        ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=colors1[1], va='bottom')

        csv_data['inter_ho_x'] = kde_x_inter
        csv_data['inter_ho_density'] = kde_y_inter

    if save_plot_values and csv_data:
        os.makedirs(os.path.join(output_folder, fname), exist_ok=True)
        kde_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in csv_data.items()])) 
        kde_df.to_csv(os.path.join(output_folder, fname, "5-num_of_hos_per_sat.csv"), index=False)

    ax.set_title(f'Cumulative Distribution of Out and In Handovers per {num_sats} serving satellites ({period} Period) - {num_ues_label} UEs')
    ax.set_xlabel('Number of Handovers')
    ax.set_ylabel('Probability Density')
    ax.grid(axis='y', alpha=0.3)
    ax.legend(title="Clusters", bbox_to_anchor=(1.05, 1), loc='upper left')
    fig.savefig(os.path.join(output_folder, "5-ho_per_sat.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("   Completed!\n")

if out_of_service:
    """
    Parses connection states to calculate and plot the continuous Out of Service (OOS) duration, representing the downtime a UE experiences between link loss and restoration.
    """
    print("6. Printing the average out of service time (lost_conn to rest_conn) ...")
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + dataframes_folder_suffix)
        cluster_out_serv_durations = []
        
        # Filtro per ignorare la disconnessione deterministica finale
        end_threshold = simTimeEnd - timedelta(seconds=60)
        
        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            if df.empty: continue
            
            df['arrival_time'] = pd.to_datetime(df['arrival_time'], format='mixed', errors='coerce').dt.tz_localize(None)
            df = df.sort_values('arrival_time')
            out_serv_start_time = None
            
            for row in df.itertuples():
                t = row.arrival_time
                dest_sat = row.dest_satellite if pd.notna(row.dest_satellite) and str(row.dest_satellite) != 'None' else None

                if dest_sat is None:
                    if out_serv_start_time is None and t < end_threshold: 
                        out_serv_start_time = t
                else:
                    if out_serv_start_time is not None:
                        cluster_out_serv_durations.append((t - out_serv_start_time).total_seconds())
                        out_serv_start_time = None 

        color = plt.cm.tab10(i)
        csv_data = {}
        
        if len(cluster_out_serv_durations) > 1 and min(cluster_out_serv_durations) != max(cluster_out_serv_durations):
            kde_out = gaussian_kde(cluster_out_serv_durations)
            x_min_out, x_max_out = min(cluster_out_serv_durations), max(cluster_out_serv_durations)
            margin_out = (x_max_out - x_min_out) * 0.2
            kde_x_out = np.linspace(x_min_out - margin_out, x_max_out + margin_out, 500)
            kde_y_out = kde_out(kde_x_out)

            ax.plot(kde_x_out, kde_y_out, color=color, linestyle='-', linewidth=1.5)
            ax.fill_between(kde_x_out, kde_y_out, alpha=0.3, color=color, label=f"Cluster {i+1}: {fname}")
            
            idx_max = np.argmax(kde_y_out)
            x_peak, y_peak = kde_x_out[idx_max], kde_y_out[idx_max]
            ax.plot(x_peak, y_peak, marker='s', color=color, markersize=8, markeredgecolor='black', zorder=5)
            ax.annotate(f'  {x_peak:.1f}', xy=(x_peak, y_peak), fontsize=8, color=color, va='bottom')

            csv_data['out_serv_x'] = kde_x_out
            csv_data['out_serv_density'] = kde_y_out

        if save_plot_values and csv_data:
            os.makedirs(os.path.join(output_folder, fname), exist_ok=True)
            kde_df = pd.DataFrame(dict([(k, pd.Series(v)) for k, v in csv_data.items()])) 
            kde_df.to_csv(os.path.join(output_folder, fname, "6-out_of_service_time.csv"), index=False)

    ax.set_title(f'Probability Density of Out of Service Time - All Clusters ({period} Period) - {num_ues_label} UEs\n(Esclusa disconnessione finale)')
    ax.set_xlabel('Out of Service Duration [s]')
    ax.set_ylabel('Probability Density')
    ax.grid(axis='y', alpha=0.3)
    ax.legend(title="Clusters", bbox_to_anchor=(1.05, 1), loc='upper left')
    fig.savefig(os.path.join(output_folder, "6-out_of_service_time.png"), dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("   Completed!\n")

if get_throuthput_ho_v2:
    """
    Plots the average downlink throughput over time across all UEs, shading the graph with a 95% statistical confidence interval.
    """
    print("7. Plotting average throughput with 95% CI ...")
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + throughput_folder_suffix)
        ues_thr = []
        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            ues_thr.append(df['dl_thr'].tolist())

        if not ues_thr: continue


        min_len = min(len(t) for t in ues_thr)
        ues_thr = [t[:min_len] for t in ues_thr]
        
        data_array = np.array(ues_thr)
        avg_thr = np.mean(data_array, axis=0)
        std_thr = np.std(data_array, axis=0)
        n = data_array.shape[0]
        ci_95 = 1.96 * (std_thr / np.sqrt(n)) 
        
        time_vector = pd.date_range(start=simTimeStart, periods=len(avg_thr), freq='1s')
        
        ax.plot(time_vector, avg_thr, label=f"{fname} (Mean)", color=plt.cm.tab10(i))
        ax.fill_between(time_vector, (avg_thr - ci_95), (avg_thr + ci_95), color=plt.cm.tab10(i), alpha=0.2)
        print(f"   {fname} Average DL Throughput: {np.mean(avg_thr):.2f} Mbit/s")

    ax.set_title('Average DL Throughput (with 95% Confidence Interval)')
    ax.set_ylabel('DL Throughput [Mbit/s]')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%M:%S'))
    fig.savefig(os.path.join(output_folder, "7-DL_throughput_ho.png"), dpi=300, bbox_inches='tight')
    plt.close('all')

if cdf_throughput:
    """
    Generates the Cumulative Distribution Function (CDF) of the downlink throughput, highlighting the 5th percentile edge as required by IEEE standards.
    """
    print("8. Plotting Throughput CDF (IEEE Standard) ...")
    fig, ax = plt.subplots(figsize=(10, 6))

    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + throughput_folder_suffix)
        all_thr_values = []
        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            all_thr_values.extend(df['dl_thr'].dropna().tolist())

        if not all_thr_values: continue
        
        sorted_data = np.sort(all_thr_values)
        yvals = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
        
        ax.plot(sorted_data, yvals, label=f"Cluster {i+1} ({fname})", color=plt.cm.tab10(i), linewidth=2)
        
        p5 = np.percentile(sorted_data, 5)
        ax.axvline(x=p5, color=plt.cm.tab10(i), linestyle=':', alpha=0.6)
        ax.annotate(f'5% Edge: {p5:.1f}', xy=(p5, 0.05), xytext=(5, 5), textcoords='offset points', fontsize=8)

    ax.set_title('Cumulative Distribution Function (CDF) of DL Throughput')
    ax.set_xlabel('DL Throughput [Mbit/s]')
    ax.set_ylabel('CDF (Probability)')
    ax.grid(True, alpha=0.4)
    ax.legend(loc='lower right')
    fig.savefig(os.path.join(output_folder, "8-CDF_Throughput.png"), dpi=300, bbox_inches='tight')
    plt.close('all')

if ping_pong_handovers:
    """
    Calculates and visualizes the average number of ping-pong handover events (redundant transitions between the same nodes) per user equipment.
    """
    print("9. Plotting Ping-Pong Handovers Analytics ...")
    fig, ax = plt.subplots(figsize=(8, 6))
    
    cluster_ping_pongs, cluster_labels = [], []

    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + dataframes_folder_suffix)
        ping_pong_count = []
        for file_path in folder_path.glob('*.csv'):
            df = pd.read_csv(file_path)
            count = 0
            for r1, r2 in zip(df.itertuples(), df.iloc[1:].itertuples()):
                if r1.from_satellite == r2.dest_satellite and str(r1.from_satellite) != 'None':
                    count += 1
            ping_pong_count.append(count)
        
        avg_pp = np.mean(ping_pong_count) if ping_pong_count else 0
        cluster_ping_pongs.append(avg_pp)
        cluster_labels.append(f"Cluster {i+1}\n({fname})")
        print(f"   {fname} Average Ping-Pong: {avg_pp:.2f}")

    bars = ax.bar(cluster_labels, cluster_ping_pongs, color='lightcoral', edgecolor='black')
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.5, f'{yval:.1f}', ha='center', va='bottom', fontweight='bold')

    ax.set_title('Average Ping-Pong Handovers per UE')
    ax.set_ylabel('Number of Ping-Pong Events')
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    fig.savefig(os.path.join(output_folder, "9-Ping_Pong_Analytics.png"), dpi=300, bbox_inches='tight')
    plt.close('all')

if satellite_load_distribution:
    """
    Evaluates network congestion over time by calculating and plotting the maximum, average, and standard deviation of the user load distributed across the visible satellite nodes.
    """
    print("11. Plotting Satellite Load Distribution (Max, Avg, Std) ...")
    fig, ax = plt.subplots(figsize=(12, 6))

    sim_start_pd = pd.to_datetime(simTimeStart)

    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        folder_path = Path("Cluster" + str(i+1) + dataframes_folder_suffix)
        
        total_seconds = int((simTimeEnd - simTimeStart).total_seconds())
        load_matrix = {sec: {} for sec in range(total_seconds + 1)}
        
        for file_path in folder_path.glob('*.csv'):
            try:
                df = pd.read_csv(file_path)
                if df.empty: continue
                
                df['arrival_time'] = pd.to_datetime(df['arrival_time'], errors='coerce').dt.tz_localize(None)
                df = df.sort_values('arrival_time')
                
                for row, next_row in zip(df.itertuples(), df.iloc[1:].itertuples()):
                    sat = str(row.dest_satellite)
                    if sat != 'None' and pd.notna(sat):
                        start_sec = int((row.arrival_time - sim_start_pd).total_seconds())
                        end_sec = int((next_row.arrival_time - sim_start_pd).total_seconds())
                        
                        start_sec = max(0, min(start_sec, total_seconds))
                        end_sec = max(0, min(end_sec, total_seconds))
                        
                        for sec in range(start_sec, end_sec):
                            if sat not in load_matrix[sec]:
                                load_matrix[sec][sat] = 0
                            load_matrix[sec][sat] += 1
            except Exception as e:
                continue

        max_load_series, avg_load_series, std_load_series = [], [], []
        
        for sec in range(total_seconds):
            active_sats = load_matrix[sec]
            if active_sats:
                vals = list(active_sats.values())
                max_load_series.append(max(vals))
                avg_load_series.append(np.mean(vals))
                std_load_series.append(np.std(vals))
            else:
                max_load_series.append(0); avg_load_series.append(0); std_load_series.append(0)

        time_vector = pd.date_range(start=simTimeStart, periods=len(avg_load_series), freq='1s')
        
        ax.plot(time_vector, max_load_series, label=f"{fname}: Max Load", color='firebrick', linewidth=2)
        ax.plot(time_vector, avg_load_series, label=f"{fname}: Avg Load", color='royalblue', linestyle='--')
        
        avg_arr = np.array(avg_load_series)
        std_arr = np.array(std_load_series)
        ax.fill_between(time_vector, avg_arr - std_arr, avg_arr + std_arr, color='royalblue', alpha=0.2, label=f"{fname}: Std Dev")

    ax.set_title('Satellite Load Distribution Over Time (Max, Avg, and Variance)')
    ax.set_ylabel('Number of Connected UEs')
    ax.grid(True, alpha=0.5)
    ax.legend(loc='upper right')
    ax.set_title('Average DL Throughputs over Time - All Clusters')
    ax.set_xlabel('Time')
    ax.set_ylabel('DL Throughput [Mbit/s]')
    ax.grid(True)
    ax.legend(title="Clusters", bbox_to_anchor=(1.05, 1), loc='upper left')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%M:%S'))
    
    ax.axhline(y=150, color='black', linestyle='-.', alpha=0.8, label='Shannon Capacity Hard Cap')
    
    fig.savefig(os.path.join(output_folder, "11-Satellite_Load_Distribution.png"), dpi=300, bbox_inches='tight')
    plt.close('all')
    print("    Completed!\n")

if comparative_plots:
    """
    Generates the comprehensive 3-way comparative plots for the IEEE paper. 
    It loops through pre-computed dataset directories to benchmark the Proposed Hybrid SDN against Active-UE baselines.
    """
    print("12. Generating 3-Way Comparative Plots (SDN vs Active UE)...")
    import seaborn as sns
    import matplotlib.dates as mdates
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning)
    
    comp_out_dir = "plots_comparison_4way"
    os.makedirs(comp_out_dir, exist_ok=True)
    
    HARD_CAP_PLOT = 25 # Parametro per la linea di demarcazione
    cluster_idx = 1
    
    dirs = {
        "Active_MaxElev": {
            "df": f"Cluster{cluster_idx} dataframes_active_max_elevation",
            "thr": f"Cluster{cluster_idx} throughput_active_max_elevation",
            "color": "#d62728", "style": ":", "label": "Active UE (Max Elev)"
        },
        "Active_AvlThr": {
            "df": f"Cluster{cluster_idx} dataframes_active_avl_throughput",
            "thr": f"Cluster{cluster_idx} throughput_active_avl_throughput",
            "color": "#ff7f0e", "style": "-.", "label": "Active UE (Avl Thr)"
        },
        "Passive_Proposed": {
            "df": f"Cluster{cluster_idx} dataframes_sdn",
            "thr": f"Cluster{cluster_idx} throughput_sdn",
            "color": "#1f77b4", "style": "-", "label": "Proposed Hybrid SDN"
        }
    }

    sim_start_pd = pd.to_datetime(simTimeStart)
    total_seconds = int((simTimeEnd - simTimeStart).total_seconds())
    time_vector = pd.date_range(start=simTimeStart, periods=total_seconds, freq='1s')

    print("    -> Plotting Throughput...")
    def get_avg_throughput(folder_path):
        """ Extracts and averages the downlink throughput across all UEs from the specified directory. """
        ues_thr = []
        if not os.path.exists(folder_path): return []
        for file_path in Path(folder_path).glob('*.csv'):
            try:
                df = pd.read_csv(file_path)
                if 'dl_thr' in df.columns: ues_thr.append(df['dl_thr'].tolist())
            except Exception: pass
        if not ues_thr: return []
        min_len = min(len(t) for t in ues_thr)
        return np.mean([t[:min_len] for t in ues_thr], axis=0).tolist()

    plt.figure(figsize=(12, 6), dpi=300)
    for key, info in dirs.items():
        avg_thr = get_avg_throughput(info["thr"])
        if avg_thr:
            min_time = min(len(avg_thr), len(time_vector))
            plt.plot(time_vector[:min_time], avg_thr[:min_time], 
                     label=info["label"], color=info["color"], linestyle=info["style"], linewidth=2.5 if key == "Passive_Proposed" else 1.5)
            
    plt.title('Global Average Downlink Throughput Comparison')
    plt.xlabel('Simulation Time')
    plt.ylabel('Average DL Throughput [Mbps]')
    plt.legend(loc='lower right')
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.tight_layout()
    plt.savefig(os.path.join(comp_out_dir, "comp_4way_1_throughput.pdf")); plt.close()

    print("    -> Plotting Maximum Beam Load...")
    def get_max_beam_load(folder_path):
        """ Calculates the MAXIMUM number of UEs connected to a SINGLE BEAM over time to evaluate local congestion. """
        if not os.path.exists(folder_path): return []
        
        load_matrix_beam = {sec: {} for sec in range(total_seconds + 1)}
        for file_path in Path(folder_path).glob('*.csv'):
            try:
                df = pd.read_csv(file_path)
                if df.empty: continue
                df['arrival_time'] = pd.to_datetime(df['arrival_time'], format='mixed', errors='coerce').dt.tz_localize(None)
                df = df.sort_values('arrival_time')
                for row, next_row in zip(df.itertuples(), df.iloc[1:].itertuples()):
                    sat = str(row.dest_satellite)
                    
                    try:
                        beam = int(float(row.dest_beam_index))
                    except:
                        beam = -1
                    
                    if sat != 'None' and pd.notna(sat) and beam != -1:
                        start_sec = max(0, min(int((row.arrival_time - sim_start_pd).total_seconds()), total_seconds))
                        end_sec = max(0, min(int((next_row.arrival_time - sim_start_pd).total_seconds()), total_seconds))
                        
                        for sec in range(start_sec, end_sec):
                            if sat not in load_matrix_beam[sec]: 
                                load_matrix_beam[sec][sat] = {}
                            if beam not in load_matrix_beam[sec][sat]:
                                load_matrix_beam[sec][sat][beam] = 0
                            load_matrix_beam[sec][sat][beam] += 1
            except Exception: pass
            
        max_l = []
        for sec in range(total_seconds):
            max_val = 0
            for sat in load_matrix_beam[sec]:
                if load_matrix_beam[sec][sat]:
                    current_max = max(load_matrix_beam[sec][sat].values())
                    if current_max > max_val:
                        max_val = current_max
            max_l.append(max_val)
        return max_l

    plt.figure(figsize=(12, 6), dpi=300)
    for key, info in dirs.items():
        max_l = get_max_beam_load(info["df"])
        if max_l:
            plt.plot(time_vector, max_l, label=info["label"], color=info["color"], linestyle=info["style"], linewidth=2)
            
    plt.title('Network Congestion: Maximum Load on a Single Beam Comparison')
    plt.ylabel('Max Number of Connected UEs on a Single Beam')
    plt.xlabel('Simulation Time')
    
    plt.axhline(y=HARD_CAP_PLOT, color='black', linestyle='-', alpha=0.9, label=f'SDN Hard Cap ({HARD_CAP_PLOT} UEs)')
    
    plt.grid(True, alpha=0.5)
    plt.legend(loc='upper right')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.tight_layout()
    plt.savefig(os.path.join(comp_out_dir, "comp_4way_2_load.pdf"))
    plt.close()

    print("    -> Plotting Service Time...")
    def get_service_times(folder_path):
        """ Computes the continuous duration a UE remains connected to a satellite before triggering a new handover. """
        cluster_sat_durations = []
        if not os.path.exists(folder_path): return []
        for file_path in Path(folder_path).glob('*.csv'):
            try:
                df = pd.read_csv(file_path)
                if df.empty: continue
                
                df['arrival_time'] = pd.to_datetime(df['arrival_time'], format='mixed', errors='coerce').dt.tz_localize(None)
                df = df.sort_values('arrival_time')
                
                curr_sat = None
                sat_start_time = None
                
                for row in df.itertuples():
                    t = row.arrival_time
                    dest_sat = row.dest_satellite if pd.notna(row.dest_satellite) and str(row.dest_satellite) != 'None' else None

                    if dest_sat is None:
                        if curr_sat is not None:
                            cluster_sat_durations.append((t - sat_start_time).total_seconds())
                            curr_sat = None
                    else:
                        if row.event_type == 'inter_ho' or row.event_type == 'init_con':
                            if curr_sat is not None: 
                                cluster_sat_durations.append((t - sat_start_time).total_seconds())
                            curr_sat = dest_sat
                            sat_start_time = t
            except Exception: pass
            
        if not cluster_sat_durations: return [0]
        return cluster_sat_durations

    plt.figure(figsize=(13, 6), dpi=300)
    has_labels = False
    markers = ['*', 'o', 's', '^']
    marker_idx = 0

    for key, info in dirs.items():
        times = get_service_times(info["df"])
        if times:
            if min(times) != max(times) and len(times) > 1:
                ax = sns.kdeplot(data=times, label=info["label"], color=info["color"], linestyle=info["style"], linewidth=2, fill=True, alpha=0.2, clip=(0, None), bw_adjust=1.2)
                lines = ax.get_lines()
                if lines:
                    last_line = lines[-1]
                    x_data = last_line.get_xdata()
                    y_data = last_line.get_ydata()
                    peak_idx = np.argmax(y_data)
                    peak_x = x_data[peak_idx]
                    peak_y = y_data[peak_idx]
                    plt.plot(peak_x, peak_y, marker=markers[marker_idx % len(markers)], markersize=14 if markers[marker_idx % len(markers)] == '*' else 10, markeredgecolor='black', color=info["color"])
                    offset_x = (max(x_data) - min(x_data)) * 0.015
                    plt.text(peak_x + offset_x, peak_y, f"{peak_x:.1f}", color=info["color"], fontsize=10, va='bottom', fontweight='bold')
                has_labels = True
                marker_idx += 1
            else:
                plt.axvline(x=times[0], color=info["color"], label=f'{info["label"]} (Constant: {times[0]:.1f}s)', linestyle=info["style"], linewidth=2.5)
                has_labels = True
                
    plt.title('Probability Density of Service Time - Comparative Analysis')
    plt.xlabel('Service Time [s]')
    plt.ylabel('Probability Density')
    plt.grid(axis='y', color='#E0E0E0', linestyle='-')
    plt.grid(axis='x', visible=False)
    if has_labels: plt.legend(title='Architecture', bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(comp_out_dir, "comp_4way_3_service_time.pdf"), bbox_inches='tight')
    plt.close()

    print("    -> Plotting Handover Counts PDF...")
    def get_ho_counts(folder_path, ho_type):
        """ Tallies the absolute number of handovers of a specific type executed by each UE. """
        ho_counts = []
        if not os.path.exists(folder_path): return []
        for file_path in Path(folder_path).glob('*.csv'):
            try:
                df = pd.read_csv(file_path)
                count = len(df[df['event_type'] == ho_type])
                ho_counts.append(count)
            except Exception: pass
        return ho_counts

    plt.figure(figsize=(10, 5), dpi=300)
    has_labels = False
    for key, info in dirs.items():
        counts = get_ho_counts(info["df"], 'intra_ho')
        if counts:
            if min(counts) != max(counts): 
                sns.kdeplot(x=counts, label=info["label"], color=info["color"], linestyle=info["style"], fill=True, alpha=0.1, linewidth=2, clip=(0, None), bw_adjust=1.5)
                has_labels = True
            else:
                plt.axvline(x=counts[0], color=info["color"], label=f'{info["label"]} (Constant: {counts[0]})', linestyle=info["style"], linewidth=2)
                has_labels = True
    plt.title('PDF of Intra-Satellite Handovers per UE - Comparative Analysis')
    plt.xlabel('Number of Handovers')
    plt.ylabel('Probability Density')
    if has_labels: plt.legend()
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(comp_out_dir, "comp_4way_4a_intra_rate.pdf")); plt.close()

    plt.figure(figsize=(10, 5), dpi=300)
    has_labels = False
    for key, info in dirs.items():
        counts = get_ho_counts(info["df"], 'inter_ho')
        if counts:
            if min(counts) != max(counts):
                sns.kdeplot(x=counts, label=info["label"], color=info["color"], linestyle=info["style"], fill=True, alpha=0.1, linewidth=2, clip=(0, None), bw_adjust=1.5)
                has_labels = True
            else:
                plt.axvline(x=counts[0], color=info["color"], label=f'{info["label"]} (Constant: {counts[0]})', linestyle=info["style"], linewidth=2)
                has_labels = True
    plt.title('PDF of Inter-Satellite Handovers per UE - Comparative Analysis')
    plt.xlabel('Number of Handovers')
    plt.ylabel('Probability Density')
    if has_labels: plt.legend()
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(comp_out_dir, "comp_4way_4b_inter_rate.pdf")); plt.close()

    print("    -> Plotting Handover Durations...")
    def get_ho_durations(folder_path, ho_type):
        """ Calculates the mean execution duration for specific handover processes to measure system latency. """
        ho_dur = []
        if not os.path.exists(folder_path): return []
        for file_path in Path(folder_path).glob('*.csv'):
            try:
                df = pd.read_csv(file_path)
                df_ho = df[df['event_type'] == ho_type]
                if not df_ho.empty:
                    arr = pd.to_datetime(df_ho['arrival_time'], format='mixed', errors='coerce').dt.tz_localize(None)
                    dep = pd.to_datetime(df_ho['departure_time'], format='mixed', errors='coerce').dt.tz_localize(None)
                    
                    durations = (dep - arr).dt.total_seconds() * 1000
                    mean_val = durations.mean()
                    if pd.notna(mean_val):
                        ho_dur.append(mean_val)
            except Exception: pass
        return ho_dur

    def plot_duration(ho_type, title, filename):
        """ Helper function to plot execution duration distributions. """
        plt.figure(figsize=(10, 5), dpi=300)
        has_labels = False
        markers = ['*', 'o', 's', '^']
        marker_idx = 0
        
        for key, info in dirs.items():
            durations = get_ho_durations(info["df"], ho_type)
            if durations:
                if (max(durations) - min(durations)) > 0.1 and len(durations) > 1:
                    ax = sns.kdeplot(
                        data=durations, 
                        label=info["label"], 
                        color=info["color"], 
                        linestyle=info["style"], 
                        linewidth=2, 
                        fill=True, 
                        alpha=0.2, 
                        clip=(0, None),
                        bw_adjust=1.5
                    )
                    
                    lines = ax.get_lines()
                    if lines:
                        last_line = lines[-1]
                        x_data = last_line.get_xdata()
                        y_data = last_line.get_ydata()
                        
                        peak_idx = np.argmax(y_data)
                        peak_x = x_data[peak_idx]
                        peak_y = y_data[peak_idx]
                        
                        plt.plot(
                            peak_x, peak_y, 
                            marker=markers[marker_idx % len(markers)],
                            markersize=14 if markers[marker_idx % len(markers)] == '*' else 10, 
                            markeredgecolor='black', 
                            color=info["color"]
                        )
                        
                        offset_x = (max(x_data) - min(x_data)) * 0.015
                        plt.text(peak_x + offset_x, peak_y, f"{peak_x:.1f}", color=info["color"], fontsize=10, va='bottom', fontweight='bold')
                    
                    has_labels = True
                    marker_idx += 1
                else:
                    plt.axvline(x=durations[0], color=info["color"], label=f'{info["label"]}', linestyle=info["style"], linewidth=2.5)
                    has_labels = True

        plt.title(title)
        plt.xlabel('Execution Duration [ms]')
        plt.ylabel('Probability Density')
        plt.grid(axis='y', color='#E0E0E0', linestyle='-')
        plt.grid(axis='x', visible=False)
        if has_labels: 
            plt.legend(title='Architecture', bbox_to_anchor=(1.02, 1), loc='upper left')
            
        plt.tight_layout()
        plt.savefig(os.path.join(comp_out_dir, filename), bbox_inches='tight')
        plt.close()

    plot_duration('intra_ho', 'Intra-Satellite Handover Duration Comparison', 'comp_4way_5a_intra_duration.pdf')
    plot_duration('inter_ho', 'Inter-Satellite Handover Duration Comparison', 'comp_4way_5b_inter_duration.pdf')

    print("    -> Plotting Out of Service Time (BOXPLOT)...")
    def get_oos_durations(folder_path):
        """ Evaluates network stability by extracting the duration of contiguous Out of Service (OOS) link failures. """
        oos_times = []
        if not os.path.exists(folder_path): return []
        
        # Filtro per ignorare l'ultimo minuto di simulazione (disconnessione deterministica)
        end_threshold = simTimeEnd - timedelta(seconds=60)
        
        for file_path in Path(folder_path).glob('*.csv'):
            try:
                df = pd.read_csv(file_path)
                if df.empty: continue
                
                df['arrival_time'] = pd.to_datetime(df['arrival_time'], format='mixed', errors='coerce').dt.tz_localize(None)
                df = df.sort_values('arrival_time')
                out_serv_start_time = None
                
                for row in df.itertuples():
                    t = row.arrival_time
                    dest_sat = row.dest_satellite if pd.notna(row.dest_satellite) and str(row.dest_satellite) != 'None' else None

                    if dest_sat is None:
                        if out_serv_start_time is None and t < end_threshold:
                            out_serv_start_time = t
                    else:
                        if out_serv_start_time is not None:
                            duration = (t - out_serv_start_time).total_seconds()
                            if duration > 0:
                                oos_times.append(duration)
                            out_serv_start_time = None 
            except Exception: pass
        
        return oos_times

    plt.figure(figsize=(10, 6), dpi=300)
    data_for_boxplot = []
    labels_for_boxplot = []
    colors_for_boxplot = []

    for key, info in dirs.items():
        durations = get_oos_durations(info["df"])
        if durations:
            data_for_boxplot.extend(durations)
            labels_for_boxplot.extend([info["label"]] * len(durations))
            colors_for_boxplot.append(info["color"])

    if data_for_boxplot:
        plot_df = pd.DataFrame({
            'Architecture': labels_for_boxplot, 
            'OOS Duration [s]': data_for_boxplot
        })
        
        palette_dict = {info["label"]: info["color"] for key, info in dirs.items()}
        
        # Generazione Boxplot
        sns.boxplot(
            x='Architecture', 
            y='OOS Duration [s]', 
            hue='Architecture',
            data=plot_df, 
            palette=palette_dict, 
            width=0.5, 
            fliersize=3,
            legend=False
        )   
        
        plt.title('Out of Service (OOS) Duration - Comparative Analysis')
        plt.ylabel('Continuous Out of Service Duration [s]')
        plt.xlabel('')
        plt.grid(axis='y', color='#E0E0E0', linestyle='--')
    else:
        plt.title('Out of Service (OOS) Duration - Comparative Analysis')
        plt.text(0.5, 0.5, 'Nessun evento OOS rilevato per le architetture selezionate\n(Esclusa la fine della simulazione)', horizontalalignment='center', verticalalignment='center', fontsize=12)

    plt.tight_layout()
    plt.savefig(os.path.join(comp_out_dir, "comp_4way_6_oos_time.pdf"), bbox_inches='tight')
    plt.close()
    
    print("    Comparative plotting completed!\n")

# ========================================================================================================= #

# 9. UL/DL Doppler Shifts over time
if doppler_shifts:
    print("9. Plotting the UL/DL Doppler Shifts over time ...")

    plt.figure(figsize=(14, 7))
    for i, (df_name_iter, fname) in enumerate(zip(dfnames, fnames)):
        # Percorso dinamico basato sulla modalità (SDN o Baseline)
        folder_path = Path("Cluster" + str(i+1) + throughput_folder_suffix)
        
        csv_files = list(folder_path.glob('*.csv'))
        if not csv_files:
            continue
            
        for file_path in csv_files:
            df = pd.read_csv(file_path)
            
            # Convert time to datetime
            df['time'] = pd.to_datetime(df['time'])
            # Check where 'sat.id' is different from the previous row's 'sat.id'.
            handovers = df[(df['sat.id'].shift(1).notna()) & (df['sat.id'] != df['sat.id'].shift(1))]
            
            dl_label = f'DL Cluster{str(i+1)}' 
            ul_label = f'UL Cluster{str(i+1)}' 
            plt.plot(df['time'], df['doppler_shift_dl_KHz'], label=dl_label, color=colors1[i])
            plt.plot(df['time'], df['doppler_shift_ul_KHz'], label=ul_label, color=colors2[i])
            
            # Mark handover events with a red X
            if not handovers.empty:
                ho_label = f'HO Cluster{str(i+1)}'
                plt.scatter(handovers['time'], handovers['doppler_shift_ul_KHz'], 
                            color='red', marker='X', s=100, zorder=5, label=ho_label)
            
            break # Only plot the first file for this cluster

    # Format the plot
    plt.xlabel('Time')
    plt.ylabel('Doppler Shift (KHz)')
    plt.title('DL and UL Doppler Shifts over Time with Handover Events')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    
    # Gestione sicura della legenda per evitare il warning
    handles, labels = plt.gca().get_legend_handles_labels()
    if handles:
        plt.legend()
        
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    combined_file_path = os.path.join(output_folder, "9-Doppler Shifts.png")
    plt.savefig(combined_file_path)

    print("   Completed!")

# 9.1 UL/DL Doppler Shifts for a single random satellite connection (focus plot)
if doppler_shifts:
    print("9.1 Plotting Doppler Shifts for a single random satellite connection ...")

    # Percorso dinamico basato sulla modalità
    folder_path = Path("Cluster1" + throughput_folder_suffix)
    
    # Prevenzione crash se la lista è vuota
    csv_files = list(folder_path.glob('*.csv'))
    
    if csv_files:
        file_path = csv_files[0] 
        
        df = pd.read_csv(file_path)
        df['time'] = pd.to_datetime(df['time'])
        unique_sats = df['sat.id'].dropna().unique()
        
        if len(unique_sats) > 0:
            chosen_sat = random.choice(unique_sats)
            print(f"    -> Selected satellite: {chosen_sat}")
            df_sat = df[df['sat.id'] == chosen_sat]

            plt.figure(figsize=(12, 6))
            plt.plot(df_sat['time'], df_sat['doppler_shift_dl_KHz'], label='DL', color='#1f77b4', linewidth=2)
            plt.plot(df_sat['time'], df_sat['doppler_shift_ul_KHz'], label='UL', color='#ff7f0e', linewidth=2)

            plt.xlabel('Time')
            plt.ylabel('Doppler Shift (KHz)') 
            plt.title(f'DL and UL Doppler Shifts (Connection to {chosen_sat})')
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plt.legend()
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            combined_file_path = os.path.join(output_folder, "9.1-Doppler Shift Focus.png")
            plt.savefig(combined_file_path)

            print("   Completed!\n")
        else:
            print("   Nessun satellite valido trovato in questo file.")
    else:
        print("   [ATTENZIONE] Nessun file CSV trovato per generare il grafico Doppler Focus.")


# ========================================================================================================= #
# 13. SPATIAL WATER-FILLING: FOOTPRINT HEATMAP & BEAM SATURATION OVER TIME
# ========================================================================================================= #


if beam_footprint_heatmap:
    print("13. Plotting Spatial Water-Filling Heatmap and Beam Saturation ...")
    
    # Cartella da analizzare
    folder_path = Path("Cluster1" + dataframes_folder_suffix)
    
    sim_start_pd = pd.to_datetime(simTimeStart)
    total_seconds = int((simTimeEnd - simTimeStart).total_seconds())
    
    # Struttura dati per memorizzare il carico: sec -> sat -> beam -> load
    load_matrix_beams = {sec: {} for sec in range(total_seconds + 1)}
    
    csv_files = list(folder_path.glob('*.csv'))
    if csv_files:
        for file_path in csv_files:
            try:
                df = pd.read_csv(file_path)
                if df.empty: continue
                df['arrival_time'] = pd.to_datetime(df['arrival_time'], format='mixed', errors='coerce').dt.tz_localize(None)
                df = df.sort_values('arrival_time')
                
                for row, next_row in zip(df.itertuples(), df.iloc[1:].itertuples()):
                    sat = str(row.dest_satellite)
                    
                    # Estrazione sicura dell'indice del beam
                    try:
                        beam = int(float(row.dest_beam_index))
                    except:
                        beam = -1
                        
                    if sat != 'None' and pd.notna(sat) and beam != -1:
                        start_sec = max(0, min(int((row.arrival_time - sim_start_pd).total_seconds()), total_seconds))
                        end_sec = max(0, min(int((next_row.arrival_time - sim_start_pd).total_seconds()), total_seconds))
                        
                        for sec in range(start_sec, end_sec):
                            if sat not in load_matrix_beams[sec]: 
                                load_matrix_beams[sec][sat] = {}
                            if beam not in load_matrix_beams[sec][sat]:
                                load_matrix_beams[sec][sat][beam] = 0
                            load_matrix_beams[sec][sat][beam] += 1
            except Exception as e: 
                pass

        # Troviamo il satellite e il secondo esatto in cui c'è il massimo carico totale
        max_total_load = -1
        best_sec = -1
        best_sat = None
        
        for sec in range(total_seconds):
            for sat, beams in load_matrix_beams[sec].items():
                total_load = sum(beams.values())
                if total_load > max_total_load:
                    max_total_load = total_load
                    best_sec = sec
                    best_sat = sat
                    
        if best_sat is not None:
            print(f"    -> Analisi focalizzata sul satellite {best_sat} al secondo {best_sec} (Totale UEs: {max_total_load})")
            
            # --- PLOT 1: LA HEATMAP 5x5 ---
            heatmap_data = np.zeros((5, 5))
            beam_loads = load_matrix_beams[best_sec][best_sat]
            
            for b_idx in range(25):
                r = b_idx // 5
                c = b_idx % 5
                heatmap_data[r, c] = beam_loads.get(b_idx, 0)
                
            plt.figure(figsize=(8, 6), dpi=300)
            
            # Colori diversi per far capire se stiamo guardando la SDN o la Baseline
            cmap = 'YlGnBu' if USE_PREHO_DATA else 'OrRd'
            vmax = 18 if USE_PREHO_DATA else None # Forza il massimo colore a 18 per SDN
            
            ax = sns.heatmap(heatmap_data, annot=True, fmt=".0f", cmap=cmap, 
                             cbar_kws={'label': 'Numero di UEs Connessi'},
                             linewidths=1, linecolor='white', square=True,
                             vmax=vmax) 
            
            ax.set_xticks(np.arange(5) + 0.5)
            ax.set_yticks(np.arange(5) + 0.5)
            ax.set_xticklabels([f"C{i+1}" for i in range(5)])
            ax.set_yticklabels([f"R{i+1}" for i in range(5)], rotation=0)
            
            mode_name = "SDN Proposed (Hard Cap = 18)" if USE_PREHO_DATA else "Baseline Greedy"
            plt.title(f'Spatial Water-Filling: Beam Load Distribution\n{best_sat} - {mode_name}')
            plt.tight_layout()
            
            heatmap_file_path = os.path.join(output_folder, "13-Beam_Footprint_Heatmap.png")
            plt.savefig(heatmap_file_path)
            plt.close()
            print("    [+] Heatmap generata!")

            # --- PLOT 2: BEAM SATURATION OVER TIME ---
            time_vector_sat = pd.date_range(start=simTimeStart, periods=total_seconds, freq='1s')
            
            # Troviamo i beam più caldi di questo satellite su tutta la simulazione
            beam_total_load = {}
            for sec in range(total_seconds):
                if best_sat in load_matrix_beams[sec]:
                    for b_idx, load in load_matrix_beams[sec][best_sat].items():
                        beam_total_load[b_idx] = beam_total_load.get(b_idx, 0) + load
                        
            # Seleziona i 5 beam più caricati
            top_beams = sorted(beam_total_load.items(), key=lambda x: x[1], reverse=True)[:5]
            top_beam_indices = [b[0] for b in top_beams]
            
            # Forza l'inclusione del beam centrale (indice 12) per il confronto
            if 12 not in top_beam_indices:
                top_beam_indices = [12] + top_beam_indices[:4]
                
            plt.figure(figsize=(12, 6), dpi=300)
            
            for b_idx in top_beam_indices:
                b_load_series = []
                for sec in range(total_seconds):
                    if best_sat in load_matrix_beams[sec]:
                        b_load_series.append(load_matrix_beams[sec][best_sat].get(b_idx, 0))
                    else:
                        b_load_series.append(0)
                
                # Applica una leggera media mobile (rolling) per smussare le linee e renderle leggibili
                b_load_series = pd.Series(b_load_series).rolling(window=5, min_periods=1).mean()
                
                is_center = (b_idx == 12)
                label = f"Beam Centrale (Idx 12)" if is_center else f"Beam Periferico {b_idx}"
                linewidth = 3 if is_center else 1.5
                linestyle = '-' if is_center else '--'
                
                plt.plot(time_vector_sat, b_load_series, label=label, linewidth=linewidth, linestyle=linestyle)
                
            plt.title(f'Dynamic Load Balancing: Saturazione dei Beam nel tempo\nSatellite: {best_sat} - {mode_name}')
            plt.xlabel('Tempo di Simulazione')
            plt.ylabel('Numero di UEs Connessi per Beam')
            
            if USE_PREHO_DATA:
                plt.axhline(y=18, color='red', linestyle='-.', alpha=0.8, linewidth=2, label='Hard Cap (Water-Filling = 18)')
                
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plt.legend(loc='upper right')
            plt.grid(True, linestyle=':', alpha=0.7)
            plt.tight_layout()
            
            saturation_file_path = os.path.join(output_folder, "14-Beam_Saturation_Over_Time.png")
            plt.savefig(saturation_file_path)
            plt.close()
            print("    [+] Grafico di Saturazione Temporale generato!\n")

        else:
            print("   Dati non sufficienti (nessun satellite valido identificato).")
    else:
        print("   Nessun file CSV trovato per calcolare la heatmap.")