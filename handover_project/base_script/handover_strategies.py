import random
import utils
import math

"""
This module contains the implementation of legacy handover strategies (State of the Art). 
Each strategy represents a distributed, UE-centric approach (Active-UE), lacking central coordination.
These serve as standard baselines to evaluate the benefits of a centralized SDN architecture.
"""

def get_random_visible_satellite(visible_satellites):
    """
    Implementation of a random selection amongst the visible satellites.
    Returns:
        tuple: (next_sat, next_beam_index) or None if no visible satellites.
    """
    number_of_satellites = len(visible_satellites)
    if number_of_satellites == 0:
        return None
        
    random_index = random.randint(0, number_of_satellites - 1) 
    next_sat = visible_satellites[random_index][0] 
    next_beam_index = visible_satellites[random_index][1] 
    return next_sat, next_beam_index

def get_max_elevation_satellite(visible_satellites, current_positions_df, round_time, mini_cluster):
    """
    Pure Greedy Baseline: Selects the satellite with the absolute maximum elevation angle.
    Being a decentralized Active-UE strategy, it is highly prone to network congestion 
    as multiple UEs might greedily select the same optimal node.
    """
    satellites_with_elevation = []
    
    for satellite, beam in visible_satellites:
        satellite_name = satellite[0]
        elevation = utils.get_elevation(current_positions_df, round_time, satellite_name, mini_cluster.position)
        satellites_with_elevation.append((satellite, beam, elevation))
        
    # Sort and pick the absolute best (Pure Greedy)
    satellites_with_elevation = sorted(satellites_with_elevation, key=lambda x: x[2], reverse=True)
    
    if not satellites_with_elevation:
        return None, None
        
    next_sat = satellites_with_elevation[0][0]
    next_beam_index = satellites_with_elevation[0][1]
    return next_sat, next_beam_index

def get_max_visibility_satellite(visible_satellites, current_positions_df, round_time):
    """
    Pure Greedy Baseline: Selects the satellite providing the maximum remaining visibility time.
    """
    satellites_with_visibility = []
    
    for satellite, beam in visible_satellites:
        satellite_name = satellite[0]
        vis_time = utils.get_visibility_time(satellite_name, round_time, current_positions_df)
        satellites_with_visibility.append((satellite, beam, vis_time))
        
    # Sort and pick the absolute best
    satellites_with_visibility = sorted(satellites_with_visibility, key=lambda x: x[2], reverse=True)
    
    if not satellites_with_visibility:
        return None, None
        
    next_sat = satellites_with_visibility[0][0]
    next_beam_index = satellites_with_visibility[0][1]
    return next_sat, next_beam_index

def get_max_available_throughput_satellite(visible_satellites, round_time, mini_cluster, service_satellites, mainframe, scenario):
    """
    Active-UE Baseline: Selects the satellite capable of providing the highest throughput value 
    considering its current load (Shannon capacity). Due to the lack of central coordination, 
    simultaneous decisions by multiple UEs can lead to sudden saturation (Herd Effect).
    """
    satellites_with_throughput = []
    
    for satellite, beam in visible_satellites:
        satellite_name = satellite[0]
        num_connected_ues = 1
        
        if satellite_name in service_satellites:
            num_connected_ues += service_satellites[satellite_name].connected_ues[beam]
            
        max_dl_thr, max_ul_thr = utils.get_max_beam_throughput(mainframe, round_time, satellite_name, mini_cluster.position, scenario)
        thr_score = max_dl_thr / num_connected_ues
        satellites_with_throughput.append((satellite, beam, thr_score))
        
    satellites_with_throughput = sorted(satellites_with_throughput, key=lambda x: x[2], reverse=True)
    
    if not satellites_with_throughput:
        return None, None
        
    next_sat = satellites_with_throughput[0][0]
    next_beam_index = satellites_with_throughput[0][1]
    return next_sat, next_beam_index