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
        
        # Parametri Ottimizzazione
        self.WATER_FILLING_LIMIT = 15.0 
        self.INTRA_HO_PENALTY = 1.0     
        self.INTER_HO_PENALTY = 0.5    
        self.SWITCHING_COST_BONUS = 0.5  # Bonus additivo per ancorare l'UE al nodo corrente
        
        # Pilastro 1: Latenza e Rumore Control Plane
        self.tau_c = 0.250  # Latenza (250 ms)
        self.sigma_theta = 0.5  # Deviazione std errore misura (gradi)
        
        # Catena di Markov a 2 Stati (Meteo)
        self.dt_markov = 1.0 
        T_good = 45.0 
        T_bad = 15.0  
        self.p_gb = self.dt_markov / T_good
        self.p_bg = self.dt_markov / T_bad
        self.weather_state = {}
        self.last_weather_update_time = None

        # Tabella Hash O(1) per telemetria orbitale (Performance)
        print("\n[SDN] Inizializzazione Hash Map telemetrica...")
        self.orbit_cache = {}
        for row in dataframe.itertuples():
            key = (str(row.time), str(row.sat_name))
            self.orbit_cache[key] = (float(row.sat_lat), float(row.sat_lon), float(row.sat_height))
        print(f"[SDN] Tabella Hash completata ({len(self.orbit_cache)} stati).\n")

    def run_optimization(self, time, service_sats, visible_sats_for_each_minicluster):
        # -----------------------------------------------------------------
        # AGGIORNAMENTO STATO AMBIENTALE (Markov)
        # -----------------------------------------------------------------
        if self.last_weather_update_time != time:
            for sat_data in [item for sublist in visible_sats_for_each_minicluster for item in sublist]:
                sat_n = sat_data[0][0]
                if sat_n not in self.weather_state:
                    self.weather_state[sat_n] = 'G'
                    
            for sat_n in list(self.weather_state.keys()):
                current_state = self.weather_state[sat_n]
                rand_val = random.random()
                if current_state == 'G' and rand_val < self.p_gb:
                    self.weather_state[sat_n] = 'B'
                elif current_state == 'B' and rand_val < self.p_bg:
                    self.weather_state[sat_n] = 'G'
            self.last_weather_update_time = time

        # -----------------------------------------------------------------
        # COSTRUZIONE SPAZIO DELLE VARIABILI
        # -----------------------------------------------------------------
        all_ues = [(ue, mc) for mc in self.cluster.list_beams for ue in mc.list_ues]
        if not all_ues: return

        unique_beam_signatures = set()
        available_beams = []
        for mc_vis in visible_sats_for_each_minicluster:
            for sat_tuple, beam_idx in mc_vis:
                sig = f"{sat_tuple[0]}_{beam_idx}"
                if sig not in unique_beam_signatures:
                    unique_beam_signatures.add(sig)
                    available_beams.append((sat_tuple, beam_idx))

        if not available_beams:
            for ue, _ in all_ues:
                ue.scheduled_handover = {'time': time, 'sat': None, 'beam': None}
            return

        # Virtualizzazione risorse (Water-Filling)
        virtual_beams = [{'sat_tuple': st, 'beam_idx': b_idx, 'slot': s} 
                         for st, b_idx in available_beams 
                         for s in range(int(self.WATER_FILLING_LIMIT))]

        num_ues, num_vbeams = len(all_ues), len(virtual_beams)
        cost_matrix = np.full((num_ues, num_vbeams), 1000.0)

        # -----------------------------------------------------------------
        # PILASTRO 2: CALCOLO FUNZIONE DI UTILITA' IBRIDA CON ISTERESI ADDITIVA
        # -----------------------------------------------------------------
        for i, (ue, mini_cluster) in enumerate(all_ues):
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()
            curr_sat_name = curr_sat_obj.name if curr_sat_obj else None
            
            valid_signatures = {f"{st[0]}_{b}" for st, b in visible_sats_for_each_minicluster[mini_cluster.index]}
            mc_lat, mc_lon, mc_alt = mini_cluster.position
            
            for j, v_beam in enumerate(virtual_beams):
                target_sat_name, target_beam_idx = v_beam['sat_tuple'][0], v_beam['beam_idx']
                if f"{target_sat_name}_{target_beam_idx}" not in valid_signatures: continue 
                
                # Geometria Reale
                target_lat, target_lon, target_alt = v_beam['sat_tuple'][1:4]
                link_elev_real = ChannelParameters.elevation_angle_deg(mc_lat, mc_lon, target_lat, target_lon, target_alt)
                
                try:
                    t_fut_str = (time + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                    if (t_fut_str, target_sat_name) in self.orbit_cache:
                        f_lat, f_lon, f_alt = self.orbit_cache[(t_fut_str, target_sat_name)]
                        slope_real = ChannelParameters.elevation_angle_deg(mc_lat, mc_lon, f_lat, f_lon, f_alt) - link_elev_real
                    else: slope_real = 0.0
                except: slope_real = 0.0
                
                # Iniezione Rumore Percezione SDN (Canale Stocastico)
                link_elev_perceived = np.clip(link_elev_real - (slope_real * self.tau_c) + random.gauss(0, self.sigma_theta), 0.0, 90.0)
                slope_perceived = slope_real + random.gauss(0, self.sigma_theta / 2.0)
                
                # Base Utility Score (Geometria + Trend Cinematico)
                w_score = max(0.01, 0.8 * (link_elev_perceived / 90.0) + 0.2 * np.clip(slope_perceived / 0.5, -1.0, 1.0))
                
                # Penalità Meteo (Markov)
                if self.weather_state.get(target_sat_name) == 'B': 
                    w_score *= 0.5 
                
                # Isteresi Moltiplicativa Legacy
                w_score *= self.INTRA_HO_PENALTY if target_sat_name == curr_sat_name else self.INTER_HO_PENALTY
                
                # Shannon Spreading (Divisione Risorse nello Stesso Fascio)
                w_score *= (1.0 / (v_beam['slot'] + 1.0))
                
                # -------------------------------------------------------------
                # MODIFICA SCIENTIFICA: ISTERESI ADDITIVA (ANTI-PING-PONG)
                # -------------------------------------------------------------
                # Se l'assegnazione virtuale coincide ESATTAMENTE con il nodo fisico 
                # (stesso satellite e stesso fascio) a cui l'UE è già connesso, 
                # iniettiamo un bonus netto. Questo impedisce il "Chasing the Noise".
                if curr_sat_name is not None and target_sat_name == curr_sat_name and target_beam_idx == curr_beam_idx:
                    w_score += self.SWITCHING_COST_BONUS
                        
                cost_matrix[i, j] = -w_score

        # -----------------------------------------------------------------
        # PILASTRO 3: OTTIMIZZAZIONE GLOBALE (Kuhn-Munkres)
        # -----------------------------------------------------------------
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        # -----------------------------------------------------------------
        # PILASTRO 4: TEMPORAL TRIGGER SPREADING (TTS)
        # -----------------------------------------------------------------
        round_time_local = (time + timedelta(microseconds=500000)).replace(microsecond=0)
        t_minus_1 = round_time_local - timedelta(seconds=1)

        for idx in range(len(row_ind)):
            ue_idx, v_beam_idx = row_ind[idx], col_ind[idx]
            ue, mini_cluster = all_ues[ue_idx]
            v_beam = virtual_beams[v_beam_idx] 
            
            target_sat_name, target_beam = v_beam['sat_tuple'][0], v_beam['beam_idx']
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()
            
            # Controllo validità
            if cost_matrix[ue_idx, v_beam_idx] == 1000.0 or (curr_sat_obj and curr_sat_obj.name == target_sat_name and curr_beam_idx == target_beam):
                ue.scheduled_handover = None if curr_sat_obj else {'time': time, 'sat': None, 'beam': None}
                continue

            # Calcolo Finestra Stocastica Delta W
            delta_w = 1.0
            if curr_sat_obj and getattr(ue, 'ema_elevation', None):
                try:
                    elev_old = utils.get_elevation(self.frame, t_minus_1, curr_sat_obj.name, mini_cluster.position)
                    derivata_elev = ue.ema_elevation - elev_old
                    if derivata_elev < -0.01:
                        theta_min = getattr(self.cluster, 'elevation_threshold', 30.0)
                        delta_w = max(1.0, min(((ue.ema_elevation - theta_min) / abs(derivata_elev)) - 2.0, 15.0))
                    else: delta_w = 10.0
                except: delta_w = 3.0
            
            # Astrazione tempo scheduling
            scheduled_time = time + timedelta(seconds=int(random.uniform(0, delta_w)))

            if target_sat_name not in service_sats:
                service_sats[target_sat_name] = Satellite(target_sat_name, self.cluster.sat_servers, self.cluster.sat_mu_inter, self.cluster.sat_mu_intra, self.cluster.num_beams)
            
            ue.scheduled_handover = {'time': scheduled_time, 'sat': service_sats[target_sat_name], 'beam': target_beam}