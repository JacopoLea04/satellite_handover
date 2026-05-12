import random
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
    satellites_with_elevation = []
    for satellite, beam in visible_satellites:
        satellite_name = satellite[0]
        elevation = utils.get_elevation(current_positions_df, round_time, satellite_name, mini_cluster.position)
        satellites_with_elevation.append((satellite, beam, elevation))
    satellites_with_elevation = sorted(satellites_with_elevation, key=lambda x: x[2], reverse=True)
    choices = max(int(0.3*len(satellites_with_elevation)), 1)
    random_index = random.randint(0, choices-1)
    next_sat = satellites_with_elevation[random_index][0]
    next_beam_index = satellites_with_elevation[random_index][1]
    return next_sat, next_beam_index

def get_max_visibility_satellite(visible_satellites, current_positions_df, round_time):
    satellites_with_visibility = []
    for satellite, beam in visible_satellites:
        satellite_name = satellite[0]
        vis_time = utils.get_visibility_time(satellite_name, round_time, current_positions_df)
        satellites_with_visibility.append((satellite, beam, vis_time))
    satellites_with_visibility = sorted(satellites_with_visibility, key=lambda x: x[2], reverse=True)
    choices = max(int(0.3*len(satellites_with_visibility)), 1)
    random_index = random.randint(0, choices-1)
    next_sat = satellites_with_visibility[random_index][0]
    next_beam_index = satellites_with_visibility[random_index][1]
    return next_sat, next_beam_index

def get_max_available_throughput_satellite(visible_satellites, round_time, mini_cluster, service_satellites, mainframe, scenario):
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
    best_index = 0
    next_sat = satellites_with_throughput[best_index][0]
    next_beam_index = satellites_with_throughput[best_index][1]
    return next_sat, next_beam_index