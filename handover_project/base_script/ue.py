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
        self.ho_flag = False # save if the ue has performed ho in the current time instant
        self.ho_duration = 0 # [ms] save the ho duration at this time instant if the ue has performed ho
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

    
    def handover(self, time, dest_sat, dest_beam_index):
        """
        Handle the handover process for the UE.
        Possible scenarios:
        1) The UE is currently connected to a satellite and needs to handover to a new beam of the same satellite (intra-satellite handover).
        2) The UE is currently connected to a satellite and needs to handover to a new beam of a different satellite (inter-satellite handover).
        3) The UE is not currently connected to any satellite and needs to connect to a new beam of a satellite (initial connection or reconnection after being out of service).
        4) The Ue is not currently connected to any satellite and no satellite is visible, so it remains out of service (out of service event).
        Args:
            time (datetime): The current time of the simulation.
            dest_sat (Satellite): The satellite to which the UE is being handed over.
            dest_beam_index (int): The index of the beam to which the UE is being handed over.
        Returns:
            handover_info (dict): a dictionary containing the following information:
                - arrival_time: The time at which the handover request arrives.
                - event_type: The type of event (e.g., "out_ho" for handover out).
                - ue_id: The ID of the UE being handed over.
                - from_satellite: The name of the current satellite.        
                - from_satellite_beam: The index of the current beam.
                - dest_satellite: The name of the destination satellite.
                - dest_satellite_beam: The index of the destination beam.
                - start_time: The time at which the handover process starts.
                - departure_time: The time at which the handover process ends.
                - duration: The duration of the handover process.
                - dest_number_ues: The number of UEs connected to the destination satellite after the handover.
        """
        curr_sat, curr_beam_index = self.get_connection_info()

        if curr_sat is not None: # disconnect the ue from the current satellite beam, and handover to the new one
            curr_sat.disconnect_ue(curr_beam_index) 
            handover_info = curr_sat.handover_manager.process_handover(time, self, curr_beam_index, dest_sat, dest_beam_index)
        else: # the UE is not connected to any satellite, just connect it to the new one
                handover_info = {
                    "arrival_time": time,
                    "event_type": "init_con",
                    "ue_id": self.id,
                    "from_satellite": None,
                    "from_satellite_beam": None,
                    "dest_satellite": dest_sat.name,
                    "dest_satellite_beam": dest_beam_index,
                    "start_time": time,
                    "departure_time": 0,
                    "duration": 1,
                    "dest_number_ues": dest_sat.connected_ues
                }
                dest_sat.handover_manager.handover_tracker.append(handover_info)


        self.connect_to_satellite(dest_sat , dest_beam_index) # so as to update to which satellite this ue is connected
        self.ho_duration = handover_info["duration"]
        self.handover_tracker.append(handover_info)

        return  
    

    def disconnect(self):
        """
        Disconnect the UE from its current satellite. This should be called when the UE goes out of service.
        """
        self.connected_to = None
        self.connected_to_beam = None
