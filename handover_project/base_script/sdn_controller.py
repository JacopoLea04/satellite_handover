import numpy as np
import utils
from scipy.optimize import linear_sum_assignment
import random
import pandas as pd
from datetime import timedelta
from satellite import Satellite
from channel_parameters import ChannelParameters # Fondamentale per la fisica reale

class SDN_Controller:
    def __init__(self, cluster, scenario, dataframe):
        self.cluster = cluster
        self.scenario = scenario
        self.df = dataframe
        self.WATER_FILLING_LIMIT = 15.0 
        self.INTRA_HO_PENALTY = 1.0     
        self.INTER_HO_PENALTY = 0.70    

    def run_optimization(self, time, service_sats, visible_sats_for_each_minicluster):
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
        
        # Inizializziamo con una penalità immensa (1000.0) per impedire le connessioni fuori copertura
        cost_matrix = np.full((num_ues, num_virtual_beams), 1000.0)

        for i, (ue, mini_cluster) in enumerate(all_ues):
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()
            curr_sat_name = curr_sat_obj.name if curr_sat_obj else None
            
            # Recuperiamo i satelliti VERAMENTE visibili da QUESTO minicluster
            valid_targets = visible_sats_for_each_minicluster[mini_cluster.index]
            valid_signatures = {f"{sat_tuple[0]}_{b_idx}" for sat_tuple, b_idx in valid_targets}
            
            mc_lat, mc_lon, mc_alt = mini_cluster.position
            
            for j, v_beam in enumerate(virtual_beams):
                target_sat_name = v_beam['sat_tuple'][0]
                target_beam_idx = v_beam['beam_idx']
                sig = f"{target_sat_name}_{target_beam_idx}"
                
                # 1. BARRIERA DI COPERTURA (Anti-Fantasma)
                if sig not in valid_signatures:
                    continue # Lascia 1000.0, l'Ungherese non lo sceglierà mai
                
                # 2. CALCOLO FISICO REALE CON DERIVATA DELL'ELEVAZIONE (LOOK-AHEAD)
                target_sat_lat = v_beam['sat_tuple'][1]
                target_sat_lon = v_beam['sat_tuple'][2]
                target_sat_alt = v_beam['sat_tuple'][3]
                
                link_elev = ChannelParameters.elevation_angle_deg(mc_lat, mc_lon, target_sat_lat, target_sat_lon, target_sat_alt)
                
                # Calcolo della derivata predittiva (guardando 1 secondo nel futuro nel dataframe)
                try:
                    time_future = time + timedelta(seconds=1)
                    # Cerchiamo la posizione futura del satellite target nel vettore di stato globale
                    t_fut_str = time_future.strftime("%Y-%m-%d %H:%M:%S") if hasattr(time_future, 'strftime') else str(time_future)
                    matched_future = self.df[(self.df['time'].astype(str) == t_fut_str) & (self.df['sat_name'].astype(str) == target_sat_name)]
                    
                    if not matched_future.empty:
                        f_lat = float(matched_future['sat_lat'].iloc[0])
                        f_lon = float(matched_future['sat_lon'].iloc[0])
                        f_alt = float(matched_future['sat_height'].iloc[0])
                        elev_future = ChannelParameters.elevation_angle_deg(mc_lat, mc_lon, f_lat, f_lon, f_alt)
                        
                        # dTheta/dt
                        slope = elev_future - link_elev
                    else:
                        slope = 0.0
                except:
                    slope = 0.0

                # Punteggio pesato: 80% elevazione istantanea, 20% trend predittivo
                alpha = 0.8
                beta = 0.2
                # Normalizziamo lo slope (assumendo variazioni massime di 0.5 gradi al secondo per costellazioni LEO)
                slope_normalized = np.clip(slope / 0.5, -1.0, 1.0)
                
                w_score = alpha * (link_elev / 90.0) + beta * slope_normalized
                w_score = max(0.01, w_score) # Evita punteggi negativi o nulli 
                
                # 3. ISTERESI ASIMMETRICA
                if curr_sat_name is not None:
                    if target_sat_name == curr_sat_name:
                        w_score *= self.INTRA_HO_PENALTY
                    else:
                        w_score *= self.INTER_HO_PENALTY
                
                # 4. SHANNON SLICE (Water-Filling Perfetto)
                slot_index = v_beam['slot'] 
                bandwidth_slice = 1.0 / (slot_index + 1.0)
                w_score *= bandwidth_slice
                        
                cost_matrix[i, j] = -w_score

        # =======================================================
        # ALGORITMO UNGHERESE (Kuhn-Munkres)
        # =======================================================
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        # =======================================================
        # TEMPORAL TRIGGER SPREADING (TTS)
        # =======================================================
        current_time_offset = 0 
        
        for idx in range(len(row_ind)):
            ue_idx = row_ind[idx]
            v_beam_idx = col_ind[idx]
            
            ue = all_ues[ue_idx][0]
            v_beam = virtual_beams[v_beam_idx] 
            
            target_sat_name = v_beam['sat_tuple'][0]
            target_beam = v_beam['beam_idx']
            
            curr_sat_obj, curr_beam_idx = ue.get_connection_info()

            if isinstance(time, pd.Timestamp):
                scheduled_time = time + timedelta(seconds=current_time_offset)
            else:
                scheduled_time = time + timedelta(seconds=current_time_offset)
            
            # Controllo Anti-Saturazione: se il costo è rimasto 1000.0, l'utente è fisicamente irraggiungibile
            if cost_matrix[ue_idx, v_beam_idx] == 1000.0:
                ue.scheduled_handover = {'time': scheduled_time, 'sat': None, 'beam': None}
                continue

            if curr_sat_obj is None or curr_sat_obj.name != target_sat_name or curr_beam_idx != target_beam:
                if target_sat_name not in service_sats:
                    sat = Satellite(target_sat_name, self.cluster.sat_servers, self.cluster.sat_mu_inter, self.cluster.sat_mu_intra, self.cluster.num_beams)
                    service_sats[target_sat_name] = sat
                dest_sat_obj = service_sats[target_sat_name]
                
                if (idx % 3) == 0: 
                    current_time_offset += 1
                
                ue.scheduled_handover = {
                    'time': scheduled_time,
                    'sat': dest_sat_obj,
                    'beam': target_beam
                }
            else:
                ue.scheduled_handover = None