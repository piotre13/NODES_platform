import numpy as np
import math
from eppy.modeleditor import IDF


class IdfEditor():
    def __init__(self,idf_path, idd_path):
        IDF.setiddname()
        idf = IDF(idf_path)
        self.idf = idf
        pass

    def surface_dimensions(self, vertices):
        # Controllo che la lista abbia 4 vertici
        if len(vertices) != 4:
            raise ValueError("La lista deve contenere esattamente 4 vertici.")

        # Calcolo le distanze tra tutti i vertici
        distances = {}
        for i, v1 in enumerate(vertices):
            for j, v2 in enumerate(vertices):
                if i != j:
                    distance = np.sqrt((v1[0] - v2[0]) ** 2 + (v1[1] - v2[1]) ** 2 + (v1[2] - v2[2]) ** 2)
                    distances[(i, j)] = distance

        # Trovo i due vertici più lontani per la larghezza nel piano XY
        max_width = max(distances, key=distances.get)
        width_vertices = (vertices[max_width[0]], vertices[max_width[1]])

        # Trovo i due vertici rimanenti per l'altezza nella direzione Z
        height_vertices = [v for i, v in enumerate(vertices) if i not in max_width]

        # Calcolo la larghezza nel piano XY
        width = distances[max_width]

        # Calcolo l'altezza nella direzione Z
        height = np.abs(height_vertices[1][2] - height_vertices[0][2])

        return width, height

    def get_surface_vertices(self, surface_obj):
        return [(surface_obj[f"Vertex_{i}_Xcoordinate"], surface_obj[f"Vertex_{i}_Ycoordinate"],
                 surface_obj[f"Vertex_{i}_Zcoordinate"]) for i in range(1, 5)]

    def calculate_surface_area(self, vertices):
        def cross_product(p1, p2):
            return (p1[1] * p2[2] - p1[2] * p2[1],
                    p1[2] * p2[0] - p1[0] * p2[2],
                    p1[0] * p2[1] - p1[1] * p2[0])

        # Calculate the normal vector of the surface
        n = len(vertices)
        normal = [0.0, 0.0, 0.0]
        for i in range(n):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % n]
            normal[0] += (v1[1] - v2[1]) * (v1[2] + v2[2])
            normal[1] += (v1[2] - v2[2]) * (v1[0] + v2[0])
            normal[2] += (v1[0] - v2[0]) * (v1[1] + v2[1])

        # Calculate the magnitude of the normal vector
        magnitude = (normal[0] ** 2 + normal[1] ** 2 + normal[2] ** 2) ** 0.5

        # Check if the magnitude is zero (i.e., invalid polygon)
        if magnitude == 0.0:
            return 0.0

        # Normalize the normal vector
        normal = [x / magnitude for x in normal]

        # Calculate the area using the normalized normal vector
        area = 0.0
        for i in range(n):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % n]
            cross = cross_product(v1, v2)
            area += cross[0] * normal[0]
            area += cross[1] * normal[1]
            area += cross[2] * normal[2]

        return abs(area) / 2.0

    def modify_surface_area(self, desired_area):
        # Get the Surface object by its name
        surface_obj = self.idf.getobject('BuildingSurface:Detailed', 'floor')

        # Get the vertices of the current surface
        vertices = self.get_surface_vertices(surface_obj)

        # Calculate the current surface area
        current_area = self.calculate_surface_area(vertices)

        # Calculate the scaling factor to achieve the desired area
        scaling_factor = math.sqrt(desired_area / current_area)

        # Update the vertices of the current surface with the scaled positions
        for i, (x, y, z) in enumerate(vertices):
            surface_obj[f"Vertex_{i + 1}_Xcoordinate"] = x * scaling_factor
            surface_obj[f"Vertex_{i + 1}_Ycoordinate"] = y * scaling_factor

        # Adjust the vertices of adjacent surfaces
        zone_name = surface_obj.Zone_Name
        adjacent_surfaces = self.idf.idfobjects["BuildingSurface:Detailed"]

        for adjacent_surface in adjacent_surfaces:
            if adjacent_surface.Zone_Name == zone_name and adjacent_surface.Name != 'floor':
                adjacent_vertices = self.get_surface_vertices(adjacent_surface)
                for i, (x, y, z) in enumerate(adjacent_vertices):
                    adjacent_surface[f"Vertex_{i + 1}_Xcoordinate"] = x * scaling_factor
                    adjacent_surface[f"Vertex_{i + 1}_Ycoordinate"] = y * scaling_factor

    def modify_window_dimensions(self, wall_name, window_to_wall_ratio):
        # Get the Wall Surface object by its name
        wall_surface = self.idf.getobject('BuildingSurface:Detailed', f'wall{wall_name}')
        wall_vertices = self.get_surface_vertices(wall_surface)

        # Calculate the current wall area
        wall_area = self.calculate_surface_area(wall_vertices)

        # Calculate the target window area based on the window-to-wall ratio
        target_window_area = wall_area * window_to_wall_ratio

        # Get the FenestrationSurface:Detailed object associated with the wall
        fenestration_surface = self.idf.getobject('FenestrationSurface:Detailed', f'window{wall_name}')
        window_vertices = self.get_surface_vertices(fenestration_surface)

        window_width, window_height = self.surface_dimensions(window_vertices)
        # Calculate the scaling factor to achieve the desired window area
        new_window_height = target_window_area / window_width

        # Get the Z-coordinate of the first and third vertices (lower vertices) of the window
        window_max_z_coordinate = window_vertices[0][2]

        wall_min_z_coordinate = wall_vertices[1][2]
        new_window_min_z_coordinate = window_max_z_coordinate - new_window_height

        # add check to not
        if new_window_min_z_coordinate < wall_min_z_coordinate:
            new_window_min_z_coordinate = wall_min_z_coordinate

        # Update the Z-coordinates of the lower vertices in the window surface
        fenestration_surface["Vertex_2_Zcoordinate"] = new_window_min_z_coordinate
        fenestration_surface["Vertex_3_Zcoordinate"] = new_window_min_z_coordinate

        # Optionally, you can also adjust the Z-coordinates of the upper vertices (index 1 and 2) if needed.
        # fenestration_surface["Vertex_2_Zcoordinate"] = new_z2
        # fenestration_surface["Vertex_4_Zcoordinate"] = new_z4

    def calculate_transmittance(self, construction):
        # Calculate the thermal transmittance of the construction
        thermal_transmittance = 0.0
        air_film_thickness = 0.0002  # Assuming a default air film thickness of 0.0002 m (200 mm)

        # Outside air film
        thermal_transmittance += air_film_thickness / 0.034  # Thermal conductivity of air (W/m-K)

        for layer_name in construction.fieldnames[2:]:
            if construction[layer_name] == '':
                continue
            layer_material = self.idf.getobject('MATERIAL', construction[layer_name])
            thermal_transmittance += layer_material.Thickness / layer_material.Conductivity

        # Inside air film
        thermal_transmittance += air_film_thickness / 0.034  # Thermal conductivity of air (W/m-K)

        return thermal_transmittance

    def calculate_new_material_thickness(self, material, actual_transmittance, target_transmittance, limits=(0.02, 0.3)):
        layer_material_thickness = (1 / (actual_transmittance - target_transmittance)) * material.Conductivity
        new_thickness = material.Thickness + layer_material_thickness

        if new_thickness < limits[0]:
            new_thickness = limits[0]
        elif new_thickness > limits[1]:
            new_thickness = limits[1]
        return new_thickness

    def modify_external_wall_transmittance(self, target_transmittance):
        # Find the construction object with the specified name
        construction = self.idf.getobject('MATERIAL', 'wall_external')
        if construction is None:
            raise ValueError(f"Construction not found in the self.idf file.")

        # Find the material object with the specified name
        material = self.idf.getobject('MATERIAL', 'insulation_fiberglass_UNI10351') # todo generalizzare
        if material is None:
            raise ValueError(f"Material not found in the self.idf file.")

        # Calculate the current thermal transmittance of the construction
        thermal_transmittance = self.calculate_transmittance( construction)

        # Calculate the needed thickness for the specified material to achieve the desired transmittance
        new_thickness = self.calculate_new_material_thickness(material, thermal_transmittance, target_transmittance)

        material.Thickness = new_thickness

        print(f'Modified wall transmittance {thermal_transmittance} -> {target_transmittance}')

    def modify_floor_transmittance(self, target_transmittance):
        # Find the construction object with the specified name
        construction = self.idf.getobject('MATERIAL', 'floor')
        if construction is None:
            raise ValueError(f"Construction not found in the self.idf file.")

        # Find the material object with the specified name
        material = self.idf.getobject('MATERIAL', 'insulation_extrudedpolystyrene_4cm_UNI10351')
        if material is None:
            raise ValueError(f"Material not found in the self.idf file.")

        # Calculate the current thermal transmittance of the construction
        thermal_transmittance = self.calculate_transmittance(construction)

        # Calculate the needed thickness for the specified material to achieve the desired transmittance
        new_thickness = self.calculate_new_material_thickness(material, thermal_transmittance, target_transmittance)

        material.Thickness = new_thickness

        print(f'Modified floor transmittance {thermal_transmittance} -> {target_transmittance}')

    def modify_roof_transmittance(self, target_transmittance):
        # Find the construction object with the specified name
        construction = self.idf.getobject('MATERIAL', 'roof')
        if construction is None:
            raise ValueError(f"Construction not found in the self.idf file.")

        # Find the material object with the specified name
        material = self.idf.getobject('MATERIAL', 'insulation_extrudedpolystyrene_6cm_UNI10351')
        if material is None:
            raise ValueError(f"Material not found in the self.idf file.")

        # Calculate the current thermal transmittance of the construction
        thermal_transmittance = self.calculate_transmittance(construction)

        # Calculate the needed thickness for the specified material to achieve the desired transmittance
        new_thickness = self.calculate_new_material_thickness(material, thermal_transmittance, target_transmittance)

        material.Thickness = new_thickness

        print(f'Modified roof transmittance {thermal_transmittance} -> {target_transmittance}')

    def modify_window_u_factor(self, target_u_factor):
        # Find the construction object with the specified name
        construction = self.idf.getobject('WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM', 'window_simple')
        if construction is None:
            raise ValueError(f"Construction not found in the self.idf file.")

        # Calculate the current U-factor of the construction
        u_factor = construction.UFactor

        # Calculate the needed thickness for the specified material to achieve the desired transmittance
        construction.UFactor = target_u_factor

        print(f'Modified window U-factor {u_factor} -> {target_u_factor}')


if __name__ == '__main__':
    idf_path = 'res_highP.idf'
    idd_path = "C:/EnergyPlusV23-1-0/Energy+.idd"