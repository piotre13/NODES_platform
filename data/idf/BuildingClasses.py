from eppy.modeleditor import IDF
import numpy as np
import math
import json
import geopandas as gpd
import shapely.wkt
import pandas as pd
import os


def find_starting_vertex(vertices):
    # Find the vertex with the minimum x-coordinate
    min_x = max(vertices, key=lambda vertex: vertex[0])

    # If there are multiple vertices with the same minimum x-coordinate, choose the one with the maximum y-coordinate
    min_x_max_y = max([vertex for vertex in vertices if vertex[0] == min_x[0]], key=lambda vertex: vertex[1])

    return min_x_max_y


def find_polygon_centroid(vertices):
    x = [vertex[0] for vertex in vertices]
    y = [vertex[1] for vertex in vertices]
    centroid_x = sum(x) / len(vertices)
    centroid_y = sum(y) / len(vertices)
    return centroid_x, centroid_y


def calculate_angle(vertex, centroid):
    # Calculate the angle between the vertex and the centroid with respect to the x-axis
    return math.atan2(vertex[1] - centroid[1], vertex[0] - centroid[0])


def sort_vertices_clockwise(vertices):
    starting_vertex = find_starting_vertex(vertices)
    centroid = find_polygon_centroid(vertices)
    sorted_vertices = sorted(vertices, key=lambda vertex: calculate_angle(vertex, centroid))

    # Rotate the list to start with the starting vertex
    starting_index = sorted_vertices.index(starting_vertex)
    sorted_vertices = sorted_vertices[starting_index:] + sorted_vertices[:starting_index]

    return sorted_vertices


def sort_vertices_counterclockwise(vertices):
    starting_vertex = find_starting_vertex(vertices)
    centroid = find_polygon_centroid(vertices)
    sorted_vertices = sorted(vertices, key=lambda vertex: calculate_angle(vertex, centroid), reverse=True)

    # Rotate the list to start with the starting vertex
    starting_index = sorted_vertices.index(starting_vertex)
    sorted_vertices = sorted_vertices[starting_index:] + sorted_vertices[:starting_index]

    return sorted_vertices


