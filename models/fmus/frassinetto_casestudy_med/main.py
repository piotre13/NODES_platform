from models.Eplus2FMU import Eplus2FMU_single
import os

idf_folderpath = '/home/pietrorm/Documents/CODE/NODES_platform/data/idf/frassinetto_casestudy_med'
config = {
    "idf_file": "/home/pietrorm/Documents/CODE/NODES_platform/data/idf/frassinetto_casestudy/SingleFamilyHouse_2.idf",
    "idd_file": "/usr/local/EnergyPlus-23-1-0/Energy+.idd",
    "weather": "/home/pietrorm/Documents/CODE/NODES_platform/data/meteo_file/meteo_bousson.epw",
    "FMI_v": "2.0",
    "path_conv": "/usr/local/EnergyPlus-23-1-0/energyplusToFMU/Scripts/EnergyPlusToFMU.py"
}
for file in os.listdir(idf_folderpath):
    if file.endswith('.idf'):
        path = os.path.join(idf_folderpath,file)
        config['idf_file'] = path
        Eplus2FMU_single(config)




