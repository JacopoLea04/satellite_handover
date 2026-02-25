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
            
        return service_sats
    
    def monitor(self, time, service_sats):

        for ue in self.list_ues:

            # just lower than the actual treshold
            snr = self.threshold - 1
            curr_sat = ue.get_connection_info()

            if(curr_sat is not None):
                snr = utils.compute_dl_snr(self.frame, curr_sat.name, time)

            # handover condition (satellite out of visibility or snr lower than trheshold)
            if(snr == None or snr < self.threshold):

                # find all visible satellites at the given time
                visible_sats = utils.get_satellites_at_time(self.frame, time)
                best_sat = utils.get_best_satellite(visible_sats, service_sats)

                exists = any(sat.name == best_sat[0] for sat in service_sats)
                if not exists:
                    dest_sat = Satellite(best_sat[0], self.sat_servers, self.sat_mu) 
                    service_sats.append(dest_sat)
                else:
                    # retrive the index of the selected satellite within the service satellites list
                    index = next((i for i, sat in enumerate(service_sats) if sat.name == best_sat[0]), -1)
                    dest_sat = service_sats[index]

                ue.handover(time, dest_sat)


        return service_sats
                