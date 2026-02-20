from handover_manager import HandoverManager

class Satellite:
    def __init__(self, name, tle_data, servers, mu):
        self.name = name
        self.handover_manager = HandoverManager(self, servers = servers, mu = mu)
        self.connected_to = []

    def deactivate(self):
        self.handover_manager.deactivate()

    def connect_to_ue(self, ue):
        self.connected_to.append(ue)
        # TODO print a line in the df

    def disconnetct_to_ue(self, ue):
        # remove the UE from the list of connected UEs
        self.connected_to = [sat for sat in self.connected_to if sat.name != ue.id]
        # TODO print a line in the df
    
    def get_connected_to(self):
        return self.connected_to