import pandas as pd
import geopandas as geopd
import osmnx
import requests
from requests import Request
from owslib.wfs import WebFeatureService
from shapely.geometry import box, Point, Polygon, MultiPolygon, MultiPoint, GeometryCollection
from shapely import STRtree
from pyproj import CRS, Proj, Transformer
import time
import numpy as np
import random
import statistics
import json
import matplotlib.pyplot as plt
from scipy import stats

class DataFiller():
    def __init__(self, config):
        self.config = config
    def geometrical_data(self, datakey, df):
        if datakey == 'area':
            return self.calc_area(df)
        elif datakey == 'n_floors':
            return self.calc_n_floors(df)
        elif datakey == 'net_leased_area':
            return self.calc_net_leased_area(df)
        elif datakey == 'gross_floor_area':
            return self.calc_gross_floor_area(df)
    def calc_area(self,df):
        df['geometry'] = df['geometry'].explode()[0:].values
        #to calculate the area crs must be a projected CRS
        df['area'] = df.to_crs('EPSG:7791').area
        return df
    def calc_n_floors(self,df):
        df['n_floors'] = (df['height']/self.config['avg_floor_height']).round().astype('Int64')
        return df

    def calc_gross_floor_area(self,df):
        df['gross_floor_area'] = df['n_floors']*df['area']
        return df
    def calc_net_leased_area(self,df):
        CF = self.config['leased_area_CF']
        df['net_leased_area'] = df['gross_floor_area']*CF
        return df

    def statistical_assignation(self,df,census_ind,tracciato):
        #if df['']
        #df = self.calc_year_of_constrcution_stat(df,census_ind,tracciato)
        #TODO aggiungere funzione per assegnazione deterministica in funzione del numero reale di edifici per year slot in ogni sezione di censimento
        #calc number of families in buildings
        #calc number of person in buildings

        return df
    def calc_year_of_constrcution_stat(self,df, census_ind,tracciato):
        #TODO parlare con silvio ha senso fare così coi numeri che abbiamo o semplicemente riportiamo i numeri di edifici con la fascia d'anno
        ind = ['E%s'%i for i in range(8,17,1)]
        year_slots = [(1800,1919),(1919,1945),(1946,1960),(1961,1970),(1971,1980),(1981,1990),(1991,2000),(2001,2005),(2005,2023)]
        sez_year_prob = {}
        df['year_of_construction'] = ''
        for zone in census_ind.SEZ2011:
            year_prob = census_ind[census_ind['SEZ2011'] == zone][ind].values.tolist()[0]
            tot = sum(year_prob)
            year_prob = [i/tot for i in year_prob]
            sez_year_prob[zone]=year_prob

        for index, row in df.iterrows():
            sez = row['sez_cens']
            try:
                i = np.random.choice(np.arange(len(ind)), p=sez_year_prob[sez])
                year = random.randint(year_slots[i][0],year_slots[i][1])
                df.at[index,'year_of_construction'] = year
            except KeyError as e:
                print ('I got a KeyError - reason "%s"' % str(e))
        return df

