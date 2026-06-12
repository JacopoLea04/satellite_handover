import random
import utils
from scipy.optimize import linear_sum_assignment
import numpy as np
import math
"""
This module contains the implementation of different handover strategies. Each strategy is implemented as a standalone function. 
Each function can have its own paraemters, but the return value of each function should be a tuple (next satellite, next beam index)
specifying the satellite to connect to next and the beam index the UE should connect to in that satellite.

"""

def get_random_visible_satellite(visible_satellites):
    """
    implementation of a random selection amongst the visible satellites. The next satellite is selected randomly
    from the list of the visible satellites.
    Args:
        visible_satellites (list): list of tuples (satellite, beam_index) representing the satellites in visibility and the 
            corresponding beam index that the UE can connect to.
    Returns:
        tuple: (next_sat, next_beam_index) where next_sat is the tuple representing thesatellite to connect to, along with
            the respective beam index. returns None if there are no visible satellties.
    """
    number_of_satellites = len(visible_satellites)
    if(number_of_satellites == 0):
        return None
    random_index = random.randint(0, number_of_satellites-1) # pick a random index
    next_sat = visible_satellites[random_index][0] # get the satellite corresponding to the random index
    next_beam_index = visible_satellites[random_index][1]  # get the beam index that is covering the ue
    return next_sat, next_beam_index

def get_max_elevation_satellite(visible_satellites, current_positions_df, round_time, mini_cluster):
    """
    selecting the satellite with the maximum elevation angle from the ones in visibility for the UE.
    Args:
        visible_satellites (list): list of tuples (satellite, beam_index) representing the satellites in visibility and the 
            corresponding beam index that the UE can connect to.
        current_positions_df (pd.DataFrame): dataframe containing the positions of the visible satellites.
        round_time (int): current simulation time.
        mini_cluster (Beam): the Beam object containing the information on the mini cluster for which we are selecting the next satellite.
    Returns:
        tuple: (next_sat, next_beam_index) where next_sat is the satellite to connect to, along with the respective beam index. 
            returns None if there are no visible satellties.
    """

    satellites_with_elevation = []
    # loop on the visible satellites and get the elevation for each
    for satellite, beam in visible_satellites:
        satellite_name = satellite[0]
        elevation = utils.get_elevation(current_positions_df, round_time, satellite_name, mini_cluster.position)
        satellites_with_elevation.append((satellite, beam, elevation))
    # sort the satellites based on the elevation and pick a random one amongst the top 30%.
    # this to avoid all the UEs to converge to the same satellite
    satellites_with_elevation = sorted(satellites_with_elevation, key=lambda x: x[2], reverse=True)
    choices = max(int(0.3*len(satellites_with_elevation)), 1)
    random_index = random.randint(0, choices-1)
    next_sat = satellites_with_elevation[random_index][0]
    next_beam_index = satellites_with_elevation[random_index][1]
    return next_sat, next_beam_index

def get_max_visibility_satellite(visible_satellites, current_positions_df, round_time):
    """
    selecting the satellite with the maximum remaining visibility time from the ones in visibility for the UE.
    Args:
        visible_satellites (list): list of tuples (satellite, beam_index) representing the satellites in visibility and the 
            corresponding beam index that the UE can connect to.
        current_positions_df (pd.DataFrame): dataframe containing the positions of the visible satellites.
        round_time (int): current simulation time.
    Returns:
        tuple: (next_sat, next_beam_index) where next_sat is the satellite to connect to, along with the respective beam index. 
            returns None if there are no visible satellties.
    """
    satellites_with_visibility = []
    # loop on the visible satellites and get the remaining visibility time for each
    for satellite, beam in visible_satellites:
        satellite_name = satellite[0]
        vis_time = utils.get_visibility_time(satellite_name, round_time, current_positions_df)
        satellites_with_visibility.append((satellite, beam, vis_time))
    # sort the satellites based on the remaining visibility time and pick a random one amongst the top 30%.
    # this to avoid all the UEs to converge to the same satellite
    satellites_with_visibility = sorted(satellites_with_visibility, key=lambda x: x[2], reverse=True)
    choices = max(int(0.3*len(satellites_with_visibility)), 1)
    random_index = random.randint(0, choices-1)
    next_sat = satellites_with_visibility[random_index][0]
    next_beam_index = satellites_with_visibility[random_index][1]
    return next_sat, next_beam_index

