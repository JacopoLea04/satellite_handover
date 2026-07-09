from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm
import argparse
import os 
import shutil
import utils
from cluster import Cluster

# Importiamo il modulo fisico appena creato
from channel import sc9_parameters, sc6_parameters

# ==============================================================================
# CONFIGURAZIONE INIZIALE E SCENARIO
# ==============================================================================
df_name_1 = "250km_sc9_padova.csv" 
ho_condition_1 = ("ELEVATION", 30)

# ==============================================================================
# PARAMETRI ARCHITETTURA SDN
# ==============================================================================
# "PREHO": Attiva l'SDN Controller globale (Algoritmo Ungherese + TTS).
# Altre opzioni legacy (per benchmark): "RANDOM", "MAX_ELEVATION", "MAX_VISIBILITY"
sat_selection_condition_1 = "PREHO"

enable_elevation_threshold = True
elevation_threshold = 30

simTime = timedelta(minutes=15)  # Durata simulazione (90 minuti)
num_ues = 100
mu_inter = 30 * 1e-3  # Costo fisico Inter-HO (30 ms)
mu_intra = 1 * 1e-3   # Costo fisico Intra-HO (1 ms)
servers = 1
scenario = sc9_parameters
handover_timer = 40

beam_size_km = 250
num_beams = 25

# ==============================================================================
# PARSING ARGOMENTI & INIZIALIZZAZIONE
# ==============================================================================
parser = argparse.ArgumentParser(description="Satellite SDN Simulation Script (6G NTN)")
parser.add_argument('--servers', type=int, default=servers, help='Number of servers per node')
parser.add_argument('--num_ues', type=int, default=num_ues, help='Number of User Equipments')
args = parser.parse_args()

servers = args.servers
num_ues = args.num_ues

# Caricamento del Digital Twin (Pre-computed Orbital Data)
print(f"\nCaricamento Dataset Orbitale: {df_name_1}...")
data_frame_1 = pd.read_csv(df_name_1)

# Istanziazione Topologia (Il Cluster istanzia autonomamente il Controller SDN)
cluster1 = Cluster(
    "Cluster1", (45.40996, 11.89261, 0), num_ues, beam_size_km, num_beams, 
    data_frame_1, servers, mu_inter, mu_intra, scenario, 
    enable_elevation_threshold, elevation_threshold
)
clusters = [cluster1] 

time = datetime(2026, 2, 19, 0, 0, 0) 
end_sim_time = time + simTime

# Fase di Bootstrap: Connessione iniziale randomica (caotica) per testare l'SDN
service_sats = {}
for cluster in clusters:    
    cluster.initial_connection_phase(time, service_sats, handover_timer)

time += timedelta(seconds=1)
total_iterations = int((end_sim_time - time).total_seconds())

# ==============================================================================
# SIMULATION MAIN LOOP (IL METRONOMO)
# ==============================================================================
print("\n=== Avvio Simulazione basata su Architettura SDN ===")

with tqdm(total=total_iterations, desc="Simulating") as pbar:
    while time < end_sim_time:
        # Il monitor gestisce telemetria MAC e innesca l'SDN Controller
        cluster1.monitor(time, service_sats, ho_condition_1, sat_selection_condition_1)
        
        pbar.set_postfix(time=time.strftime("%H:%M:%S"))
        time += timedelta(seconds=1)
        pbar.update(1)

print("\nSimulazione di Rete Completata!")

# ==============================================================================
# POST-PROCESSING E ANALYTICS (DOPPLER SHIFT)
# ==============================================================================
print("\n=== Calcolo Analitiche Avanzate (Doppler Shift) ===")

with tqdm(total=num_ues, desc="Processing Analytics") as pbar:
    for cluster in clusters: 
        frame = cluster.frame

        # Ottimizzazione computazionale estrema: Mappa Hash O(1) per posizioni orbitali
        sat_positions_map = {
            (str(sat), str(t)): (lat, lon, alt)
            for sat, t, lat, lon, alt in zip(
                frame['sat_name'], frame['time'], frame['sat_lat'], 
                frame['sat_lon'], frame['sat_height']
            )
        }
        time_cache = {}

        for mini_cluster in cluster.list_beams:
            ue_pos = mini_cluster.position
            
            for ue in mini_cluster.list_ues:
                for line in ue.thr_tracker:
                    t_val = line["time"]
                    sat_name = str(line["sat.id"])

                    if t_val not in time_cache:
                        if isinstance(t_val, datetime):
                            t_curr = t_val.strftime("%Y-%m-%d %H:%M:%S")
                            t_old = (t_val - pd.Timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                            t_fut = (t_val + pd.Timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            t_curr = str(t_val)
                            t_old = str(t_val - pd.Timedelta(seconds=1))
                            t_fut = str(t_val + pd.Timedelta(seconds=1))
                        time_cache[t_val] = (t_old, t_curr, t_fut)
                    
                    t_old, t_curr, t_fut = time_cache[t_val]
                    default_pos = (None, None, None)
                    
                    old_pos = sat_positions_map.get((sat_name, t_old), default_pos)
                    curr_pos = sat_positions_map.get((sat_name, t_curr), default_pos)
                    fut_pos = sat_positions_map.get((sat_name, t_fut), default_pos)

                    doppler_dl, doppler_ul = utils.compute_doppler_shift(
                        ue_pos, old_pos, curr_pos, fut_pos, scenario
                    )
                    
                    line['doppler_shift_dl_KHz'] = doppler_dl / 1000
                    line['doppler_shift_ul_KHz'] = doppler_ul / 1000
                    
                pbar.set_postfix(time=t_val.strftime("%H:%M:%S") if isinstance(t_val, datetime) else str(t_val))
                pbar.update(1)

# ==============================================================================
# ESPORTAZIONE DATI E SPEGNIMENTO
# ==============================================================================
print("\n=== Esportazione Dataframes e Chiusura Nodi ===")

output_folders = (
    [f"{cluster.name} dataframes_preho" for cluster in clusters] +
    [f"{cluster.name} throughput_preho" for cluster in clusters] +
    ["Satellite dataframes_preho"]
)

for folder in output_folders:
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder, exist_ok=True)

with tqdm(total=len(service_sats), desc="Deallocazione Satelliti") as pbar:
    for name, sat in service_sats.items():
        sat.deactivate()
        pbar.update(1)

with tqdm(total=num_ues, desc="Esportazione Telemetria UE") as pbar:
    for cluster in clusters:
        for mini_cluster in cluster.list_beams:
            for ue in mini_cluster.list_ues:
                ue.deactivate(cluster.name)
                pbar.update(1)

print("\nTerminazione Script. Log salvati con successo.")
