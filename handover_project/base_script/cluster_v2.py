from ue import Ue
from satellite import Satellite
from datetime import timedelta
import utils
import random
from satellite import Satellite

class Cluster:
    def __init__(self, name, position, num_ues, satellites_frame, threshold_snr, servers, mu):
        self.name = name
        self.num_ues = num_ues
        self.position = position
        # TODO for the moment all the UEs in the cluster are at the same position
        self.list_ues = [Ue(ii+1, position) for ii in range(num_ues)]
        self.frame = satellites_frame
        self.threshold = threshold_snr
        self.sat_servers = servers
        self.sat_mu = mu
    
    def get_ues_list(self):
        return self.list_ues


    # only at the beginning of the simulation
    def initial_connection_phase(self, time):

        # Find all visible satellites at the given time
        visible_sats = utils.get_satellites_at_time(self.frame, time)

        # list of selected service satellite (Satellite object)
        service_sats = []

        if(len(visible_sats) > 0):
            # For each UE, connect to a random satellite
            for ue in self.list_ues:

                random_index = random.randint(0, len(visible_sats)-1)
                selected_sat = visible_sats[random_index]

                # is this satellite already configured?
                exists = any(sat.name == selected_sat[0] for sat in service_sats)
                if not exists:
                    sat = Satellite(selected_sat[0], self.sat_servers, self.sat_mu)
                    service_sats.append(sat)

                # retrive the index of the selected satellite within the service satellites list
                index = next((i for i, sat in enumerate(service_sats) if sat.name == selected_sat[0]), -1)
                ue.connect_to_satellite(service_sats[index])
                service_sats[index].connect_ue()

                handover_info = {
                    "arrival_time": time,
                    "event_type": "init_con",
                    "ue_id": ue.id,
                    "from_satellite": None,
                    "dest_satellite": service_sats[index].name,
                    "start_time": time,
                    "departure_time": 0,
                    "duration": 0,
                    "dest_number_ues": service_sats[index].connected_ues
                }
                service_sats[index].handover_manager.handover_tracker.append(handover_info)
                ue.handover_tracker.append(handover_info)
        else:
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

        for ue in random_list_ues:
            # just lower than the actual treshold
            snr = self.threshold - 1
            curr_sat = ue.get_connection_info()
            if(curr_sat is not None):
                snr = utils.compute_dl_snr(self.frame, curr_sat.name, time)
            handover = False
            if(ho_condition == "SNR"):
                # handover condition (satellite out of visibility or snr lower than trheshold)
                handover = (snr == None or snr < self.threshold)
            else:
                print("!!! Something wrong, I can feel it: no valid handover condition provided!")
            if(handover):
                if visible_sats is None:
                    # visible_sats is a tuple representing a satellite, but the number of connected users is at zero
                    visible_sats = utils.get_satellites_at_time(self.frame, time)
                # find all visible satellites at the given time RMEOVED FOR OPTIMIZATION 
                # visible_sats = utils.get_satellites_at_time(self.frame, time)

                ## note: this loop is wrong, the assegnation sat = sat[:10] + (sat_obj.connected_ues,) does nothing 
                # for (index, sat) in enumerate(visible_sats):
                #     exists = any(ss.name == sat[0] for ss in service_sats)
                #     if(exists):
                #         index = next((i for i, ss in enumerate(service_sats) if ss.name == sat[0]), -1)
                #         sat_obj = service_sats[index]
                #         sat = sat[:10] + (sat_obj.connected_ues,)
                
                best_sat = None
                if(sat_selection_condition == "AVL_THR"):
                    best_sat = utils.get_best_satellite(visible_sats, service_sats)
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
                            "event_type": "lost_serv",
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
                    exists = any(sat.name == best_sat[0] for sat in service_sats)
                    if not exists:
                        dest_sat = Satellite(best_sat[0], self.sat_servers, self.sat_mu) 
                        dest_sat.connect_ue()
                        service_sats.append(dest_sat)
                    else:
                        # retrive the index of the selected satellite within the service satellites list
                        index = next((i for i, sat in enumerate(service_sats) if sat.name == best_sat[0]), -1)
                        dest_sat = service_sats[index]
                        dest_sat.connect_ue()
                    if(ue.get_connection_info() is None):
                        ue.initial_connection_to(time, dest_sat)
                    else:
                        ue.handover(time, dest_sat)
        return service_sats