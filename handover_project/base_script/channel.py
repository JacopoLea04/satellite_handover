import math
import itur

"""
Link Budget Parameters for Ka-band (DL: 400 MHz, UL: 400 MHz)

Baseline Calibration Assumption:
- At least X = 10 UEs per beam, uniformly distributed across each beam's cell area.
- Each beam's coverage area is defined by its corresponding cell.
- Bandwidth per beam may vary based on frequency reuse factor and polarization reuse configuration.

Satellite Altitudes:
- SC6 & SC7  → 600 km LEO
- SC11 & SC12 → 1200 km LEO

Table 6.1.3.3-1 — Link Budget Results

-------------------------------------------------------------------------------------------------------------------
| Case | Orbit Alt. | Rx Mode | Freq [GHz] | EIRP [dBW] | G/T [dB/K] | BW [MHz] | Beam footprint | Cell diameter |
|      | [km]       |         |            |            |            |          | [km]           | [km]          |
-------------------------------------------------------------------------------------------------------------------
| ST_  | 500        | UL      | 30.0       | 45.01      | 5.0        | 400.0    | 150.0          | 750.0         |
|      |            | DL      | 20.0       | 36.02      | 21.44      | 400.0    | 150.0          | 750.0         |
-------------------------------------------------------------------------------------------------------------------
| SC6  | 600        | UL      | 30.0       | 45.01      | 5.0        | 400.0    | 200.0          | 1000.0        |
|      |            | DL      | 20.0       | 36.02      | 21.44      | 400.0    | 200.0          | 1000.0        |
-------------------------------------------------------------------------------------------------------------------
| SC11 | 1200       | UL      | 30.0       | 45.01      | 5.0        | 400.0    | 450.0          | 2250.0        |
|      |            | DL      | 20.0       | 36.02      | 21.44      | 400.0    | 450.0          | 2250.0        |
-------------------------------------------------------------------------------------------------------------------
| SC_  | 8000       | UL      | 30.0       | 50.01      | 10.0       | 400.0    | 3000.0         | 15000.0       |
|      |            | DL      | 20.0       | 36.02      | 21.44      | 400.0    | 3000.0         | 15000.0       |
-------------------------------------------------------------------------------------------------------------------


Parameter Key:
- FSPL: Free Space Path Loss
- G/T: Receiver Antenna Gain over System Noise Temperature
- CNR: Carrier-to-Noise Ratio
- Shadow Fading, Scintillation, Polarization and Additional Losses are included as fixed margins (dB)
"""


class Channel:
    BOLTZ_CONST = -228.6  # Boltzmann constant [dB]
    c = 3e8  # Speed of light in meters per second
    #BANDWIDTH = 10*(10**6) # Bandwith [Hz]
    FSPL_CONSTANT = 92.45

    ATTENUATION_PERCENTAGE = 0
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
    
    def get_path_loss(self, dlUl):
        fspl = 0
        if dlUl == "DL":
            fspl = self.FSPL_CONSTANT + 20 * math.log10(self.distance) + 20 * math.log10(self.frequency_dl)
            atm_loss = itur.atmospheric_attenuation_slant_path(
                self.device_lat, self.device_lon, self.frequency_dl, self.elevation_angle,
                self.ATTENUATION_PERCENTAGE, self.TX_SIZE_device, return_contributions=True, include_gas=True,
                include_rain=True, include_scintillation=True, include_clouds=True)[0].value
        elif dlUl == "UL":
            fspl = self.FSPL_CONSTANT + 20 * math.log10(self.distance) + 20 * math.log10(self.frequency_ul)
            atm_loss = itur.atmospheric_attenuation_slant_path(
                self.device_lat, self.device_lon, self.frequency_ul, self.elevation_angle,
                self.ATTENUATION_PERCENTAGE, self.TX_SIZE_device, return_contributions=True, include_gas=True,
                include_rain=True, include_scintillation=True, include_clouds=True)[0].value
        else:
            raise ValueError("dlUl must either be 'DL' or 'UL'")

        path_loss = fspl + atm_loss
        return path_loss

    def get_snr_dl(self):
        snr = self.eirp_satellite + self.gain_to_noise_gt - self.get_path_loss("DL") - self.BOLTZ_CONST - 10 * math.log10(self.bandwidth_dl)
        snr = round(snr, 4)
  
        return snr

    def get_snr_ul(self):
        snr = self.eirp_gt + self.gain_to_noise_satellite - self.get_path_loss("UL") - self.BOLTZ_CONST - 10 * math.log10(self.bandwidth_ul)
        snr = round(snr, 4)

        return snr
    
    def compute_dl_rate(self):
        dl_SNR = self.get_snr_dl()  # Calculate your downlink SNR
        dl_rate = self.bandwidth_dl * math.log2(1 + 10 ** (dl_SNR / 10))

        return dl_rate

    def compute_ul_rate(self):
        ul_SNR = self.get_snr_ul()  # Calculate your uplink SNR
        ul_rate = self.bandwidth_ul * math.log2(1 + 10 ** (ul_SNR / 10))

        return ul_rate
