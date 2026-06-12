from pyclbr import Class
from skyfield.api import load, EarthSatellite
# Import rimosso: non usiamo più 'heapq' per simulare code intasate
import random
import pandas as pd
import os
from datetime import datetime

class Satellite:
    def __init__(self, name, servers = 1, mu_inter = 0.03, mu_intra = 0.001, num_beams = 0, tle_data = None):
        self.name = name
        self.tle_data = tle_data
        self.handover_manager = self.HandoverManager(self, servers = servers, mu_inter = mu_inter , mu_intra = mu_intra)
        self.num_beams = num_beams
        self.connected_ues = [0] * num_beams # I create a satellite only when a Ue wants to connect to him


    class HandoverManager:
        # In architettura SDN, la congestione è risolta a monte dal Temporal Trigger Spreading (TTS).
        # Il server del satellite esegue deterministicamente il ritardo di propagazione puro.
        def __init__(self, satellite, servers, mu_inter, mu_intra):
            self.satellite = satellite
            self.servers = servers
            self.mu_inter = mu_inter
            self.mu_intra = mu_intra
            # Nessuna coda stocastica. L'esecuzione è governata centralmente.
            self.handover_tracker = []

        def process_handover_intra(self, arrival_time, ue, curr_beam_index, dest_satellite, dest_beam_index):
            """
            Processa l'intra-handover. Durata puramente fisica (1 ms). Nessun accodamento.
            """
            event_type = "intra_ho"
            duration = self.mu_intra # 1 ms
            
            # Esecuzione istantanea rispetto al trigger SDN
            arrival_time_rel = arrival_time.timestamp()
            start_time = arrival_time_rel
            end_time = start_time + duration
            
            start_time_dt = datetime.fromtimestamp(start_time)
            end_time_dt = datetime.fromtimestamp(end_time)

            handover_info = {
                "arrival_time": arrival_time,
                "event_type": event_type,
                "ue_id": ue.id,
                "from_satellite": self.satellite.name,
                "from_beam_index": curr_beam_index,
                "dest_satellite": dest_satellite.name,
                "dest_beam_index": dest_beam_index,
                "start_time": start_time_dt,
                "departure_time": end_time_dt,
                "duration": duration,
                "dest_number_ues": dest_satellite.connected_ues.copy()
            }
                
            return handover_info

        def process_handover_inter(self, arrival_time, ue, curr_beam_index, dest_satellite, dest_beam_index):
            """
            Processa l'inter-handover. Durata puramente fisica (30 ms). Nessun accodamento.
            """
            event_type = "inter_ho"
            duration = self.mu_inter  # 30 ms
            
            # Esecuzione istantanea rispetto al trigger SDN
            arrival_time_rel = arrival_time.timestamp()
            start_time = arrival_time_rel
            end_time = start_time + duration
            
            start_time_dt = datetime.fromtimestamp(start_time)
            end_time_dt = datetime.fromtimestamp(end_time)

            handover_info = {
                "arrival_time": arrival_time,
                "event_type": event_type,
                "ue_id": ue.id,
                "from_satellite": self.satellite.name,
                "from_beam_index": curr_beam_index,
                "dest_satellite": dest_satellite.name,
                "dest_beam_index": dest_beam_index,
                "start_time": start_time_dt,
                "departure_time": end_time_dt,
                "duration": duration,
                "dest_number_ues": dest_satellite.connected_ues.copy()
            }

            return handover_info

        def deactivate(self):
            """
            This function should be called once the satellite is no longer needed. It will save the output dataframe to a csv file.
            """
            df = pd.DataFrame(self.handover_tracker)
            filename = f"{self.satellite.name}_handover_events.csv"

            output_folder = "Satellite dataframes_preho"
            full_path = os.path.join(output_folder, filename)
            os.makedirs(output_folder, exist_ok=True)

            df.to_csv(full_path, index=False)


    def connect_ue(self, beam_index):
        """
        Handles the connection of a single UE.
        """
        self.connected_ues[beam_index] += 1
        return self.connected_ues[beam_index]
    
    def deactivate(self):
        """
        Deactivate the satellite. This should be called once the satellite is no longer needed.
        It will call the respective deactivate method of the handover_manager class to save the output dataframe to a csv file.
        """
        self.handover_manager.deactivate()
        self.handover_manager = None

    def disconnect_ue(self, index):
        """
        Handles the disconnection of a single UE.
        """
        if self.connected_ues[index] > 0:
            self.connected_ues[index] -= 1
        return self.connected_ues

    def get_position(self, time):
        ts = load.timescale()
        t = ts.utc(time.year, time.month, time.day, time.hour, time.minute, time.second)

        satellite = EarthSatellite(self.tle_data[1], self.tle_data[2])  # Create EarthSatellite object
        geocentric = satellite.at(t)  # Use the created EarthSatellite object here
        subpoint = geocentric.subpoint()

        latitude = subpoint.latitude.degrees
        longitude = subpoint.longitude.degrees
        height = subpoint.elevation.m

        return latitude, longitude, height