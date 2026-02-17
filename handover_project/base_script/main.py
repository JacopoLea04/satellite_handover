from datetime import datetime
import numpy as np
import math

from datetime import datetime, deltatime

from scipy import cluster
from satellite import Satellite
from cluster import Cluster
from ue import Ue

# initial configuration
cluster = Cluster("Cluster1", (45.4384, 11.0086, 0), 10, [], -10)
time = datetime(2025, 6, 8, 0, 0, 0) # year, month, day, hour, minute, second
end_sim_time = datetime(2025, 6, 8, 1, 0, 0)

# Initial connection phase and time translation 
delay = cluster.initial_connection_phase(time)
time += delay

while time < end_sim_time:
    # Monitor the SNR of the current connections and apply conditional handover if needed
    delay = cluster.monitor(time)
    time += delay
