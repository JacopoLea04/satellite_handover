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
        self.remaining_handover_execution_time = 0 # [ms] save the ho duration at this time instant if the ue has performed ho
        self.thr_tracker = []

        # =======================================================
        # NUOVE VARIABILI SDN (Architettura Passiva / eDRX)
        # =======================================================
        # Schedule dell'Handover dettato dal Controller Centrale
        # Struttura attesa: {'time': datetime, 'sat': sat_obj, 'beam': index}
        self.scheduled_handover = None 

        # Stati del Filtro EMA (Exponential Moving Average) per pulire il rumore
        self.ema_snr_dl = None
        self.ema_snr_ul = None
        self.ema_elevation = None
        self.EMA_ALPHA = 0.3 # Fattore di smorzamento (0 = ignora rumore, 1 = reattivo 100%)


    def update_ema_filters(self, raw_snr_dl, raw_snr_ul, raw_elev):
        """
        Aggiorna la Media Mobile Esponenziale.
        Viene chiamata dal simulatore a ogni istante t per pulire il rumore gaussiano.
        """
        if self.ema_snr_dl is None:
            # Inizializzazione al primo segnale ricevuto
            self.ema_snr_dl = raw_snr_dl
            self.ema_snr_ul = raw_snr_ul
            self.ema_elevation = raw_elev
        else:
            # Applica la formula EMA
            self.ema_snr_dl = (self.EMA_ALPHA * raw_snr_dl) + ((1 - self.EMA_ALPHA) * self.ema_snr_dl)
            self.ema_snr_ul = (self.EMA_ALPHA * raw_snr_ul) + ((1 - self.EMA_ALPHA) * self.ema_snr_ul)
            self.ema_elevation = (self.EMA_ALPHA * raw_elev) + ((1 - self.EMA_ALPHA) * self.ema_elevation)
        
        return self.ema_snr_dl, self.ema_snr_ul, self.ema_elevation


    def execute_scheduled_handover(self, current_time):
        """
        Motore di esecuzione passivo.
        Se l'SDN Controller ha programmato un handover per l'istante attuale, l'UE lo esegue.
        """
        if self.scheduled_handover is not None:
            exec_time = self.scheduled_handover['time']
            
            # Controlla se è arrivato il momento esatto (TTS - Temporal Trigger)
            if str(current_time) == str(exec_time) or current_time >= exec_time:
                dest_sat = self.scheduled_handover['sat']
                dest_beam = self.scheduled_handover['beam']
                
                curr_sat, curr_beam_index = self.get_connection_info()
                
                # Esecuzione Fisica
                if curr_sat is not None and dest_sat is not None and curr_sat.name == dest_sat.name:
                    self.intra_handover(current_time, curr_sat, dest_beam)
                else:
                    self.inter_handover(current_time, dest_sat, dest_beam)
                
                # Ordine completato, svuota la coda
                self.scheduled_handover = None
                return True 
                
        return False


    def connect_to_satellite(self, satellite, beam_index):
        """
        Connect the UE to a satellite and a specific beam index.
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

        output_folder = cluster_name + " dataframes_preho"
        full_path = os.path.join(output_folder, filename)
        os.makedirs(output_folder, exist_ok=True)

        df.to_csv(full_path, index=False)

        # throughput df
        df = pd.DataFrame(self.thr_tracker)
        filename = f"{self.id}_thr_over_time.csv"

        output_folder = cluster_name + " throughput_preho"
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
        Handle the handover process for the UE...
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
        Handle the intra-handover process for the UE...
        """
        curr_sat, curr_beam_index = self.get_connection_info()
        handover_info = curr_sat.handover_manager.process_handover_intra(time, self, curr_beam_index, dest_sat, dest_beam_index)
        
        curr_sat.handover_manager.handover_tracker.append(handover_info)
        curr_sat.disconnect_ue(curr_beam_index)
        dest_sat.connect_ue(dest_beam_index)

        # update the ue infos
        self.connect_to_satellite(dest_sat , dest_beam_index) 
        self.remaining_handover_execution_time = handover_info["duration"] * 1000
        self.handover_tracker.append(handover_info)

        return 
    
    def disconnect(self):
        """
        Disconnect the UE from its current satellite.
        """
        self.connected_to = None
        self.connected_to_beam = None
