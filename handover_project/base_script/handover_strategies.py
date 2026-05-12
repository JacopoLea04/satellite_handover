from random import random
import utils

def get_random_visible_satellite(visible_satellites):
    number_of_satellites = len(visible_satellites)
    if(number_of_satellites == 0):
        return None
    random_index = random.randint(0, number_of_satellites-1)
    next_sat = visible_satellites[random_index][0]
    next_beam_index = visible_satellites[random_index][1]
    return next_sat, next_beam_index

def get_max_elevation_satellite(visible_satellites, current_positions_df, round_time, mini_cluster):
    for i, (satellite, beam) in enumerate(visible_satellites):
        elevation = utils.get_elevation(current_positions_df, round_time, satellite, mini_cluster.position)
        visible_satellites[i] = (satellite, beam, elevation)
    visible_satellites = sorted(visible_satellites, key=lambda x: x[2], reverse=True)
    
    choices = max(int(0.3*len(visible_satellites)), 1)
    random_index = random.randint(0, choices-1)
    next_sat = visible_satellites[random_index][0]
    next_beam_index = visible_satellites[random_index][1]
    return next_sat, next_beam_index

def get_max_visibility_satellite(visible_satellites, current_positions_df, round_time):
    for i, (satellite, beam) in enumerate(visible_satellites):
        vis_time = utils.get_visibility_time(satellite, round_time, current_positions_df)
        visible_satellites[i] = (satellite, beam, vis_time)
    visible_satellites = sorted(visible_satellites, key=lambda x: x[2], reverse=True)
    
    choices = max(int(0.3*len(visible_satellites)), 1)
    random_index = random.randint(0, choices-1)
    next_sat = visible_satellites[random_index][0]
    next_beam_index = visible_satellites[random_index][1]
    return next_sat, next_beam_index