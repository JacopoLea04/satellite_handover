from skyfield.api import load, EarthSatellite

class Satellite:
    def __init__(self, name, tle_data):
        self.name = name
        self.tle_data = tle_data
        self.load = 0  # Initialize load to 0

    def get_position(self, time):
        ts = load.timescale()
        t = ts.utc(time.year, time.month, time.day, time.hour, time.minute, time.second)

        satellite = EarthSatellite(self.tle_data[1], self.tle_data[2])  # Create EarthSatellite object
        geocentric = satellite.at(t)  # Use the created EarthSatellite object here
        subpoint = geocentric.subpoint()

        latitude = subpoint.latitude.degrees
        longitude = subpoint.longitude.degrees
        height = subpoint.elevation.m

        return latitude, longitude, height
    
    def update_load(self):
        self.load += 1

    def get_rate(self, frame, time):
        # TODO
        # Example: equally divide the total available rate among all connected UEs
        return self.get_max_rate(frame, time) / self.load if self.load > 0 else 0