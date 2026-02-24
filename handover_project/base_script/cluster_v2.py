from ue import Ue
from satellite import Satellite
from datetime import timedelta
import utils
import random
from satellite import Satellite

class Cluster:
    def __init__(self, name, position, num_ues, satellites_frame, threshold_snr):
        self.name = name
        self.num_ues = num_ues
        self.position = position
        # TODO for the moment all the UEs in the cluster are at the same position
        self.list_ues = [Ue(ii+1, position) for ii in range(num_ues)]
        self.frame = satellites_frame
        self.threshold = threshold_snr
    
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

            random_index = random.randint(0, len(self.list_ues))
            selected_sat = visible_sats[random_index]

            exists = any(sat.name == selected_sat['sat_name'] for sat in service_sats)
            if not exists:
                sat = Satellite(selected_sat) # TODO how to actually create a Satellite object
                service_sats.append(sat)

            # retrive the index of the selected satellite within the service satellites list
            index = next((i for i, sat in enumerate(service_sats) if sat.name == selected_sat['sat_name']), -1)
            ue.connect_to_satellite(service_sats[index])
            service_sats[index].connect_to_ue(ue)
            
        return service_sats
    
    def monitor(self, time, service_sats):

        for ue in self.list_ues:

            # just lower than the actual treshold
            snr = self.threshold - 1
            curr_sat = ue.get_connection_info()

            if(curr_sat is not None):
                snr = utils.compute_dl_snr(self.frame, curr_sat.name, time )

            # handover condition
            if(snr == None or snr < self.threshold):

                # find all visible satellites at the given time
                visible_sats = utils.get_satellites_at_time(self.frame, service_sats, time)
                best_sat = utils.get_best_satellite(visible_sats, service_sats)
                ue.handover(time, curr_sat, best_sat)

                exists = any(sat.name == best_sat['sat_name'] for sat in service_sats)
                if not exists:
                    sat = Satellite(best_sat) # TODO how to actually create a Satellite object
                    service_sats.append(sat)

        return service_sats
                
            

        







    











        

   

    def snr_conditional_handover(self, ue, time):
        snr = -1000
        delay = timedelta(0)
        curr_satellite = ue.get_connection_info()

        if(curr_satellite is not None):
            # return None if no SNR value is found for the satellite at the given time 
            snr = utils.compute_dl_snr(self.frame, curr_satellite[0], time) 
        
        # TODO: this process should required some time! And now
        # we are not considering it
        # Handover conditions:
        #   satellite == None: 
        #   snr == None: our satellite went out of visibility
        #   snr < self.threshold: the SNR is too bad

        # Right now we are not connected to any satellite
        if(curr_satellite == None or snr == None or snr < self.threshold):
            # find the best satellite to connect to based on the highest SNR
            visible_sats = utils.get_satellites_at_time(self.frame, time)
            if(not visible_sats):
                print(f"*** No visible satellites for UE {ue.id} at time {time}. ***")
                if(curr_satellite is not None):
                    delay += ue.disconnect_from_satellite("No visible satellites")
                    self.frame = utils.decrement_connected_users_df(self.frame, time, curr_satellite[0])
                return delay
            new_satellite = utils.get_best_satellite_by_available_dl_thr(visible_sats)
            # perform handover and update the UE's connection and the satellite's load in the DF
            delay = timedelta(0)
            # we are currently connected to a satellite
            if curr_satellite is not None:
                msg = " "
                if snr is None:
                    msg = "it went out of visibility"
                else:
                    msg = f"SNR {snr} is below the threshold {self.threshold}"
                delay += ue.disconnect_from_satellite(msg)
                self.frame = utils.decrement_connected_users_df(self.frame, time, curr_satellite[0])
            
            delay += ue.connect_to_satellite(new_satellite)
            self.frame = utils.increment_connected_users_df(self.frame, time, new_satellite[0])

        return delay
    