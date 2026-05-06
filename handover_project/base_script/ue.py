from satellite import Satellite
import pandas as pd
import os

class Ue:
    def __init__(self, id, position):
        self.id = id
        self.lat = position[0]
        self.lon = position[1]
        self.alt = position[2]
        self.connected_to = None
        self.connected_to_beam = None
        self.handover_tracker = []
        self.intra_handover_flag = False # save if the ue has performed ho in the current time instant
        self.inter_handover_flag = False
        self.remaining_handover_execution_time = 0 # [ms] save the ho duration at this time instant if the ue has performed ho
        self.thr_tracker = []

    
    def connect_to_satellite(self, satellite, beam_index):
        """
        Connect the UE to a satellite and a specific beam index.
        This should be called whenever the UE needs to connect to a satellite,
        either for the initial connection or for a handover.
        """
        self.connected_to = satellite
        self.connected_to_beam = beam_index

    
    def deactivate(self, cluster_name):
        """
        Deactivate the UE. This should be called once the UE is no longer needed.
        """
        # handover df
        df = pd.DataFrame(self.handover_tracker)
        filename = f"{self.id}_handover_events.csv"

        output_folder = cluster_name + " dataframes"
        full_path = os.path.join(output_folder, filename)
        os.makedirs(output_folder, exist_ok=True)

        df.to_csv(full_path, index=False)

        # throughput df
        df = pd.DataFrame(self.thr_tracker)
        filename = f"{self.id}_thr_over_time.csv"

        output_folder = cluster_name + " throughput"
        full_path = os.path.join(output_folder, filename)
        os.makedirs(output_folder, exist_ok=True)

        df.to_csv(full_path, index=False)


    def get_connection_info(self):
        """
        Return the satellite object and the beam index to which the UE is currently connected.
        """
        return self.connected_to, self.connected_to_beam

    
    def inter_handover(self, time, dest_sat, dest_beam_index):
        """
        Handle the handover process for the UE, and append the handover_info structh and the general connection infos 
        to all the nodes involved according to the specific case we fall in.
        All the possible cases are:
            1) From None to None (out_serv)
            2) From Sat1 to None (lost_conn)
            3) From None to Sat2 (rest_conn)
            4) From Sat1 to Sat2 (inter_ho)
        """
        curr_sat, curr_beam_index = self.get_connection_info()

        # Case 1) and 2)
        if(dest_sat is None):
            event_type = "out_serv"
            curr_sat_name = None

            if(curr_sat is not None): # Case 2)
                event_type = "lost_conn"
                curr_sat_name = curr_sat.name

            handover_info = {
                    "arrival_time": time,
                    "event_type": event_type,
                    "ue_id": self.id,
                    "from_satellite": curr_sat_name,
                    "from_beam_index": curr_beam_index,
                    "dest_satellite": None,
                    "dest_beam_index": None,
                    "start_time": time,
                    "departure_time": 0,
                    "duration": 1,
                    "dest_number_ues": None
                }

            # update curr_sat infos
            if(curr_sat is not None):
                curr_sat.disconnect_ue(curr_beam_index)
                curr_sat.handover_manager.handover_tracker.append(handover_info)

            # update UE infos
            self.disconnect()
            self.remaining_handover_execution_time = handover_info["duration"]
            self.handover_tracker.append(handover_info)

            return 
        
        # Case 3) and 4)
        else: 
            if(curr_sat is None): # Case 3)
                handover_info = {
                    "arrival_time": time,
                    "event_type": "rest_conn",
                    "ue_id": self.id,
                    "from_satellite": None,
                    "from_beam_index": None,
                    "dest_satellite": dest_sat.name,
                    "dest_beam_index": dest_beam_index,
                    "start_time": time,
                    "departure_time": 0,
                    "duration": 1,
                    "dest_number_ues": dest_sat.connected_ues.copy()
                }

                # update destt_sat infos 
                dest_sat.handover_manager.handover_tracker.append(handover_info)
                dest_sat.connect_ue(dest_beam_index)

                # update UE infos
                self.remaining_handover_execution_time = handover_info["duration"] * 1000
                self.handover_tracker.append(handover_info)
                self.connect_to_satellite(dest_sat , dest_beam_index)

            else: # Case 4)
                handover_info = curr_sat.handover_manager.process_handover_inter(time, self, curr_beam_index, dest_sat, dest_beam_index)

                # update satellites infos
                dest_sat.handover_manager.handover_tracker.append(handover_info)
                dest_sat.connect_ue(dest_beam_index)
                curr_sat.handover_manager.handover_tracker.append(handover_info)
                curr_sat.disconnect_ue(curr_beam_index)

                # update UE infos
                self.remaining_handover_execution_time = handover_info["duration"] * 1000
                self.handover_tracker.append(handover_info)
                self.connect_to_satellite(dest_sat , dest_beam_index)

        return  

    def intra_handover(self, time, dest_sat, dest_beam_index):
        """
        Handle the intra-handover process for the UE, append the handover_info struct to both ue and curr_sat
        (please notice that the dest_sast is equal to the curr_sat), and update the counter of curr_sat and 
        beam_index for the UE.
        """

        # update curr_sat and dest_sat infos and retrive the handover_info struct according to the queue process
        curr_sat, curr_beam_index = self.get_connection_info()
        handover_info = curr_sat.handover_manager.process_handover_intra(time, self, curr_beam_index, dest_sat, dest_beam_index)
        curr_sat.handover_manager.handover_tracker.append(handover_info)
        curr_sat.disconnect_ue(curr_beam_index)
        dest_sat.connect_ue(dest_beam_index)

        # update the ue infos
        self.connect_to_satellite(dest_sat , dest_beam_index) # so as to update to which satellite this ue is connected
        self.remaining_handover_execution_time = handover_info["duration"] * 1000
        self.handover_tracker.append(handover_info)

        return 
    

    def disconnect(self):
        """
        Disconnect the UE from its current satellite. This should be called when the UE goes out of service.
        """
        self.connected_to = None
        self.connected_to_beam = None
