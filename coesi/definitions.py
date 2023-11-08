import os
from pathlib import Path


pathroot = os.path.abspath(os.path.dirname(__file__))

PROJECT_ROOT = str(Path(__file__).resolve().parents[1]).replace('\\','/')
SCENARIO_ROOT = os.path.join(PROJECT_ROOT, 'scenarios').replace('\\','/')
UESA_ROOT = os.path.join(PROJECT_ROOT, 'coesi').replace('\\','/')
SIM_ROOT = os.path.join(UESA_ROOT, 'mk_sims').replace('\\','/')
MODELS_ROOT = os.path.join(PROJECT_ROOT, 'models').replace('\\','/')
OUTPUTS_ROOT = os.path.join(PROJECT_ROOT, 'Outputs').replace('\\','/')
TEMP_ROOT = os.path.join(PROJECT_ROOT, 'coesi/resources/temp').replace('\\','/')
RESOURCE_ROOT = os.path.join(PROJECT_ROOT, 'coesi/resources').replace('\\','/')

# Automatically retrive MATLAB folder in Windows system
path = os.environ.get('path')
pathlist = path.split(';')
matlabpath = [s for s in pathlist if all(x in s for x in ['MATLAB','R','bin'])]
matlabpath = matlabpath[0].split('\\')
matlabpath.pop()
MATLABROOT = '\\'.join(matlabpath) + '\\toolbox\\shared\\fmu_share\\script'