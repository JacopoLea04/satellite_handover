"""
This file implements the Centralized Software-Defined Networking (SDN) Controller for a Non-Terrestrial Network (NTN) LEO satellite constellation. 
It provides a holistic framework for predictive handover management, utilizing a deterministic Digital Twin, Constrained Resource Virtualization (Hard Cap), Bipartite Matching (Kuhn-Munkres), and dual-stage temporal filters (Asymmetric TTT and TTS). 
"""

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
        """
        Initializes the optimized SDN controller with parameters defined for structural stability and spatial water-filling validation.
        """
        self.cluster = cluster
        self.scenario = scenario
        self.df = dataframe
        
        # --- PARAMETRI OTTIMIZZATI PER LA RUN DEFINITIVA ---
        self.WATER_FILLING_LIMIT = 25.0  
        self.PRE_FILTER_LIMIT = 11.0     
        self.LOCK_IN_ELEVATION = 40.0    
        self.CRITICAL_ELEVATION = 30.0    
        
        self.INTRA_HO_PENALTY = 0.35      
        self.INTER_HO_PENALTY = 0.20     
        self.SWITCHING_COST_BONUS = 0.05  
        
        self.TTT_NORMAL = 2             
        self.TTT_CRITICAL = 1             
        self.pending_handovers = {}       
        # ---------------------------------------------------
        
        self.tau_c = 0.250  
        self.sigma_theta = 0.5  
        
        self.dt_markov = 1.0 
        self.T_good = 45.0 
        self.T_bad = 15.0  
        self.p_gb = self.dt_markov / self.T_good
        self.p_bg = self.dt_markov / self.T_bad
        self.weather_state = {}
        self.last_weather_update_time = None

        print("\n[SDN] Controller Inizializzato (Architettura Proposta - Elastic Soft-Cap)")
        print("[SDN] Generazione Hash Map telemetrica (Digital Twin)...")
        self.orbit_cache = {}
        for row in dataframe.itertuples():
            key = (str(row.time), str(row.sat_name))
            self.orbit_cache[key] = (float(row.sat_lat), float(row.sat_lon), float(row.sat_height))
        print(f"[SDN] Tabella Hash completata ({len(self.orbit_cache)} stati pre-calcolati).\n")

    def run_optimization(self, time, service_sats, visible_sats_for_each_minicluster):
        """
        Executes the Hybrid SDN handover orchestration. 
        """
        # 1. Markov Weather Fading Update
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

        active_ues = []
        locked_beam_counts = {}

        # 2. Capacity-Aware Pre-Filtering (Lock-in)
        for ue, mc in all_ues:
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()
            mc_valid_signatures = {f"{st[0]}_{b}" for st, b in visible_sats_for_each_minicluster[mc.index]}
            
            is_locked = False
            if curr_sat_obj:
                curr_sat_name = curr_sat_obj.name
                sig = f"{curr_sat_name}_{curr_beam_idx}"
                weather = self.weather_state.get(curr_sat_name, 'G')
                
                elev = getattr(ue, 'ema_elevation', 0.0)
                if elev is None: elev = 0.0
                
                current_locks = locked_beam_counts.get(sig, 0)
                
                if weather == 'G' and elev >= self.LOCK_IN_ELEVATION and sig in mc_valid_signatures and current_locks < self.PRE_FILTER_LIMIT:
                    is_locked = True
                    locked_beam_counts[sig] = current_locks + 1
                    if id(ue) in self.pending_handovers:
                        del self.pending_handovers[id(ue)]
                        
            if not is_locked:
                active_ues.append((ue, mc))

        if not active_ues:
            return  

        # 3. Virtualization and Elastic Water-Filling (Soft Cap)
        virtual_beams = []
        OVERFLOW_LIMIT = 45  # Limite di emergenza assoluto per evitare drop
        
        for st, b_idx in available_beams:
            sig = f"{st[0]}_{b_idx}"
            used_slots = locked_beam_counts.get(sig, 0)
            
            # 3.A Generiamo gli Slot Garantiti (Fino al WATER_FILLING_LIMIT)
            available_guaranteed = max(0, int(self.WATER_FILLING_LIMIT) - used_slots)
            for s in range(used_slots, used_slots + available_guaranteed):
                virtual_beams.append({'sat_tuple': st, 'beam_idx': b_idx, 'slot': s, 'type': 'guaranteed'})
            
            # 3.B Generiamo gli Slot di Overflow (Best-Effort)
            current_total = used_slots + available_guaranteed
            if current_total < OVERFLOW_LIMIT:
                for s in range(current_total, OVERFLOW_LIMIT):
                    virtual_beams.append({'sat_tuple': st, 'beam_idx': b_idx, 'slot': s, 'type': 'overflow'})

        num_ues, num_vbeams = len(active_ues), len(virtual_beams)
        if num_vbeams == 0: return
        cost_matrix = np.full((num_ues, num_vbeams), 1000.0)

        # 4. Utility Matrix Construction
        for i, (ue, mini_cluster) in enumerate(active_ues):
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()
            curr_sat_name = curr_sat_obj.name if curr_sat_obj else None
            
            valid_signatures = {f"{st[0]}_{b}" for st, b in visible_sats_for_each_minicluster[mini_cluster.index]}
            mc_lat, mc_lon, mc_alt = mini_cluster.position
            
            for j, v_beam in enumerate(virtual_beams):
                target_sat_name, target_beam_idx = v_beam['sat_tuple'][0], v_beam['beam_idx']
                if f"{target_sat_name}_{target_beam_idx}" not in valid_signatures: continue 
                
                target_lat, target_lon, target_alt = v_beam['sat_tuple'][1:4]
                link_elev_real = ChannelParameters.elevation_angle_deg(mc_lat, mc_lon, target_lat, target_lon, target_alt)
                
                try:
                    t_fut_str = (time + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
                    if (t_fut_str, target_sat_name) in self.orbit_cache:
                        f_lat, f_lon, f_alt = self.orbit_cache[(t_fut_str, target_sat_name)]
                        slope_real = ChannelParameters.elevation_angle_deg(mc_lat, mc_lon, f_lat, f_lon, f_alt) - link_elev_real
                    else: slope_real = 0.0
                except: slope_real = 0.0
                
                link_elev_perceived = np.clip(link_elev_real - (slope_real * self.tau_c) + random.gauss(0, self.sigma_theta), 0.0, 90.0)
                slope_perceived = slope_real + random.gauss(0, self.sigma_theta / 2.0)
                
                w_score = max(0.01, 0.8 * (link_elev_perceived / 90.0) + 0.2 * np.clip(slope_perceived / 0.5, -1.0, 1.0))
                
                if self.weather_state.get(target_sat_name) == 'B': 
                    w_score *= 0.5 
                
                # --- LA MAGIA DELL'ELASTIC CAP ---
                # Penalità classica di Shannon per la banda condivisa
                w_score *= (1.0 / (v_beam['slot'] + 1.0)) 
                
                # Penalità MASSIVA se è uno slot di Overflow
                if v_beam['type'] == 'overflow':
                    w_score *= 0.001  # L'algoritmo lo userà solo per salvare l'utente dall'OOS
                # ---------------------------------

                if curr_sat_name is not None:
                    if target_sat_name == curr_sat_name and target_beam_idx == curr_beam_idx:
                        w_score += self.SWITCHING_COST_BONUS
                    elif target_sat_name == curr_sat_name and target_beam_idx != curr_beam_idx:
                        w_score *= self.INTRA_HO_PENALTY
                    else:
                        w_score *= self.INTER_HO_PENALTY

                cost_matrix[i, j] = -w_score 

        # 5. Global Bipartite Matching
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        
        # [NEW]: Admission Control di Emergenza (Evita i fantasmi oltre l'Overflow)
        assigned_ue_indices = set(row_ind)
        for idx, (ue, _) in enumerate(active_ues):
            if idx not in assigned_ue_indices:
                ue.scheduled_handover = {'time': time, 'sat': None, 'beam': None}
                if id(ue) in self.pending_handovers:
                    del self.pending_handovers[id(ue)]
        
        round_time_local = (time + timedelta(microseconds=500000)).replace(microsecond=0)
        t_minus_1 = round_time_local - timedelta(seconds=1)

        # 6. Asymmetric TTT and Temporal Spreading (TTS) Execution
        for idx in range(len(row_ind)):
            ue_idx, v_beam_idx = row_ind[idx], col_ind[idx]
            ue, mini_cluster = active_ues[ue_idx]
            v_beam = virtual_beams[v_beam_idx] 
            
            target_sat_name, target_beam = v_beam['sat_tuple'][0], v_beam['beam_idx']
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()
            
            # Scarta assegnazioni non valide (costo 1000) o mantenimento dello stesso stato
            if cost_matrix[ue_idx, v_beam_idx] == 1000.0 or (curr_sat_obj and curr_sat_obj.name == target_sat_name and curr_beam_idx == target_beam):
                if id(ue) in self.pending_handovers:
                    del self.pending_handovers[id(ue)]
                if not curr_sat_obj:
                    ue.scheduled_handover = {'time': time, 'sat': None, 'beam': None}
                continue

            ue_id = id(ue)
            sig_target = f"{target_sat_name}_{target_beam}"
            
            elev_current = getattr(ue, 'ema_elevation', 0.0)
            if elev_current is None: elev_current = 0.0
            
            if curr_sat_obj is None or elev_current < self.CRITICAL_ELEVATION:
                required_ttt = self.TTT_CRITICAL  
            else:
                required_ttt = self.TTT_NORMAL    

            if ue_id not in self.pending_handovers or self.pending_handovers[ue_id]['sig'] != sig_target:
                self.pending_handovers[ue_id] = {'sig': sig_target, 'sat': target_sat_name, 'beam': target_beam, 'count': 1}
            else:
                self.pending_handovers[ue_id]['count'] += 1
                
            if self.pending_handovers[ue_id]['count'] >= required_ttt:
                if ue_id in self.pending_handovers:
                    del self.pending_handovers[ue_id]
                    
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
                
                scheduled_time = time + timedelta(seconds=int(random.uniform(0, delta_w)))

                if target_sat_name not in service_sats:
                    service_sats[target_sat_name] = Satellite(target_sat_name, self.cluster.sat_servers, self.cluster.sat_mu_inter, self.cluster.sat_mu_intra, self.cluster.num_beams)
                
                ue.scheduled_handover = {'time': scheduled_time, 'sat': service_sats[target_sat_name], 'beam': target_beam}