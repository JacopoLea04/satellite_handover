from ue import Ue
from datetime import timedelta
import utils

class Cluster:
    def __init__(self, name, position, num_ues, satellites_frame, threshold_snr):
        self.name = name
        self.num_ues = num_ues
        self.position = position
        # TODO for the moment all the UEs in the cluster are at the same position
        self.list_ues = [Ue(ii+1, position) for ii in range(num_ues)]
        self.frame = satellites_frame
        self.threshold = threshold_snr


    # only at the beginning of the simulation
    def initial_connection_phase(self, time):
        print("\n=====================================================")
        print(f"INITIAL CONNECTION PHASE AT TIME: {time}")
        print("=====================================================\n")
        # For each UE, find the best satellite to connect to based on the highest SNR
        # TODO at the moment, there is no priority among the UEs
        for ue in self.list_ues:
            # Find all visible satellites at the given time
            visible_sats = utils.get_satellites_at_time(self.frame, time)
            # Select the best one according to the DL SNR
            satellite = utils.get_best_satellite_by_available_dl_thr(visible_sats)
            # Update the UE's connection and the satellite's load in the DF
            ue.connect_to_satellite(satellite)
            self.frame = utils.increment_connected_users_df(self.frame, time, satellite[0])

        # return the total time required for this entire process and the updated frame
        # TODO: 10 ms is the estimated time for conditional handover provided by the 3GPP
        delay = timedelta(milliseconds=10)
        return self.frame, delay


    
    # apply conditional handover based on SNR
    def monitor(self, frame, time):
        print("\n===========================================")
        print(f"MONITOR PHASE AT TIME: {time}")
        print("===========================================\n")
        # update the frame: this is needed if we have multiple clusters
        self.frame = frame
        delay_list = []
        for ue in self.list_ues:
            delay = self.snr_conditional_handover(ue, time)
            delay_list.append((ue, delay))
        return self.frame, delay_list

   

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
