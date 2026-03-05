from pyclbr import Class
import heapq
import random
import pandas as pd
import os

class Satellite:
    def __init__(self, name, servers, mu):
        self.name = name
        self.handover_manager = self.HandoverManager(self, servers = servers, mu = mu)
        self.connected_ues = 0 # I create a satellite only when a Ue wants to connect to him


    class HandoverManager:
        # typical values for number of servers n and mean service time 1/mu could be the following:
        # n = 8-16-32, mu = 1/30ms. These values can be adjusted to simulate different scenarios and 
        # evaluate the associated performance impact. 
        # note that the UE shall not be unable to communicate for the whole duration of the handover,
        # only for the time it takes for the disconnection from the serving satellite and RACH to the target.
        def __init__(self, satellite, servers, mu):
            # print(f"\n=== initializing hom for {satellite.name} ===")
            self.satellite = satellite
            self.servers = servers
            self.mu = mu
            self.events_queue = [0.0] * servers
            heapq.heapify(self.events_queue)
            self.handover_tracker = []

        def process_handover(self, arrival_time, ue, dest_satellite):
            """
            Handles the handover process for a UE moving from current satellite to destination as */M/k queue.
                Args:
                    arrival_time (float): The time at which the handover request arrives.
                    ue (Ue): The UE object that is being handed over.
                    dest_satellite (Satellite): The destination satellite to which the UE is being handed over.
                Returns:
                    handover_info (dict): a dictionary containing the following information:
                        - arrival_time: The time at which the handover request arrives.
                        - event_type: The type of event (e.g., "out_ho" for handover out).
                        - ue_id: The ID of the UE being handed over.
                        - from_satellite: The name of the current satellite.
                        - dest_satellite: The name of the destination satellite.
                        - start_time: The time at which the handover process starts.
                        - departure_time: The time at which the handover process ends.
                        - duration: The duration of the handover process.
            """

            # print(f"{arrival_time}:processing handover for ue {ue.id}")
            duration = random.expovariate(self.mu)
            # print(f"\thandover duration: {duration}")
            earliest_time = heapq.heappop(self.events_queue)
            # print(f"\tearliest time: {earliest_time}")

            # TODO: we need a time instant with respect to the actual time start of this slot, and not respect to the entire simulation time
            arrival_time_rel = arrival_time.timestamp()

            start_time = max(arrival_time_rel, earliest_time)
            end_time = start_time + duration
            heapq.heappush(self.events_queue, end_time)
            handover_info = {
                "arrival_time": arrival_time,
                "event_type": "in_ho",
                "ue_id": ue.id,
                "from_satellite": self.satellite.name,
                "dest_satellite": dest_satellite.name,
                "start_time": start_time,
                "departure_time": end_time,
                "duration": duration,
                "dest_number_ues": dest_satellite.connected_ues
            }
            dest_satellite.handover_manager.handover_tracker.append(handover_info)
            out_ho_info = handover_info.copy()
            out_ho_info["event_type"] = "out_ho"
            self.handover_tracker.append(out_ho_info)
            return out_ho_info


        def deactivate(self):
            df = pd.DataFrame(self.handover_tracker)
            # print(f"\n=== saving output file for {self.satellite.name} ===")
            filename = f"{self.satellite.name}_handover_events.csv"

            output_folder = "Satellite dataframes"
            full_path = os.path.join(output_folder, filename)
            os.makedirs(output_folder, exist_ok=True)

            df.to_csv(full_path, index=False)


    def connect_ue(self):
        """
        Handles the connection of a single UE.
        """
        self.connected_ues += 1
        return self.connected_ues
    
    def disconnect_ue(self):
        """
        Handles the disconnection of a single UE.
        """
        if self.connected_ues > 0:
            self.connected_ues -= 1
        return self.connected_ues

    def deactivate(self):
        """
        Deactivate the satellite. This should be called once the satellite is no longer needed.
        It will call the respective deactivate method of the handover_manager class to save the output dataframe to a csv file.
        """
        self.handover_manager.deactivate()
        self.handover_manager = None