class ElevationMapper:
    def __init__(self, gdf):
        self.gdf = gdf

    def get_3d_coordinates(self, crs, lat, lon, alt_slm, building_height):
        source_crs = CRS.from_string("+proj=latlong +datum=WGS84 +ellps=WGS84 +geoidgrids=egm96_15.gtx")
        target_crs = CRS.from_string(crs)

        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        transformed_coords = transformer.transform(lat, lon, alt_slm + building_height)

        return transformed_coords[2]

    def get_elevation(self, crs, bbox, res, h_slm, columns):
        cells, cells_elevs = self.divide_bbox_into_cells(crs, bbox, h_slm, res)
        for i in range(len(self.gdf[columns[0]])):
            geom = self.gdf[columns[0]].iloc[i]
            h_bld = self.gdf[columns[1]].iloc[i]
            if isinstance(geom, Point):
                coords = list(geomFrassinetto_limitecomunale.shp.coords)
                lat, lon = coords[0][1], coords[0][0]
                terrain_elevation = self.get_elevation_for_point(crs, cells, cells_elevs, lat, lon, h_slm)
                z_coord = terrain_elevation + h_bld
                coords[0] = (lon, lat, z_coord)
                new_point = Point(coords)
                self.gdf[columns[0]].iloc[i] = new_point
            elif isinstance(geom, Polygon):
                coords = list(geom.exterior.coords)
                new_coords = []
                z_coords = []
                for j in range(len(coords)):
                    lat, lon = coords[j][1], coords[j][0]
                    terrain_elevation = self.get_elevation_for_point(crs, cells, cells_elevs, lat, lon, h_slm)
                    z_coord = terrain_elevation + h_bld
                    z_coords.append(z_coord)
                    sum_z = 0
                for z in range(len(z_coords)):
                    sum_z += z_coords[z]
                new_z_coord = sum_z / len(z_coords)
                for j in range(len(coords)):
                    lat, lon = coords[j][1], coords[j][0]
                    new_coords.append((lon, lat, new_z_coord))
                new_poly = Polygon(new_coords)
                self.gdf[columns[0]].iloc[i] = new_poly
            elif isinstance(geom, MultiPolygon):
                polygons = list(geom.geoms)
                new_polygons = []
                for p in range(len(polygons)):
                    coords = list(polygons[p].exterior.coords)
                    new_coords = []
                    z_coords = []
                    for j in range(len(coords)):
                        lat, lon = coords[j][1], coords[j][0]
                        terrain_elevation = self.get_elevation_for_point(crs, cells, cells_elevs, lat, lon, h_slm)
                        z_coord = terrain_elevation + h_bld
                        z_coords.append(z_coord)
                    sum_z = 0
                    for z in range(len(z_coords)):
                        sum_z += z_coords[z]
                    new_z_coord = sum_z/len(z_coords)
                    for j in range(len(coords)):
                        lat, lon = coords[j][1], coords[j][0]
                        new_coords.append((lon, lat, new_z_coord))
                    new_poly = Polygon(new_coords)
                    new_polygons.append(new_poly)
                new_mp = MultiPolygon(new_polygons)
                self.gdf[columns[0]].iloc[i] = new_mp
            else:
                # To be defined what it should be done in case of different geometry type with respect to Point, Polygon or MultiPolygon
                pass
            print(f"Z coordinate successfully mapped to building {i + 1}")
        return self.gdf, cells

    def get_elevation_for_point(self, crs, cells, cells_elevs, lat, lon, h_slm):
        source_crs = CRS.from_string(crs)
        target_crs = CRS.from_string("+proj=latlong +datum=WGS84 +ellps=WGS84 +geoidgrids=egm96_15.gtx")
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        transformed_coords = transformer.transform(lon, lat)

        lon, lat = transformed_coords[0], transformed_coords[1]

        matching_cells = []
        for i, cell in enumerate(cells):
            cell_bbox = box(cell[0], cell[1], cell[2], cell[3])
            if cell_bbox.contains(Point(lon, lat)):
                matching_cells.append(i)

        if len(matching_cells) != 0:
            elevs = [cells_elevs[index] for index in matching_cells]
            average_elevation = sum(elevs) / len(elevs)
            return average_elevation
        else:
            return h_slm

    def get_elevations(self, points, h_slm, max_retry, delay):
        retry_count = 0
        while retry_count < max_retry:
            locations = "|".join([f"{point.y},{point.x}" for point in points])
            url = f"https://api.open-elevation.com/api/v1/lookup?locations={locations}"
            response = requests.get(url)

            if response.status_code == 200:
                # print("Success!")
                data = response.json()
                elevations = [result["elevation"] for result in data["results"]]
                return elevations
            else:
                print(f"Request failed. New attempt in {delay} s")
                retry_count += 1
                time.sleep(delay)

        elevs = []
        for p in range(len(points)):
            elevs.append(h_slm)
        return elevs

    def divide_bbox_into_cells(self, crs, bbox, h_slm, resolution):
        lon_min, lat_min, lon_max, lat_max = bbox

        source_crs = CRS.from_string(crs)
        target_crs = CRS.from_string("+proj=aeqd +datum=WGS84 +ellps=WGS84")

        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        lon_min_geo, lat_min_geo = transformer.transform(lon_min, lat_min)
        lon_max_geo, lat_max_geo = transformer.transform(lon_max, lat_max)

        lon_cell_count = int((lon_max_geo - lon_min_geo) / resolution)
        lat_cell_count = int((lat_max_geo - lat_min_geo) / resolution)
        cells = []

        for i in range(lon_cell_count):
            for j in range(lat_cell_count):
                lon_start = lon_min_geo + i * resolution
                lat_start = lat_min_geo + j * resolution
                lon_end = lon_start + resolution
                lat_end = lat_start + resolution

                lon_start_geo, lat_start_geo = transformer.transform(lon_start, lat_start, direction="INVERSE")
                lon_end_geo, lat_end_geo = transformer.transform(lon_end, lat_end, direction="INVERSE")

                cell_bbox = (lon_start_geo, lat_start_geo, lon_end_geo, lat_end_geo)
                cells.append(cell_bbox)

        def get_cell_centroids(cells):
            centroids = [Point((cell[0] + cell[2]) / 2, (cell[1] + cell[3]) / 2) for cell in cells]
            return centroids

        cell_centroids = get_cell_centroids(cells)
        self.elevations = self.get_elevations(cell_centroids, h_slm, max_retry=10, delay=0.5)

        return cells, self.elevations

    def get_bbox_z_coords(self):
        return min(self.elevations), max(self.elevations)

