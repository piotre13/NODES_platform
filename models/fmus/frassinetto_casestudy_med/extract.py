from models.Eplus2FMU import Eplus2FMU_single
import os
sys.path.insert(0, '..')
from conf import *
idf_folderpath = '../../../data/idf/frassinetto_casestudy_med'
for file in os.listdir(idf_folderpath):
    if file.endswith('.idf'):
        path = os.path.join(idf_folderpath,file)
        config['idf_file'] = path
        Eplus2FMU_single(config)




