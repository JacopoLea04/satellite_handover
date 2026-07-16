import pandas as pd
import os

class Ue:
    def __init__(self, ue_id, position):
        self.id = ue_id
        self.lat = position[0]
        self.lon = position[1]
        self.alt = position[2]
        
        # Stato Connessione (Data Plane)
        self.connected_to = None
        self.connected_to_beam = None
        
        # Variabili SDN (Control Plane - Architettura Passiva)
        # Struttura attesa: {'time': datetime, 'sat': sat_obj, 'beam': index}
        self.scheduled_handover = None 
        
        # Filtri IIR (Exponential Moving Average) per mitigazione rumore canale
        self.ema_snr_dl = None
        self.ema_snr_ul = None
        self.ema_elevation = None
        self.EMA_ALPHA = 0.3 # Fattore di reattività del filtro EMA

        # Tracker Statistico
        self.handover_tracker = []
        self.thr_tracker = []
        self.remaining_handover_execution_time = 0 # [ms] Latenza causata dall'ultimo HO

    def update_ema_filters(self, raw_snr_dl, raw_snr_ul, raw_elev):
        """
        Aggiorna i filtri EMA per livellare il rumore gaussiano delle letture PHY.
        Garantisce la stabilità metrica richiesta dall'algoritmo MADM-PREHO SDN.
        """
        if self.ema_snr_dl is None:
            self.ema_snr_dl = raw_snr_dl
            self.ema_snr_ul = raw_snr_ul
            self.ema_elevation = raw_elev
        else:
            self.ema_snr_dl = (self.EMA_ALPHA * raw_snr_dl) + ((1 - self.EMA_ALPHA) * self.ema_snr_dl)
            self.ema_snr_ul = (self.EMA_ALPHA * raw_snr_ul) + ((1 - self.EMA_ALPHA) * self.ema_snr_ul)
            self.ema_elevation = (self.EMA_ALPHA * raw_elev) + ((1 - self.EMA_ALPHA) * self.ema_elevation)
        
        return self.ema_snr_dl, self.ema_snr_ul, self.ema_elevation

    def execute_scheduled_handover(self, current_time):
        """
        Motore attuatore passivo: l'UE subisce le decisioni di routing centralizzato.
        Verifica se il trigger temporale dettato dal TTS Stocastico è scattato.
        """
        if self.scheduled_handover is not None:
            exec_time = self.scheduled_handover['time']
            
            # Trigger temporale (eliminato il casting str() per O(1) performance)
            if current_time >= exec_time:
                dest_sat = self.scheduled_handover['sat']
                dest_beam = self.scheduled_handover['beam']
                
                curr_sat, curr_beam_index = self.get_connection_info()
                
                if curr_sat is not None and dest_sat is not None and curr_sat.name == dest_sat.name:
                    self.intra_handover(current_time, curr_sat, dest_beam)
                else:
                    self.inter_handover(current_time, dest_sat, dest_beam)
                
                self.scheduled_handover = None
                return True 
                
        return False

    def get_connection_info(self):
        """ Ritorna i puntatori al nodo di routing attuale. """
        return self.connected_to, self.connected_to_beam

    def connect_to_satellite(self, satellite, beam_index):
        """ Attuatore fisico: stabilisce il link con il nuovo nodo. """
        self.connected_to = satellite
        self.connected_to_beam = beam_index

    def disconnect(self):
        """ Sgancia l'UE dal nodo corrente (Link Failure). """
        self.connected_to = None
        self.connected_to_beam = None

    def deactivate(self, cluster_name, label):
        """
        Terminazione ciclo vitale: esporta i log (Digital Twin Telemetry).
        """
        # Esporta Handover Tracker
        if self.handover_tracker:
            df_ho = pd.DataFrame(self.handover_tracker)
            output_folder_ho = f"{cluster_name} dataframes_{label}"
            os.makedirs(output_folder_ho, exist_ok=True)
            df_ho.to_csv(os.path.join(output_folder_ho, f"{self.id}_handover_events.csv"), index=False)

        # Esporta Throughput Tracker
        if self.thr_tracker:
            df_thr = pd.DataFrame(self.thr_tracker)
            output_folder_thr = f"{cluster_name} throughput_{label}"
            os.makedirs(output_folder_thr, exist_ok=True)
            df_thr.to_csv(os.path.join(output_folder_thr, f"{self.id}_thr_over_time.csv"), index=False)

    def inter_handover(self, time, dest_sat, dest_beam_index):
        """
        Gestisce la transizione fisica verso un satellite differente (Inter-HO).
        Invoca il manager MAC ALOHA dei satelliti coinvolti e aggiorna la topologia.
        """
        curr_sat, curr_beam_index = self.get_connection_info()

        # Case 1 & 2: Perdita di copertura totale
        if dest_sat is None:
            event_type = "lost_conn" if curr_sat is not None else "out_serv"
            curr_sat_name = curr_sat.name if curr_sat is not None else None

            handover_info = {
                    "arrival_time": time, "event_type": event_type, "ue_id": self.id,
                    "from_satellite": curr_sat_name, "from_beam_index": curr_beam_index,
                    "dest_satellite": None, "dest_beam_index": None,
                    "start_time": time, "departure_time": 0, "duration": 1, "dest_number_ues": None
                }

            if curr_sat is not None:
                curr_sat.disconnect_ue(curr_beam_index)
                curr_sat.handover_manager.handover_tracker.append(handover_info)

            self.disconnect()
            self.remaining_handover_execution_time = handover_info["duration"]
            self.handover_tracker.append(handover_info)
            return 
        
        # Case 3: Riconnessione da stato offline
        if curr_sat is None: 
            handover_info = {
                    "arrival_time": time, "event_type": "rest_conn", "ue_id": self.id,
                    "from_satellite": None, "from_beam_index": None,
                    "dest_satellite": dest_sat.name, "dest_beam_index": dest_beam_index,
                    "start_time": time, "departure_time": 0, "duration": 1,
                    "dest_number_ues": dest_sat.connected_ues.copy()
                }
            dest_sat.handover_manager.handover_tracker.append(handover_info)
            dest_sat.connect_ue(dest_beam_index)

            self.remaining_handover_execution_time = handover_info["duration"] * 1000
            self.handover_tracker.append(handover_info)
            self.connect_to_satellite(dest_sat, dest_beam_index)

        # Case 4: Transizione normale da Sat_A a Sat_B
        else: 
            handover_info = curr_sat.handover_manager.process_handover_inter(time, self, curr_beam_index, dest_sat, dest_beam_index)

            dest_sat.handover_manager.handover_tracker.append(handover_info)
            dest_sat.connect_ue(dest_beam_index)
            curr_sat.handover_manager.handover_tracker.append(handover_info)
            curr_sat.disconnect_ue(curr_beam_index)

            self.remaining_handover_execution_time = handover_info["duration"] * 1000
            self.handover_tracker.append(handover_info)
            self.connect_to_satellite(dest_sat, dest_beam_index)

    def intra_handover(self, time, dest_sat, dest_beam_index):
        """
        Gestisce la transizione logica tra due fasci dello stesso satellite (Intra-HO).
        Latenza strutturalmente ridotta rispetto all'Inter-HO.
        """
        curr_sat, curr_beam_index = self.get_connection_info()
        handover_info = curr_sat.handover_manager.process_handover_intra(time, self, curr_beam_index, dest_sat, dest_beam_index)
        
        curr_sat.handover_manager.handover_tracker.append(handover_info)
        curr_sat.disconnect_ue(curr_beam_index)
        dest_sat.connect_ue(dest_beam_index)

        self.connect_to_satellite(dest_sat, dest_beam_index) 
        self.remaining_handover_execution_time = handover_info["duration"] * 1000
        self.handover_tracker.append(handover_info)
