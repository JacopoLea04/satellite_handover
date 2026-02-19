from handover_manager import HandoverManager

class Satellite:
    def __init__(self, name, tle_data, servers, mu):
        self.name = name
        self.handover_manager = HandoverManager(self, servers = servers, mu = mu)

    def deactivate(self):
        self.handover_manager.deactivate()