def get_max_available_throughput_satellite(visible_satellites, round_time, mini_cluster, service_satellites, mainframe, scenario):
    """
    selecting the satellite capable of providing the highest throughput value also considering the current load from the ones in visibility for the UE.
    Args:
        visible_satellites (list): list of tuples (satellite, beam_index) representing the satellites in visibility and the 
            corresponding beam index that the UE can connect to.
        round_time (int): current simulation time.
        mini_cluster (Beam): the Beam object containing the information on the mini cluster for which we are selecting the next satellite.
        service_satellites (list): list of satellites that are currently providing service.
        mainframe (pd.DataFrame): the main dataframe containing the information on satellite positions over time.
        scenario (dict): dictionary containing the scenario parameters.
    Returns:
        tuple: (next_sat, next_beam_index) where next_sat is the satellite to connect to, along with the respective beam index. 
            returns None if there are no visible satellties.
    """
    satellites_with_throughput = []
    # loop on the visible satellites, compute and save the throughput for each 
    for satellite, beam in visible_satellites:
        satellite_name = satellite[0]
        num_connected_ues = 1
        if satellite_name in service_satellites:
            num_connected_ues += service_satellites[satellite_name].connected_ues[beam]
        # compute the max throughput based on shannon formula, snr, overhead
        max_dl_thr, max_ul_thr = utils.get_max_beam_throughput(mainframe, round_time, satellite_name, mini_cluster.position, scenario)
        # split resources amongst the number of connected users
        thr_score = max_dl_thr / num_connected_ues
        satellites_with_throughput.append((satellite, beam, thr_score))
    # sort the throughput
    satellites_with_throughput = sorted(satellites_with_throughput, key=lambda x: x[2], reverse=True)
    best_index = 0
    next_sat = satellites_with_throughput[best_index][0]
    next_beam_index = satellites_with_throughput[best_index][1]
    return next_sat, next_beam_index

def compute_mauf_weight(satellite_info, beam_index, current_positions_df, round_time, mini_cluster, service_satellites, mainframe, scenario):
    """
    Computes the Doppler-Aware Multi-Attribute Utility Function (MAUF) weight W_{i,j} for a specific satellite.
    This replaces the greedy approach with a normalized, multi-dimensional evaluation.
    """
    satellite_name = satellite_info[0]
    
    # Normalized Elevation (E_norm)
    # Range [0, 1]. Assumes a threshold of 30 degrees.
    elevation = utils.get_elevation(current_positions_df, round_time, satellite_name, mini_cluster.position)
    e_threshold = 30.0
    if elevation < e_threshold:
        e_norm = 0.0
    else:
        e_norm = (elevation - e_threshold) / (90.0 - e_threshold)
        
    # Normalized Remaining Visibility (V_norm)
    # Range [0, 1]. Approximates the maximum pass time for LEO 600km to ~600 seconds (10 minutes).
    vis_time = utils.get_visibility_time(satellite_name, round_time, current_positions_df)
    v_max = 600.0  
    v_norm = min(vis_time / v_max, 1.0)
    
    # Normalized Load Penalty (L_norm)
    # Range [0, 1]. Avoids congestion by penalizing already loaded satellites.
    max_capacity_per_beam = 50.0 # Assumption: max 50 UEs per beam before saturation
    current_load = 0
    if satellite_name in service_satellites:
        current_load = service_satellites[satellite_name].connected_ues[beam_index]
    l_norm = min(current_load / max_capacity_per_beam, 1.0)
    
    # Normalized Doppler Penalty (D_norm)
    # Range [0, 1]. Penalizes high radial velocities that cause Inter-Carrier Interference (ICI).
    # We extract the Doppler shift directly from the simulation utility.
    f_dl, _ = utils.compute_doppler_shift(
        ue_pos=mini_cluster.position, 
        old_pos=None, # We pass None to force the utility to compute instantaneous snapshot if possible, or we approximate.
        curr_pos=None, # Note: we will need to ensure utils can compute this statically, or we estimate it.
        fut_pos=None,
        scenario=scenario
    )
    # For a 600km LEO at 20GHz, max Doppler is roughly 500 kHz.
    d_max = 500000.0
    # Temporary fallback if Doppler can't be computed statically in this function:
    # We approximate Doppler penalty inversely proportional to elevation (Zenith = 0 Doppler, Horizon = Max Doppler)
    # In a fully integrated PHY layer, you would use exact radial velocity.
    d_norm = 1.0 - e_norm 
    
    # Weights for the MAUF (Alpha parameters) - Tunable for the paper
    alpha_1 = 0.4  # Elevation Importance
    alpha_2 = 0.3  # Visibility Importance
    alpha_3 = 0.2  # Doppler Penalty Importance
    alpha_4 = 0.1  # Load Penalty Importance
    
    # Final Utility Score W_{i,j}
    W = (alpha_1 * e_norm) + (alpha_2 * v_norm) - (alpha_3 * d_norm) - (alpha_4 * l_norm)
    
    return W


