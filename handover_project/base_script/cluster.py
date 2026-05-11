from ue import Ue
from beam import Beam
from satellite import Satellite
from datetime import timedelta
import utils
import random
from satellite import Satellite
import numpy as np

class Cluster:
    def __init__(self, name, position, num_ues, beam_size_km, num_beams, satellites_frame, threshold_snr, servers, mu_inter, mu_intra, scenario):
        self.name = name
        self.position = position
        self.num_ues = num_ues
        self.beam_size_km = beam_size_km
        self.num_beams = num_beams
        self.frame = satellites_frame
        self.threshold = threshold_snr
        self.sat_servers = servers
        self.sat_mu_inter = mu_inter
        self.sat_mu_intra = mu_intra
        self.scenario = scenario

        # beams computation
        self.positions = self.calculate_beams_grid(self.position[0], self.position[1], self.beam_size_km, self.num_beams)
        self.list_beams = [Beam(self.name + "-Beam" + str(ii+1), ii, self.positions[ii], int(num_ues/num_beams), self.beam_size_km, int(np.sqrt(num_beams)), servers, mu_inter, mu_intra) for ii in range(self.num_beams)]

    # in order to compute the position of the beams, we assume that they are arranged in a grid centered on the cluster position, 
    # and that the distance between adjacent beams is equal to the beam size. We then compute the latitude and longitude of each 
    # beam based on the center position and the beam size, taking into account the curvature of the Earth. 
    def calculate_beams_grid(self, center_lat, center_lon, beam_size_km, num_beams):
        """
        This function calculates the positions of the beams' centers in a grid pattern around the center position.
        """
        grid_size = int(np.sqrt(num_beams))
        # Ensure inputs are treated as float64 (doubles)
        center_lat = np.float64(center_lat)
        center_lon = np.float64(center_lon)
        
        KM_PER_DEG_LAT = np.float64(111.32)
        km_per_deg_lon = KM_PER_DEG_LAT * np.cos(np.radians(center_lat))
        
        indices = np.arange(grid_size)
        center_idx = grid_size // 2 
        
        col_grid, row_grid = np.meshgrid(indices, indices)
        
        # Calculate offsets using float64 math
        delta_y_km = (center_idx - row_grid).astype(np.float64) * beam_size_km
        delta_x_km = (col_grid - center_idx).astype(np.float64) * beam_size_km
        
        # Final Lats and Lons
        lats = (center_lat + (delta_y_km / KM_PER_DEG_LAT)).flatten()
        lons = (center_lon + (delta_x_km / km_per_deg_lon)).flatten()
        
        # Create altitude as float64 zeros
        alts = np.zeros_like(lats, dtype=np.float64)

        return list(zip(lats, lons, alts))



    # only at the beginning of the simulation, we attech every UEs of all the mini-cluster to a beam 
    # of a random satellite within the visibility.
    def initial_connection_phase(self, time, service_sats):
        """
        This function handles the initial connection phase for the UEs in the mini-cluster.
        It should connect each UE to a random visible satellite. If no available satellite is visible, the UE will be 
        considered out of service until a satellite becomes visible.
        Inputs:
            - time: the current time of the simulation, used to determine the visible satellites at this time.
            - service_sats: a dictionary that will be updated with the satellites that are serving the UEs of the cluster.
        
        """
        # Find all visible satellites at the given time
        # round to the closest sec
        round_time = (time + timedelta(microseconds=500000)).replace(microsecond=0)
        visible_sats = utils.get_satellites_at_time(self.frame, round_time)

        # visible_sats identifies all the satellites visibled by at least one mini-cluster of the cluster.
        # we need to find which mini-clusters can see each satellite
        # "visible_sats_for_each_minicluster" is a list of lists, where the i-th element is the list of 
        # satellites visible from the i-th mini-cluster
        visible_sats_for_each_minicluster = [[] for _ in range(self.num_beams)]
        for sat in visible_sats:
            sat_lat, sat_lon = sat[1], sat[2]
            sat_cell_boundaries = utils.compute_cell_boundaries_lla(sat_lat, sat_lon, self.beam_size_km*1000, int(np.sqrt(self.num_beams)))
            visible_clusters_indices = utils.check_clusters_visibility(self.positions, sat_cell_boundaries, int(np.sqrt(self.num_beams)))

            # case when the current examinated satellite illimunate only a portion of a specific mini-cluster but not its center, i.e., it
            # illuminates less then 50%, so we conclude that mini-cluster cannot be served by that satellite beam.
            if(visible_clusters_indices.size == 0):
                continue

            satellite_beam_indices = utils.get_coverage_beam_indices_matrix(visible_clusters_indices, int(np.sqrt(self.num_beams)))
            
            rows, cols = visible_clusters_indices.shape
            for ii in range(rows):
                for jj in range(cols):
                    idx_cluster = visible_clusters_indices[ii][jj]
                    idx_sat_beam = satellite_beam_indices[ii][jj]
                    visible_sats_for_each_minicluster[idx_cluster].append((sat, idx_sat_beam))

        for index, mini_cluster in enumerate(self.list_beams):
            mini_cluster.initial_connection_phase(visible_sats_for_each_minicluster[index], time, service_sats)
                
        return service_sats
    


    def monitor(self, time, service_sats, ho_condition, sat_selection_condition):
        """
            This function handles the monitoring of the current connections of the UEs and the handover process if needed. 
            It should be called at each time step of the simulation. For each mini-cluster, it checks the visibility of the satellites
            and determines if a handover is needed for each UE. If a handover is needed, it selects the target satellite randomly. 
            For the moment the only ho condition is the visibility. 

            visible_sats_for_each_minicluster is a list of lists, where each element is a list containing the visible 
            satellites for the corresponding mini-cluster as follows: [(sat1, idx_sat_beam1), (sat2, idx_sat_beam2), ...] 
            Specifically, satX is a tuple with the satellite info (name, lat, lon) and idx_sat_beamX is the index of the 
            beam of the satellite that covers the mini-cluster.

            For example, if we have 3 mini-clusters, the structure of visible_sats_for_each_minicluster will be as follows:

            __                                                                                                              __
            |                                                                                                                |
            | [(sat1, idx_sat_beam1), ...]   ,   [(sat1, idx_sat_beam1), ...]   ,   [(sat1, idx_sat_beam1), ...]   ,   ...   |
            |_                                                                                                              _|
            
                mini-cluster 1 (index 0)            mini-cluster 2 (index 1)           mini-cluster 3 (index 2)        ...


            Handle the handover process for the UE.
            Possible scenarios:
            1) The UE is currently connected to a satellite and needs to handover to a new beam of the same satellite (intra-satellite handover).
            2) The UE is currently connected to a satellite and needs to handover to a new beam of a different satellite (inter-satellite handover).
            3) The UE is not currently connected to any satellite and needs to connect to a new beam of a satellite (inter-satellite handover).
            4) The Ue is not currently connected to any satellite and no satellite is visible, so it remains out of service (inter-satellite handover)).
        """
        # round to the closest sec
        round_time = (time + timedelta(microseconds=500000)).replace(microsecond=0)

        # check the visibility of all satellites respect to the whole cluster
        visible_sats = utils.get_satellites_at_time(self.frame, round_time)
        visible_sats_for_each_minicluster = [[] for _ in range(self.num_beams)]
        for sat in visible_sats:
            sat_lat, sat_lon = sat[1], sat[2]
            sat_cell_boundaries = utils.compute_cell_boundaries_lla(sat_lat, sat_lon, self.beam_size_km*1000, int(np.sqrt(self.num_beams)))
            visible_clusters_indices = utils.check_clusters_visibility(self.positions, sat_cell_boundaries, int(np.sqrt(self.num_beams)))

            # case when the current examinated satellite illimunate only a portion of a specific mini-cluster but not its center, i.e., it
            # illuminates less then 50%, so we conclude that mini-cluster cannot be served by that satellite beam.
            if(visible_clusters_indices.size == 0):
                continue

            satellite_beam_indices = utils.get_coverage_beam_indices_matrix(visible_clusters_indices, int(np.sqrt(self.num_beams)))
            rows, cols = visible_clusters_indices.shape
            for ii in range(rows):
                for jj in range(cols):
                    idx_cluster = visible_clusters_indices[ii][jj]
                    idx_sat_beam = satellite_beam_indices[ii][jj]
                    visible_sats_for_each_minicluster[idx_cluster].append((sat, idx_sat_beam))


        # check if each UE needs to perform an intra or an inter handover based on the handover condition.
        for mini_cluster in self.list_beams:
            for ue in mini_cluster.list_ues:
                curr_sat, curr_beam_index = ue.get_connection_info()
                ue.intra_handover_flag = False
                ue.inter_handover_flag = False
                next_sat = None

                # ============== Detect the type of required handover (if needed) ==============

                # check if the current satellite is still visible from the mini-cluster of the UE
                if curr_sat is None: # UE is not connected to any satellite
                    index = -1
                else:
                    index = next((i for i, (obj, *_) in enumerate(visible_sats_for_each_minicluster[mini_cluster.index]) if obj[0] == curr_sat.name), -1)
                    
                if (index == -1): # the current satellite is not visible anymore --> inter handover
                    ue.inter_handover_flag = True
                elif (curr_beam_index != visible_sats_for_each_minicluster[mini_cluster.index][index][1]): # the current satellite is still visible --> check if intra handover is needed
                    ue.intra_handover_flag = True
                else: # Other possible handover trigger events
                    event = ho_condition[0]
                    if(event == "SNR"):
                        dl_threshold, ul_threshold = ho_condition[1], ho_condition[2]
                        snr_dl, snr_ul = utils.get_snr(self.frame, round_time, curr_sat.name, mini_cluster.position, self.scenario)
                        if(snr_dl < dl_threshold or snr_ul < ul_threshold):
                            ue.inter_handover_flag = True
                    elif(event == "ELEVATION"):
                        elev_threshold = ho_condition[1]
                        sat_elev = utils.get_elevation(self.frame, round_time, curr_sat.name, mini_cluster.position)
                        if(sat_elev < elev_threshold):
                            ue.inter_handover_flag = True


                # ============== Performe the handover (if selected) ==============
                
                if(ue.intra_handover_flag): # handover to a new visible beam of the same satellite
                    next_sat = curr_sat
                    next_beam_index = visible_sats_for_each_minicluster[mini_cluster.index][index][1]
                    ue.intra_handover(time, next_sat, next_beam_index)

                elif(ue.inter_handover_flag): # handover to a new beam of a new satellite

                    # possible satellites beams towards which the ue could handover
                    choices = len(visible_sats_for_each_minicluster[mini_cluster.index])
                    # if no one, the ue goes out of service
                    if(choices == 0):
                        next_sat = None
                        next_beam_index = None
                    # if there is at least one, select a random one among them and handover
                    else:
                        # select a random satellite among the visible ones and handover to it
                        random_index = random.randint(0, choices-1)
                        next_sat = visible_sats_for_each_minicluster[mini_cluster.index][random_index][0]
                        next_beam_index = visible_sats_for_each_minicluster[mini_cluster.index][random_index][1]

                        # is this satellite already configured?
                        selected_sat_name = next_sat[0]
                        if selected_sat_name not in service_sats:
                            sat = Satellite(selected_sat_name, self.sat_servers, self.sat_mu_inter, self.sat_mu_intra, self.num_beams)
                            service_sats[selected_sat_name] = sat
                        next_sat = service_sats[selected_sat_name]

                    # handover to the selected sat (if no one, go out of service)
                    ue.inter_handover(time, next_sat, next_beam_index)
        self.save_instant_throughput(time)

    def save_instant_throughput(self, target_time):
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
                connected_users = serving_satellite.connected_ues[serving_beam_index]
                # instant throughput computation
                dl_ue_throughput = max_dl_thr / connected_users
                ul_ue_throughput = max_ul_thr / connected_users
                ho_duration_ms = ue.remaining_handover_execution_time
                if(ue.remaining_handover_execution_time >= 1000):
                    dl_ue_throughput = 0
                    ul_ue_throughput = 0
                    ue.remaining_handover_execution_time -= 1000
                elif(ue.remaining_handover_execution_time > 0):
                    dl_ue_throughput = dl_ue_throughput * (1 - ue.remaining_handover_execution_time/1000)
                    ul_ue_throughput = ul_ue_throughput * (1 - ue.remaining_handover_execution_time/1000)
                    ue.remaining_handover_execution_time = 0
                thr_info = {
                        "time": target_time,
                        "ue.id": ue.id,
                        "sat.id": serving_satellite.name,
                        "max_dl_thr": max_dl_thr,
                        "max_ul_thr": max_ul_thr,
                        "connected_users": connected_users,
                        "ho_duration": ho_duration_ms,
                        "dl_thr": dl_ue_throughput,
                        "ul_thr": ul_ue_throughput
                    }
                ue.thr_tracker.append(thr_info)