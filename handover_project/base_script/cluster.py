from ue import Ue
from beam import Beam
from satellite import Satellite
from datetime import datetime, timedelta
import utils
import random
import numpy as np

# Importiamo il nuovo cervello centrale
from sdn_controller import SDN_Controller

class Cluster:
    def __init__(self, name, position, num_ues, beam_size_km, num_beams, satellites_frame, servers, mu_inter, mu_intra, scenario, enable_elevation = False, elevation_threshold = 0):
        self.name = name
        self.position = position
        self.num_ues = num_ues
        self.beam_size_km = beam_size_km
        self.num_beams = num_beams
        self.enable_elevation = enable_elevation
        self.elevation_threshold = elevation_threshold
        self.frame = satellites_frame
        self.sat_servers = servers
        self.sat_mu_inter = mu_inter
        self.sat_mu_intra = mu_intra
        self.scenario = scenario

        # Inizializziamo il Controller SDN
        self.sdn_controller = SDN_Controller(self, scenario, satellites_frame)

        # Beams computation
        self.positions = self.calculate_beams_grid(self.position[0], self.position[1], self.beam_size_km, self.num_beams)
        self.list_beams = [Beam(self.name + "-Beam" + str(ii+1), ii, self.positions[ii], int(num_ues/num_beams), self.beam_size_km, int(np.sqrt(num_beams)), servers, mu_inter, mu_intra) for ii in range(self.num_beams)]

        # =====================================================================
        # 3. IMPLEMENTAZIONE STOCASTICA: Traffico Bursty (Markov ON/OFF)
        # =====================================================================
        self.t_on_mean = 3.0   
        self.t_off_mean = 12.0 
        
        self.p_on_to_off = 1.0 / self.t_on_mean
        self.p_off_to_on = 1.0 / self.t_off_mean
        
        for mini_cluster in self.list_beams:
            for ue in mini_cluster.list_ues:
                ue.traffic_state = 'ON' if random.random() < (self.t_on_mean / (self.t_on_mean + self.t_off_mean)) else 'OFF'

    def calculate_beams_grid(self, center_lat, center_lon, beam_size_km, num_beams):
        grid_size = int(np.sqrt(num_beams))
        center_lat = np.float64(center_lat)
        center_lon = np.float64(center_lon)
        
        KM_PER_DEG_LAT = np.float64(111.32)
        km_per_deg_lon = KM_PER_DEG_LAT * np.cos(np.radians(center_lat))
        
        indices = np.arange(grid_size)
        center_idx = grid_size // 2 
        
        col_grid, row_grid = np.meshgrid(indices, indices)
        
        delta_y_km = (center_idx - row_grid).astype(np.float64) * beam_size_km
        delta_x_km = (col_grid - center_idx).astype(np.float64) * beam_size_km
        
        lats = (center_lat + (delta_y_km / KM_PER_DEG_LAT)).flatten()
        lons = (center_lon + (delta_x_km / km_per_deg_lon)).flatten()
        alts = np.zeros_like(lats, dtype=np.float64)

        return list(zip(lats, lons, alts))

    def initial_connection_phase(self, time, service_sats, handover_timer = 0):
        round_time = (time + timedelta(microseconds=500000)).replace(microsecond=0)
        visible_sats = utils.get_satellites_at_time(self.frame, round_time)
        visible_sats_for_each_minicluster = [[] for _ in range(self.num_beams)]
        
        for sat in visible_sats:
            sat_lat, sat_lon = sat[1], sat[2]
            sat_cell_boundaries = utils.compute_cell_boundaries_lla(sat_lat, sat_lon, self.beam_size_km*1000, int(np.sqrt(self.num_beams)))
            visible_clusters_indices = utils.check_clusters_visibility(self.positions, sat_cell_boundaries, int(np.sqrt(self.num_beams)))

            if(visible_clusters_indices.size == 0):
                continue

            satellite_beam_indices = utils.get_coverage_beam_indices_matrix(visible_clusters_indices, int(np.sqrt(self.num_beams)))
            
            rows, cols = visible_clusters_indices.shape
            for ii in range(rows):
                for jj in range(cols):
                    idx_cluster = visible_clusters_indices[ii][jj]
                    idx_sat_beam = satellite_beam_indices[ii][jj]
                    if(idx_sat_beam != -1):
                        visible_sats_for_each_minicluster[idx_cluster].append((sat, idx_sat_beam))
        
        for index, mini_cluster in enumerate(self.list_beams):
            mini_cluster.initial_connection_phase(visible_sats_for_each_minicluster[index], time, service_sats, handover_timer)
                
        self.sdn_controller.run_optimization(time, service_sats, visible_sats_for_each_minicluster)
        return service_sats
    

    def monitor(self, time, service_sats, ho_condition, sat_selection_condition):
        round_time = (time + timedelta(microseconds=500000)).replace(microsecond=0)

        visible_sats = utils.get_satellites_at_time(self.frame, round_time)
        visible_sats_for_each_minicluster = [[] for _ in range(self.num_beams)]
        
        for sat in visible_sats:
            sat_lat, sat_lon, sat_alt = sat[1], sat[2], sat[3]
            sat_cell_boundaries = utils.compute_cell_boundaries_lla(sat_lat, sat_lon, self.beam_size_km*1000, int(np.sqrt(self.num_beams)))
            visible_clusters_indices = utils.check_clusters_visibility(self.positions, sat_cell_boundaries, int(np.sqrt(self.num_beams)), self.enable_elevation, self.elevation_threshold, sat_lat, sat_lon, sat_alt)

            if(visible_clusters_indices.size == 0):
                continue

            satellite_beam_indices = utils.get_coverage_beam_indices_matrix(visible_clusters_indices, int(np.sqrt(self.num_beams)))
            rows, cols = visible_clusters_indices.shape
            for ii in range(rows):
                for jj in range(cols):
                    idx_cluster = visible_clusters_indices[ii][jj]
                    idx_sat_beam = satellite_beam_indices[ii][jj]
                    if(idx_sat_beam != -1):
                        visible_sats_for_each_minicluster[idx_cluster].append((sat, idx_sat_beam))

        for mini_cluster in self.list_beams:
            for ue in mini_cluster.list_ues:
                curr_sat, curr_beam_index = ue.get_connection_info()
                
                if ue.traffic_state == 'ON':
                    if random.random() < self.p_on_to_off:
                        ue.traffic_state = 'OFF'
                else:
                    if random.random() < self.p_off_to_on:
                        ue.traffic_state = 'ON'
                
                if curr_sat is not None:
                    try:
                        raw_snr_dl, raw_snr_ul = utils.get_snr(self.frame, round_time, curr_sat.name, mini_cluster.position, self.scenario)
                        raw_snr_dl += random.gauss(0, self.scenario['dlul_snr_variance'])
                        raw_snr_ul += random.gauss(0, self.scenario['dlul_snr_variance'])
                        raw_elev = utils.get_elevation(self.frame, round_time, curr_sat.name, mini_cluster.position)
                    except:
                        raw_snr_dl, raw_snr_ul, raw_elev = 0, 0, 0
                else:
                    raw_snr_dl, raw_snr_ul, raw_elev = 0, 0, 0
                
                ue.update_ema_filters(raw_snr_dl, raw_snr_ul, raw_elev)

        # =====================================================================
        # 3A. MODELLO RACH (Random Access Channel) - Slotted ALOHA
        # =====================================================================
        rach_attempts = {}
        for mini_cluster in self.list_beams:
            for ue in mini_cluster.list_ues:
                if getattr(ue, 'scheduled_handover', None) is not None:
                    sched_time = ue.scheduled_handover['time']
                    
                    # BUG FIX: Controlliamo esplicitamente che 'sat' non sia None
                    if sched_time <= time and ue.remaining_handover_execution_time == 0:
                        target_sat_obj = ue.scheduled_handover['sat']
                        if target_sat_obj is not None: # Solo se saltiamo su un satellite vero
                            target_sat = target_sat_obj.name
                            rach_attempts.setdefault(target_sat, []).append(ue)
        
        collided_ues = set()
        rach_preambles = 64 
        
        for sat, ues_in_rach in rach_attempts.items():
            if len(ues_in_rach) > 1:
                preambles = [random.randint(1, rach_preambles) for _ in ues_in_rach]
                for idx, ue in enumerate(ues_in_rach):
                    if preambles.count(preambles[idx]) > 1:
                        collided_ues.add(ue.id) 

        # =====================================================================
        # 3B. Esecuzione Ordini SDN e Applicazione Penalità di Backoff
        # =====================================================================
        for mini_cluster in self.list_beams:
            for ue in mini_cluster.list_ues:
                was_in_ho = ue.remaining_handover_execution_time > 0
                
                ue.execute_scheduled_handover(time)
                
                is_in_ho = ue.remaining_handover_execution_time > 0
                
                if (not was_in_ho) and is_in_ho and (ue.id in collided_ues):
                    backoff_delay_ms = random.randint(500, 1500) 
                    ue.remaining_handover_execution_time += backoff_delay_ms

        trigger_sdn = False
        if time.second % 5 == 0:
            trigger_sdn = True
        else:
            for mini_cluster in self.list_beams:
                for ue in mini_cluster.list_ues:
                    curr_sat, _ = ue.get_connection_info()
                    if curr_sat is not None and ue.ema_elevation is not None:
                        try:
                            elev_old = utils.get_elevation(self.frame, round_time - timedelta(seconds=1), curr_sat.name, mini_cluster.position)
                            derivata_elev = ue.ema_elevation - elev_old
                            
                            if derivata_elev < 0:
                                t_crit = (ue.ema_elevation - self.elevation_threshold) / abs(derivata_elev)
                                if t_crit <= 1.0:
                                    trigger_sdn = True
                                    break
                        except:
                            pass
                if trigger_sdn:
                    break

        if trigger_sdn and sat_selection_condition == "MADM_PREHO":
            self.sdn_controller.run_optimization(time, service_sats, visible_sats_for_each_minicluster)

        self.save_instant_throughput(time)

    def save_instant_throughput(self, target_time):
        active_users_map = {}
        for mc in self.list_beams:
            for u in mc.list_ues:
                sat_obj, b_idx = u.get_connection_info()
                if sat_obj is not None and getattr(u, 'traffic_state', 'OFF') == 'ON':
                    key = (sat_obj.name, b_idx)
                    active_users_map[key] = active_users_map.get(key, 0) + 1

        for mini_cluster in self.list_beams:
            for ue in mini_cluster.list_ues:
                serving_satellite, serving_beam_index = ue.get_connection_info()
                if(serving_satellite is None or serving_beam_index is None):
                    thr_info = {
                        "time": target_time,
                        "ue.id": ue.id,
                        "sat.id": None,
                        "max_dl_thr": 0,
                        "max_ul_thr": 0,
                        "connected_users": 1,
                        "ho_duration": 0,
                        "dl_thr": 0,
                        "ul_thr": 0
                    }
                    ue.thr_tracker.append(thr_info)
                    continue
                
                max_dl_thr, max_ul_thr = utils.get_max_beam_throughput(self.frame, target_time, serving_satellite.name, mini_cluster.position, self.scenario)
                
                key = (serving_satellite.name, serving_beam_index)
                active_users_in_beam = max(1, active_users_map.get(key, 0))
                
                dl_ue_throughput = max_dl_thr / active_users_in_beam
                ul_ue_throughput = max_ul_thr / active_users_in_beam
                
                equivalent_snr_dl_db, equivalent_snr_ul_db = utils.reverse_snr_from_thr(dl_ue_throughput, ul_ue_throughput, self.scenario)
                equivalent_snr_dl_db -= self.scenario['dl_db_headroom']
                equivalent_snr_ul_db -= self.scenario['ul_db_headroom']
                
                dl_ue_throughput, ul_ue_throughput = utils.compute_shannon_from_snr(equivalent_snr_dl_db, equivalent_snr_ul_db, self.scenario)
                
                ho_duration_ms = ue.remaining_handover_execution_time
                if(ue.remaining_handover_execution_time >= 1000):
                    dl_ue_throughput = 0
                    ul_ue_throughput = 0
                    ue.remaining_handover_execution_time -= 1000
                elif(ue.remaining_handover_execution_time > 0):
                    dl_ue_throughput = dl_ue_throughput * (1 - ue.remaining_handover_execution_time/1000)
                    ul_ue_throughput = ul_ue_throughput * (1 - ue.remaining_handover_execution_time/1000)
                    ue.remaining_handover_execution_time = 0

                dl_ue_throughput *= (1 - self.scenario['3gpp_overhead_dl'])
                ul_ue_throughput *= (1 - self.scenario['3gpp_overhead_ul'])

                thr_info = {
                        "time": target_time,
                        "ue.id": ue.id,
                        "sat.id": serving_satellite.name,
                        "max_dl_thr": max_dl_thr,
                        "max_ul_thr": max_ul_thr,
                        "connected_users": active_users_in_beam, 
                        "ho_duration": ho_duration_ms,
                        "dl_thr": dl_ue_throughput,
                        "ul_thr": ul_ue_throughput
                    }
                ue.thr_tracker.append(thr_info)