class ZoneSelector():
    def __init__(self, study_area,processing_config, **raw_inputs):
        #preliminary information
        self.study_area = self.import_study_area(study_area) #must be a shapely polygon
        self.inputs = self.read_inputs(raw_inputs)

        #outcomes
        self.buildings = None

        #configurations
        with open (processing_config) as f:
            self.proc_conf = json.load(f)

        # helper classes
        self.Elevation = None
        self.Datafilling = DataFiller(self.proc_conf)



    def read_inputs(self, raw_inputs):
        inp_dict = {}
        for key, value in raw_inputs.items():
            if value:
                if not value.endswith('.csv'):
                    inp_dict[key] = geopd.read_file(value)
                else:
                    inp_dict[key] = pd.read_csv(value, delimiter =';', encoding='latin-1')
            else:
                inp_dict[key] = None
        return inp_dict

    def import_study_area(self, path):
        data = geopd.read_file(path)
        data = self.check_coordinates(data)
        polygon = data['geometry'][0]
        return polygon

    def check_coordinates(self, data):
        '''data must be a geodataframe'''
        return data.to_crs(4326)

    def get_buildings(self):

        if self.inputs['buildings'] is None:
            #convert study area to right coordinates
            self.study_area = self.check_coordinates(self.study_area)
            #download OSM data
            self.buildings = osmnx.features.features_from_polygon(self.study_area, tags={'building': True})
            # self.zone_graph = osmnx.graph_from_polygon(self.study_area)
            print('data downloaded')
        else:
            self.buildings = self.inputs['buildings']
            print('Buildings data already present')

        #perform some stupid cleaning for all nan columns
        #TODO generalize the cleaning and keep only interesting infos
        self.buildings = self.buildings.dropna(how='all')
        return
    def get_destination(self):

        if 'dest' not in self.buildings.columns and self.proc_conf['matching_col'][
            self.proc_conf['output_columns'].index('dest')] not in self.buildings.columns: # caso in cui non ho il dato
            #todo capire come scaricare la destinazione d'uso automaticamente
            return
        elif 'dest' not in self.buildings.columns: # caso in cui ho il dato ma non è strutturato come voglio
            self.buildings['dest']=' '
            col_name = self.proc_conf['matching_col'][self.proc_conf['output_columns'].index('dest')]
            self.buildings['dest'] = self.buildings.apply(lambda row: next((key for key, values in self.proc_conf['matching_values']['dest'].items()
                                                                            if row[col_name] in values), row['dest']), axis=1)
            #remove the old column
            self.buildings = self.buildings.drop(columns=[col_name])
            return
        else: #caso in cui dest è gia presente
            #todo check che sia strutturato come voglio io
            self.buildings['dest'] = self.buildings.apply(
                lambda row: next((key for key, values in self.proc_conf['matching_values']['dest'].items()
                                  if row['dest'] in values), row['dest']), axis=1)
            return
    def get_elevation(self):

        if ('height' not in self.buildings.columns and self.proc_conf['matching_col'][self.proc_conf['output_columns'].index('height')]
                not in self.buildings.columns):
            #TODO check the functioning of using DSM and DTM and generalize the keys for the height
            self.elevationMap = ElevationMapper(self.buildings)
            crs = self.buildings.crs
            bbox = self.study_area
            self.buildings = self.elevationMap.get_elevation()
            return
        if 'height' not in self.buildings.columns:
            old_name = self.proc_conf['matching_col'][self.proc_conf['output_columns'].index('height')]
            mapper = {old_name: 'height'}
            self.buildings = self.buildings.rename(columns=mapper)            # rename column
            print('Height values are already present with the wrong column name: KEY UPDATED')
            return
        else:
            print('Height values are already present with the correct column name')
            return
    def get_geometrical_values(self):
        for element in ['area','n_floors', 'gross_floor_area','net_leased_area']:
            if (element not in self.buildings.columns and self.proc_conf['matching_col'][
                self.proc_conf['output_columns'].index(element)]
                    not in self.buildings.columns):

                self.buildings = self.Datafilling.geometrical_data(element,self.buildings)
                print('%s values have been calculated'%element)

                continue

            if element not in self.buildings.columns:
                old_name = self.proc_conf['matching_col'][self.proc_conf['output_columns'].index(element)]
                mapper = {old_name: element}
                self.buildings = self.buildings.rename(columns=mapper)  # rename column
                print('%s values are already present with the wrong column name: KEY UPDATED'%element)
                continue

            else:
                print('%s values are already present with the correct column name'%element)
                continue

    def clean_df(self, cut=False, filter=False):
        self.buildings = self.buildings[self.proc_conf['output_columns']]
        if cut :
            self.buildings = self.cut_building_data()
        if filter:
            self.filter()
        #converting formats
        self.buildings= self.buildings.astype({'height': 'float', 'area': 'float','net_leased_area': 'float','gross_floor_area': 'float'})
        self.set_unique_ids()
    def get_year_of_construction(self, autorange=False):
        if autorange!= False:
            self.buildings['year_of_construction'] = ''
            self.buildings['year_of_construction'] =self.buildings['year_of_construction'].apply(lambda x: random.randint(autorange[0],autorange[1]))
            return

        if ('year_of_construction' not in self.buildings.columns and self.proc_conf['matching_col'][
            self.proc_conf['output_columns'].index('year_of_construction')]
                not in self.buildings.columns):
            print('Year_of_construction is not present, it will be statistically estimated with demographi data.')
            return
        if 'year_of_construction' not in self.buildings.columns:
            old_name = self.proc_conf['matching_col'][self.proc_conf['output_columns'].index('year_of_construction')]
            mapper = {old_name: 'year_of_construction'}
            self.buildings = self.buildings.rename(columns=mapper)  # rename column
            print('Year_of_construction values are already present with the wrong column name: KEY UPDATED')
            return
        else:
            print('Year_of_construction values are already present with the correct column name')
            return
    def get_w2w(self):
        self.buildings['w2w']=0.2
    def get_construction_type(self):
        '''strictly related to the year of construction of the buildings, the archetypes that defines the type of construction depends on the year
        it will be added also a distinction on the type of building'''

        def ass(x):
            for i in self.proc_conf['construction_ranges']:
                if x>i[0] and x<=i[1]:
                    return f'{i[0]}_{i[1]}'

        self.buildings['construction_type'] = self.buildings['year_of_construction'].apply(ass)


    def get_tabula_archetype(self):
        #TODO in future for teaser lets use this one enhanced by Finocchiaro thesis
        self.buildings['Tabula_type'] = 'SFH'
        self.buildings['Tabula_id'] = 'SFH_01'

        pass
    def get_hvac_id(self):
        #todo must implement an unique taxonomy to include the hvac type
        self.buildings['hvac_type'] = 'gb'

    def get_demographics (self):
        #NO user inputs for now only from istat data
        #TODO generalize the demographic assignation
        df = self.check_coordinates(self.inputs['census_zone'])
        df = df[[self.proc_conf['matching_col'][
                self.proc_conf['output_columns'].index('sez_cens')], 'geometry']]
        self.buildings = self.buildings.sjoin(df,how='left', predicate='intersects')
        old_name = self.proc_conf['matching_col'][self.proc_conf['output_columns'].index('sez_cens')]
        mapper = {old_name: 'sez_cens'}
        self.buildings = self.buildings.rename(columns=mapper)

        #start_statistical assignation
        self.inputs['census_ind'] = self.inputs['census_ind'].loc[self.inputs['census_ind']['SEZ2011'].isin(self.inputs['census_zone']['SEZ2011'])]
        self.buildings = self.Datafilling.statistical_assignation(self.buildings,self.inputs['census_ind'], self.inputs['census_ind_tracciato'])

    def set_unique_ids(self):
        self.buildings = self.buildings.reset_index()
        self.buildings['b_id'] = self.buildings.apply(lambda i: 'BUI_%s'%i.name, axis=1)
        self.buildings = self.buildings.set_index('b_id')

    def get_shading_surfaces(self, distance = 40):
        #TODO questo andrebbe fatto prima del cleaning perche anche gli edifici non selezionati possono fare ombra
        self.buildings['neighbours_surfaces'] = pd.Series()
        self.buildings['neighbours_vertices'] = pd.Series()
        self.buildings['neighbours_ids'] = pd.Series()
        #need to convert buildings to projected cartesian
        self.buildings = self.buildings.to_crs('EPSG:32632')

        for index, row in self.buildings.iterrows():
            num = int(index.split('_')[-1])
            centroid = row['geometry'].centroid
            buffer = centroid.buffer(distance)
            neigh_list = self.buildings.sindex.query(buffer, predicate= 'contains' )
            neigh_list = np.delete(neigh_list, np.where(neigh_list == num))
            self.buildings.at[index,'neighbours_ids'] = str(neigh_list)
            #ref_x = 500000.0
            #ref_y = 4649776.22
            neigh_vertex = []
            for neigh in neigh_list:
                idx = 'BUI_%s'%neigh
                height = self.buildings.loc[idx,'height']
                geom = self.buildings.loc[idx,'geometry'].exterior.coords.xy
                surfaces = []
                x=geom[0]
                y=geom[1]
                vertex = []
                for i in range(len(geom[0])):
                    vertex.append((x[i], y[i], 0))
                    vertex.append((x[i], y[i], height))
                    #vertex.append([x[i]-ref_x,ref_y-y[i],0])
                    #vertex.append([x[i]-ref_x,ref_y-y[i],height])

                    try:
                        #surf = [(x[i]-ref_x,y[i]-ref_y,0),(x[i+1]-ref_x,y[i+1]-ref_y,0),(x[i+1]-ref_x,y[i+1]-ref_y,height),(x[i]-ref_x,y[i]-ref_y,height)]
                        surf = [(x[i], y[i], 0), (x[i + 1], y[i + 1], 0),
                                (x[i + 1], y[i + 1], height), (x[i], y[i], height)]
                        #surf = MultiPolygon(surf)
                    except IndexError:
                        #surf = [[x[i]-ref_x,y[i]-ref_y,0],[x[0]-ref_x,y[0]-ref_y,0],[x[0]-ref_x,y[0]-ref_y,height],[x[i]-ref_x,y[i]-ref_y,height]]
                        surf = [(x[i],y[i],0),(x[0],y[0],0),(x[0],y[0],height),(x[i],y[i],height)]

                        #surf = MultiPolygon(surf)

                    surfaces.append(Polygon(surf))


                tmp = str(surfaces)
                tmp2 = list(tmp)
                self.buildings.at[index,'neighbours_surfaces']=MultiPolygon(surfaces).wkt
                self.buildings.at[index,'neighbours_vertices']=MultiPoint(vertex).wkt
            #self.buildings['b_id'] = self.buildings['b_id'].astype(str)

        print(geom)




        return
    def cut_building_data (self):
        return self.buildings.clip(self.inputs['cut_area'])
    def filter(self):
        filter_dict = self.proc_conf['filter']
        for key,val in filter_dict.items():
            self.buildings = self.buildings[self.buildings[key].isin(val)]
    def df2geojson(self, path):
        types = self.buildings.dtypes
        self.buildings.to_file(path, driver='GeoJSON')
        #self.buildings.to_file('outcomes/frassinetto_test.csv', driver='CSV')


    def df2shp(self, path):
        types = self.buildings.dtypes
        self.buildings.to_file(path)
    def df2excel(self,path):
        self.buildings.to_excel(path)

if __name__ == '__main__':

    zone = 'Frasssinetto_limitecomunale.shp'
    raw_inputs = {
        'buildings': 'edifici_frassinetto_uso_altezza.geojson',
        'census_zone': 'census_data_Frassinetto.geojson',
        'census_ind': 'R01_indicatori_2011_sezioni.csv',
        'census_ind_tracciato':'tracciato_2011_sezioni.csv',
        'cut_area': 'limite_frassinetto_reduced.geojson',
    }
    proc_conf = '../processing_config.json'
    zone = ZoneSelector(zone,proc_conf,**raw_inputs)
    zone.get_buildings()
    zone.get_destination()
    zone.get_elevation()
    zone.get_geometrical_values()
    zone.get_year_of_construction( autorange=(1800,1949))
    zone.get_demographics()
    zone.clean_df(cut=True,filter=True)
    zone.get_construction_type()
    zone.get_w2w()
    zone.get_shading_surfaces()
    zone.get_hvac_id()
    zone.get_tabula_archetype()
    zone.df2geojson('outcomes/frassinetto_test_low.geojson')
    #zone.df2geojson('outcomes/frassinetto_test.xlsx')

    print('yo')