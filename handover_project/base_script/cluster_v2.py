from ue import Ue
from satellite import Satellite
from datetime import timedelta
import utils
import random
from satellite import Satellite
import numpy as np

class Cluster:
    def __init__(self, name, position, num_ues, satellites_frame, threshold_snr, servers, mu):
        self.name = name
        self.num_ues = num_ues
        self.position = position
        # TODO for the moment all the UEs in the cluster are at the same position
        self.list_ues = [Ue(self.name + "-Ue" + str(ii+1), position) for ii in range(num_ues)]
        self.frame = satellites_frame
        self.threshold = threshold_snr
        self.sat_servers = servers
        self.sat_mu = mu
    
    def get_ues_list(self):
        return self.list_ues


    # only at the beginning of the simulation
    def initial_connection_phase(self, time, service_sats):

        # Find all visible satellites at the given time
        # round to the closest sec
        round_time = (time + timedelta(microseconds=500000)).replace(microsecond=0)
        visible_sats = utils.get_satellites_at_time(self.frame, round_time)

        if(len(visible_sats) > 0):
            # For each UE, connect to a random satellite
            for ue in self.list_ues:

                random_index = random.randint(0, len(visible_sats)-1)
                selected_sat = visible_sats[random_index]
                selected_sat_name = selected_sat[0]

                # is this satellite already configured?
                if selected_sat_name not in service_sats:
                    sat = Satellite(selected_sat_name, self.sat_servers, self.sat_mu)
                    service_sats[selected_sat_name] = sat

                ue.connect_to_satellite(service_sats[selected_sat_name])
                service_sats[selected_sat_name].connect_ue()

                handover_info = {
                    "arrival_time": time,
                    "event_type": "init_con",
                    "ue_id": ue.id,
                    "from_satellite": None,
                    "dest_satellite": service_sats[selected_sat_name].name,
                    "start_time": time,
                    "departure_time": 0,
                    "duration": 0,
                    "dest_number_ues": service_sats[selected_sat_name].connected_ues
                }
                service_sats[selected_sat_name].handover_manager.handover_tracker.append(handover_info)
                ue.handover_tracker.append(handover_info)
        else:
            # all the ues are out of service
            for ue in self.list_ues:
                handover_info = {
                    "arrival_time": time,
                    "event_type": "out_serv",
                    "ue_id": ue.id,
                    "from_satellite": None,
                    "dest_satellite": None,
                    "start_time": time,
                    "departure_time": 0,
                    "duration": 1.0,
                    "dest_number_ues": 0
                }
                ue.handover_tracker.append(handover_info)
                
        return service_sats
    
    def monitor(self, time, service_sats, ho_condition, sat_selection_condition):

        # note service_sats is a list of Satellite objects.
        # so as to avoid tha UE1 is always the first one to be served
        random_list_ues = self.list_ues.copy()
        random.shuffle(random_list_ues)
        visible_sats = None # optimized so the visible satellites are computed at most once per time instant
        # round to the closest sec
        round_time = (time + timedelta(microseconds=500000)).replace(microsecond=0)
        max_visible_time_sat = None

        for ue in random_list_ues:
            # just lower than the actual treshold
            snr = self.threshold - 1
            curr_sat = ue.get_connection_info()
            if(curr_sat is not None):
                # the UE does not have a perfect knowledge of the SNR, so the measurement should be affected by some noise. 
                # we therefore introduce a measurement error expressed as zero-mean gaussian noise with a standard deviation of 1 dB.
                # this reflects 3GPP TS 38.133 (Requirements for support of radio resource management).
                snr = utils.compute_dl_snr(self.frame, curr_sat.name, round_time)
                if snr is not None:
                    snr += np.random.normal(0, 1)  # add gaussian noise
            handover = False
            if(ho_condition == "SNR"):
                # handover condition (satellite out of visibility or snr lower than trheshold)
                handover = (snr == None or snr < self.threshold)
            elif(ho_condition == "VISIBILITY"):
                handover = (curr_sat == None or snr is None)
            else:
                print("!!! Something wrong, I can feel it: no valid handover condition provided!")

            # update ho_flag for the current ue (save if the ue has performed ho in this time instant)
            ue.ho_flag = handover
            if(handover):
                if visible_sats is None:
                    # visible_sats is a tuple representing a satellite, but the number of connected users is at zero
                    visible_sats = utils.get_satellites_at_time(self.frame, round_time)
                
                best_sat = None
                if(sat_selection_condition == "AVL_THR"):
                    best_sat = utils.get_best_satellite(visible_sats, service_sats)
                elif(sat_selection_condition == "SNR_THR"):
                    best_sat = utils.get_best_satellite_by_snr_and_thr(visible_sats, service_sats)
                elif(sat_selection_condition == "RANDOM"):
                    best_sat = utils.get_random_satellite(visible_sats)
                elif(sat_selection_condition == "MAX_VISIBILITY"):
                    if(not max_visible_time_sat):
                        max_visible_time_sat = utils.get_max_visibility_satellite_v2(visible_sats, time, self.frame, fraction = 0.3, n_min = 5)
                    index = random.randint(0, len(max_visible_time_sat)-1)
                    best_sat = max_visible_time_sat[index]
                elif(sat_selection_condition == "MAX_ELEVATION"):
                    best_sat = utils.get_max_elevation_satellite(visible_sats, fraction = 0.3, n_min = 5)
                else:
                    print("!!! Something wrong, I can feel it: no valid satellite selection criterion provided")
                
                # handle situation where no visible satellites
                if(best_sat == None):

                    if(curr_sat is None):
                        handover_info = {
                            "arrival_time": time,
                            "event_type": "out_serv",
                            "ue_id": ue.id,
                            "from_satellite": None,
                            "dest_satellite": None,
                            "start_time": time,
                            "departure_time": 0,
                            "duration": 1.0,
                            "dest_number_ues": 0
                        }
                    else:
                        handover_info = {
                            "arrival_time": time,
                            "event_type": "lost_conn",
                            "ue_id": ue.id,
                            "from_satellite": None,
                            "dest_satellite": None,
                            "start_time": time,
                            "departure_time": 0,
                            "duration": 1.0,
                            "dest_number_ues": 0
                        }
                    ue.handover_tracker.append(handover_info)
                    if(ue.get_connection_info() is not None):
                        curr_sat = ue.get_connection_info()
                        curr_sat.disconnect_ue()
                        sat_handover_info = {
                            "arrival_time": time,
                            "event_type": "lost_conn",
                            "ue_id": ue.id,
                            "from_satellite": curr_sat.name,
                            "dest_satellite": None,
                            "start_time": time,
                            "departure_time": 0,
                            "duration": 1.0,
                            "dest_number_ues": 0
                        }
                        curr_sat.handover_manager.handover_tracker.append(sat_handover_info)
                        ue.connected_to = None
                else: # we have at least one visible satellite
                    dest_sat = None
                    # is this satellite already configured?
                    if best_sat[0] not in service_sats:
                        dest_sat = Satellite(best_sat[0], self.sat_servers, self.sat_mu) 
                        dest_sat.connect_ue()
                        service_sats[best_sat[0]] = dest_sat
                    else:
                        dest_sat = service_sats[best_sat[0]]
                        dest_sat.connect_ue()
                    if(ue.get_connection_info() is None):
                        ue.initial_connection_to(time, dest_sat)
                    else:
                        ue.handover(time, dest_sat)


    def save_instant_thr(self, time, service_sats):

        for ue in self.list_ues:
            # data collection
            serv_sat = ue.connected_to
            max_dl_thr, max_ul_thr = utils.get_max_thr(self.frame, serv_sat.name, time)
            connected_users = serv_sat.connected_ues
            ho_duration_ms = 0
            if(ue.ho_flag):
                ho_duration_ms = ue.ho_duration

            # instant throughput computation
            temp_dl_throughput = max_dl_thr / connected_users
            temp_ul_throughput = max_ul_thr / connected_users
            if(ho_duration_ms >= 1000):
                temp_dl_throughput = 0
                temp_ul_throughput = 0
                ho_duration_ms -= 1000
            elif(ho_duration_ms > 0):
                temp_dl_throughput = temp_dl_throughput * (1 - ho_duration_ms/1000)
                temp_ul_throughput = temp_ul_throughput * (1 - ho_duration_ms/1000)

            thr_info = {
                        "time": time,
                        "ue.id": ue.id,
                        "sat.id": serv_sat.name,
                        "max_dl_thr": max_dl_thr,
                        "max_ul_thr": max_ul_thr,
                        "connected_users": connected_users,
                        "ho_duration": ho_duration_ms,
                        "dl_thr": temp_dl_throughput,
                        "ul_thr": temp_ul_throughput
                    }
            ue.thr_tracker.append(thr_info)
