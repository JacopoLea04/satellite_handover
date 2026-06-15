import numpy as np
import utils
from scipy.optimize import linear_sum_assignment
import random
import pandas as pd
from datetime import timedelta
from satellite import Satellite
from channel_parameters import ChannelParameters 

class SDN_Controller:
    def __init__(self, cluster, scenario, dataframe):
        self.cluster = cluster
        self.scenario = scenario
        self.df = dataframe
        self.WATER_FILLING_LIMIT = 15.0 
        self.INTRA_HO_PENALTY = 1.0     
        self.INTER_HO_PENALTY = 0.70    
        self.tau_c = 0.250  # Latenza del Control Plane (250 ms)
        self.sigma_theta = 0.5  # Deviazione standard dell'errore di misura (0.5 gradi)
        
        # Parametri Fading Atmosferico (Markov a 2 Stati)
        self.dt_markov = 1.0 # Aggiornamento ogni secondo simulato
        T_good = 45.0 # Durata media cielo sereno (secondi)
        T_bad = 15.0  # Durata media copertura nuvolosa (secondi)
        
        self.p_gb = self.dt_markov / T_good
        self.p_bg = self.dt_markov / T_bad
        self.attenuation_bad_db = 6.0 # 6 dB di perdita in caso di nuvole/pioggia
        
        # Dizionario per mantenere la persistenza del meteo per ogni satellite: {sat_name: 'G' o 'B'}
        self.weather_state = {}
        self.last_weather_update_time = None

        # =====================================================================
        # OTTIMIZZAZIONE COMPUTAZIONALE: COSTRUZIONE DELLA HASH MAP (CACHE O(1))
        # =====================================================================
        print("\n[SDN] Inizializzazione: Generazione della tabella Hash per la telemetria orbitale...")
        self.orbit_cache = {}
        
        # L'uso di itertuples() è infinitamente più veloce rispetto a iterrows() in Pandas
        for row in dataframe.itertuples():
            key = (str(row.time), str(row.sat_name))
            self.orbit_cache[key] = (float(row.sat_lat), float(row.sat_lon), float(row.sat_height))
            
        print(f"[SDN] Tabella Hash completata! {len(self.orbit_cache)} stati orbitali indicizzati a costo O(1).\n")

    def run_optimization(self, time, service_sats, visible_sats_for_each_minicluster):
        # =====================================================================
        # 2A. AGGIORNAMENTO DEL METEO (Catena di Markov)
        # Eseguito una sola volta all'inizio dell'ottimizzazione per il tempo 't'
        # =====================================================================
        if self.last_weather_update_time != time:
            # Assicuriamoci che tutti i satelliti attualmente considerati abbiano uno stato
            for sat_data in [item for sublist in visible_sats_for_each_minicluster for item in sublist]:
                sat_n = sat_data[0][0]
                if sat_n not in self.weather_state:
                    self.weather_state[sat_n] = 'G' # Iniziamo col sereno
                    
            # Transizioni di stato di Markov
            for sat_n in list(self.weather_state.keys()):
                current_state = self.weather_state[sat_n]
                rand_val = random.random()
                if current_state == 'G':
                    if rand_val < self.p_gb:
                        self.weather_state[sat_n] = 'B'
                else:
                    if rand_val < self.p_bg:
                        self.weather_state[sat_n] = 'G'
                        
            self.last_weather_update_time = time

        all_ues = []
        for mini_cluster in self.cluster.list_beams:
            for ue in mini_cluster.list_ues:
                all_ues.append((ue, mini_cluster))
                
        if not all_ues:
            return

        available_beams = []
        unique_beam_signatures = set()
        
        for mini_cluster_vis in visible_sats_for_each_minicluster:
            for sat_data in mini_cluster_vis:
                sat_tuple = sat_data[0] 
                beam_idx = sat_data[1]
                
                sig = f"{sat_tuple[0]}_{beam_idx}"
                if sig not in unique_beam_signatures:
                    unique_beam_signatures.add(sig)
                    available_beams.append((sat_tuple, beam_idx))

        if not available_beams:
            for ue, _ in all_ues:
                ue.scheduled_handover = {'time': time, 'sat': None, 'beam': None}
            return

        num_ues = len(all_ues)
        MAX_SLOTS_PER_BEAM = int(self.WATER_FILLING_LIMIT) 

        virtual_beams = []
        for sat_tuple, beam_idx in available_beams:
            for slot in range(MAX_SLOTS_PER_BEAM):
                virtual_beams.append({
                    'sat_tuple': sat_tuple,
                    'beam_idx': beam_idx,
                    'slot': slot
                })

        num_virtual_beams = len(virtual_beams)
        cost_matrix = np.full((num_ues, num_virtual_beams), 1000.0)

        for i, (ue, mini_cluster) in enumerate(all_ues):
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()
            curr_sat_name = curr_sat_obj.name if curr_sat_obj else None
            
            valid_targets = visible_sats_for_each_minicluster[mini_cluster.index]
            valid_signatures = {f"{sat_tuple[0]}_{b_idx}" for sat_tuple, b_idx in valid_targets}
            
            mc_lat, mc_lon, mc_alt = mini_cluster.position
            
            for j, v_beam in enumerate(virtual_beams):
                target_sat_name = v_beam['sat_tuple'][0]
                target_beam_idx = v_beam['beam_idx']
                sig = f"{target_sat_name}_{target_beam_idx}"
                
                if sig not in valid_signatures:
                    continue 
                
                target_sat_lat = v_beam['sat_tuple'][1]
                target_sat_lon = v_beam['sat_tuple'][2]
                target_sat_alt = v_beam['sat_tuple'][3]
                
                link_elev_real = ChannelParameters.elevation_angle_deg(mc_lat, mc_lon, target_sat_lat, target_sat_lon, target_sat_alt)
                
                try:
                    time_future = time + timedelta(seconds=1)
                    t_fut_str = time_future.strftime("%Y-%m-%d %H:%M:%S") if hasattr(time_future, 'strftime') else str(time_future)
                    
                    key_future = (t_fut_str, target_sat_name)
                    
                    if key_future in self.orbit_cache:
                        f_lat, f_lon, f_alt = self.orbit_cache[key_future]
                        elev_future = ChannelParameters.elevation_angle_deg(mc_lat, mc_lon, f_lat, f_lon, f_alt)
                        slope_real = elev_future - link_elev_real
                    else:
                        slope_real = 0.0
                except:
                    slope_real = 0.0
                
                # =====================================================================
                # 2B. INIEZIONE STOCASTICA MULTI-DOMINIO
                # =====================================================================
                noise_theta = random.gauss(0, self.sigma_theta)
                noise_slope = random.gauss(0, self.sigma_theta / 2.0)

                # Percezione errata dell'SDN
                link_elev_perceived = link_elev_real - (slope_real * self.tau_c) + noise_theta
                link_elev_perceived = np.clip(link_elev_perceived, 0.0, 90.0)
                
                slope_perceived = slope_real + noise_slope
                
                # Penalità Meteo (Se il satellite è nella nuvola, dimezza l'utilità base)
                weather_penalty_linear = 1.0 
                if target_sat_name in self.weather_state and self.weather_state[target_sat_name] == 'B':
                    weather_penalty_linear = 0.5 

                alpha = 0.8
                beta = 0.2
                slope_normalized = np.clip(slope_perceived / 0.5, -1.0, 1.0)
                
                # Calcolo punteggio finale
                base_score = alpha * (link_elev_perceived / 90.0)
                base_score *= weather_penalty_linear 
                
                w_score = base_score + beta * slope_normalized
                w_score = max(0.01, w_score) 
                
                # Isteresi
                if curr_sat_name is not None:
                    if target_sat_name == curr_sat_name:
                        w_score *= self.INTRA_HO_PENALTY
                    else:
                        w_score *= self.INTER_HO_PENALTY
                
                # Shannon Slice
                slot_index = v_beam['slot'] 
                bandwidth_slice = 1.0 / (slot_index + 1.0)
                w_score *= bandwidth_slice
                        
                cost_matrix[i, j] = -w_score

        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        for idx in range(len(row_ind)):
            ue_idx = row_ind[idx]
            v_beam_idx = col_ind[idx]
            
            ue = all_ues[ue_idx][0]
            mini_cluster = all_ues[ue_idx][1] # Recuperiamo il mini_cluster per l'elevazione
            v_beam = virtual_beams[v_beam_idx] 
            
            target_sat_name = v_beam['sat_tuple'][0]
            target_beam = v_beam['beam_idx']
            
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()
            
            # -----------------------------------------------------------------
            # VERIFICA DELLA NECESSITÀ DI HANDOVER
            # -----------------------------------------------------------------
            is_valid_ho = False
            # 1. Se il target è il vuoto (costo = 1000)
            if cost_matrix[ue_idx, v_beam_idx] == 1000.0:
                ue.scheduled_handover = {'time': time, 'sat': None, 'beam': None}
                continue # Utente sganciato per mancanza di copertura

            # 2. Se stiamo effettivamente cambiando satellite o fascio
            if curr_sat_obj is None or curr_sat_obj.name != target_sat_name or curr_beam_idx != target_beam:
                is_valid_ho = True
            
            if not is_valid_ho:
                ue.scheduled_handover = None
                continue

            # -----------------------------------------------------------------
            # INIZIO: TTS PURO (TEMPORAL TRIGGER SPREADING STOCASTICO)
            # -----------------------------------------------------------------
            delta_w = 0.0 # Finestra di default per chi non ha storico o sta salendo
            
            if curr_sat_obj is not None and getattr(ue, 'ema_elevation', None) is not None:
                try:
                    # Calcolo derivata per stimare il T_crit
                    # Arrotondiamo il tempo localmente per garantire la sincronia con il database orbitale
                    round_time_local = (time + timedelta(microseconds=500000)).replace(microsecond=0)
                    t_minus_1 = round_time_local - timedelta(seconds=1)
                    
                    elev_old = utils.get_elevation(self.frame, t_minus_1, curr_sat_obj.name, mini_cluster.position)
                    derivata_elev = ue.ema_elevation - elev_old
                    
                    if derivata_elev < -0.01: # Se il satellite sta scendendo
                        theta_min = self.cluster.elevation_threshold if hasattr(self.cluster, 'elevation_threshold') else 30.0
                        t_crit = (ue.ema_elevation - theta_min) / abs(derivata_elev)
                        
                        t_margin = 2.0
                        delta_w_calc = t_crit - t_margin
                        
                        # Clamping della finestra (min 1s, max 15s)
                        delta_w = max(1.0, min(delta_w_calc, 15.0))
                    else:
                        # Se il satellite sta salendo o è stabile, ma l'SDN vuole fare HO per meteo/carico,
                        # concediamo una finestra standard ampia per non stressare il RACH.
                        delta_w = 10.0
                except:
                    delta_w = 3.0 # Fallback in caso di errore sui dati orbitali vecchi
            else:
                delta_w = 1.0 # Fallback per initial connection

            # Estrazione stocastica del tempo di scheduling all'interno di [0, delta_w]
            # Convertiamo in int per i secondi di offset
            random_offset_seconds = int(random.uniform(0, delta_w))
            
            if isinstance(time, pd.Timestamp):
                scheduled_time = time + timedelta(seconds=random_offset_seconds)
            else:
                scheduled_time = time + timedelta(seconds=random_offset_seconds)

            # -----------------------------------------------------------------
            # REGISTRAZIONE DELL'HANDOVER E CREAZIONE SATELLITE
            # -----------------------------------------------------------------
            if target_sat_name not in service_sats:
                sat = Satellite(target_sat_name, self.cluster.sat_servers, self.cluster.sat_mu_inter, self.cluster.sat_mu_intra, self.cluster.num_beams)
                service_sats[target_sat_name] = sat
            dest_sat_obj = service_sats[target_sat_name]
            
            ue.scheduled_handover = {
                'time': scheduled_time,
                'sat': dest_sat_obj,
                'beam': target_beam
            }