def reduce_distance_and_maintain_center(point1, point2, reduction_percentage):
    # Calculate the center point
    center_x = (point1[0] + point2[0]) / 2
    center_y = (point1[1] + point2[1]) / 2

    # Calculate the original distance
    original_distance = math.sqrt((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)

    # Calculate the reduction in distance
    reduction = reduction_percentage / 100 * original_distance

    # Calculate the new distance
    new_distance = original_distance - reduction

    # Calculate the new coordinates
    new_x1 = center_x + (point1[0] - center_x) * (new_distance / original_distance)
    new_y1 = center_y + (point1[1] - center_y) * (new_distance / original_distance)
    new_x2 = center_x + (point2[0] - center_x) * (new_distance / original_distance)
    new_y2 = center_y + (point2[1] - center_y) * (new_distance / original_distance)

    return [(new_x1, new_y1), (new_x2, new_y2)]


def surface_dimensions(vertices):
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


def get_surface_vertices(surface_obj):
    return [(surface_obj[f"Vertex_{i}_Xcoordinate"], surface_obj[f"Vertex_{i}_Ycoordinate"],
             surface_obj[f"Vertex_{i}_Zcoordinate"]) for i in range(1, 5)]


def calculate_surface_area(vertices):
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


def polygon_orientation(vertices):
    # Calcola il centroide del poligono
    centroid = np.mean(vertices, axis=0)

    # Calcola l'angolo tra il nord geografico e il vettore che collega il centroide a un vertice
    first_vertex = vertices[0]
    angle_radians = math.atan2(first_vertex[1] - centroid[1], first_vertex[0] - centroid[0])

    # Converte l'angolo da radianti a gradi
    angle_degrees = math.degrees(angle_radians)

    return angle_degrees


class Building:
    def __init__(self, idf_path, idd_path):
        IDF.setiddname(idd_path)
        self.idf = IDF(idf_path)


class SingleFamilyHouse(Building):
    def __init__(self, idf_path, idd_path, config):
        super().__init__(idf_path, idd_path)
        self.building_name = config['name']
        self.materials_list = config['materials_list']
        self.constructions_list = config['construction_list']
        self.height = config['height']
        self.n_floors = config['n_floors']
        self.window_to_wall_ratio = config['window_to_wall_ratio']
        self.window_distance_from_roof = 0.5
        self.floor_vertices = list(config['floor_vertices'].exterior.coords)
        self.floor_vertices.pop()
        self.building_surface_area = config['area']
        self.heated_surface_area = self.building_surface_area * self.n_floors

        # getting neighbours if presents
        if not pd.isnull(config['shading_surfaces']):
            self.shading_surfaces = shapely.wkt.loads(config['shading_surfaces'])
            self.shading_surfaces = [list(x.exterior.coords) for x in self.shading_surfaces.geoms]
            self.shading_vertices = shapely.wkt.loads(config['shading_vertices'])
        else:
            self.shading_surfaces = []

        self._define_materials()
        self._define_constructions()
        self._create_floor_and_roof_surfaces()
        self._create_wall_surfaces()
        self._add_floor_internal_mass()
        if len(self.shading_surfaces) > 0:
            self._add_shading()
            #print('shades_added')
        # self._add_shading()

    def _define_materials(self):
        # for each material in materials_list, create a Material object in idf if material name starts with "airgap"
        # create an AirGap object in idf instead
        for material in self.materials_list:
            if material['name'].startswith('airgap'):
                material_obj = self.idf.newidfobject('Material:Airgap')
                # set the name of the material
                material_obj.Name = material['name']
                # set the thermal resistance of the material
                material_obj.Thermal_Resistance = material['properties']['Thermal_Resistance']
            else:
                material_obj = self.idf.newidfobject('Material')
                # set the name of the material
                material_obj.Name = material['name']
                # set the roughness of the material
                material_obj.Roughness = material['properties']['Roughness']
                # set the thickness of the material
                material_obj.Thickness = material['properties']['Thickness']
                # set the conductivity of the material
                material_obj.Conductivity = material['properties']['Conductivity']
                # set the density of the material
                material_obj.Density = material['properties']['Density']
                # set the specific heat of the material
                material_obj.Specific_Heat = material['properties']['Specific_Heat']
                # set the thermal absorptance of the material
                material_obj.Thermal_Absorptance = material['properties']['Thermal_Absorptance']
                # set the solar absorptance of the material
                material_obj.Solar_Absorptance = material['properties']['Solar_Absorptance']
                # set the visible absorptance of the material
                material_obj.Visible_Absorptance = material['properties']['Visible_Absorptance']

    def _define_constructions(self):
        # TODO testing only for window
        for construction in self.constructions_list:
            if construction['name'].startswith('window'):
                construction_obj = self.idf.getobject('WindowMaterial:SimpleGlazingSystem', 'window_simple')
                construction_obj.UFactor = construction['properties']['U']
                construction_obj.Solar_Heat_Gain_Coefficient = construction['properties']['g']
            else:
                construction_obj = self.idf.newidfobject('CONSTRUCTION')
                # set the name of the construction
                construction_obj.Name = construction['name']
                # set the outside layer of the construction
                for layer in construction['layers']:
                    construction_obj[layer] = construction['layers'][layer]

    def _create_floor_and_roof_surfaces(self):

        sorted_vertices = sort_vertices_counterclockwise(self.floor_vertices)

        surface = self.idf.newidfobject(
            "BuildingSurface:Detailed")
        surface.Name = 'floor'
        surface.Surface_Type = 'Floor'
        surface.Construction_Name = 'floor_ground'
        surface.Zone_Name = 'Zn001'
        surface.Outside_Boundary_Condition = 'Ground'
        surface.Sun_Exposure = 'NoSun'
        surface.Wind_Exposure = 'NoWind'
        surface.View_Factor_to_Ground = ''
        surface.Number_of_Vertices = len(sorted_vertices)
        for i, vertex in enumerate(sorted_vertices, start=1):
            setattr(surface, f"Vertex_{i}_Xcoordinate", "{:.7f}".format(vertex[0]))
            setattr(surface, f"Vertex_{i}_Ycoordinate", "{:.7f}".format(vertex[1]))
            setattr(surface, f"Vertex_{i}_Zcoordinate", "0")
        #print('ok')

        sorted_vertices = sort_vertices_counterclockwise(self.floor_vertices)

        surface = self.idf.newidfobject(
            "BuildingSurface:Detailed")
        surface.Name = 'roof'
        surface.Surface_Type = 'Roof'
        surface.Construction_Name = 'roof_external'
        surface.Zone_Name = 'Zn001'
        surface.Outside_Boundary_Condition = 'Outdoors'
        surface.Sun_Exposure = 'SunExposed'
        surface.Wind_Exposure = 'WindExposed'
        surface.View_Factor_to_Ground = ''
        surface.Number_of_Vertices = len(sorted_vertices)
        sorted_vertices = sorted_vertices[::-1]
        for i, vertex in enumerate(sorted_vertices, start=1):
            setattr(surface, f"Vertex_{i}_Xcoordinate", "{:.7f}".format(vertex[0]))
            setattr(surface, f"Vertex_{i}_Ycoordinate", "{:.7f}".format(vertex[1]))
            setattr(surface, f"Vertex_{i}_Zcoordinate", "{:.7f}".format(self.height))
        #print('ok')

    def _create_wall_surfaces(self):

        shading_control = self.idf.getobject(
            "WindowShadingControl", "shadingControl")

        sorted_floor_vertices = sort_vertices_counterclockwise(self.floor_vertices)

        for i in range(len(sorted_floor_vertices)):

            if i == len(sorted_floor_vertices) - 1:
                wall_base_vertices = [sorted_floor_vertices[i], sorted_floor_vertices[0]]
            else:
                wall_base_vertices = [sorted_floor_vertices[i], sorted_floor_vertices[i + 1]]

            window_base_vertices = reduce_distance_and_maintain_center(wall_base_vertices[0],
                                                                       wall_base_vertices[1],
                                                                       reduction_percentage=0.01)

            surface = self.idf.newidfobject(
                "BuildingSurface:Detailed")
            surface.Name = f'wall{i}'
            surface.Surface_Type = 'Wall'
            surface.Construction_Name = 'wall_external'
            surface.Zone_Name = 'Zn001'
            surface.Outside_Boundary_Condition = 'Outdoors'
            surface.Sun_Exposure = 'SunExposed'
            surface.Wind_Exposure = 'WindExposed'
            surface.View_Factor_to_Ground = ''
            surface.Number_of_Vertices = 4
            surface.Vertex_1_Xcoordinate = "{:.7f}".format(wall_base_vertices[0][0])
            surface.Vertex_1_Ycoordinate = "{:.7f}".format(wall_base_vertices[0][1])
            surface.Vertex_1_Zcoordinate = "{:.7f}".format(self.height)
            surface.Vertex_2_Xcoordinate = "{:.7f}".format(wall_base_vertices[1][0])
            surface.Vertex_2_Ycoordinate = "{:.7f}".format(wall_base_vertices[1][1])
            surface.Vertex_2_Zcoordinate = "{:.7f}".format(self.height)
            surface.Vertex_3_Xcoordinate = "{:.7f}".format(wall_base_vertices[1][0])
            surface.Vertex_3_Ycoordinate = "{:.7f}".format(wall_base_vertices[1][1])
            surface.Vertex_3_Zcoordinate = "0.0"
            surface.Vertex_4_Xcoordinate = "{:.7f}".format(wall_base_vertices[0][0])
            surface.Vertex_4_Ycoordinate = "{:.7f}".format(wall_base_vertices[0][1])
            surface.Vertex_4_Zcoordinate = "0.0"

            window_height = self.height * self.window_to_wall_ratio
            if (self.height - self.window_distance_from_roof) - window_height < 0:
                window_height = self.height - self.window_distance_from_roof

            window_min_z_coordinate = (self.height - self.window_distance_from_roof) - window_height

            window_surface = self.idf.newidfobject(
                "FenestrationSurface:Detailed")
            window_surface.Name = f'window{i}'
            window_surface.Surface_Type = 'Window'
            window_surface.Construction_Name = 'window_simple'
            window_surface.Building_Surface_Name = f'wall{i}'
            window_surface.Outside_Boundary_Condition_Object = ''
            window_surface.View_Factor_to_Ground = ''
            window_surface.Frame_and_Divider_Name = 'windowFrame'
            window_surface.Multiplier = ''
            window_surface.Number_of_Vertices = ''
            window_surface.Vertex_1_Xcoordinate = "{:.7f}".format(window_base_vertices[0][0])
            window_surface.Vertex_1_Ycoordinate = "{:.7f}".format(window_base_vertices[0][1])
            window_surface.Vertex_1_Zcoordinate = "{:.7f}".format(self.height - self.window_distance_from_roof)
            window_surface.Vertex_2_Xcoordinate = "{:.7f}".format(window_base_vertices[1][0])
            window_surface.Vertex_2_Ycoordinate = "{:.7f}".format(window_base_vertices[1][1])
            window_surface.Vertex_2_Zcoordinate = "{:.7f}".format(self.height - self.window_distance_from_roof)
            window_surface.Vertex_3_Xcoordinate = "{:.7f}".format(window_base_vertices[1][0])
            window_surface.Vertex_3_Ycoordinate = "{:.7f}".format(window_base_vertices[1][1])
            window_surface.Vertex_3_Zcoordinate = "{:.7f}".format(window_min_z_coordinate)
            window_surface.Vertex_4_Xcoordinate = "{:.7f}".format(window_base_vertices[0][0])
            window_surface.Vertex_4_Ycoordinate = "{:.7f}".format(window_base_vertices[0][1])
            window_surface.Vertex_4_Zcoordinate = "{:.7f}".format(window_min_z_coordinate)
            try:
                setattr(shading_control, f"Fenestration_Surface_{i + 1}_Name", f'window{i}')

            except ValueError as e:
                shading_control.objls.append(f"Fenestration_Surface_{i + 1}_Name")
                setattr(shading_control, f"Fenestration_Surface_{i + 1}_Name", f'window{i}')
                print(self.building_name)
                print(shading_control.__dict__)
                print(e)
                #print('yo')

    def _add_shading(self):
        self.shading_surfaces.pop()
        for i in range(len(self.shading_surfaces)):
            surafaces_vertices = self.shading_surfaces[i]
            surafaces_vertices.pop()
            # surafaces_vertices = sort_vertices_counterclockwise(surafaces_vertices)
            # create shading object:
            shading_surface = self.idf.newidfobject('Shading:Building:Detailed')
            shading_surface.Name = f'shading_{i}'
            for i, vertex in enumerate(surafaces_vertices, start=1):
                setattr(shading_surface, f"Vertex_{i}_Xcoordinate", "{:.7f}".format(vertex[0]))
                setattr(shading_surface, f"Vertex_{i}_Ycoordinate", "{:.7f}".format(vertex[1]))
                setattr(shading_surface, f"Vertex_{i}_Zcoordinate", "{:.7f}".format(vertex[2]))

    def _add_floor_internal_mass(self):
        if self.n_floors > 1:
            floor_internal_mass = self.idf.newidfobject('InternalMass')
            floor_internal_mass.Name = 'floorInternalMass'
            floor_internal_mass.Construction_Name = 'floor_internal'
            floor_internal_mass.Zone_or_ZoneList_Name = 'Zn001'
            floor_internal_mass.Surface_Area = self.building_surface_area * (self.n_floors - 1)

    def save_idf(self, path):
        try:
            self.idf.savecopy(path)
        except FileNotFoundError:
            out_dir = path.split('/')[0]
            os.mkdir(out_dir)
            self.idf.savecopy(path)


def main(config):
    # open material.json:
    with open(config['material_file']) as f:
        materials_list = json.load(f)
        materials_list = materials_list['materials']
    # open construction.json:
    with open(config['construction_file']) as f:
        constructions_list = json.load(f)

    gdf = gpd.read_file(config['gdf_file'])

    for bid, b_row in gdf.iterrows():
        params = {'name': 'BUI_%s' % bid, 'materials_list': None,
                  'construction_list': constructions_list[b_row['construction_type']],
                  'window_to_wall_ratio': b_row['w2w'],
                  'height': b_row['height'],
                  'floor_vertices': b_row['geometry'],
                  'shading_surfaces': b_row['neighbours_surfaces'],
                  "shading_vertices": b_row['neighbours_vertices'],
                  'n_floors': b_row['n_floors'],
                  'area': b_row['area']}

        # prepare the material list
        unique_materials = set()

        for construction in constructions_list[b_row['construction_type']]:
            materials = construction.get("layers", {})
            unique_materials.update(materials.values())
        # filter materials_list elements to include only elements which name is in unique_materials
        mat_list = [material for material in materials_list if material['name'] in unique_materials]
        params['materials_list'] = mat_list

        # instantiating a class for creating an IDF
        # TODO the name must be passed as config
        name = config['FMU_name']
        idf_name = config['idf_out_dir'] + '/%s_%s.idf' % (name,bid)
        sfh = SingleFamilyHouse(config=params, idf_path=config['idf_template'], idd_path=config['idd_path'])
        sfh.save_idf(idf_name)


if __name__ == '__main__':
    perf = 'high'

    config = {"material_file": "materials.json",
              "construction_file": "constructions.json",
              "gdf_file": "../geometric/outcomes/frassinetto_test_%s.geojson"%perf,
              "idd_path": "/usr/local/EnergyPlus-23-1-0/Energy+.idd",
              "idf_template": "singleFamilyHouse_test.idf",
              "idf_out_dir": "frassinetto_casestudy_%s"%perf,
              "FMU_name":'SF_%s'%perf
              }

    main(config)

    # floor_coordinates = [[392783.116707601875532, 5037970.027620642445982],
    #                      [392786.345666732289828, 5037964.115988032892346],
    #                      [392776.852269067545421, 5037966.634060244075954],
    #                      [392780.073409866658039, 5037960.722557845525444]]
    #
    # shading_surfaces = [
    #     [
    #         [392804.10487793584, 5037965.924153913, 0],
    #         [392808.0357948013, 5037960.3783843955, 0],
    #         [392808.0357948013, 5037960.3783843955, 3],
    #         [392804.10487793584, 5037965.924153913, 3]
    #     ], [
    #         [392808.0357948013, 5037960.3783843955, 0],
    #         [392802.38684248074, 5037956.407532597, 0],
    #         [392802.38684248074, 5037956.407532597, 3],
    #         [392808.0357948013, 5037960.3783843955, 3]
    #     ], [
    #         [392802.38684248074, 5037956.407532597, 0],
    #         [392798.4561175372, 5037961.964415291, 0],
    #         [392798.4561175372, 5037961.964415291, 3],
    #         [392802.38684248074, 5037956.407532597, 3]
    #     ], [
    #         [392798.4561175372, 5037961.964415291, 0],
    #         [392804.10487793584, 5037965.924153913, 0],
    #         [392804.10487793584, 5037965.924153913, 3],
    #         [392798.4561175372, 5037961.964415291, 3]
    #     ]
    # ]