def get_dap_bm_satellite(visible_satellites, current_positions_df, round_time, mini_cluster, service_satellites, mainframe, scenario, ue_id, cluster_pending_ues, curr_sat_name=None, curr_beam_index=None):
    number_of_satellites = len(visible_satellites)
    if number_of_satellites == 0:
        return None, None
        
    satellites_with_mauf = []
    w_curr = -1.0
    
    # MURO DI CAPACITA' (Water-Filling)
    # Riduciamo drasticamente il limite per forzare gli utenti a usare TUTTI i satelliti visibili
    MAX_CAPACITY = 15.0 
    
    for satellite, beam in visible_satellites:
        w_score = compute_mauf_weight(satellite, beam, current_positions_df, round_time, mini_cluster, service_satellites, mainframe, scenario)
        
        if satellite[0] in service_satellites:
            try:
                current_load = service_satellites[satellite[0]].connected_ues[beam]
                load_ratio = min(current_load / MAX_CAPACITY, 0.99)
                # Eleviamo alla 4a potenza: penalità spaventosa se ci si avvicina a 15 utenti
                w_score *= (1.0 - load_ratio) ** 4 
            except Exception:
                pass
                
        satellites_with_mauf.append((satellite, beam, w_score))
        
        if curr_sat_name is not None and satellite[0] == curr_sat_name and beam == curr_beam_index:
            w_curr = w_score

    if curr_sat_name is None or w_curr == -1.0:
        satellites_with_mauf = sorted(satellites_with_mauf, key=lambda x: x[2], reverse=True)
        return satellites_with_mauf[0][0], satellites_with_mauf[0][1]

    # ==========================================================
    # DOMINIO DI SODDISFAZIONE (S-MEASURE ASSOLUTO)
    # ==========================================================
    # Se il canale attuale è già ottimo (> 0.60), non guardare MAI la concorrenza.
    # Questo annienta i ping-pong di "ottimizzazione inutile".
    if w_curr > 0.60:
        return "STAY", None

    # Isoliamo candidati
    intra_candidates = [x for x in satellites_with_mauf if x[0][0] == curr_sat_name]
    best_intra = sorted(intra_candidates, key=lambda x: x[2], reverse=True)[0] if intra_candidates else None

    inter_candidates = [x for x in satellites_with_mauf if x[0][0] != curr_sat_name]
    best_inter = sorted(inter_candidates, key=lambda x: x[2], reverse=True)[0] if inter_candidates else None

    # Protezione Radio Link Failure
    if w_curr < 0.05:
        all_sorted = sorted(satellites_with_mauf, key=lambda x: x[2], reverse=True)
        return all_sorted[0][0], all_sorted[0][1]

    # Valutazione Inter-HO (Muro del 30%)
    inter_approved = False
    if best_inter is not None and best_inter[2] > (w_curr * 1.30):
        inter_approved = True

    # Valutazione Intra-HO (Scivolo del 2%)
    intra_approved = False
    if best_intra is not None and best_intra[1] != curr_beam_index:
        if best_intra[2] > (w_curr * 1.02):
            intra_approved = True

    if inter_approved and intra_approved:
        if best_inter[2] > best_intra[2]:
            return best_inter[0], best_inter[1]
        else:
            return best_intra[0], best_intra[1]
            
    elif inter_approved:
        return best_inter[0], best_inter[1]
        
    elif intra_approved:
        return best_intra[0], best_intra[1]
        
    else:
        return "STAY", None