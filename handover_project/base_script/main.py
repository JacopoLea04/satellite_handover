from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import argparse
import os 
import shutil
import re
from cluster import Cluster
import utils


# ==============================================================================
# INITIAL CONFIGURATION
# ==============================================================================
df_name_1 = "250km_sc9_padova.csv"  #"100km_25beams_sc9_padova.csv"
ho_condition_1 = ("ELEVATION", 30)

# ==============================================================================
# SAT SELECTION CONDITION (SDN ARCHITECTURE)
# ==============================================================================
# "MADM_PREHO": Attiva l'SDN Controller. Il sistema smette di essere reattivo e
#               passa a un controllo globale. Costruisce la super-matrice dei pesi
#               (tramite filtro EMA e MAUF asimmetrica), risolve l'ottimo globale
#               tramite Algoritmo Ungherese (Kuhn-Munkres) e applica il Temporal
#               Trigger Spreading (TTS) per evitare il collasso delle code (M/D/1 -> D/D/1).
# Altre opzioni legacy: "RANDOM", "MAX_ELEVATION", "MAX_VISIBILITY", "AVL_THR"
sat_selection_condition_1 = "MADM_PREHO"

enable_elevation_threshold = True
elevation_threshold = 30

simTime = timedelta(minutes=25)
num_ues = 100
mu_inter = 30 * 1e-3
mu_intra = 1 * 1e-3 
servers = 1
scenario = utils.sc9_parameters
handover_timer = 40


# retrive parameters
data_frame_1 = pd.read_csv(df_name_1)

beam_size_km = 250
num_beams = 25

# parsing input parameters 
parser = argparse.ArgumentParser(description="Satellite SDN Simulation Script")
parser.add_argument('--servers', type=int, default=servers, help='Number of servers')
parser.add_argument('--num_ues', type=int, default=num_ues, help='Number of User Equipments')
args= parser.parse_args()
servers = args.servers
num_ues = args.num_ues

# Inizializzazione del Cluster (che ora istanzia autonomamente l'SDN Controller)
cluster1 = Cluster("Cluster1", (45.40996, 11.89261, 0), num_ues, beam_size_km, num_beams, data_frame_1, servers, mu_inter, mu_intra, scenario, enable_elevation_threshold, elevation_threshold)
clusters = [cluster1] 

# (# year, month, day, hour, minute, second)
time = datetime(2026, 2, 19, 0, 0, 0) 
end_sim_time = time + simTime

# Initial connection phase: each ue connects to a random satellite
service_sats = {}
for cluster in clusters:    
    cluster.initial_connection_phase(time, service_sats, handover_timer)

# increment the time by 100 ms
time += timedelta(seconds=1)

total_iterations = int((end_sim_time - time).total_seconds())

print("\nStarting SDN-based Simulation...")

with tqdm(total=total_iterations, desc="Simulating") as pbar:
    
    # Loop Temporale Principale (Il Metronomo)
    while time < end_sim_time:

        # Il monitor ora gestisce la telemetria, le esecuzioni passive e risveglia
        # l'SDN Controller centrale ogni 5 secondi per l'ottimizzazione di rete.
        cluster1.monitor(time, service_sats, ho_condition_1, sat_selection_condition_1)
        
        # Display the current time on the right side of the progress bar
        pbar.set_postfix(time=time.strftime("%H:%M:%S"))
        
        # increment the time by 1 sec
        time += timedelta(seconds=1)
        
        # Manually advance the progress bar by 1 tick
        pbar.update(1)


print("Simulation Complete!\n")

# ==============================================================================
# POST-PROCESSING & ANALYTICS
# ==============================================================================
print("Computing Doppler Shifts for all the UEs ...")

total_iterations = num_ues
with tqdm(total=total_iterations, desc="Processing Analytics") as pbar:
    for cluster in clusters: 
        frame = cluster.frame

        # O(1) lookup dictionary
        sat_positions_map = {
            (str(sat), str(t)): (lat, lon, alt)
            for sat, t, lat, lon, alt in zip(
                frame['sat_name'], 
                frame['time'], 
                frame['sat_lat'], 
                frame['sat_lon'], 
                frame['sat_height']
            )
        }

        time_cache = {}

        for mini_cluster in cluster.list_beams:
            ue_pos = mini_cluster.position
            
            for ue in mini_cluster.list_ues:
                handover_info = ue.thr_tracker
                
                for line in handover_info:
                    time = line["time"]
                    sat_name = str(line["sat.id"])

                    if time not in time_cache:
                        if isinstance(time, datetime):
                            t_curr = time.strftime("%Y-%m-%d %H:%M:%S")
                            t_old = (time - pd.Timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                            t_fut = (time + pd.Timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            t_curr = str(time)
                            t_old = str(time - pd.Timedelta(seconds=1))
                            t_fut = str(time + pd.Timedelta(seconds=1))
                        time_cache[time] = (t_old, t_curr, t_fut)
                    
                    t_old, t_curr, t_fut = time_cache[time]

                    default_pos = (None, None, None)
                    old_pos = sat_positions_map.get((sat_name, t_old), default_pos)
                    curr_pos = sat_positions_map.get((sat_name, t_curr), default_pos)
                    fut_pos = sat_positions_map.get((sat_name, t_fut), default_pos)

                    doppler_dl, doppler_ul = utils.compute_doppler_shift(
                        ue_pos, old_pos, curr_pos, fut_pos, scenario
                    )
                    
                    line['doppler_shift_dl_KHz'] = doppler_dl / 1000
                    line['doppler_shift_ul_KHz'] = doppler_ul / 1000
                pbar.set_postfix(time=time.strftime("%H:%M:%S"))
                pbar.update(1)
            
print("Computation completed!\n")

print("Creating the folder with the ue dataframes ...")

output_folders = (
    [f"{cluster.name} dataframes_preho" for cluster in clusters] +
    [f"{cluster.name} throughput_preho" for cluster in clusters] +
    ["Satellite dataframes_preho"]
)

for folder in output_folders:
    if os.path.exists(folder):
        shutil.rmtree(folder)

total_iterations = len(service_sats)
with tqdm(total=total_iterations, desc="Saving Satellites") as pbar:
    for name, sat in service_sats.items():
        sat.deactivate()
        pbar.set_postfix(time=time.strftime("%H:%M:%S"))
        pbar.update(1)

print("Folder created!\n")

print("Creating the folder with the sat dataframes ...")

total_iterations = num_ues
with tqdm(total=total_iterations, desc="Saving UEs") as pbar:
    for cluster in clusters:
        for mini_cluster in cluster.list_beams:
            for ue in mini_cluster.list_ues:
                ue.deactivate(cluster.name)
                pbar.set_postfix(time=time.strftime("%H:%M:%S"))
                pbar.update(1)

print("Folder created!\n")
