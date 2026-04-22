import utils
import cluster

beam_size_m = 50000 # 50 km beam
cell_dim_beams = 5

# Define the center of the cluster
center_lat = 45.40969451353066
center_lon = 11.89266205327162
cluster_position = (center_lat, center_lon)
cluster_name = "Test Cluster"
num_ues = 0
beam_size_km = beam_size_m / 1000  # Convert meters to kilometers
num_beams = 25
frame = ""
threshold = 5
sat_servers = 1
sat_mu = 1

# Calculate the coordinates of cell boundaries
cell_boundaries = utils.compute_cell_boundaries_lla(center_lat, center_lon, beam_size_m, cell_dim_beams)
print("cell boundaries:")
print(cell_boundaries)

test_cluster = cluster.Cluster(cluster_name, cluster_position, num_ues, beam_size_km, num_beams, frame, threshold, sat_servers, sat_mu)
print("printing the positions of the mini cluster centers:")
for positions in test_cluster.positions:
    print(positions)

visible_cluster_indices = utils.check_clusters_visibility(test_cluster.positions, cell_boundaries, cell_dim_beams)
print("indices of miniclusters that can see the satellite:")
print(visible_cluster_indices)

print("\n\nnew cluster moved east:")
new_center_lat = center_lat
new_center_lon = center_lon + 1  # Move 1 degrees east
new_cluster_position = (new_center_lat, new_center_lon)
test_cluster_new = cluster.Cluster(cluster_name, new_cluster_position, num_ues, beam_size_km, num_beams, frame, threshold, sat_servers, sat_mu)
print("printing the positions of the mini cluster centers:")
for positions in test_cluster_new.positions:
    print(positions)
visible_cluster_indices = utils.check_clusters_visibility(test_cluster_new.positions, cell_boundaries, cell_dim_beams)
print("indices of miniclusters that can see the satellite:")
print(visible_cluster_indices)