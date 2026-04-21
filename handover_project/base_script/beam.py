from ue import Ue
from satellite import Satellite
from datetime import timedelta
import numpy as np

class Beam:
    def __init__(self, name, position, num_ues):
        self.name = name
        self.num_ues = num_ues
        self.position = position
        self.list_ues = [Ue(self.name + "-Ue" + str(ii+1), position) for ii in range(num_ues)]

