import math
import itur

class Channel:
    BOLTZ_CONST = -228.6  # Boltzmann constant [dB]
    c = 3e8  # Speed of light in meters per second
    #BANDWIDTH = 10*(10**6) # Bandwith [Hz]
    FSPL_CONSTANT = 92.45

    ATTENUATION_PERCENTAGE = 0.1  # Atmospheric attenuation percentage (0.1 for clear sky, can be adjusted based on conditions)
    GAS = True
    RAIN = False
    SCINTILLATION = True
    CLOUDS = False
    TX_SIZE_device = 1
    TX_SIZE_satellite = 1

    def __init__(self, device_lat, device_lon, satellite_lat, satellite_lon, distance, elevation_angle, eirp_gt, eirp_satellite, gain_to_noise_gt, gain_to_noise_satellite, frequency_dl, frequency_ul, bandwidth_dl, bandwidth_ul):
        self.device_lat, self.device_lon = device_lat, device_lon
        self.satellite_lat, self.satellite_lon = satellite_lat, satellite_lon
        self.distance = distance/1000
        self.elevation_angle = elevation_angle
        self.eirp_gt = eirp_gt
        self.eirp_satellite = eirp_satellite
        self.gain_to_noise_gt = gain_to_noise_gt
        self.gain_to_noise_satellite = gain_to_noise_satellite
        self.frequency_dl = frequency_dl
        self.frequency_ul = frequency_ul
        self.bandwidth_dl = bandwidth_dl
        self.bandwidth_ul = bandwidth_ul

    def get_path_loss(self, dlUl, sc6, sc9):
        fspl = 0
        atm_loss = 0
        
        if dlUl == "DL":
            fspl = self.FSPL_CONSTANT + 20 * math.log10(self.distance) + 20 * math.log10(self.frequency_dl)
            #atm_loss = itur.atmospheric_attenuation_slant_path(
                #self.device_lat, self.device_lon, self.frequency_dl, self.elevation_angle,
                #self.ATTENUATION_PERCENTAGE, self.TX_SIZE_device, return_contributions=True, include_gas=True,
                #include_rain=True, include_scintillation=True, include_clouds=True)[0].value
        elif dlUl == "UL":
            fspl = self.FSPL_CONSTANT + 20 * math.log10(self.distance) + 20 * math.log10(self.frequency_ul)
            #atm_loss = itur.atmospheric_attenuation_slant_path(
                #self.device_lat, self.device_lon, self.frequency_ul, self.elevation_angle,
                #self.ATTENUATION_PERCENTAGE, self.TX_SIZE_device, return_contributions=True, include_gas=True,
                #include_rain=True, include_scintillation=True, include_clouds=True)[0].value
        else:
            raise ValueError("dlUl must either be 'DL' or 'UL'")
    
        if sc6:
            atm_loss = 0.5 + 0.3
        if sc9:
            atm_loss = 0.1 + 3.0 + 2.2

        path_loss = fspl + atm_loss
        return path_loss

    def get_snr_dl(self, sc6, sc9):
        snr = self.eirp_satellite + self.gain_to_noise_gt - self.get_path_loss("DL", sc6, sc9) - self.BOLTZ_CONST - 10 * math.log10(self.bandwidth_dl)
        snr = round(snr, 4)
  
        return snr

    def get_snr_ul(self, sc6, sc9):
        snr = self.eirp_gt + self.gain_to_noise_satellite - self.get_path_loss("UL", sc6, sc9) - self.BOLTZ_CONST - 10 * math.log10(self.bandwidth_ul)
        snr = round(snr, 4)

        return snr
    
    def compute_dl_rate(self, sc6, sc9):
        dl_SNR = self.get_snr_dl(sc6, sc9)  # Calculate your downlink SNR
        dl_rate = self.bandwidth_dl * math.log2(1 + 10 ** (dl_SNR / 10))

        return dl_rate

    def compute_ul_rate(self, sc6, sc9):
        ul_SNR = self.get_snr_ul(sc6, sc9)  # Calculate your uplink SNR
        ul_rate = self.bandwidth_ul * math.log2(1 + 10 ** (ul_SNR / 10))

        return ul_rate
