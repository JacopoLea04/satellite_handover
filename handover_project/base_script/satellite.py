from pyclbr import Class
import heapq
import random
import pandas as pd

class Satellite:
    def __init__(self, name, servers, mu):
        self.name = name
        self.handover_manager = self.HandoverManager(self, servers = servers, mu = mu)
        self.connected_ues = 0


    class HandoverManager:
        # typical values for number of servers n and mean service time 1/mu could be the following:
        # n = 8-16-32, mu = 1/30ms. These values can be adjusted to simulate different scenarios and 
        # evaluate the associated performance impact. 
        # note that the UE shall not be unable to communicate for the whole duration of the handover,
        # only for the time it takes for the disconnection from the serving satellite and RACH to the target.
        def __init__(self, satellite, servers, mu):
            print(f"\n=== initializing hom for {satellite.name} ===")
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

            print(f"{arrival_time}:processing handover for ue {ue.id}")
            duration = random.expovariate(self.mu)
            print(f"\thandover duration: {duration}")
            earliest_time = heapq.heappop(self.events_queue)
            print(f"\tearliest time: {earliest_time}")
            start_time = max(arrival_time, earliest_time)
            end_time = start_time + duration
            heapq.heappush(self.events_queue, end_time)
            handover_info = {
                "arrival_time": arrival_time,
                "event_type": "out_ho",
                "ue_id": ue.id,
                "from_satellite": self.satellite.name,
                "dest_satellite": dest_satellite.name,
                "start_time": start_time,
                "departure_time": end_time,
                "duration": duration
            }
            self.handover_tracker.append(handover_info)
            return handover_info


        def deactivate(self):
            df = pd.DataFrame(self.handover_tracker)
            print(f"\n=== saving output file for {self.satellite.name} ===")
            filename = f"{self.satellite.name}_handover_events"
            df.to_csv(f'{filename}.csv', index=False)


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

    def connect_to_ue(self, ue):
        self.connected_to.append(ue)
        # TODO print a line in the df

    def disconnetct_to_ue(self, ue):
        # remove the UE from the list of connected UEs
        self.connected_to = [sat for sat in self.connected_to if sat.name != ue.id]
        # TODO print a line in the df
    
    def get_connected_to(self):
        return self.connected_to