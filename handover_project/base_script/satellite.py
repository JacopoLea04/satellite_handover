from pyclbr import Class
from skyfield.api import load, EarthSatellite
import heapq
import random
import pandas as pd
import os

class Satellite:
    def __init__(self, name, servers = 1, mu_inter = 0.03, mu_intra = 0.001, num_beams = 0, tle_data = None):
        self.name = name
        self.tle_data = tle_data
        self.handover_manager = self.HandoverManager(self, servers = servers, mu_inter = mu_inter , mu_intra = mu_intra)
        self.num_beams = num_beams
        self.connected_ues = [0] * num_beams # I create a satellite only when a Ue wants to connect to him


    class HandoverManager:
        # typical values for number of servers n and mean service time 1/mu could be the following:
        # n = 8-16-32, mu = 1/30ms. These values can be adjusted to simulate different scenarios and 
        # evaluate the associated performance impact. 
        # note that the UE shall not be unable to communicate for the whole duration of the handover,
        # only for the time it takes for the disconnection from the serving satellite and RACH to the target.
        def __init__(self, satellite, servers, mu_inter, mu_intra):
            # print(f"\n=== initializing hom for {satellite.name} ===")
            self.satellite = satellite
            self.servers = servers
            self.mu_inter = mu_inter
            self.mu_intra = mu_intra
            self.events_queue_inter = [0.0] * servers
            self.events_queue_intra = [0.0] * servers
            heapq.heapify(self.events_queue_inter)
            heapq.heapify(self.events_queue_intra)
            self.handover_tracker = []

        def process_handover(self, arrival_time, ue, curr_beam_index, dest_satellite, dest_beam_index):
            """
            Handles the handover process for a UE moving from current satellite to destination as */M/k queue.
                Args:
                    arrival_time (float): The time at which the handover request arrives.
                    ue (Ue): The UE object that is being handed over.
                    curr_beam_index (int): The index of the beam to which the UE is currently connected.
                    dest_satellite (Satellite): The destination satellite to which the UE is being handed over.
                    dest_beam_index (int): The index of the beam to which the UE will be connected in the destination satellite.
                Returns:
                    handover_info (dict): a dictionary containing the following information:
                        - arrival_time: The time at which the handover request arrives.
                        - event_type: The type of event (e.g., "out_ho" for handover out).
                        - ue_id: The ID of the UE being handed over.
                        - from_satellite: The name of the current satellite.
                        - from_beam_index: The index of the beam to which the UE is currently connected.
                        - dest_satellite: The name of the destination satellite.
                        - dest_beam_index: The index of the beam to which the UE will be connected in the destination satellite.
                        - start_time: The time at which the handover process starts.
                        - departure_time: The time at which the handover process ends.
                        - duration: The duration of the handover process.
            """
            # intra satellite handover 
            if(dest_satellite.name == self.satellite.name):
                event_type = "intra_ho"
                # duration = random.expovariate(self.mu_intra)
                duration = self.mu_intra # for testing purposes, we set a fixed duration of 30ms for the handover process
                earliest_time = heapq.heappop(self.events_queue_intra)
                arrival_time_rel = arrival_time.timestamp()
                start_time = max(arrival_time_rel, earliest_time)
                end_time = start_time + duration
                heapq.heappush(self.events_queue_intra, end_time)

                handover_info = {
                "arrival_time": arrival_time,
                "event_type": event_type,
                "ue_id": ue.id,
                "from_satellite": self.satellite.name,
                "from_beam_index": curr_beam_index,
                "dest_satellite": dest_satellite.name,
                "dest_beam_index": dest_beam_index,
                "start_time": start_time,
                "departure_time": end_time,
                "duration": duration,
                "dest_number_ues": dest_satellite.connected_ues
                }
                self.handover_tracker.append(handover_info)
            # inter satellite handover 
            else:
                event_type = "inter_ho"
                # duration = random.expovariate(self.mu_inter)
                duration = self.mu_inter # for testing purposes, we set a fixed duration of 30ms for the handover process
                earliest_time = heapq.heappop(self.events_queue_inter)
                arrival_time_rel = arrival_time.timestamp()
                start_time = max(arrival_time_rel, earliest_time)
                end_time = start_time + duration
                heapq.heappush(self.events_queue_inter, end_time)

                handover_info = {
                "arrival_time": arrival_time,
                "event_type": event_type,
                "ue_id": ue.id,
                "from_satellite": self.satellite.name,
                "from_beam_index": curr_beam_index,
                "dest_satellite": dest_satellite.name,
                "dest_beam_index": dest_beam_index,
                "start_time": start_time,
                "departure_time": end_time,
                "duration": duration,
                "dest_number_ues": dest_satellite.connected_ues
                }
                self.handover_tracker.append(handover_info)
                dest_satellite.handover_manager.handover_tracker.append(handover_info)
                dest_satellite.connect_ue(dest_beam_index)

            return handover_info


        def deactivate(self):
            """
            This function should be called once the satellite is no longer needed. It will save the output dataframe to a csv file.
            """
            df = pd.DataFrame(self.handover_tracker)
            # print(f"\n=== saving output file for {self.satellite.name} ===")
            filename = f"{self.satellite.name}_handover_events.csv"

            output_folder = "Satellite dataframes"
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











# ========================= TO FIX =========================
    
    
    def get_position(self, time):
        """
        TODO: update this function to get the position of the satellite at the given time.

        This function returns the current position of the satellite in ECI coordinates.
        """
        ts = load.timescale()
        t = ts.utc(time.year, time.month, time.day, time.hour, time.minute, time.second)

        satellite = EarthSatellite(self.tle_data[1], self.tle_data[2])  # Create EarthSatellite object
        geocentric = satellite.at(t)  # Use the created EarthSatellite object here
        subpoint = geocentric.subpoint()

        latitude = subpoint.latitude.degrees
        longitude = subpoint.longitude.degrees
        height = subpoint.elevation.m

        return latitude, longitude, height
    

    def get_rate(self, frame, time):
        """
        TODO: update this function to get the rate of the satellite at the given time.

        This function returns the current rate of the satellite in Mbps.
        """
        return self.get_max_rate(frame, time) / self.load if self.load > 0 else 0