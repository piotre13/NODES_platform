from eppy.modeleditor import IDF
from fnct_idf_mod import *

idf_path = 'eplus_idf_modify/res_highP/res_highP.idf'
desired_area = 150  # in square meters #?
IDF.setiddname("C:/EnergyPlusV23-1-0/Energy+.idd")
idf = IDF(idf_path)

# Modify the floor surface to have the desired surface area
modify_surface_area(idf, desired_area)

# Define the desired window-to-wall ratio for each wall
window_to_wall_ratio_east = 0.5  # Example: 20% window-to-wall ratio for the east wall
window_to_wall_ratio_west = 0.1  # Example: 10% window-to-wall ratio for the west wall
window_to_wall_ratio_north = 0.15  # Example: 15% window-to-wall ratio for the north wall
window_to_wall_ratio_south = 0.25  # Example: 25% window-to-wall ratio for the south wall

# Modify the window dimensions for each wall to achieve the desired window-to-wall ratio
modify_window_dimensions(idf, 'East', window_to_wall_ratio_east)
# modify_window_dimensions(idf, 'wallWest', window_to_wall_ratio_west)
# modify_window_dimensions(idf, 'wallNorth', window_to_wall_ratio_north)
# modify_window_dimensions(idf, 'wallSouth', window_to_wall_ratio_south)

construction_name = 'wall_external'
material_name = 'insulation_fiberglass_UNI10351'
desired_transmittance = 1.5  # Replace with your desired transmittance value
modify_external_wall_transmittance(idf, desired_transmittance)


# Save the modified IDF file
# modified_idf_path = 'path/to/modified_idf_file.idf'
# idf.save(modified_idf_path)
