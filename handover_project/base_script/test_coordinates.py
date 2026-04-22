import utils

beam_size_m = 50000 # 50 km beam
cell_dim_beams = 5

# Define the center of the cluster
center_lat = 45.40969451353066
center_lon = 11.89266205327162

# Calculate the coordinates of cell boundaries
cell_boundaries = utils.compute_cell_boundaries_lla(center_lat, center_lon, beam_size_m,cell_dim_beams)
print(cell_boundaries)