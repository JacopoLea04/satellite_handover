from datetime import timedelta

class Ue:
    def __init__(self, id, position):
        self.id = id
        self.lat = position[0]
        self.lon = position[1]
        self.alt = position[2]
        self.connected_to = None


    def connect_to_satellite(self, satellite):
        # satellite is a tuple (sat_name, sat_lat, sat_lon, sat_alt, elev, slant, snr_dl, snr_ul, thr_dl, thr_ul, connected_users)
        self.connected_to = satellite
        print(f"UE {self.id} connected to {satellite[0]}")
        return timedelta(milliseconds=10)  # Estimated time for connection


    def get_connection_info(self):
        return self.connected_to


    def disconnect_from_satellite(self, msg):
        print(f"UE {self.id} disconnected from {self.connected_to[0]} since: {msg}")
        self.connected_to = None
        return timedelta(milliseconds=10)  # Estimated time for disconnection

        

