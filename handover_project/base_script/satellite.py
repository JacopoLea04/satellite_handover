from skyfield.api import load, EarthSatellite
import pandas as pd
import os
from datetime import datetime

class Satellite:
    def __init__(self, name, servers=1, mu_inter=0.03, mu_intra=0.001, num_beams=0, tle_data=None):
        self.name = name
        self.tle_data = tle_data
        self.num_beams = num_beams
        
        # Inizializza un array per tracciare il numero di UE connessi a ciascun beam
        self.connected_ues = [0] * num_beams 
        
        # Inizializza l'Handover Manager del satellite
        self.handover_manager = self.HandoverManager(
            self, servers=servers, mu_inter=mu_inter, mu_intra=mu_intra
        )

    class HandoverManager:
        """
        Motore Data Plane del Satellite.
        In un'architettura SDN, la congestione è risolta a monte dal Temporal Trigger 
        Spreading (TTS). Il server del satellite esegue deterministicamente il ritardo 
        di propagazione puro, fungendo da nodo passivo.
        """
        def __init__(self, satellite, servers, mu_inter, mu_intra):
            self.satellite = satellite
            self.servers = servers
            self.mu_inter = mu_inter
            self.mu_intra = mu_intra
            # Nessuna coda stocastica. L'esecuzione è governata centralmente dall'SDN.
            self.handover_tracker = []

        def process_handover_intra(self, arrival_time, ue, curr_beam_index, dest_satellite, dest_beam_index):
            """
            Processa l'intra-handover logico. Durata puramente fisica, nessun accodamento.
            """
            event_type = "intra_ho"
            duration = self.mu_intra 
            
            # Esecuzione istantanea calcolando il tempo finale
            end_time_dt = arrival_time + pd.Timedelta(seconds=duration)

            handover_info = {
                "arrival_time": arrival_time,
                "event_type": event_type,
                "ue_id": ue.id,
                "from_satellite": self.satellite.name,
                "from_beam_index": curr_beam_index,
                "dest_satellite": dest_satellite.name,
                "dest_beam_index": dest_beam_index,
                "start_time": arrival_time,
                "departure_time": end_time_dt,
                "duration": duration,
                "dest_number_ues": dest_satellite.connected_ues.copy()
            }
                
            return handover_info

        def process_handover_inter(self, arrival_time, ue, curr_beam_index, dest_satellite, dest_beam_index):
            """
            Processa l'inter-handover fisico. Durata puramente fisica, nessun accodamento.
            """
            event_type = "inter_ho"
            duration = self.mu_inter 
            
            # Esecuzione istantanea calcolando il tempo finale
            end_time_dt = arrival_time + pd.Timedelta(seconds=duration)

            handover_info = {
                "arrival_time": arrival_time,
                "event_type": event_type,
                "ue_id": ue.id,
                "from_satellite": self.satellite.name,
                "from_beam_index": curr_beam_index,
                "dest_satellite": dest_satellite.name,
                "dest_beam_index": dest_beam_index,
                "start_time": arrival_time,
                "departure_time": end_time_dt,
                "duration": duration,
                "dest_number_ues": dest_satellite.connected_ues.copy()
            }

            return handover_info

        def deactivate(self):
            """
            Esporta il log di tutte le transizioni fisiche elaborate da questo nodo in un file CSV.
            """
            if self.handover_tracker:
                df = pd.DataFrame(self.handover_tracker)
                output_folder = "Satellite dataframes_preho"
                os.makedirs(output_folder, exist_ok=True)
                
                filename = f"{self.satellite.name}_handover_events.csv"
                full_path = os.path.join(output_folder, filename)
                df.to_csv(full_path, index=False)


    def connect_ue(self, beam_index):
        """ Gestisce la connessione di un singolo UE incrementando il contatore del beam. """
        self.connected_ues[beam_index] += 1
        return self.connected_ues[beam_index]
    
    def disconnect_ue(self, beam_index):
        """ Gestisce la disconnessione di un singolo UE decrementando il contatore del beam. """
        if self.connected_ues[beam_index] > 0:
            self.connected_ues[beam_index] -= 1
        return self.connected_ues

    def deactivate(self):
        """
        Disattiva il satellite. Termina il ciclo vitale del nodo chiamando 
        il metodo deactivate dell'Handover Manager per salvare i dati.
        """
        if self.handover_manager:
            self.handover_manager.deactivate()
            self.handover_manager = None

    def get_position(self, time):
        """
        Propaga le TLE del satellite usando Skyfield per ottenere la posizione geocentrica 
        a un dato istante temporale.
        """
        ts = load.timescale()
        t = ts.utc(time.year, time.month, time.day, time.hour, time.minute, time.second)

        # Crea l'oggetto EarthSatellite e calcola la posizione
        satellite_obj = EarthSatellite(self.tle_data[1], self.tle_data[2])
        geocentric = satellite_obj.at(t) 
        subpoint = geocentric.subpoint()

        latitude = subpoint.latitude.degrees
        longitude = subpoint.longitude.degrees
        height = subpoint.elevation.m

        return latitude, longitude, height