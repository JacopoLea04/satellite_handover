import random
import heapq
from satellite import Satellite
import pandas as pd
from ue import Ue

class Handover_manager:
    def __init__(self, satellite, servers, mu):
        print(f"\n=== initializing hom for {satellite.name} ===")
        self.satellite = satellite
        self.servers = servers
        self.mu = mu
        self.events_queue = [0.0] * servers
        heapq.heapify(self.events_queue)
        self.handover_tracker = []

    def process_handover(self, arrival_time, ue, dest_satellite):
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

