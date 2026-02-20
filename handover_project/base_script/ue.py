from datetime import timedelta

class Ue:
    def __init__(self, id, position):
        self.id = id
        self.lat = position[0]
        self.lon = position[1]
        self.alt = position[2]
        self.connected_to = None


    def connect_to_satellite(self, satellite):
        self.connected_to = satellite
        # TODO print a line in the df

    def handover(self, ime, dest_sat):
        from_sat = self.get_connection_info
        self.connect_to_satellite(dest_sat) # so as to update to which satellite this ue is connected
        from_sat.disconnetct_to_ue(self) # disconnect the ue from the current satellite

        # TODO from_sat.handover_manager.process_handover(time, from_sat, dest_sat)
        # TODO print a line in its df
        return


    def get_connection_info(self):
        return self.connected_to




        

