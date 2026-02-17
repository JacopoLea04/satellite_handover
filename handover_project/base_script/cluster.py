from ue import Ue
from datetime import timedelta

class Cluster:
    def __init__(self, name, position, num_ues, satellites_frame, threshold_snr):
        self.name = name
        self.num_ues = num_ues
        self.position = position
        # for the moment all the UEs in the cluster are at the same position
        self.list_ues = [Ue(ii+1, position) for ii in range(num_ues)]
        self.frame = satellites_frame
        self.threshold = threshold_snr



    def initial_connection_phase(self, time):
        # For each UE, find the best satellite to connect to based on the highest SNR
        # This entire process should be managed in parallel for all UEs in the cluster, 
        # so it would require the time required for a single connection.
        for ue in self.list_ues:
            # Find the best satellite for this UE according to link budget metrics and number
            # of UEs already connected to the satellite. Update the satellite's load and the 
            # UE's connection information accordingly.
            satellite = get_best_satellite(self.frame, time) # TODO
            ue.connect_to_satellite(satellite)
            satellite.update_load() 


        # return the total time required for this entire process
        # 10 ms is the estimated time for conditional handover provided by the 3GPP
        return timedelta(milliseconds=10)



    # apply conditional handover based on SNR
    def monitor(self, time):
        for ue in self.list_ues:
            delay = self.snr_conditional_handover(ue, time)



    def snr_conditional_handover(self, ue, time):
        snr = -1000
        delay = timedelta(0)
        if ue.get_connection_info() is not None:
                print("DIO CAN che cazzo stai facendo allora")
        else:
            satellite = ue.get_connection_info()
            snr = compute_snr(satellite, time) # TODO

        # PLEASE NOTICE: this process should required some time! And now
        # we are not considering it
        if(snr < self.threshold):
            # until now the handover trigger event is equal for all
            # the UEs!!!
            satellite = get_best_satellite(self.frame, time)
            delay = ue.handover(satellite)
        return delay



    def get_rates(self, frame, time):
        rates = []
        for ue in self.list_ues:
            current_sat = ue.get_connection_info()
            if current_sat is not None:
                rate = current_sat.get_rate(frame, time) # TODO
                rates.append((ue, rate))
        return rates