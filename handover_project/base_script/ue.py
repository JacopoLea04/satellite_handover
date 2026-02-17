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
        return timedelta(milliseconds=10)  # Estimated time for connection


    def disconnect_from_satellite(self):
        self.connected_to = None
        return timedelta(milliseconds=10)  # Estimated time for disconnection

    def get_connection_info(self):
        return self.connected_to


    # Check the SNR of the current connection and decide if a handover is needed
        # If a handover is needed, find the best satellite to connect to and perform the handover
        # Update the satellite's load and the UE's connection information accordingly.
    def handover(self, satellite):
        delay = timedelta(0)
        delay += self.disconnect_from_satellite()
        delay += self.connect_to_satellite(satellite)
        return delay