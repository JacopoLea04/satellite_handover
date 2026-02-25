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
        self.handover_tracker = []


    def connect_to_satellite(self, satellite):
        self.connected_to = satellite
        # TODO print a line in the df

    def handover(self, time, dest_sat):
        curr_sat = self.get_connection_info()
        self.connect_to_satellite(dest_sat) # so as to update to which satellite this ue is connected
        curr_sat.disconnect_ue() # disconnect the ue from the current satellite

        handover_info = curr_sat.handover_manager.process_handover(time, self, dest_sat) # actual handover process
        self.handover_tracker.append(handover_info)

        # TODO what to do with handover_info ???
        return


    def get_connection_info(self):
        return self.connected_to
    
    def deactivate(self):
            df = pd.DataFrame(self.handover_tracker)
            filename = f"{self.id}_handover_events.csv"

            output_folder = "Ue dataframes"
            full_path = os.path.join(output_folder, filename)
            os.makedirs(output_folder, exist_ok=True)

            df.to_csv(full_path, index=False)




        

